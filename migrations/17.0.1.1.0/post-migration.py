# -*- coding: utf-8 -*-
"""Department used to be a Selection on the doctor (column `department`).
It is now a Many2one (`department_id`). Copy the old values over to the new
departments, fill the departments of existing appointments, then drop the old column."""

OLD_TO_XMLID = {
    'general_medicine': 'department_general_medicine',
    'pediatrics': 'department_pediatrics',
    'cardiology': 'department_cardiology',
    'dermatology': 'department_dermatology',
    'gynecology': 'department_gynecology',
    'orthopedics': 'department_orthopedics',
    'ophthalmology': 'department_ophthalmology',
    'urology': 'department_urology',
}


def migrate(cr, version):
    cr.execute("""SELECT 1 FROM information_schema.columns
                  WHERE table_name = 'medcare_doctor' AND column_name = 'department'""")
    if cr.fetchone():
        for old, xmlid in OLD_TO_XMLID.items():
            cr.execute("""
                UPDATE medcare_doctor d
                   SET department_id = imd.res_id
                  FROM ir_model_data imd
                 WHERE imd.module = 'medcare' AND imd.name = %s
                   AND d.department = %s AND d.department_id IS NULL
            """, (xmlid, old))
        cr.execute("ALTER TABLE medcare_doctor DROP COLUMN department")

    # appointments created before this version have no department yet
    cr.execute("""
        UPDATE medcare_appointment a
           SET department_id = d.department_id
          FROM medcare_doctor d
         WHERE a.doctor_id = d.id AND a.department_id IS NULL
    """)
