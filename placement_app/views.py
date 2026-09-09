import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.db.models import Q, Count, Max, Avg
from django.http import HttpResponse, JsonResponse
from django.conf import settings

from placement_app.models import Department, Student, Company, PlacementDrive, InterviewRecord, UserProfile
from placement_app.services.excel_service import import_students_from_excel, export_students_to_excel, generate_selection_report_excel
from placement_app.services.pdf_service import generate_selection_report_pdf

@login_required
def dashboard_view(request):
    """
    Placement Dashboard showing key metrics & department statistics.
    """
    total_students = Student.objects.count()
    companies_visited = Company.objects.count()
    placed_students = Student.objects.filter(placement_status='PLACED').count()
    
    placement_percentage = round((placed_students / total_students * 100), 2) if total_students > 0 else 0.0
    awaiting_placement = total_students - placed_students

    # Highest Package calculation
    selected_records = InterviewRecord.objects.filter(final_result__in=['SELECTED', 'JOINED'])
    highest_package = "₹0.00 LPA"
    if selected_records.exists():
        # Look for packages
        salaries = [r.salary for r in selected_records if r.salary]
        if salaries:
            highest_package = max(salaries, key=lambda s: float(s.replace('₹','').replace('LPA','').strip()) if ('LPA' in s or '₹' in s) else 0)
            if not highest_package.startswith('₹') and 'LPA' in highest_package:
                highest_package = f"₹{highest_package}"

    # Department-wise breakdown
    departments = Department.objects.all()
    dept_stats = []
    for dept in departments:
        dept_total = Student.objects.filter(department=dept).count()
        dept_placed = Student.objects.filter(department=dept, placement_status='PLACED').count()
        dept_pct = round((dept_placed / dept_total * 100), 2) if dept_total > 0 else 0.0
        dept_stats.append({
            'pk': dept.pk,
            'code': dept.code,
            'name': dept.name,
            'total': dept_total,
            'placed': dept_placed,
            'pct': dept_pct
        })

    # Recent drives
    recent_drives = PlacementDrive.objects.select_related('company').order_by('-drive_date')[:5]

    context = {
        'total_students': total_students,
        'companies_visited': companies_visited,
        'placed_students': placed_students,
        'placement_percentage': placement_percentage,
        'highest_package': highest_package,
        'awaiting_placement': awaiting_placement,
        'dept_stats': dept_stats,
        'recent_drives': recent_drives,
    }
    return render(request, 'dashboard.html', context)

@login_required
def student_list_view(request):
    """
    Student Master Database with live search & multi-criteria filtering.
    """
    students = Student.objects.select_related('department').all()
    departments = Department.objects.all()

    # Search query
    q = request.GET.get('q', '').strip()
    if q:
        students = students.filter(
            Q(register_number__icontains=q) |
            Q(name__icontains=q) |
            Q(email__icontains=q)
        )

    # Filters
    dept_code = request.GET.get('department', '')
    if dept_code:
        students = students.filter(department__code=dept_code)

    batch = request.GET.get('batch', '')
    if batch:
        students = students.filter(batch=batch)

    arrears_filter = request.GET.get('arrears', '')
    if arrears_filter == 'no':
        students = students.filter(no_of_arrears=0)
    elif arrears_filter == 'yes':
        students = students.filter(no_of_arrears__gt=0)

    min_perc = request.GET.get('min_perc', '')
    if min_perc:
        try:
            val = float(min_perc)
            students = [s for s in students if s.avg_sem_perc >= val]
        except ValueError:
            pass

    iti_filter = request.GET.get('iti', '')
    if iti_filter == 'yes':
        students = [s for s in students if s.iti]
    elif iti_filter == 'no':
        students = [s for s in students if not s.iti]

    status = request.GET.get('status', '')
    if status:
        students = [s for s in students if s.placement_status == status]

    # Excel export handle
    if 'export' in request.GET and request.GET['export'] == 'excel':
        wb = export_students_to_excel(students)
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="Student_Database_Report.xlsx"'
        wb.save(response)
        return response

    context = {
        'students': students,
        'departments': departments,
        'selected_dept': dept_code,
        'selected_batch': batch,
        'selected_arrears': arrears_filter,
        'selected_min_perc': min_perc,
        'selected_iti': iti_filter,
        'selected_status': status,
        'q': q,
    }
    return render(request, 'students/student_list.html', context)

@login_required
def student_detail_view(request, pk):
    """
    Student Profile Page showing personal, academic, contact & complete placement history.
    """
    student = get_object_or_404(Student.objects.select_related('department'), pk=pk)
    interview_records = InterviewRecord.objects.filter(student=student).select_related('drive', 'company').order_by('-drive__drive_date')

    context = {
        'student': student,
        'interview_records': interview_records,
    }
    return render(request, 'students/student_detail.html', context)

@login_required
def student_create_view(request):
    """
    Add a new student manually.
    """
    departments = Department.objects.all()

    if request.method == 'POST':
        reg_no = request.POST.get('register_number', '').strip()
        name = request.POST.get('name', '').strip()
        dept_id = request.POST.get('department')
        
        if Student.objects.filter(register_number=reg_no).exists():
            messages.error(request, f"Student with Register Number '{reg_no}' already exists.")
            return render(request, 'students/student_form.html', {'departments': departments})

        dept = get_object_or_404(Department, pk=dept_id)
        student = Student.objects.create(
            register_number=reg_no,
            name=name,
            department=dept,
            email=request.POST.get('email', '').strip(),
            student_mobile=request.POST.get('student_mobile', '').strip(),
            parent_mobile=request.POST.get('parent_mobile', '').strip(),
            dob=request.POST.get('dob') or None,
            aadhar_number=request.POST.get('aadhar_number', '').strip(),
            gender=request.POST.get('gender', 'Male'),
            address=request.POST.get('address', '').strip(),
            batch=request.POST.get('batch', '2024-2027'),
            passout_year=int(request.POST.get('passout_year', 2026)),
            history_of_arrears=request.POST.get('history_of_arrears') == 'on',
            no_of_arrears=int(request.POST.get('no_of_arrears', 0)),
            sem1_perc=float(request.POST.get('sem1_perc', 0) or 0),
            sem2_perc=float(request.POST.get('sem2_perc', 0) or 0),
            sem3_perc=float(request.POST.get('sem3_perc', 0) or 0),
            sem4_perc=float(request.POST.get('sem4_perc', 0) or 0),
            sem5_perc=float(request.POST.get('sem5_perc', 0) or 0),
            sem6_perc=float(request.POST.get('sem6_perc', 0) or 0),
            x_perc=float(request.POST.get('x_perc', 0) or 0),
            xii_perc=float(request.POST.get('xii_perc', 0) or 0),
            iti=request.POST.get('iti') == 'on',
            skills=request.POST.get('skills', '').strip(),
            placement_status=request.POST.get('placement_status', 'UNPLACED')
        )

        if 'photo' in request.FILES:
            student.photo = request.FILES['photo']
            student.save()

        if 'resume' in request.FILES:
            student.resume = request.FILES['resume']
            student.save()

        messages.success(request, f"Student '{name}' added successfully.")
        return redirect('student_detail', pk=student.pk)

    return render(request, 'students/student_form.html', {'departments': departments})

@login_required
def student_update_view(request, pk):
    """
    Edit an existing student record.
    """
    student = get_object_or_404(Student, pk=pk)
    departments = Department.objects.all()

    if request.method == 'POST':
        reg_no = request.POST.get('register_number', '').strip()
        name = request.POST.get('name', '').strip()
        dept_id = request.POST.get('department')
        
        if Student.objects.filter(register_number=reg_no).exclude(pk=student.pk).exists():
            messages.error(request, f"Another student with Register Number '{reg_no}' already exists.")
            return render(request, 'students/student_form.html', {'student': student, 'departments': departments})

        dept = get_object_or_404(Department, pk=dept_id)
        student.register_number = reg_no
        student.name = name
        student.department = dept
        student.email = request.POST.get('email', '').strip()
        student.student_mobile = request.POST.get('student_mobile', '').strip()
        student.parent_mobile = request.POST.get('parent_mobile', '').strip()
        student.dob = request.POST.get('dob') or None
        student.aadhar_number = request.POST.get('aadhar_number', '').strip()
        student.gender = request.POST.get('gender', 'Male')
        student.address = request.POST.get('address', '').strip()
        student.batch = request.POST.get('batch', '2024-2027')
        student.passout_year = int(request.POST.get('passout_year', 2026))
        student.history_of_arrears = request.POST.get('history_of_arrears') == 'on'
        student.no_of_arrears = int(request.POST.get('no_of_arrears', 0))
        student.sem1_perc = float(request.POST.get('sem1_perc', 0) or 0)
        student.sem2_perc = float(request.POST.get('sem2_perc', 0) or 0)
        student.sem3_perc = float(request.POST.get('sem3_perc', 0) or 0)
        student.sem4_perc = float(request.POST.get('sem4_perc', 0) or 0)
        student.sem5_perc = float(request.POST.get('sem5_perc', 0) or 0)
        student.sem6_perc = float(request.POST.get('sem6_perc', 0) or 0)
        student.x_perc = float(request.POST.get('x_perc', 0) or 0)
        student.xii_perc = float(request.POST.get('xii_perc', 0) or 0)
        student.iti = request.POST.get('iti') == 'on'
        student.skills = request.POST.get('skills', '').strip()
        student.placement_status = request.POST.get('placement_status', 'UNPLACED')

        if 'photo' in request.FILES:
            student.photo = request.FILES['photo']

        if 'resume' in request.FILES:
            student.resume = request.FILES['resume']

        student.save()
        messages.success(request, f"Student '{name}' updated successfully.")
        return redirect('student_detail', pk=student.pk)

    return render(request, 'students/student_form.html', {'student': student, 'departments': departments})

@login_required
def student_delete_view(request, pk):
    """
    Delete a student record.
    """
    student = get_object_or_404(Student, pk=pk)
    name = student.name
    reg_no = student.register_number
    student.delete()
    messages.success(request, f"Student '{name}' ({reg_no}) deleted successfully.")
    return redirect('student_list')

@login_required
def student_bulk_delete_view(request):
    """
    Bulk delete selected student records.
    """
    if request.method == 'POST':
        student_ids = request.POST.getlist('selected_students')
        if student_ids:
            count = Student.objects.filter(pk__in=student_ids).count()
            Student.objects.filter(pk__in=student_ids).delete()
            messages.success(request, f"Successfully deleted {count} student record(s).")
        else:
            messages.warning(request, "No students were selected for deletion.")
    return redirect('student_list')

@login_required
def department_list_view(request):
    """
    Manage departments, add new department, edit or delete unwanted department records.
    """
    departments = Department.objects.annotate(student_count=Count('students')).order_by('code')
    
    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        name = request.POST.get('name', '').strip()
        if code:
            dept, created = Department.objects.get_or_create(code=code, defaults={'name': name or f"Diploma in {code}"})
            if created:
                messages.success(request, f"Department '{code}' created successfully.")
            else:
                messages.warning(request, f"Department '{code}' already exists.")
        next_url = request.POST.get('next') or request.GET.get('next') or 'department_list'
        return redirect(next_url)

    context = {
        'departments': departments
    }
    return render(request, 'departments/department_list.html', context)

@login_required
def department_update_view(request, pk):
    """
    Update department code and name.
    """
    dept = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        name = request.POST.get('name', '').strip()
        if code:
            dept.code = code
            dept.name = name or f"Diploma in {code}"
            dept.save()
            messages.success(request, f"Department '{code}' updated successfully.")
    return redirect('department_list')

@login_required
def department_delete_view(request, pk):
    """
    Delete an unwanted department record.
    """
    dept = get_object_or_404(Department, pk=pk)
    code = dept.code
    if dept.students.exists():
        messages.error(request, f"Cannot remove department '{code}' because it has {dept.students.count()} enrolled student(s).")
    else:
        dept.delete()
        messages.success(request, f"Department '{code}' removed successfully.")
    next_url = request.GET.get('next') or request.POST.get('next') or 'department_list'
    return redirect(next_url)

@login_required
def department_bulk_delete_view(request):
    """
    Bulk delete selected unwanted department records.
    """
    if request.method == 'POST':
        dept_ids = request.POST.getlist('selected_departments')
        if dept_ids:
            depts = Department.objects.filter(pk__in=dept_ids)
            deleted_count = 0
            skipped_count = 0
            for d in depts:
                if d.students.exists():
                    skipped_count += 1
                else:
                    d.delete()
                    deleted_count += 1
            if deleted_count > 0:
                messages.success(request, f"Successfully deleted {deleted_count} unwanted department(s).")
            if skipped_count > 0:
                messages.warning(request, f"Skipped {skipped_count} department(s) because they have active student records.")
        else:
            messages.warning(request, "No departments were selected for deletion.")
    return redirect('department_list')




@login_required
def import_excel_view(request):
    """
    Bulk import students from Excel file with auto photo mapping.
    """
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']
        
        # Save temporary file
        temp_path = os.path.join(settings.MEDIA_ROOT, 'temp_import.xlsx')
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        with open(temp_path, 'wb+') as destination:
            for chunk in excel_file.chunks():
                destination.write(chunk)

        imported, updated, errors = import_students_from_excel(temp_path)
        
        if os.path.exists(temp_path):
            os.remove(temp_path)

        if errors:
            for err in errors:
                messages.error(request, err)
        else:
            messages.success(request, f"Successfully imported {imported} new students and updated {updated} existing records.")
        
        return redirect('student_list')

    return render(request, 'students/import_excel.html')

@login_required
def company_list_view(request):
    """
    Company Management module.
    """
    companies = Company.objects.prefetch_related('eligible_departments').all()
    return render(request, 'companies/company_list.html', {'companies': companies})

@login_required
def company_create_view(request):
    """
    Add a new company.
    """
    departments = Department.objects.all()
    if request.method == 'POST':
        company_id = request.POST.get('company_id', '').strip()
        name = request.POST.get('name', '').strip()
        
        company = Company.objects.create(
            company_id=company_id,
            name=name,
            address=request.POST.get('address', '').strip(),
            hr_name=request.POST.get('hr_name', '').strip(),
            hr_contact=request.POST.get('hr_contact', '').strip(),
            hr_email=request.POST.get('hr_email', '').strip(),
            website=request.POST.get('website', '').strip(),
            industry=request.POST.get('industry', '').strip(),
            job_role=request.POST.get('job_role', 'Diploma Trainee').strip(),
            qualification=request.POST.get('qualification', 'Diploma').strip(),
            min_percentage=float(request.POST.get('min_percentage', 0) or 0),
            max_arrears=int(request.POST.get('max_arrears', 0) or 0),
            salary_ctc=request.POST.get('salary_ctc', '2.80 LPA').strip(),
            job_location=request.POST.get('job_location', 'Chennai').strip(),
            drive_date=request.POST.get('drive_date'),
            selection_process=request.POST.get('selection_process', '').strip(),
        )

        dept_ids = request.POST.getlist('departments')
        if dept_ids:
            company.eligible_departments.set(dept_ids)

        messages.success(request, f"Company '{name}' added successfully.")
        return redirect('company_list')

    return render(request, 'companies/company_form.html', {'departments': departments})

@login_required
def company_update_view(request, pk):
    """
    Edit an existing company record.
    """
    company = get_object_or_404(Company, pk=pk)
    departments = Department.objects.all()

    if request.method == 'POST':
        company.company_id = request.POST.get('company_id', '').strip()
        company.name = request.POST.get('name', '').strip()
        company.address = request.POST.get('address', '').strip()
        company.hr_name = request.POST.get('hr_name', '').strip()
        company.hr_contact = request.POST.get('hr_contact', '').strip()
        company.hr_email = request.POST.get('hr_email', '').strip()
        company.website = request.POST.get('website', '').strip()
        company.industry = request.POST.get('industry', '').strip()
        company.job_role = request.POST.get('job_role', 'Diploma Trainee').strip()
        company.qualification = request.POST.get('qualification', 'Diploma').strip()
        company.min_percentage = float(request.POST.get('min_percentage', 0) or 0)
        company.max_arrears = int(request.POST.get('max_arrears', 0) or 0)
        company.salary_ctc = request.POST.get('salary_ctc', '2.80 LPA').strip()
        company.job_location = request.POST.get('job_location', 'Chennai').strip()
        
        drive_date = request.POST.get('drive_date')
        if drive_date:
            company.drive_date = drive_date
            
        company.selection_process = request.POST.get('selection_process', '').strip()
        company.save()

        dept_ids = request.POST.getlist('departments')
        if dept_ids:
            company.eligible_departments.set(dept_ids)
        else:
            company.eligible_departments.clear()

        messages.success(request, f"Company '{company.name}' updated successfully.")
        return redirect('company_list')

    return render(request, 'companies/company_form.html', {
        'company': company,
        'departments': departments
    })

@login_required
def company_delete_view(request, pk):
    """
    Delete a company record.
    """
    company = get_object_or_404(Company, pk=pk)
    name = company.name
    try:
        company.delete()
        messages.success(request, f"Company '{name}' deleted successfully.")
    except Exception as e:
        messages.error(request, f"Could not delete company '{name}': {str(e)}")
    return redirect('company_list')

@login_required
def drive_list_view(request):
    """
    Placement Drives list.
    """
    drives = PlacementDrive.objects.select_related('company').prefetch_related('eligible_departments').all()
    return render(request, 'drives/drive_list.html', {'drives': drives})

@login_required
def drive_create_view(request):
    """
    Create a new placement drive for a company.
    """
    companies = Company.objects.all()
    departments = Department.objects.all()

    if request.method == 'POST':
        company_id = request.POST.get('company')
        company = get_object_or_404(Company, pk=company_id)

        drive = PlacementDrive.objects.create(
            company=company,
            title=request.POST.get('title', f"{company.name} Campus Drive").strip(),
            drive_date=request.POST.get('drive_date'),
            salary_ctc=request.POST.get('salary_ctc', company.salary_ctc).strip(),
            job_role=request.POST.get('job_role', company.job_role).strip(),
            min_percentage=float(request.POST.get('min_percentage', company.min_percentage) or 0),
            max_arrears=int(request.POST.get('max_arrears', company.max_arrears) or 0),
            status=request.POST.get('status', 'ONGOING')
        )

        dept_ids = request.POST.getlist('departments')
        if dept_ids:
            drive.eligible_departments.set(dept_ids)
        else:
            drive.eligible_departments.set(company.eligible_departments.all())

        # Auto register eligible students
        eligible_depts = drive.eligible_departments.all()
        eligible_students = Student.objects.filter(department__in=eligible_depts, no_of_arrears__lte=drive.max_arrears)
        
        reg_count = 0
        for s in eligible_students:
            if s.avg_sem_perc >= drive.min_percentage:
                rec, created = InterviewRecord.objects.get_or_create(
                    student=s,
                    drive=drive,
                    company=company,
                    defaults={
                        'salary': drive.salary_ctc,
                        'job_role': drive.job_role,
                        'location': company.job_location,
                        'interview_attended': True,
                        'final_result': 'SELECTED'
                    }
                )
                if created:
                    s.placement_status = 'PLACED'
                    s.save()
                reg_count += 1

        messages.success(request, f"Drive '{drive.title}' created and {reg_count} eligible students added as Selected.")
        return redirect('drive_detail', pk=drive.pk)

    return render(request, 'drives/drive_form.html', {'companies': companies, 'departments': departments})

@login_required
def drive_update_view(request, pk):
    """
    Edit an existing placement drive.
    """
    drive = get_object_or_404(PlacementDrive, pk=pk)
    companies = Company.objects.all()
    departments = Department.objects.all()

    if request.method == 'POST':
        company_id = request.POST.get('company')
        company = get_object_or_404(Company, pk=company_id)

        drive.company = company
        drive.title = request.POST.get('title', f"{company.name} Campus Drive").strip()
        drive.drive_date = request.POST.get('drive_date')
        drive.salary_ctc = request.POST.get('salary_ctc', company.salary_ctc).strip()
        drive.job_role = request.POST.get('job_role', company.job_role).strip()
        drive.min_percentage = float(request.POST.get('min_percentage', company.min_percentage) or 0)
        drive.max_arrears = int(request.POST.get('max_arrears', company.max_arrears) or 0)
        drive.status = request.POST.get('status', 'ONGOING')
        drive.save()

        dept_ids = request.POST.getlist('departments')
        if dept_ids:
            drive.eligible_departments.set(dept_ids)
        else:
            drive.eligible_departments.clear()

        messages.success(request, f"Placement drive '{drive.title}' updated successfully.")
        return redirect('drive_detail', pk=drive.pk)

    return render(request, 'drives/drive_form.html', {
        'drive': drive,
        'companies': companies,
        'departments': departments
    })

@login_required
def drive_delete_view(request, pk):
    """
    Delete a placement drive.
    """
    drive = get_object_or_404(PlacementDrive, pk=pk)
    title = drive.title
    try:
        drive.delete()
        messages.success(request, f"Placement drive '{title}' deleted successfully.")
    except Exception as e:
        messages.error(request, f"Could not delete drive '{title}': {str(e)}")
    return redirect('drive_list')

@login_required
def drive_complete_view(request, pk):
    """
    Mark a placement drive as Completed or toggle back to Ongoing.
    """
    drive = get_object_or_404(PlacementDrive, pk=pk)
    if drive.status == 'COMPLETED':
        drive.status = 'ONGOING'
        messages.info(request, f"Drive '{drive.title}' reopened as Ongoing.")
    else:
        drive.status = 'COMPLETED'
        messages.success(request, f"Drive '{drive.title}' marked as COMPLETED!")
    drive.save()
    next_url = request.GET.get('next') or request.POST.get('next')
    if next_url == 'list':
        return redirect('drive_list')
    return redirect('drive_detail', pk=drive.pk)

@login_required
def drive_add_students_view(request, pk):
    """
    Add / Register selected students from the database into this placement drive.
    """
    drive = get_object_or_404(PlacementDrive, pk=pk)
    if request.method == 'POST':
        student_ids = request.POST.getlist('selected_students')
        if student_ids:
            students = Student.objects.filter(pk__in=student_ids)
            added_count = 0
            for s in students:
                rec, created = InterviewRecord.objects.get_or_create(
                    student=s,
                    drive=drive,
                    company=drive.company,
                    defaults={
                        'salary': drive.salary_ctc,
                        'job_role': drive.job_role,
                        'location': drive.company.job_location,
                        'interview_attended': True,
                        'final_result': 'SELECTED'
                    }
                )
                if created:
                    added_count += 1
                elif rec.final_result == 'REGISTERED':
                    rec.interview_attended = True
                    rec.final_result = 'SELECTED'
                    rec.save()
                    added_count += 1
                s.placement_status = 'PLACED'
                s.save()
            if added_count > 0:
                messages.success(request, f"Successfully added {added_count} student(s) as Selected into drive '{drive.title}'.")
            else:
                messages.info(request, "Selected student(s) are already added to this drive.")
        else:
            messages.warning(request, "No students were selected from the database.")
    return redirect('drive_detail', pk=drive.pk)

@login_required
def drive_remove_student_view(request, pk, student_id):
    """
    Remove a student record from this placement drive.
    """
    drive = get_object_or_404(PlacementDrive, pk=pk)
    record = InterviewRecord.objects.filter(drive=drive, student_id=student_id).first()
    if record:
        reg_no = record.student.register_number
        record.delete()
        messages.success(request, f"Student '{reg_no}' removed from drive tracker.")
    else:
        messages.warning(request, "Student record not found in this drive.")
    return redirect('drive_detail', pk=drive.pk)

@login_required
def drive_detail_view(request, pk):
    """
    Placement Drive detail & round-by-round interview tracker.
    Tracks: Registered -> Attended -> Aptitude -> Technical -> HR -> Selected -> Rejected -> Joined
    """
    drive = get_object_or_404(PlacementDrive.objects.select_related('company'), pk=pk)
    records = InterviewRecord.objects.filter(drive=drive).select_related('student', 'student__department')

    if request.method == 'POST':
        # Batch update interview results
        record_id = request.POST.get('record_id')
        record = get_object_or_404(InterviewRecord, pk=record_id)
        
        record.interview_attended = request.POST.get('attended') == 'on'
        record.aptitude = request.POST.get('aptitude', 'PENDING')
        record.technical = request.POST.get('technical', 'PENDING')
        record.hr = request.POST.get('hr', 'PENDING')
        record.final_result = request.POST.get('final_result', 'REGISTERED')
        record.remarks = request.POST.get('remarks', '')

        if record.final_result in ['SELECTED', 'JOINED']:
            record.student.placement_status = 'PLACED'
            record.student.save()

        record.save()
        messages.success(request, f"Updated interview details for student {record.student.register_number}.")
        return redirect('drive_detail', pk=drive.pk)

    all_students = Student.objects.select_related('department').all()
    registered_student_ids = set(records.values_list('student_id', flat=True))

    context = {
        'drive': drive,
        'records': records,
        'all_students': all_students,
        'registered_student_ids': registered_student_ids,
    }
    return render(request, 'drives/drive_detail.html', context)

@login_required
def selection_report_view(request):
    """
    Automatic Selection Report Generator matching exact college format:
    SHREE VENKATESHWARA HI-TECH POLYTECHNIC COLLEGE
    TRAINING AND PLACEMENT CELL
    SALARY : 2.80 LPA NAME OF THE COMPANY : HYUNDAI
    Table: S.No | Register Number | Student Name | Department | Student Photo
    """
    companies = Company.objects.all()
    departments = Department.objects.all()

    company_id = request.GET.get('company')
    dept_code = request.GET.get('department')
    
    selected_company = None
    records = []
    
    if company_id:
        selected_company = get_object_or_404(Company, pk=company_id)
        records = InterviewRecord.objects.filter(
            company=selected_company,
            final_result__in=['SELECTED', 'JOINED']
        ).select_related('student', 'student__department')

        if dept_code:
            records = records.filter(student__department__code=dept_code)

    # Export Excel option
    if request.GET.get('export') == 'excel' and selected_company:
        excel_bytes = generate_selection_report_excel(records=records, selected_company=selected_company)
        response = HttpResponse(excel_bytes, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="Selection_Report_{selected_company.name}.xlsx"'
        return response

    # Export PDF option
    if request.GET.get('export') == 'pdf' and selected_company:
        pdf_bytes = generate_selection_report_pdf(
            records=records,
            company_name=selected_company.name,
            salary=selected_company.salary_ctc,
            drive_date=selected_company.drive_date.strftime('%d-%m-%Y') if selected_company.drive_date else '',
            department_code=dept_code or 'ALL'
        )
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Selection_Report_{selected_company.name}.pdf"'
        return response

    context = {
        'companies': companies,
        'departments': departments,
        'selected_company': selected_company,
        'records': records,
        'selected_company_id': int(company_id) if company_id else None,
        'selected_dept': dept_code,
    }
    return render(request, 'reports/selection_report.html', context)

@login_required
def reports_hub_view(request):
    """
    Reports Hub providing Company-wise, Department-wise, Batch, and Placement History reports.
    """
    report_type = request.GET.get('type', 'dept_wise')
    departments = Department.objects.all()

    data = {}
    if report_type == 'dept_wise':
        dept_stats = []
        for d in departments:
            total = Student.objects.filter(department=d).count()
            placed = Student.objects.filter(department=d, placement_status='PLACED').count()
            pct = round((placed / total * 100), 2) if total > 0 else 0.0
            dept_stats.append({
                'department': d,
                'total': total,
                'placed': placed,
                'unplaced': total - placed,
                'pct': pct
            })
        data['dept_stats'] = dept_stats

    elif report_type == 'company_wise':
        companies = Company.objects.prefetch_related('interview_records').all()
        company_stats = []
        for c in companies:
            registered = c.interview_records.count()
            attended = c.interview_records.filter(interview_attended=True).count()
            selected = c.interview_records.filter(final_result__in=['SELECTED', 'JOINED']).count()
            company_stats.append({
                'company': c,
                'registered': registered,
                'attended': attended,
                'selected': selected,
            })
        data['company_stats'] = company_stats

    elif report_type == 'unplaced':
        unplaced_students = Student.objects.filter(placement_status='UNPLACED').select_related('department')
        data['unplaced_students'] = unplaced_students

    context = {
        'report_type': report_type,
        'data': data,
    }
    return render(request, 'reports/reports_hub.html', context)

def login_user_view(request):
    """
    User Login View.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()

    return render(request, 'login.html', {'form': form})

def logout_user_view(request):
    """
    User Logout.
    """
    logout(request)
    messages.info(request, "You have logged out successfully.")
    return redirect('login')
