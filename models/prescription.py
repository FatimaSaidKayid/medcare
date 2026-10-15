from odoo import models, fields, api
from odoo.exceptions import ValidationError


class MedcarePrescription(models.Model):
    _name = 'medcare.prescription'
    _description = 'Prescription'
    _inherit = ['mail.thread']
    _order = 'prescription_date desc, id desc'

    def _default_doctor(self):
        """If the logged-in user is a doctor, default to their doctor record."""
        return self.env['medcare.doctor'].search([('user_id', '=', self.env.uid)], limit=1)

    name = fields.Char(string='Prescription Ref', copy=False, readonly=True, default='New')

    # prescription -> Many2one patient (the patient has the One2many back)
    patient_id = fields.Many2one('medcare.patient', string='Patient', required=True,
                                 tracking=True, ondelete='restrict')
    doctor_id = fields.Many2one('medcare.doctor', string='Doctor', required=True,
                                tracking=True, default=_default_doctor, ondelete='restrict')
    # one appointment -> at most one prescription (see SQL constraint below)
    appointment_id = fields.Many2one('medcare.appointment', string='Appointment',
                                     copy=False, ondelete='set null')

    prescription_date = fields.Date(string='Date', required=True,
                                    default=fields.Date.context_today)
    diagnosis = fields.Text(string='Diagnosis')
    line_ids = fields.One2many('medcare.prescription.line', 'prescription_id',
                               string='Medicines', copy=True)
    notes = fields.Text(string='Doctor Notes / Advice')

    _sql_constraints = [
        ('appointment_uniq', 'unique(appointment_id)',
         'This appointment already has a prescription!'),
    ]

    @api.onchange('appointment_id')
    def _onchange_appointment_id(self):
        if self.appointment_id:
            self.patient_id = self.appointment_id.patient_id
            self.doctor_id = self.appointment_id.doctor_id

    @api.constrains('appointment_id', 'patient_id', 'doctor_id')
    def _check_appointment_consistency(self):
        for rec in self:
            appt = rec.appointment_id
            if appt and (appt.patient_id != rec.patient_id or appt.doctor_id != rec.doctor_id):
                raise ValidationError(
                    'The patient and doctor must match the selected appointment.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('medcare.prescription') or 'New'
        return super().create(vals_list)


class MedcarePrescriptionLine(models.Model):
    _name = 'medcare.prescription.line'
    _description = 'Prescription Line'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    prescription_id = fields.Many2one('medcare.prescription', string='Prescription',
                                      required=True, ondelete='cascade')
    medicine = fields.Char(string='Medicine', required=True)
    dosage = fields.Char(string='Dosage', help='e.g. 500 mg, 1 tablet')
    frequency = fields.Char(string='Frequency', help='e.g. 3 times daily')
    duration = fields.Char(string='Duration', help='e.g. 7 days')
    instructions = fields.Char(string='Instructions', help='e.g. after meals')
