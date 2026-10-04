from odoo import fields, models


class SolvitaskCustomer(models.Model):
    _name = 'solvitask.customer'
    _description = 'Customer'
    _inherit = ['solvitask.whatsapp.mixin']

    name = fields.Char(string='Name', required=True)
    surname = fields.Char(string='Surname')
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    address = fields.Char(string='Address')
    birthday = fields.Date(string='Birthday')

    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Related User',
        ondelete='set null',
        help='Portal/internal login belonging to this customer.')

    job_ids = fields.One2many(
        comodel_name='solvitask.job',
        inverse_name='customer_id',
        string='Jobs'
    )
    request_ids = fields.One2many(
        comodel_name="solvitask.requests",
        inverse_name="customer_id",
        string="Requests"
    )
