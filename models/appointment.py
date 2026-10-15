from datetime import timedelta
from odoo import models, fields, api


class MedcareAppointment(models.Model):
    _name = 'medcare.appointment'
    _description = 'Appointment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'appointment_date desc, appointment_time'

    name = fields.Char(string='Appointment Ref', copy=False, readonly=True, default='New')

    patient_id = fields.Many2one('medcare.patient', string='Patient', required=True, tracking=True)
    # Department is chosen first to narrow the doctor list; picking a doctor fills it in
    department_id = fields.Many2one('medcare.department', string='Department',
                                    compute='_compute_department_id', store=True, readonly=False)
    doctor_id = fields.Many2one('medcare.doctor', string='Doctor', required=True, tracking=True)

    appointment_date = fields.Date(string='Appointment Date', required=True, default=fields.Date.context_today)
    appointment_time = fields.Float(string='Appointment Time (hour)', required=True)
    start_datetime = fields.Datetime(string='Start', compute='_compute_start_datetime', store=True)
    stop_datetime = fields.Datetime(string='End', compute='_compute_start_datetime', store=True)

    reason = fields.Char(string='Reason for Visit', required=True)
    appointment_type = fields.Selection([
        ('general_consultation', 'General Consultation'),
        ('follow_up', 'Follow Up'),
        ('initial_consultation', 'Initial Consultation'),
        ('consultation', 'Consultation'),
        ('checkup', 'General Checkup'),
        ('other', 'Other'),
    ], string='Appointment Type', default='general_consultation')

    duration = fields.Integer(string='Duration (minutes)', default=30)
    location = fields.Selection([
        ('clinic', 'Clinic'),
        ('online', 'Online'),
        ('home', 'Home Visit'),
    ], string='Location', default='clinic')

    status = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('in_consultation', 'In Consultation'),
        ('completed', 'Completed'),
        ('pending', 'Pending'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='scheduled', tracking=True)

    notes = fields.Text(string='Notes')
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

    account_move_id = fields.Many2one('account.move', string='Invoice', copy=False, readonly=True)

    # one appointment -> one prescription (enforced by SQL constraint on the prescription)
    prescription_ids = fields.One2many('medcare.prescription', 'appointment_id', string='Prescriptions')
    prescription_count = fields.Integer(compute='_compute_prescription_count')

    @api.depends('doctor_id')
    def _compute_department_id(self):
        for rec in self:
            if rec.doctor_id:
                rec.department_id = rec.doctor_id.department_id

    @api.onchange('department_id')
    def _onchange_department_id(self):
        if self.doctor_id and self.department_id and self.doctor_id.department_id != self.department_id:
            self.doctor_id = False

    @api.depends('prescription_ids')
    def _compute_prescription_count(self):
        for rec in self:
            rec.prescription_count = len(rec.sudo().prescription_ids)

    def action_view_prescription(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Prescription',
            'res_model': 'medcare.prescription',
            'view_mode': 'form',
            'res_id': self.prescription_ids[:1].id,
        }

    @api.depends('appointment_date', 'appointment_time', 'duration')
    def _compute_start_datetime(self):
        for rec in self:
            if rec.appointment_date:
                hour = int(rec.appointment_time or 0)
                minute = int(round((rec.appointment_time or 0) % 1 * 60))
                start = fields.Datetime.to_datetime(rec.appointment_date)
                start = start.replace(hour=hour, minute=minute)
                rec.start_datetime = start
                rec.stop_datetime = start + timedelta(minutes=rec.duration or 30)
            else:
                rec.start_datetime = False
                rec.stop_datetime = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('medcare.appointment') or 'New'
        return super().create(vals_list)

    def action_confirm(self):
        self.write({'status': 'confirmed'})
        for rec in self:
            rec._create_account_invoice()

    def _create_account_invoice(self):
        """Register a customer invoice in Invoicing/Accounting for this
        appointment, automatically, the first time it's confirmed."""
        self.ensure_one()
        if self.account_move_id:
            return self.account_move_id
        partner = self.patient_id._get_or_create_partner()
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'doctor_id': self.doctor_id.id,
            'invoice_date': fields.Date.context_today(self),
            'ref': self.name,
            'invoice_line_ids': [(0, 0, {
                'name': self.reason or 'Consultation',
                'quantity': 1,
                'price_unit': self.doctor_id.consultation_fee or 0.0,
            })],
        })
        self.account_move_id = move.id
        return move

    def action_view_invoice(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.account_move_id.id,
        }

    def action_start_consultation(self):
        self.write({'status': 'in_consultation'})

    def action_complete(self):
        self.write({'status': 'completed'})

    def action_cancel(self):
        self.write({'status': 'cancelled'})
