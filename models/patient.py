from datetime import date
from odoo import models, fields, api


class MedcarePatient(models.Model):
    _name = 'medcare.patient'
    _description = 'Patient'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'name'

    name = fields.Char(string='Full Name', required=True, tracking=True)
    patient_ref = fields.Char(string='Patient ID', copy=False, readonly=True, default='New')
    image_1920 = fields.Image(string='Photo', max_width=1024, max_height=1024)

    phone = fields.Char(string='Phone', required=True)
    email = fields.Char(string='Email')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
    ], string='Gender', required=True)
    date_of_birth = fields.Date(string='Date of Birth', required=True)
    age = fields.Integer(string='Age', compute='_compute_age', store=True)
    blood_type = fields.Selection([
        ('a+', 'A+'), ('a-', 'A-'),
        ('b+', 'B+'), ('b-', 'B-'),
        ('ab+', 'AB+'), ('ab-', 'AB-'),
        ('o+', 'O+'), ('o-', 'O-'),
    ], string='Blood Type')

    partner_id = fields.Many2one('res.partner', string='Patient', copy=False, readonly=True)


    # Address information
    street = fields.Char(string='Street')
    city = fields.Char(string='City')
    country_id = fields.Many2one('res.country', string='Country')
    postal_code = fields.Char(string='Postal Code')

    # Medical history
    allergies = fields.Char(string='Allergies')
    chronic_diseases = fields.Text(string='Chronic Diseases')
    notes = fields.Text(string='Additional Notes')

    active = fields.Boolean(default=True)
    status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ], string='Status', default='active')

    last_visit_date = fields.Date(string='Last Appointment', compute='_compute_last_visit', store=True)

    appointment_ids = fields.One2many('medcare.appointment', 'patient_id', string='Appointments')
    appointment_count = fields.Integer(compute='_compute_counts', string='Appointments Count')

    # Login user of this patient -> a patient user sees only his own prescriptions
    user_id = fields.Many2one('res.users', string='Related User', copy=False,
                              help='The login user of this patient. Used to show the patient '
                                   'only his own prescriptions.')

    # patient -> many prescriptions (a doctor only gets to see his own, via record rules)
    prescription_ids = fields.One2many('medcare.prescription', 'patient_id', string='Prescriptions')
    prescription_count = fields.Integer(compute='_compute_prescription_count', string='Prescriptions Count')

    _sql_constraints = [
        ('patient_ref_uniq', 'unique(patient_ref)', 'Patient ID must be unique!'),
        ('user_uniq', 'unique(user_id)', 'This user is already linked to another patient!'),
    ]

    @api.depends('date_of_birth')
    def _compute_age(self):
        for rec in self:
            if rec.date_of_birth:
                today = date.today()
                dob = rec.date_of_birth
                rec.age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            else:
                rec.age = 0

    @api.depends('appointment_ids.appointment_date')
    def _compute_last_visit(self):
        for rec in self:
            appts = rec.sudo().appointment_ids.sorted('appointment_date', reverse=True)
            rec.last_visit_date = appts[0].appointment_date if appts else False

    def _compute_counts(self):
        for rec in self:
            rec.appointment_count = len(rec.appointment_ids)

    def _compute_prescription_count(self):
        # separate from _compute_counts so users without prescription access
        # (e.g. receptionist) never trigger it
        for rec in self:
            rec.prescription_count = len(rec.prescription_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('patient_ref', 'New') == 'New':
                vals['patient_ref'] = self.env['ir.sequence'].next_by_code('medcare.patient') or 'New'
        return super().create(vals_list)

    def name_get(self):
        result = []
        for rec in self:
            name = f"[{rec.patient_ref}] {rec.name}" if rec.patient_ref else rec.name
            result.append((rec.id, name))
        return result

    def action_view_appointments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Appointments',
            'res_model': 'medcare.appointment',
            'view_mode': 'tree,form,calendar',
            'domain': [('patient_id', '=', self.id)],
            'context': {'default_patient_id': self.id},
        }

    def action_view_prescriptions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Prescriptions',
            'res_model': 'medcare.prescription',
            'view_mode': 'tree,form',
            'domain': [('patient_id', '=', self.id)],
            'context': {'default_patient_id': self.id},
        }

    def _get_or_create_partner(self):
        """Return this patient's linked Contact (res.partner), creating one
        from the patient's own data the first time it's needed (e.g. when an
        invoice is generated for one of their appointments)."""
        self.ensure_one()
        if self.partner_id:
            return self.partner_id
        partner = self.env['res.partner'].create({
            'name': self.name,
            'phone': self.phone,
            'email': self.email,
            'street': self.street,
            'city': self.city,
            'country_id': self.country_id.id if self.country_id else False,
            'zip': self.postal_code,
        })
        self.partner_id = partner.id
        return partner
