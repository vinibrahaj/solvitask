from odoo import fields, models


class SolvitaskJobStage(models.Model):
    _name = 'solvitask.job.stage'
    _description = 'Job Stage'
    _order = 'sequence, id'

    name = fields.Char(string='Stage', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    fold = fields.Boolean(string='Folded in Kanban')

    # These two booleans are what let the Job logic reason about a stage without
    # hard-coding stage names. Editable from the UI, so "our own stages" stays true.
    is_scheduled = fields.Boolean(
        string='Scheduled',
        help='Stage a job moves to automatically once a date is set. '
             'Tick this on exactly one stage.')
    is_started = fields.Boolean(
        string='Work Started',
        help='A job entering this stage must already have a worker and a price.')
    is_done = fields.Boolean(
        string='Job Finished',
        help='Work is complete; the invoice can be generated from this stage on.')