from odoo import fields, models, api
from odoo.exceptions import ValidationError


class SolvitaskService(models.Model):
    _name = 'solvitask.service'
    _description = 'Service'

    name = fields.Char(string='Service', required=True)
    # The catalog price for this kind of work. Copied onto a job as its
    # starting price (see job._compute_initial_price).
    unit_price = fields.Float(string='Unit Price', digits=(12, 2), required=True)
    worker_count = fields.Integer(
        string='Workers Required', default=1, required=True,
        help='How many plumbers this kind of job normally needs.')
    description = fields.Text(string='Description')

    # The tools you'd normally bring for this kind of job.
    default_tool_ids = fields.Many2many('solvitask.tool', string='Recommended Tools')

    @api.constrains('worker_count')
    def _check_worker_count(self):
        for service in self:
            if service.worker_count < 1:
                raise ValidationError("A service needs at least one worker.")