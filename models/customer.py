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

    job_count = fields.Integer(string='Job Count', compute='_compute_job_count')

    @api.depends('job_ids')
    def _compute_job_count(self):
        for customer in self:
            customer.job_count = len(customer.job_ids)
