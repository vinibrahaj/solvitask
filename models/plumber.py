from odoo import fields, models, api
from odoo.exceptions import ValidationError


WEEKDAYS = [
    ('0', 'Monday'), ('1', 'Tuesday'),
    ('2', 'Wednesday'), ('3', 'Thursday'),
    ('4', 'Friday'), ('5', 'Saturday'),
    ('6', 'Sunday')
]

PLUMBER_HOURS = [
    (f'{h:02d}:{m:02d}', f'{h:02d}:{m:02d}')
    for h in range(24) for m in (0, 30)
]


class SolvitaskWorker(models.Model):
    _name = 'solvitask.plumber'
    _description = 'Worker / Plumber'

    name = fields.Char(string='Name', required=True)
    surname = fields.Char(string='Surname')
    phone = fields.Char(string='Phone', required=True)
    email = fields.Char(string='Email')
    address = fields.Char(string='Address', required=True)
    balance = fields.Float(string="Balance")

    slot_ids = fields.One2many(
        comodel_name='solvitask.plumber.slot',
        inverse_name='plumber_id',
        string='Weekly Availability'
    )

    hourly_rate = fields.Float(string='Hourly Rate', digits=(12, 2))
    payment_method = fields.Selection(
        string='Payment Method',
        selection=[('cash', 'Cash'), ('bank', 'Bank Transfer')]
    )
    iban = fields.Char(string="IBAN", size=36)

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
        if not self.slot_ids:
            return True
        # Slots are entered in local time; the database stores UTC.
        local = fields.Datetime.context_timestamp(self, dt)
        day = str(local.weekday())                 # Monday = '0'
        hour = local.hour + local.minute / 60.0
        return any(
            slot.day_of_week == day and slot.hour_from <= hour < slot.hour_to
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
            if not 0 <= slot.hour_from < slot.hour_to:
                raise ValidationError(
                    "A time slot must start before it ends")

    @api.constrains('plumber_id', 'day_of_week', 'hour_from', 'hour_to')
    def _check_overlap(self):
        for slot in self:
            overlapping = self.search_count([
                ('id', '!=', slot.id),
                ('plumber_id', '=', slot.plumber_id.id),
                ('day_of_week', '=', slot.day_of_week),
                ('hour_from', '<', slot.hour_to),
                ('hour_to', '>', slot.hour_from),
            ])
            if overlapping:
                raise ValidationError(
                    "This slot overlaps another slot on the same day.")
