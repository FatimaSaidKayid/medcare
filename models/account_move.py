from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    doctor_id = fields.Many2one('medcare.doctor', string='Doctor', copy=False, readonly=True)
