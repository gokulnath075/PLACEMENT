import os
import tempfile
import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from placement_app.models import Department, Student, Company, PlacementDrive, InterviewRecord
from placement_app.services.pdf_service import generate_selection_report_pdf
from placement_app.services.excel_service import export_students_to_excel, import_students_from_excel

class PlacementSystemTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.dept = Department.objects.create(code='DME', name='Department of Mechanical Engineering')
        self.user = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        self.client.login(username='admin', password='admin123')

        self.student = Student.objects.create(
            register_number='24213946',
            name='AKILA DEEPAN S S',
            department=self.dept,
            batch='2024-2027',
            email='akila@example.com',
            student_mobile='9876543210',
            parent_mobile='9443311223',
            dob=datetime.date(2005, 4, 15),
            aadhar_number='123456789012',
            sem1_perc=80.0,
            sem2_perc=85.0,
            sem3_perc=82.0,
            sem4_perc=88.0,
            sem5_perc=90.0,
            sem6_perc=86.0,
            x_perc=85.0,
            xii_perc=88.0,
            no_of_arrears=0
        )

        self.company = Company.objects.create(
            company_id='HYUNDAI-01',
            name='HYUNDAI',
            salary_ctc='2.80 LPA',
            job_role='Diploma Trainee',
            drive_date=datetime.date(2026, 9, 7)
        )
        self.company.eligible_departments.add(self.dept)

        self.drive = PlacementDrive.objects.create(
            company=self.company,
            title='Hyundai Drive',
            drive_date=datetime.date(2026, 9, 7),
            salary_ctc='2.80 LPA'
        )

        self.record = InterviewRecord.objects.create(
            student=self.student,
            drive=self.drive,
            company=self.company,
            interview_attended=True,
            aptitude='PASS',
            technical='PASS',
            hr='PASS',
            final_result='SELECTED',
            salary='2.80 LPA'
        )

    def test_dashboard_access(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'PLACEMENT DASHBOARD')

    def test_student_list_and_filter(self):
        response = self.client.get(reverse('student_list') + '?department=DME&arrears=no&min_perc=60')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '24213946')

    def test_student_detail_profile(self):
        response = self.client.get(reverse('student_detail', kwargs={'pk': self.student.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'AKILA DEEPAN S S')
        self.assertContains(response, 'HYUNDAI')

    def test_selection_report_generation(self):
        response = self.client.get(reverse('selection_report') + f'?company={self.company.pk}&department=DME')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'SHREE VENKATESHWARA HI-TECH POLYTECHNIC COLLEGE')
        self.assertContains(response, 'TRAINING AND PLACEMENT CELL')
        self.assertContains(response, 'SALARY :')
        self.assertContains(response, '24213946')

    def test_pdf_report_service(self):
        records = InterviewRecord.objects.filter(company=self.company, final_result='SELECTED')
        pdf_bytes = generate_selection_report_pdf(
            records=records,
            company_name=self.company.name,
            salary=self.company.salary_ctc,
            drive_date='07-09-2026',
            department_code='DME'
        )
        self.assertTrue(len(pdf_bytes) > 0)
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))

    def test_excel_export_and_import_value_alignment(self):
        # Test that exporting to Excel and importing it back preserves exact field alignments
        students = Student.objects.all()
        wb = export_students_to_excel(students)

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            tmp_path = tmp.name
            wb.save(tmp_path)

        try:
            imported, updated, errors = import_students_from_excel(tmp_path)
            self.assertEqual(len(errors), 0)
            
            # Check re-fetched student record
            s = Student.objects.get(register_number='24213946')
            self.assertEqual(s.name, 'AKILA DEEPAN S S')
            self.assertEqual(s.student_mobile, '9876543210')
            self.assertEqual(s.parent_mobile, '9443311223')
            self.assertEqual(s.sem1_perc, 80.0)
            self.assertEqual(s.sem2_perc, 85.0)
            self.assertEqual(s.sem3_perc, 82.0)
            self.assertEqual(s.sem4_perc, 88.0)
            self.assertEqual(s.sem5_perc, 90.0)
            self.assertEqual(s.sem6_perc, 86.0)
            self.assertEqual(s.x_perc, 85.0)
            self.assertEqual(s.xii_perc, 88.0)
            self.assertEqual(s.no_of_arrears, 0)
            self.assertEqual(s.aadhar_number, '123456789012')
            self.assertEqual(s.dob, datetime.date(2005, 4, 15))
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_excel_import_with_sno_column(self):
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["S.No", "Register Number", "Student Name", "Department"])
        ws.append([1, "24219999", "TEST SNO STUDENT", "DME"])

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            tmp_path = tmp.name
            wb.save(tmp_path)

        try:
            imported, updated, errors = import_students_from_excel(tmp_path)
            self.assertEqual(imported, 1)
            s = Student.objects.get(register_number="24219999")
            self.assertEqual(s.name, "TEST SNO STUDENT")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_bulk_delete_students(self):
        s2 = Student.objects.create(register_number='24213947', name='ALWIN PAULRAJ.P', department=self.dept)
        response = self.client.post(reverse('student_bulk_delete'), {'selected_students': [self.student.pk, s2.pk]})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Student.objects.filter(pk=self.student.pk).exists())
        self.assertFalse(Student.objects.filter(pk=s2.pk).exists())

    def test_department_management_and_delete(self):
        unwanted_dept = Department.objects.create(code='UNWANTED', name='Unwanted Dept')
        response = self.client.get(reverse('department_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'UNWANTED')

        delete_resp = self.client.get(reverse('department_delete', kwargs={'pk': unwanted_dept.pk}))
        self.assertEqual(delete_resp.status_code, 302)
        self.assertFalse(Department.objects.filter(pk=unwanted_dept.pk).exists())

    def test_company_edit_and_delete(self):
        edit_resp = self.client.post(reverse('company_edit', kwargs={'pk': self.company.pk}), {
            'company_id': 'HYUNDAI-01',
            'name': 'HYUNDAI MOTOR INDIA LTD',
            'salary_ctc': '3.20 LPA',
            'job_role': 'Graduate Trainee',
            'drive_date': '2026-09-10',
            'departments': [self.dept.pk]
        })
        self.assertEqual(edit_resp.status_code, 302)
        self.company.refresh_from_db()
        self.assertEqual(self.company.name, 'HYUNDAI MOTOR INDIA LTD')
        self.assertEqual(self.company.salary_ctc, '3.20 LPA')

        comp2 = Company.objects.create(company_id='TEMP-01', name='TEMP COMP', salary_ctc='2.0 LPA', drive_date=datetime.date(2026, 9, 7))
        del_resp = self.client.get(reverse('company_delete', kwargs={'pk': comp2.pk}))
        self.assertEqual(del_resp.status_code, 302)
        self.assertFalse(Company.objects.filter(pk=comp2.pk).exists())


