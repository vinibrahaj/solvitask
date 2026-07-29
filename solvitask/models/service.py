from odoo import fields, models


class SolvitaskService(models.Model):
    _name = 'solvitask.service'
    _description = 'Service'

    name = fields.Char(string='Service', required=True)
    description = fields.Text(string='Description')
    base_price = fields.Float(string='Base Price', digits=(12, 2))

    # The tools you'd normally bring for this kind of job.
    default_tool_ids = fields.Many2many('solvitask.tool', string='Recommended Tools')
