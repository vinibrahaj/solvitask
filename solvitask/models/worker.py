from odoo import fields, models


class SolvitaskWorker(models.Model):
    _name = 'solvitask.worker'
    _description = 'Worker / Plumber'

    name = fields.Char(string='Name', required=True)
    surname = fields.Char(string='Surname')
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    address = fields.Char(string='Address')

    # Plain boolean. NOTE: don't call this 'active' — that name is reserved by
    # Odoo and would hide (archive) the worker when set to False.
    available = fields.Boolean(string='Available', default=True)

    hourly_rate = fields.Float(string='Hourly Rate', digits=(12, 2))
    payment_method = fields.Selection(
        string='Payment Method',
        selection=[('cash', 'Cash'),
                   ('bank', 'Bank Transfer')],
    )

    # Many workers <-> many services. Creates a hidden link table automatically.
    service_ids = fields.Many2many('solvitask.service', string='Skills / Services')

    # Reverse side of Job.worker_id.
    job_ids = fields.One2many('solvitask.job', 'worker_id', string='Assigned Jobs')
