from odoo import fields, models, api


class SolvitaskCustomer(models.Model):
    _name = 'solvitask.customer'
    _description = 'Customer'

    name = fields.Char(string='Name', required=True)
    surname = fields.Char(string='Surname')
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    address = fields.Char(string='Address')
    birthday = fields.Date(string='Birthday')

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
