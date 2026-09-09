import os
import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings
from PIL import Image, ImageDraw, ImageFont
from placement_app.models import Department, UserProfile, Student, Company, PlacementDrive, InterviewRecord

class Command(BaseCommand):
    help = "Seed database with initial sample data for Shree Venkateshwara Hi-Tech Polytechnic College."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding data for Shree Venkateshwara Hi-Tech Polytechnic College..."))

        # Create Media Student Photos directory
        photos_dir = os.path.join(settings.MEDIA_ROOT, 'student_photos')
        os.makedirs(photos_dir, exist_ok=True)

        # 1. Departments
        depts = [
            {'code': 'DME', 'name': 'Diploma in Mechanical Engineering'},
            {'code': 'EEE', 'name': 'Diploma in Electrical and Electronics Engineering'},
            {'code': 'ECE', 'name': 'Diploma in Electronics and Communication Engineering'},
            {'code': 'CSE', 'name': 'Diploma in Computer Engineering'},
            {'code': 'CIVIL', 'name': 'Diploma in Civil Engineering'},
        ]
        dept_objs = {}
        for d in depts:
            obj, _ = Department.objects.get_or_create(code=d['code'], defaults={'name': d['name']})
            dept_objs[d['code']] = obj
            self.stdout.write(f"Department: {obj.code}")

        # 2. Users / Roles
        # Placement Officer / Admin
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'first_name': 'Placement',
                'last_name': 'Officer',
                'email': 'placement@svhpc.ac.in',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            UserProfile.objects.create(user=admin_user, role='ADMIN', phone='9876543210')

        # Department Staff Coordinator
        staff_user, created = User.objects.get_or_create(
            username='coordinator_dme',
            defaults={
                'first_name': 'DME',
                'last_name': 'Coordinator',
                'email': 'dme@svhpc.ac.in',
                'is_staff': True
            }
        )
        if created:
            staff_user.set_password('staff123')
            staff_user.save()
            UserProfile.objects.create(user=staff_user, role='STAFF', department=dept_objs['DME'], phone='9876543211')

        # Helper to generate student avatar image
        def create_student_photo(reg_no, name_initials, bg_color):
            photo_filename = f"{reg_no}.png"
            full_path = os.path.join(photos_dir, photo_filename)
            if not os.path.exists(full_path):
                img = Image.new('RGB', (160, 200), color=bg_color)
                draw = ImageDraw.Draw(img)
                
                # Draw head silhouette outline
                draw.ellipse((40, 30, 120, 110), fill=(255, 255, 255))
                draw.ellipse((20, 115, 140, 210), fill=(255, 255, 255))
                
                # Add text initials
                draw.text((65, 60), name_initials, fill=(31, 78, 121))
                img.save(full_path)
            return f"student_photos/{photo_filename}"

        # 3. Students
        sample_students = [
            {'reg': '24213946', 'name': 'AKILA DEEPAN S S', 'dept': 'DME', 'sem1': 82.5, 'sem2': 85.0, 'sem3': 81.0, 'sem4': 88.0, 'color': (31, 78, 121)},
            {'reg': '24213947', 'name': 'ALWIN PAULRAJ.P', 'dept': 'DME', 'sem1': 78.0, 'sem2': 80.5, 'sem3': 79.0, 'sem4': 82.0, 'color': (46, 117, 89)},
            {'reg': '24213955', 'name': 'BALAJI.D', 'dept': 'DME', 'sem1': 85.0, 'sem2': 87.0, 'sem3': 89.0, 'sem4': 90.0, 'color': (184, 80, 66)},
            {'reg': '24213959', 'name': 'BOOBALAN.V', 'dept': 'DME', 'sem1': 74.0, 'sem2': 76.5, 'sem3': 75.0, 'sem4': 78.0, 'color': (110, 72, 140)},
            {'reg': '24243964', 'name': 'DHANAPAL.M', 'dept': 'DME', 'sem1': 88.5, 'sem2': 91.0, 'sem3': 89.5, 'sem4': 92.0, 'color': (180, 120, 40)},
            {'reg': '24213967', 'name': 'DHARANIDHARAN.D', 'dept': 'DME', 'sem1': 80.0, 'sem2': 82.0, 'sem3': 84.0, 'sem4': 85.0, 'color': (50, 130, 160)},
            
            # EEE
            {'reg': '24221010', 'name': 'GOKULAKRISHNAN.K', 'dept': 'EEE', 'sem1': 81.0, 'sem2': 83.0, 'sem3': 80.0, 'sem4': 84.0, 'color': (40, 90, 120)},
            {'reg': '24221015', 'name': 'HARIHARAN.M', 'dept': 'EEE', 'sem1': 76.0, 'sem2': 79.0, 'sem3': 77.0, 'sem4': 81.0, 'color': (90, 120, 50)},
            
            # ECE
            {'reg': '24232001', 'name': 'KAVIN KUMAR.R', 'dept': 'ECE', 'sem1': 89.0, 'sem2': 92.0, 'sem3': 90.0, 'sem4': 93.0, 'color': (150, 60, 90)},
            {'reg': '24232008', 'name': 'LOGESHWARAN.S', 'dept': 'ECE', 'sem1': 82.0, 'sem2': 84.0, 'sem3': 81.0, 'sem4': 86.0, 'color': (70, 70, 120)},
            
            # CSE
            {'reg': '24244005', 'name': 'MANIKANDAN.P', 'dept': 'CSE', 'sem1': 91.0, 'sem2': 93.5, 'sem3': 92.0, 'sem4': 95.0, 'color': (30, 140, 100)},
            {'reg': '24244012', 'name': 'NITHISH KUMAR.V', 'dept': 'CSE', 'sem1': 86.0, 'sem2': 88.0, 'sem3': 87.0, 'sem4': 89.0, 'color': (160, 100, 30)},
        ]

        student_objs = []
        for s_data in sample_students:
            photo_rel_path = create_student_photo(s_data['reg'], s_data['name'][:2], s_data['color'])
            student, _ = Student.objects.get_or_create(
                register_number=s_data['reg'],
                defaults={
                    'name': s_data['name'],
                    'department': dept_objs[s_data['dept']],
                    'batch': '2024-2027',
                    'passout_year': 2026,
                    'gender': 'Male',
                    'email': f"{s_data['reg']}@svhpc.ac.in",
                    'student_mobile': f"98765{s_data['reg'][-5:]}",
                    'parent_mobile': f"94433{s_data['reg'][-5:]}",
                    'address': 'Erode, Tamil Nadu',
                    'x_perc': 85.0,
                    'xii_perc': 88.0,
                    'sem1_perc': s_data['sem1'],
                    'sem2_perc': s_data['sem2'],
                    'sem3_perc': s_data['sem3'],
                    'sem4_perc': s_data['sem4'],
                    'no_of_arrears': 0,
                    'history_of_arrears': False,
                    'photo': photo_rel_path,
                    'placement_status': 'UNPLACED'
                }
            )
            student_objs.append(student)

        # 4. Companies
        hyundai, _ = Company.objects.get_or_create(
            company_id='COMP-HYUNDAI',
            defaults={
                'name': 'HYUNDAI MOTOR INDIA',
                'industry': 'Automotive Manufacturing',
                'job_role': 'Diploma Trainee',
                'qualification': 'Diploma in Mechanical / Electrical / Electronics',
                'salary_ctc': '2.80 LPA',
                'job_location': 'Chennai',
                'drive_date': datetime.date(2026, 9, 7),
                'hr_name': 'S. Ramanathan',
                'hr_contact': '9840011223',
                'hr_email': 'recruitment@hyundai.co.in',
                'min_percentage': 60.0,
                'max_arrears': 0,
                'selection_process': '1. Aptitude Test\n2. Technical Interview\n3. HR Interview'
            }
        )
        hyundai.eligible_departments.set([dept_objs['DME'], dept_objs['EEE'], dept_objs['ECE']])

        byd, _ = Company.objects.get_or_create(
            company_id='COMP-BYD',
            defaults={
                'name': 'BYD INDIA PRIVATE LIMITED',
                'industry': 'EV Technology',
                'job_role': 'Graduate / Diploma Apprentice',
                'salary_ctc': '3.20 LPA',
                'job_location': 'Sriperumbudur, Chennai',
                'drive_date': datetime.date(2026, 8, 20),
                'hr_name': 'K. Priya',
                'hr_contact': '9840099887',
                'hr_email': 'hr@byd.co.in',
                'min_percentage': 65.0,
                'max_arrears': 0
            }
        )
        byd.eligible_departments.set([dept_objs['DME'], dept_objs['EEE']])

        tata, _ = Company.objects.get_or_create(
            company_id='COMP-TATA',
            defaults={
                'name': 'TATA ELECTRONICS',
                'industry': 'Electronics & Semiconductor Manufacturing',
                'job_role': 'Production Trainee',
                'salary_ctc': '3.00 LPA',
                'job_location': 'Hosur',
                'drive_date': datetime.date(2026, 8, 10),
                'hr_name': 'M. Suresh',
                'hr_contact': '9840044556',
                'hr_email': 'careers@tataelectronics.com',
                'min_percentage': 60.0,
                'max_arrears': 1
            }
        )
        tata.eligible_departments.set([dept_objs['ECE'], dept_objs['CSE'], dept_objs['EEE']])

        # 5. Placement Drive for HYUNDAI
        drive_hyundai, _ = PlacementDrive.objects.get_or_create(
            company=hyundai,
            title='HYUNDAI Campus Recruitment Drive 2026',
            defaults={
                'drive_date': datetime.date(2026, 9, 7),
                'salary_ctc': '2.80 LPA',
                'job_role': 'Diploma Trainee',
                'min_percentage': 60.0,
                'max_arrears': 0,
                'status': 'COMPLETED'
            }
        )
        drive_hyundai.eligible_departments.set([dept_objs['DME'], dept_objs['EEE']])

        # Create interview selection records matching user example image!
        # DME Students selected for HYUNDAI
        dme_students = Student.objects.filter(department=dept_objs['DME'])
        for s in dme_students:
            rec, _ = InterviewRecord.objects.get_or_create(
                student=s,
                drive=drive_hyundai,
                company=hyundai,
                defaults={
                    'interview_attended': True,
                    'aptitude': 'PASS',
                    'technical': 'PASS',
                    'hr': 'PASS',
                    'final_result': 'SELECTED',
                    'salary': '2.80 LPA',
                    'job_role': 'Diploma Trainee',
                    'location': 'Chennai',
                    'remarks': 'Selected in Hyundai Off-Campus Drive'
                }
            )
            s.placement_status = 'PLACED'
            s.save()

        self.stdout.write(self.style.SUCCESS("Successfully seeded sample data for Placement Management System!"))
