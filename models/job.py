import base64

from odoo import fields, models, api
from odoo.exceptions import ValidationError, UserError


class SolvitaskJob(models.Model):
    _name = 'solvitask.job'
    _description = 'Service Request / Job'
    _order = 'scheduled_date desc, id desc'

    name = fields.Char(string='Reference', compute='_compute_name', store=True)

    customer_id = fields.Many2one('solvitask.customer',
                                  string='Customer',
                                  required=True)
    service_id = fields.Many2one(
        comodel_name='solvitask.service',
        string='Service'
    )
    is_custom = fields.Boolean(string='Custom Request')
    description = fields.Text(string='Problem Description')
    problem_photo = fields.Image(string='Problem Photo')
    service_address = fields.Char(string='Service Address')

    is_cancelled = fields.Boolean(string='Cancelled', default=False)
    request_ids = fields.One2many(
        'solvitask.job.request', 'job_id', string='Change Requests')

    priority = fields.Selection(
        string='Priority',
        selection=[('low', 'Low'),
                   ('normal', 'Normal'),
                   ('high', 'High'),
                   ('emergency', 'Emergency')],
        default='normal',
    )

    # --- assignment / scheduling ---
    worker_ids = fields.Many2many(
        comodel_name='solvitask.worker',
        relation='solvitask_job_worker_relation',
        string='Assigned Plumber'
    )
    scheduled_date = fields.Datetime(string='Scheduled Date')
    tool_ids = fields.Many2many('solvitask.tool', string='Required Tools')

    # --- work done ---
    material_line_ids = fields.One2many(
        'solvitask.job.material', 'job_id', string='Materials Used')
    work_notes = fields.Text(string='Work Notes')
    hours_worked = fields.Float(string='Hours Worked')

    # --- pipeline stage: this is what the kanban board drags between ---
    stage_id = fields.Many2one(
        'solvitask.job.stage', string='Stage',
        default=lambda self: self._default_stage_id(),
        group_expand='_read_group_stage_ids',
    )
    # Related mirror so the form's invoice button can test the stage.
    # A view's invisible="..." can only read fields on THIS record, not dotted
    # paths like stage_id.is_done -- so we pull the flag onto the job.
    stage_is_done = fields.Boolean(related='stage_id.is_done')
    stage_is_started = fields.Boolean(related='stage_id.is_started')

    # How many plumbers this job needs, read off the chosen service.
    # Informational: it tells the scheduler what to plan for.
    workers_required = fields.Integer(
        string='Workers Required', related='service_id.worker_count', readonly=True)

    # --- requests raised against this job (by a customer or a plumber) ---
    request_ids = fields.One2many(
        'solvitask.requests', 'job_id', string='Requests')
    request_count = fields.Integer(
        string='Request Count', compute='_compute_request_count')
    last_request_update = fields.Datetime(
        string='Last Request Approved', readonly=True, copy=False,
        help='Stamped when the manager approves a request tied to this job.')


    # --- money ---
    initial_price = fields.Float(
        string='Initial Price', compute='_compute_initial_price',
        store=True, readonly=False, digits=(12, 2),
        help='Quoted starting price. Prefilled from the service, still editable.')
    labor_cost = fields.Float(string='Labor Cost',
                              compute='_compute_costs', store=True, digits=(12, 2))
    material_cost = fields.Float(string='Material Cost',
                                 compute='_compute_costs', store=True, digits=(12, 2))
    total_price = fields.Float(string='Total Price',
                               compute='_compute_costs', store=True, digits=(12, 2))

    # ---- default stage + kanban column expansion ----
    def _default_stage_id(self):
        # New jobs land in the first stage by sequence.
        return self.env['solvitask.job.stage'].search([], order='sequence', limit=1)

    @api.depends('request_ids')
    def _compute_request_count(self):
        for job in self:
            job.request_count = len(job.request_ids)

    def action_view_requests(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Requests',
            'res_model': 'solvitask.requests',
            'view_mode': 'tree,form',
            'domain': [('job_id', '=', self.id)],
            'context': {
                'default_job_id': self.id,
                'default_source': 'customer',
                'default_customer_id': self.customer_id.id,
            },
        }

    @api.model
    def _read_group_stage_ids(self, stages, domain, *args):
        # Return ALL stages so every column shows on the board, even empty ones.
        # (*args safely absorbs the extra 'order' arg some Odoo versions pass.)
        return stages.search([], order='sequence')

    # ---- computes (the transforms) ----
    @api.depends('service_id', 'customer_id')
    def _compute_name(self):
        for job in self:
            service = job.service_id.name or 'Custom'
            customer = job.customer_id.name or ''
            job.name = f'{service} - {customer}'.strip(' -')

    @api.depends('service_id')
    def _compute_initial_price(self):
        for job in self:
            job.initial_price = job.service_id.unit_price if job.service_id else 0.0

    @api.depends('hours_worked', 'worker_ids.hourly_rate',
                 'material_line_ids.subtotal', 'initial_price', 'is_custom')
    def _compute_costs(self):
        for job in self:
            # Listed services are charged at the catalog price, so no hourly
            # labor. Only a custom job bills time.
            if job.is_custom:
                job.labor_cost = sum(
                    worker.hourly_rate * job.hours_worked
                    for worker in job.worker_ids
                )
            else:
                job.labor_cost = 0.0
            job.material_cost = sum(job.material_line_ids.mapped('subtotal'))
            job.total_price = job.initial_price + job.labor_cost + job.material_cost

    # The kanban board and the status bar both just write stage_id, so this
    # single override blocks moving a job backward from either one.
    def write(self, vals):
        if 'stage_id' in vals:
            new_stage = self.env['solvitask.job.stage'].browse(vals['stage_id'])
            for job in self:
                if job.stage_id and new_stage.sequence < job.stage_id.sequence:
                    raise UserError(
                        "A job can't move backward in the pipeline "
                        "(from '%s' to '%s')." % (job.stage_id.name, new_stage.name))
        return super().write(vals)

    # ==== RULE 1 & 2 =========================================================
    # One constraint guards BOTH the drag-and-drop drop and the status bar click,
    # because both just write stage_id -- and this fires on any such write.
    @api.constrains('stage_id', 'worker_ids', 'total_price')
    def _check_started_requirements(self):
        for job in self:
            if job.stage_id.is_started:
                if not job.worker_ids:                       # RULE 1
                    raise ValidationError(
                        "Assign a worker before starting this job.")
                if job.total_price <= 0:                    # RULE 2
                    raise ValidationError(
                        "Set an initial price before starting this job "
                        "(the total is currently 0).")

    @api.onchange('is_custom')
    def _onchange_is_custom(self):
        if self.is_custom:
            self.service_id=False

    @api.onchange('scheduled_date')
    def _onchange_scheduled_date(self):
        if self.scheduled_date:
            scheduled_stage = self.env['solvitask.job.stage'].search(
                [('is_scheduled', '=', True)],
                order='sequence',
                limit=1
            )
            if scheduled_stage and not (self.stage_id.is_started or self.stage_id.is_done):
                self.stage_id = scheduled_stage

    @api.constrains('is_custom', 'service_id')
    def _check_custom_or_service(self):
        for job in self:
            if job.is_custom and job.service_id:
                raise ValidationError(
                    "A custom request cannot also point to a listed service.")
            if not job.is_custom and not job.service_id:
                raise ValidationError(
                    "Choose a service, or tick 'Custom request' and describe "
                    "the problem.")

    @api.constrains('worker_ids')
    def _check_worker_availability(self):
        for job in self:
            unavailable = job.worker_ids.filtered(lambda w: not w.available)
            if unavailable:
                names = ", ".join(unavailable.mapped('name'))
                raise ValidationError(
                    f"The following worker(s) are not available: {names}"
                )

    # Plumber marks the job as started (moves it to the first "started" stage).
    def action_mark_started(self):
        started_stage = self.env['solvitask.job.stage'].search(
            [('is_started', '=', True)], order='sequence', limit=1)
        for job in self:
            if started_stage:
                job.stage_id = started_stage

    # Cancel the job. Once work has started, only a manager may do this.
    def action_cancel(self):
        for job in self:
            if job.stage_id.is_started and not self.env.user.has_group(
                    'solvitask.group_solvitask_manager'):
                raise ValidationError(
                    "This job has already started. Only a manager can "
                    "cancel it.")
            job.is_cancelled = True

    # Generate invoice:
    def action_generate_invoice(self):
        self.ensure_one()
        # 1) render the QWeb report into raw PDF bytes
        pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf(
            'solvitask.report_job_invoice', self.ids)
        # 2) save those bytes as a PDF file attached to this job (kept on record)
        attachment = self.env['ir.attachment'].create({
            'name': 'Invoice - %s.pdf' % (self.name or self.id),
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),   # bytes -> base64, the stored format
            'res_model': 'solvitask.job',
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })
        # 3) hand that file to the browser as a download
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'new',
        }


class SolvitaskJobMaterial(models.Model):
    _name = 'solvitask.job.material'
    _description = 'Job Material Line'

    job_id = fields.Many2one('solvitask.job', string='Job',
                             required=True, ondelete='cascade')
    material_id = fields.Many2one('solvitask.material', string='Material',
                                  required=True)
    quantity = fields.Float(string='Quantity', default=1.0)
    unit_price = fields.Float(string='Unit Price',
                              related='material_id.unit_price',
                              compute='_compute_unit_price',
                              store=True, digits=(12, 2), readonly=False)
    @api.depends('material_id')
    def _compute_unit_price(self):
        for line in self:
            line.unit_price = line.material_id.unit_price

    subtotal = fields.Float(string='Subtotal',
                            compute='_compute_subtotal', store=True, digits=(12, 2))

    @api.depends('quantity', 'unit_price')  # me kete llogaritet ne cast pa u bere save
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_price
