from odoo import fields, models


class SolvitaskMaterial(models.Model):
    _name = 'solvitask.material'
    _description = 'Material / Part'

    name = fields.Char(string='Material', required=True)
    unit = fields.Selection(
        string='Unit',
        selection=[('unit', 'Unit'),
                   ('m', 'Meter'),
                   ('kg', 'Kg'),
                   ('l', 'Liter')],
        default='unit',
    )
    unit_price = fields.Float(string='Unit Price', digits=(12, 2))
