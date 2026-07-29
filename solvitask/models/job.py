import base64

from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError


class SolvitaskJob(models.Model):
    _name = 'solvitask.job'
    _description = 'Service Request / Job'
    _order = 'scheduled_date desc, id desc'

    name = fields.Char(string='Reference', compute='_compute_name', store=True)

    # --- who / what ---
    customer_id = fields.Many2one('solvitask.customer', string='Customer', required=True)
    service_id = fields.Many2one('solvitask.service', string='Service')
    is_custom = fields.Boolean(string='Custom Request')
    description = fields.Text(string='Problem Description')
    problem_photo = fields.Image(string='Problem Photo')

    priority = fields.Selection(
        string='Priority',
        selection=[('emergency', 'Emergency'),
                   ('high', 'High'),
                   ('normal', 'Normal'),
                   ('low', 'Low')],
        default='normal',
    )

    # --- assignment / scheduling ---
    worker_id = fields.Many2one('solvitask.worker', string='Assigned Plumber')
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
            if job.service_id:
                # Transform: catalog base price -> this job's starting price.
                job.initial_price = job.service_id.base_price

    @api.depends('hours_worked', 'worker_id.hourly_rate',
                 'material_line_ids.subtotal', 'initial_price')
    def _compute_costs(self):
        for job in self:
            job.labor_cost = job.hours_worked * job.worker_id.hourly_rate
            job.material_cost = sum(job.material_line_ids.mapped('subtotal'))
            job.total_price = job.initial_price + job.labor_cost + job.material_cost

    # ==== RULE 1 & 2 =========================================================
    # One constraint guards BOTH the drag-and-drop drop and the status bar click,
    # because both just write stage_id -- and this fires on any such write.
    @api.constrains('stage_id', 'worker_id', 'total_price')
    def _check_started_requirements(self):
        for job in self:
            if job.stage_id.is_started:
                if not job.worker_id:                       # RULE 1
                    raise ValidationError(
                        "Assign a worker before starting this job.")
                if job.total_price <= 0:                    # RULE 2
                    raise ValidationError(
                        "Set an initial price before starting this job "
                        "(the total is currently 0).")

    # ==== RULE 3 =============================================================
    def action_generate_invoice(self):
        self.ensure_one()
        if not self.customer_id.email:
            raise UserError("This customer has no email address on file.")
        # 1) render the QWeb report into raw PDF bytes
        pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf(
            'solvitask.report_job_invoice', self.ids)
        # 2) save those bytes as a file attached to this job
        attachment = self.env['ir.attachment'].create({
            'name': 'Invoice - %s.pdf' % (self.name or self.id),
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),   # bytes -> base64, the DB format
            'res_model': 'solvitask.job',
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })
        # 3) create and send the email carrying that attachment
        self.env['mail.mail'].create({
            'subject': 'Invoice for %s' % (self.name or ''),
            'email_to': self.customer_id.email,
            'body_html': '<p>Dear %s,</p><p>Please find your invoice attached.</p>'
                         % (self.customer_id.name or 'customer'),
            'attachment_ids': [(6, 0, attachment.ids)],
        }).send()
        return True


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
                              store=True, digits=(12, 2))
    subtotal = fields.Float(string='Subtotal',
                            compute='_compute_subtotal', store=True, digits=(12, 2))

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_price
