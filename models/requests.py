from odoo import fields, models, api
from odoo.exceptions import ValidationError


class SolvitaskRequests(models.Model):
    _name = 'solvitask.requests'
    _description = 'Request from a customer or plumber to the manager'
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Title', required=True)
    description = fields.Text(string='Description')

    request_type = fields.Selection(
        string='Type',
        selection=[
            ('time', 'Time / reschedule adjustment'),
            ('custom', 'Diagnose as custom job'),
            ('materials', 'Extra materials needed'),
            ('scope_price', 'Scope / price adjustment'),
            ('cancel', 'Cancellation request'),
            ('other', 'Other'),
        ],
        default='other',
        required=True,
    )

    job_id = fields.Many2one('solvitask.job', string='Job',
                             required=True, ondelete='cascade')

    # --- who raised it ---
    source = fields.Selection(
        string='From',
        selection=[('customer', 'Customer'), ('plumber', 'Plumber')],
        required=True,
    )
    customer_id = fields.Many2one('solvitask.customer', string='Customer')
    plumber_id = fields.Many2one('solvitask.plumber', string='Plumber')

    # --- workflow ---
    state = fields.Selection(
        string='Status',
        selection=[
            ('draft', 'New'),
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        default='draft',
        required=True,
    )
    manager_note = fields.Text(
        string='Manager Note',
        help='What the manager decided or changed on the job.')
    decision_date = fields.Datetime(string='Decision Date', readonly=True,
                                    copy=False)

    @api.onchange('job_id')
    def _onchange_job_id(self):
        # Prefill the customer from the job when the request is from a customer.
        if self.job_id and self.source == 'customer' and not self.customer_id:
            self.customer_id = self.job_id.customer_id

    @api.onchange('source')
    def _onchange_source(self):
        if self.source == 'customer':
            self.plumber_id = False
        elif self.source == 'plumber':
            self.customer_id = False

    @api.constrains('source', 'customer_id', 'plumber_id')
    def _check_source_party(self):
        for req in self:
            if req.source == 'customer' and not req.customer_id:
                raise ValidationError(
                    "Select the customer this request comes from.")
            if req.source == 'plumber' and not req.plumber_id:
                raise ValidationError(
                    "Select the plumber this request comes from.")

    # --- buttons: the manager still edits the job by hand; these just record
    #     the decision and stamp the job so it shows as freshly updated. ---
    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_approve(self):
        for req in self:
            req.state = 'approved'
            req.decision_date = fields.Datetime.now()
            req.job_id.last_request_update = req.decision_date

    def action_reject(self):
        for req in self:
            req.state = 'rejected'
            req.decision_date = fields.Datetime.now()

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})
