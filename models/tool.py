from odoo import fields, models


class SolvitaskTool(models.Model):
    _name = 'solvitask.tool'
    _description = 'Tool'

    name = fields.Char(string='Tool', required=True)
    description = fields.Char(string='Description')
