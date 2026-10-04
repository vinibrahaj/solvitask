from odoo import fields, models, api
from odoo.exceptions import ValidationError


PLUMBER_HOURS = [
    (f'{h:02d}:{m:02d}', f'{h:02d}:{m:02d}')
    for h in range(24) for m in (0, 30)
]


class SolvitaskWeekdays(models.model):
    _name = 'solvitask.weekday'
    _description = 'Week Day'
    _order = 'sequence'
 
    name = fields.Char(string='Day', required=True)
    # 0 = Monday, so it lines up with python's date.weekday()
    sequence = fields.Integer(string='Sequence', required=True)
 
    _sql_constraints = [
        ('uniq_sequence', 'unique(sequence)',
         'Two week days cannot share the same sequence.'),
    ]


class SolvitaskPlumber(models.Model):
    _name = 'solvitask.plumber'
    _description = 'Worker / Plumber'
    _inherit = ['solvitask.whatsapp.mixin']

    # visitble to everyone
    name = fields.Char(string='Name', required=True)
    surname = fields.Char(string='Surname')
    phone = fields.Char(string='Phone', required=True)

    # invisible for customers
    email = fields.Char(string='Email', groups='!solvitask.group_solvitask_customer')
    address = fields.Char(
        string='Address',
        required=True,
        groups='!solvitask.group_solvitask_customer'
    )
    balance = fields.Float(
        string="Balance",
        readonly=True,
        groups='!solvitask.group_solvitask_customer'
    )

    slot_ids = fields.One2many(
        comodel_name='solvitask.plumber.slot',
        inverse_name='plumber_id',
        string='Weekly Availability'
    )

    hourly_rate = fields.Float(
        string='Hourly Rate', digits=(12, 2)
    )
    payment_method = fields.Selection(
        string='Payment Method',
        selection=[('cash', 'Cash'), ('bank', 'Bank Transfer')],
        groups='!solvitask.group_solvitask_customer'
    )
    iban = fields.Char(
        string="IBAN",
        size=36,
        groups='!solvitask.group_solvitask_customer'
    )

    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Related User',
        ondelete='set null',
        groups='solvitask.group_solvitask_plumber',
        help='Login belonging to this plumber.'
    )
    # Many workers <-> many services. Creates a hidden link table automatically.
    service_ids = fields.Many2many(
        comodel_name='solvitask.service',
        string='Skills / Services')

    job_ids = fields.Many2many(
        'solvitask.job',
        relation='solvitask_job_plumber_relation',
        string='Assigned Jobs'
    )
    request_ids = fields.One2many(
        comodel_name='solvitask.requests',
        inverse_name='plumber_id',
        string="Requests"
    )

    def is_available_at(self, dt):
        """True if this plumber has a slot covering dt (a UTC datetime).

        A plumber with no slots at all is treated as unrestricted.
        """
        self.ensure_one()

        plumber = self.sudo()
        if not plumber.slot_ids:
            return True
        # Slots are entered in local time; the database stores UTC.
        local = fields.Datetime.context_timestamp(self, dt)
        day = str(local.weekday())                 # Monday = '0'
        now = f'{local.hour:02d}:{local.minute:02d}'
        return any(
            slot.day_of_week == day and slot.hour_from <= now < slot.hour_to
            for slot in self.slot_ids
        )

class SolvitaskPlumberSlot(models.Model):
    _name = 'solvitask.plumber.slot'
    _description = 'Plumber Weekly Time Slot'
    _order = 'day_of_week, hour_from'

    plumber_id = fields.Many2one(
        comodel_name='solvitask.plumber',
        string='Plumber',
        required=True, ondelete='cascade'
    )
    day_of_week = fields.Selection(WEEKDAYS, string='Day', required=True)
    hour_from = fields.Selection(PLUMBER_HOURS, string='From', required=True,
                                default='08:00')
    hour_to = fields.Selection(PLUMBER_HOURS, string='To', required=True,
                              default='16:00')

    @api.constrains('hour_from', 'hour_to')
    def _check_hours(self):
        for slot in self:
            if slot.hour_from >= slot.hour_to:
                raise ValidationError(
                    "A time slot must start before it ends")
