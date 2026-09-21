from odoo import fields, models


class SolvitaskWorker(models.Model):
    _name = 'solvitask.plumber'
    _description = 'Worker / Plumber'

    name = fields.Char(string='Name', required=True)
    surname = fields.Char(string='Surname')
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    address = fields.Char(string='Address')


    available = fields.Boolean(string='Available', default=True)

    hourly_rate = fields.Float(string='Hourly Rate', digits=(12, 2))
    payment_method = fields.Selection(
        string='Payment Method',
        selection=[('cash', 'Cash'),
                   ('bank', 'Bank Transfer')],
    )

    # Many workers <-> many services. Creates a hidden link table automatically.
    service_ids = fields.Many2many('solvitask.service', string='Skills / Services')

    job_ids = fields.Many2many(
        'solvitask.job',
        relation='solvitask_job_worker_relation',
        string='Assigned Jobs'
    )
    request_ids = fields.One2many(
        comodel_name='solvitask.requests',
        inverse_name='worker_id',
        string="Requests"
    )

