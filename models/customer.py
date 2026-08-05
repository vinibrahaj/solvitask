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

    # Reverse side of Job.customer_id. This field is NOT a column in the DB;
    # Odoo fills it by finding every solvitask.job whose customer_id points here.
    job_ids = fields.One2many('solvitask.job', 'customer_id', string='Jobs')

    # Derived value (does not live in the DB unless store=True).
    job_count = fields.Integer(string='Job Count', compute='_compute_job_count')

    @api.depends('job_ids')
    def _compute_job_count(self):
        for customer in self:
            # THE transform: a recordset of jobs -> its length (an int).
            customer.job_count = len(customer.job_ids)
