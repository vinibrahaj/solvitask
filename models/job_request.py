from odoo import fields, models, api
from odoo.exceptions import ValidationError


class SolvitaskJobRequest(models.Model):
    _name = 'solvitask.job.request'
    _description = 'Job Change Request'
    _order = 'id desc'

    name = fields.Char(string='Request', compute='_compute_name')

    job_id = fields.Many2one('solvitask.job', string='Job',
                             required=True, ondelete='cascade')

    request_type = fields.Selection(
        string='Request Type',
        selection=[('reschedule', 'Change Schedule'),
                   ('address', 'Change Address'),
                   ('cancel', 'Cancel Job'),
                   ('other', 'Other')],
        required=True, default='reschedule',
    )
    requested_by = fields.Selection(
        string='Requested By',
        selection=[('customer', 'Customer'),
                   ('worker', 'Plumber')],
        required=True, default='customer',
    )

    new_scheduled_date = fields.Datetime(string='New Scheduled Date')
    new_address = fields.Char(string='New Service Address')
    note = fields.Text(string='Note')

    state = fields.Selection(
        string='Status',
        selection=[('draft', 'New'),
                   ('approved', 'Approved'),
                   ('rejected', 'Rejected')],
        default='draft',
    )

    @api.depends('request_type', 'job_id.name')
    def _compute_name(self):
        request_types = dict(self._fields['request_type'].selection)
        for rec in self:
            rec.name = f"{request_types.get(rec.request_type, '')} - {rec.job_id.name or ''}"

    def action_approve(self):
        for rec in self:
            job = rec.job_id

            if rec.request_type == 'cancel':
                job.action_cancel()
            else:
                # RULE: everything except cancelling requires the job to not
                # have started yet. Cancelling after start is handled (and
                # restricted to managers) inside job.action_cancel().
                if job.stage_id.is_started:
                    raise ValidationError(
                        "This job has already started. It can no longer be "
                        "rescheduled or edited; it can only be cancelled by "
                        "a manager.")

                if rec.request_type == 'reschedule':
                    if not rec.new_scheduled_date:
                        raise ValidationError(
                            "Set a new scheduled date before approving.")
                    job.scheduled_date = rec.new_scheduled_date

                elif rec.request_type == 'address':
                    if not rec.new_address:
                        raise ValidationError(
                            "Set a new address before approving.")
                    job.service_address = rec.new_address

            rec.state = 'approved'

    def action_reject(self):
        self.write({'state': 'rejected'})
