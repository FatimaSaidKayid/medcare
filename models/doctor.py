from odoo import models, fields, api


class MedcareDoctor(models.Model):
    _name = 'medcare.doctor'
    _description = 'Doctor'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'name'

    name = fields.Char(string='Full Name', required=True, tracking=True)
    doctor_ref = fields.Char(string='Doctor ID', copy=False, readonly=True, default='New')
    image_1920 = fields.Image(string='Photo', max_width=1024, max_height=1024)

    phone = fields.Char(string='Phone', required=True)
    email = fields.Char(string='Email', required=True)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
    ], string='Gender', required=True)
    date_of_birth = fields.Date(string='Date of Birth')
    experience_years = fields.Integer(string='Experience (Years)')

    specialty = fields.Selection([
        ('general', 'General Practitioner'),
        ('cardiologist', 'Cardiologist'),
        ('pediatrician', 'Pediatrician'),
        ('dermatologist', 'Dermatologist'),
        ('gynecologist', 'Gynecologist'),
        ('orthopedic', 'Orthopedic'),
        ('ophthalmologist', 'Ophthalmologist'),
        ('urologist', 'Urologist'),
        ('other', 'Other'),
    ], string='Specialty', required=True)

    qualification = fields.Selection([
        ('mbbs', 'MBBS'),
        ('md', 'MD'),
        ('phd', 'PhD'),
        ('ms', 'MS'),
        ('other', 'Other'),
    ], string='Qualification')

    # Many doctors -> one department (department.doctor_ids is the One2many side)
    department_id = fields.Many2one('medcare.department', string='Department',
                                    tracking=True, ondelete='restrict')
    # Link the doctor record to a login user, so a doctor sees only his own data
    user_id = fields.Many2one('res.users', string='Related User', copy=False,
                              help='The login user of this doctor. Used to show the doctor '
                                   'only his own patients, appointments and prescriptions.')

    consultation_fee = fields.Float(string='Consultation Fee')
    license_number = fields.Char(string='License Number')
    notes = fields.Text(string='Notes')
    brief_about = fields.Text(string='Brief About')

    status = fields.Selection([
        ('active', 'Active'),
        ('on_leave', 'On Leave'),
        ('inactive', 'Inactive'),
    ], string='Status', default='active', tracking=True)

    partner_id = fields.Many2one('res.partner', string='Doctor', copy=False, readonly=True)


    # Address
    street = fields.Char(string='Street')
    city = fields.Char(string='City')
    country_id = fields.Many2one('res.country', string='Country')

    appointment_ids = fields.One2many('medcare.appointment', 'doctor_id', string='Appointments')
    prescription_ids = fields.One2many('medcare.prescription', 'doctor_id', string='Prescriptions')
    appointment_count = fields.Integer(compute='_compute_counts')
    today_appointment_count = fields.Integer(compute='_compute_counts')

    _sql_constraints = [
        ('doctor_ref_uniq', 'unique(doctor_ref)', 'Doctor ID must be unique!'),
        ('user_uniq', 'unique(user_id)', 'This user is already linked to another doctor!'),
    ]

    def _compute_counts(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.appointment_count = len(rec.appointment_ids)
            rec.today_appointment_count = len(rec.appointment_ids.filtered(
                lambda a: a.appointment_date == today))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('doctor_ref', 'New') == 'New':
                vals['doctor_ref'] = self.env['ir.sequence'].next_by_code('medcare.doctor') or 'New'
        return super().create(vals_list)

    def name_get(self):
        result = []
        for rec in self:
            name = f"Dr. {rec.name}" if not rec.name.lower().startswith('dr') else rec.name
            result.append((rec.id, name))
        return result

    def action_view_appointments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Appointments',
            'res_model': 'medcare.appointment',
            'view_mode': 'tree,form,calendar',
            'domain': [('doctor_id', '=', self.id)],
            'context': {'default_doctor_id': self.id},
        }


    def _get_or_create_partner(self):
        """Return this doctor's linked Contact (res.partner), creating one
        from the doctor's own data the first time it's needed (e.g. when an
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
        })
        self.partner_id = partner.id
        return partner
