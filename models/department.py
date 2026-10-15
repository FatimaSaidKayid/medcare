from odoo import models, fields, api


class MedcareDepartment(models.Model):
    _name = 'medcare.department'
    _description = 'Department'
    _order = 'name'

    name = fields.Char(string='Department', required=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)

    # One department -> many doctors
    doctor_ids = fields.One2many('medcare.doctor', 'department_id', string='Doctors')
    doctor_count = fields.Integer(string='Doctors', compute='_compute_doctor_count')

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Department name must be unique!'),
    ]

    @api.depends('doctor_ids')
    def _compute_doctor_count(self):
        for rec in self:
            rec.doctor_count = len(rec.doctor_ids)

    def action_view_doctors(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Doctors',
            'res_model': 'medcare.doctor',
            'view_mode': 'tree,form',
            'domain': [('department_id', '=', self.id)],
            'context': {'default_department_id': self.id},
        }
