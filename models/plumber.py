from odoo import fields, models, api
from odoo.exceptions import ValidationError


WEEKDAYS = [
    ('0', 'Monday'), ('1', 'Tuesday'),
    ('2', 'Wednesday'), ('3', 'Thursday'),
    ('4', 'Friday'), ('5', 'Saturday'),
    ('6', 'Sunday'),
]
PLUMBER_HOURS = [
    (f'{h:02d}:{m:02d}', f'{h:02d}:{m:02d}')
    for h in range(24) for m in (0, 30)
]
DEFAULT_FROM = '08:00'
DEFAULT_TO = '16:00'


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
        groups='!solvitask.group_solvitask_customer'
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Give every new plumber the full week, Monday to Sunday.
        """
        plumbers = super().create(vals_list)
        plumbers._ensure_week()
        return plumbers

    def _ensure_week(self):
        slot_model = self.env['solvitask.plumber.slot'].sudo()
        for plumber in self:
            existing = plumber.sudo().slot_ids.mapped('day_of_week')
            missing = [day for day, _label in WEEKDAYS if day not in existing]
            if missing:
                slot_model.create([{
                    'plumber_id': plumber.id,
                    'day_of_week': day,
                } for day in missing])

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
        slot = plumber.slot_ids.filtered(lambda s: s.day_of_week == day)
        if not slot or slot.day_off:
            return False
        return slot.hour_from <= now < slot.hour_to

class SolvitaskPlumberSlot(models.Model):
    _name = 'solvitask.plumber.slot'
    _description = 'Plumber Weekly Time Slot'
    _order = 'day_id, hour_from'

    plumber_id = fields.Many2one(
        comodel_name='solvitask.plumber',
        string='Plumber',
        required=True, ondelete='cascade'
    )
    day_of_week = fields.Selection(
        WEEKDAYS, string='Day', required=True, readonly=True)
 
    day_off = fields.Boolean(
        string='Absent',
        help='Tick it and the hours beside it are ignored for this day.')
 
    hour_from = fields.Selection(
        PLUMBER_HOURS, string='From', required=True, default=DEFAULT_FROM)
    hour_to = fields.Selection(
        PLUMBER_HOURS, string='To', required=True, default=DEFAULT_TO)

    available_day_ids = fields.Many2many(
        comodel_name='solvitask.weekday',
        string='Selectable Days',
        compute='_compute_available_day_ids')

    _sql_constraints = [
        ('uniq_plumber_day', 'unique(plumber_id, day_id)',
         'This plumber already has a time frame for that day.'),
    ]


    _sql_constraints = [
        ('uniq_plumber_day', 'unique(plumber_id, day_of_week)',
         'This plumber already has a time frame for that day.'),
    ]

    @api.onchange('day_off')
    def _onchange_day_off(self):
        if self.day_off:
            self.hour_from = DEFAULT_FROM
            self.hour_to = DEFAULT_TO
 
    @api.constrains('day_off', 'hour_from', 'hour_to')
    def _check_hours(self):
        for slot in self:
            if slot.day_off:
                continue
            if slot.hour_from >= slot.hour_to:
                raise ValidationError(
                    "A time slot must start before it ends.")
