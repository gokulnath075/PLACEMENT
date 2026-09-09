import os
import re
import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from django.conf import settings
from placement_app.models import Student, Department

def clean_header(h):
    if h is None:
        return ''
    s = str(h).lower()
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    return s.strip()

def parse_dob(val):
    """
    Parses Date of Birth values from Excel strings, datetime objects, or Excel serial numbers.
    """
    if val is None or val == '':
        return None
    if hasattr(val, 'date'):
        return val.date()
    if hasattr(val, 'strftime'):
        return val

    val_str = str(val).strip()
    if not val_str or val_str.lower() in ['none', 'null', 'nan', '-']:
        return None

    date_formats = [
        '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d',
        '%d.%m.%Y', '%Y.%m.%d', '%d-%b-%Y', '%d-%B-%Y',
        '%m/%d/%Y', '%m-%d-%Y'
    ]
    for fmt in date_formats:
        try:
            return datetime.datetime.strptime(val_str, fmt).date()
        except (ValueError, TypeError):
            pass

    try:
        dt = openpyxl.utils.datetime.from_excel(float(val_str))
        if hasattr(dt, 'date'):
            return dt.date()
        return dt
    except Exception:
        pass

    return None

def import_students_from_excel(file_path):
    """
    Imports students from an Excel file (.xlsx or .xls) with robust header mapping.
    Fixes Date of Birth and Aadhar Number field parsing and persistence.
    """
    wb = openpyxl.load_workbook(file_path, data_only=True)
    sheet = wb.active

    imported_count = 0
    updated_count = 0
    errors = []

    raw_headers = [cell.value for cell in sheet[1]]
    cleaned_headers = [clean_header(h) for h in raw_headers]

    header_map = {}

    for idx, ch in enumerate(cleaned_headers):
        if not ch:
            continue

        # S.No / Serial Number Column
        if re.search(r'\b(s[\s._]*no|sl[\s._]*no|serial[\s._]*no|sno|slno)\b', ch) or ch in ['s no', 'sno', 'sl no', 'slno', 'serial no']:
            header_map['s_no'] = idx
            continue

        # Register Number
        elif re.search(r'\b(register|reg)[\s._]*(number|no|num)?\b', ch) or ch in ['register', 'regno', 'reg_no']:
            if 'reg_no' not in header_map:
                header_map['reg_no'] = idx
        # Student Name
        elif re.search(r'\b(student[\s._]*)?name\b', ch):
            if 'name' not in header_map:
                header_map['name'] = idx
        # Department
        elif re.search(r'\b(department|dept|branch)\b', ch):
            header_map['dept'] = idx
        # Email
        elif 'email' in ch:
            header_map['email'] = idx
        # Parent Mobile Number
        elif re.search(r'\b(parent|father|mother)[\s._]*(mobile|phone|contact)?\b', ch):
            header_map['parent_mobile'] = idx
        # Student Mobile Number
        elif re.search(r'\b(student[\s._]*)?(mobile|phone|contact)\b', ch):
            if 'student_mobile' not in header_map:
                header_map['student_mobile'] = idx
        # Date of Birth
        elif re.search(r'\b(dob|date[\s._]*of[\s._]*birth|birth[\s._]*date)\b', ch) or ch in ['dob', 'd o b']:
            header_map['dob'] = idx
        # Aadhar Number
        elif re.search(r'\b(aadhar|adhar|uid)\b', ch):
            header_map['aadhar'] = idx
        # Gender
        elif ch in ['gender', 'sex']:
            header_map['gender'] = idx
        # Address
        elif 'address' in ch:
            header_map['address'] = idx
        # Batch / Year
        elif 'batch' in ch:
            header_map['batch'] = idx
        # Pass-out Year
        elif re.search(r'\b(pass[\s._]*out|passout|passing)\b', ch):
            header_map['passout_year'] = idx
        # History of Arrears
        elif re.search(r'\b(history[\s._]*of[\s._]*arrears|arrear[s]?[\s._]*history)\b', ch):
            header_map['history_arrears'] = idx
        # No. of Arrears
        elif re.search(r'\b(no[\s._]*of[\s._]*arrears|number[\s._]*of[\s._]*arrears|arrears[\s._]*count|arrears)\b', ch):
            header_map['no_arrears'] = idx
        # Semesters VI down to I
        elif re.search(r'\b(vi|6th|6)[\s._]*(semester|sem)\b|\bsem[\s._]*6\b|\bsem[\s._]*vi\b', ch):
            header_map['sem6'] = idx
        elif re.search(r'\b(v|5th|5)[\s._]*(semester|sem)\b|\bsem[\s._]*5\b|\bsem[\s._]*v\b', ch):
            header_map['sem5'] = idx
        elif re.search(r'\b(iv|4th|4)[\s._]*(semester|sem)\b|\bsem[\s._]*4\b|\bsem[\s._]*iv\b', ch):
            header_map['sem4'] = idx
        elif re.search(r'\b(iii|3rd|3)[\s._]*(semester|sem)\b|\bsem[\s._]*3\b|\bsem[\s._]*iii\b', ch):
            header_map['sem3'] = idx
        elif re.search(r'\b(ii|2nd|2)[\s._]*(semester|sem)\b|\bsem[\s._]*2\b|\bsem[\s._]*ii\b', ch):
            header_map['sem2'] = idx
        elif re.search(r'\b(i|1st|1)[\s._]*(semester|sem)\b|\bsem[\s._]*1\b|\bsem[\s._]*i\b', ch):
            header_map['sem1'] = idx
        # X Marks %
        elif re.search(r'\b(x|10th|sslc)\b', ch):
            header_map['x_perc'] = idx
        # XII Marks %
        elif re.search(r'\b(xii|12th|hsc)\b', ch):
            header_map['xii_perc'] = idx
        # ITI
        elif 'iti' in ch:
            header_map['iti'] = idx
        # Skills
        elif 'skills' in ch:
            header_map['skills'] = idx

    if 'reg_no' not in header_map or 'name' not in header_map:
        return 0, 0, ["Excel file must contain 'Register Number' and 'Student Name' column headers."]

    for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        if not row or not any(row):
            continue

        raw_reg = row[header_map['reg_no']] if header_map['reg_no'] < len(row) else None
        if raw_reg is None:
            continue
        reg_no = str(raw_reg).strip()
        if not reg_no or reg_no.lower() in ['none', 'null', '']:
            continue

        raw_name = row[header_map['name']] if header_map['name'] < len(row) else None
        name = str(raw_name).strip() if raw_name is not None else ''

        def get_str(key, default=''):
            if key in header_map and header_map[key] < len(row):
                val = row[header_map[key]]
                if val is not None:
                    return str(val).strip()
            return default

        def get_val(key, default=0.0):
            if key in header_map and header_map[key] < len(row):
                val = row[header_map[key]]
                if val is not None:
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return default
            return default

        def get_bool(key):
            if key in header_map and header_map[key] < len(row):
                val = row[header_map[key]]
                if val is not None:
                    v = str(val).strip().lower()
                    return v in ['yes', 'y', '1', 'true']
            return False

        # Department
        dept_code = get_str('dept', 'DME').upper()
        dept, _ = Department.objects.get_or_create(
            code=dept_code,
            defaults={'name': f"Diploma in {dept_code}"}
        )

        # Parse Date of Birth
        raw_dob = row[header_map['dob']] if 'dob' in header_map and header_map['dob'] < len(row) else None
        dob_val = parse_dob(raw_dob)

        student_data = {
            'name': name,
            'department': dept,
            'email': get_str('email'),
            'student_mobile': get_str('student_mobile'),
            'parent_mobile': get_str('parent_mobile'),
            'dob': dob_val,
            'aadhar_number': get_str('aadhar'),
            'gender': get_str('gender', 'Male'),
            'address': get_str('address'),
            'batch': get_str('batch', '2024-2027'),
            'passout_year': int(get_val('passout_year', 2026)),
            'history_of_arrears': get_bool('history_arrears'),
            'no_of_arrears': int(get_val('no_arrears', 0)),
            'sem1_perc': get_val('sem1'),
            'sem2_perc': get_val('sem2'),
            'sem3_perc': get_val('sem3'),
            'sem4_perc': get_val('sem4'),
            'sem5_perc': get_val('sem5'),
            'sem6_perc': get_val('sem6'),
            'x_perc': get_val('x_perc'),
            'xii_perc': get_val('xii_perc'),
            'iti': get_bool('iti'),
            'skills': get_str('skills'),
        }

        student, created = Student.objects.get_or_create(
            register_number=reg_no,
            defaults=student_data
        )

        if not created:
            for attr, value in student_data.items():
                if value is not None and value != '':
                    setattr(student, attr, value)
            student.save()
            updated_count += 1
        else:
            imported_count += 1

        # Auto photo matching by Register Number
        photo_dir = os.path.join(settings.MEDIA_ROOT, 'student_photos')
        if os.path.exists(photo_dir):
            for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.PNG']:
                photo_file = f"{reg_no}{ext}"
                if os.path.exists(os.path.join(photo_dir, photo_file)):
                    student.photo = f"student_photos/{photo_file}"
                    student.save()
                    break

    return imported_count, updated_count, errors

def export_students_to_excel(queryset):
    """
    Generates an openpyxl Workbook matching exact master schema.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Student Database"

    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    thin_border = Border(
        left=Side(style='thin', color='D3D3D3'),
        right=Side(style='thin', color='D3D3D3'),
        top=Side(style='thin', color='D3D3D3'),
        bottom=Side(style='thin', color='D3D3D3')
    )

    headers = [
        "S.No", "Register Number", "Student Name", "Department", "Batch/Year", "Pass-out Year", "Gender",
        "Email Address", "Student Mobile Number", "Parent Mobile Number", "Date of Birth", "Aadhar Number", "Address",
        "History of Arrears – Yes/No", "No. of Arrears",
        "I Semester Marks %", "II Semester Marks %", "III Semester Marks %", "IV Semester Marks %", "V Semester Marks %", "VI Semester Marks %",
        "X Marks %", "XII Marks %", "ITI – Yes/No", "Skills", "Placement Status"
    ]

    ws.append(headers)
    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = align_center

    for idx, s in enumerate(queryset, start=1):
        row = [
            idx,
            s.register_number,
            s.name,
            s.department.code,
            s.batch,
            s.passout_year,
            s.gender,
            s.email or '',
            s.student_mobile or '',
            s.parent_mobile or '',
            s.dob.strftime('%Y-%m-%d') if s.dob else '',
            s.aadhar_number or '',
            s.address or '',
            "Yes" if s.history_of_arrears else "No",
            s.no_of_arrears,
            s.sem1_perc,
            s.sem2_perc,
            s.sem3_perc,
            s.sem4_perc,
            s.sem5_perc,
            s.sem6_perc,
            s.x_perc,
            s.xii_perc,
            "Yes" if s.iti else "No",
            s.skills or '',
            s.get_placement_status_display()
        ]
        ws.append(row)

        row_num = idx + 1
        for col_num in range(1, len(row) + 1):
            cell = ws.cell(row=row_num, column=col_num)
            cell.border = thin_border
            if col_num in [1, 2, 4, 5, 6, 7, 11, 14, 15, 24, 26]:
                cell.alignment = align_center
            else:
                cell.alignment = align_left

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    return wb

def generate_selection_report_excel(records, selected_company):
    import io
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Selection Report"

    # College Title Header
    ws.merge_cells('A1:E1')
    ws['A1'] = "SHREE VENKATESHWARA HI-TECH POLYTECHNIC COLLEGE"
    ws['A1'].font = Font(name='Arial', size=14, bold=True, color='1F4E79')
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')

    ws.merge_cells('A2:E2')
    ws['A2'] = "TRAINING AND PLACEMENT CELL"
    ws['A2'].font = Font(name='Arial', size=11, bold=True, color='D9534F')
    ws['A2'].alignment = Alignment(horizontal='center', vertical='center')

    ws.merge_cells('A4:B4')
    ws['A4'] = f"SALARY : {selected_company.salary_ctc}"
    ws['A4'].font = Font(name='Arial', size=11, bold=True)

    ws.merge_cells('C4:E4')
    ws['C4'] = f"NAME OF THE COMPANY : {selected_company.name.upper()}"
    ws['C4'].font = Font(name='Arial', size=11, bold=True)

    headers = ["S.NO", "REGISTER NUMBER", "STUDENT NAME", "DEPARTMENT", "MOBILE NUMBER"]
    ws.append([])
    ws.append(headers)

    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(name='Arial', size=10, bold=True, color="FFFFFF")
    
    thin_border = Border(
        left=Side(style='thin', color='94A3B8'),
        right=Side(style='thin', color='94A3B8'),
        top=Side(style='thin', color='94A3B8'),
        bottom=Side(style='thin', color='94A3B8')
    )

    for col_num in range(1, 6):
        cell = ws.cell(row=6, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = thin_border

    for idx, rec in enumerate(records, start=1):
        row_num = 6 + idx
        ws.cell(row=row_num, column=1, value=idx).alignment = Alignment(horizontal='center')
        ws.cell(row=row_num, column=2, value=str(rec.student.register_number)).alignment = Alignment(horizontal='center')
        ws.cell(row=row_num, column=3, value=rec.student.name.upper()).alignment = Alignment(horizontal='left')
        ws.cell(row=row_num, column=4, value=rec.student.department.code).alignment = Alignment(horizontal='center')
        ws.cell(row=row_num, column=5, value=str(rec.student.student_mobile or '')).alignment = Alignment(horizontal='center')

        for col_num in range(1, 6):
            cell = ws.cell(row=row_num, column=col_num)
            cell.border = thin_border
            cell.font = Font(name='Arial', size=10)

    ws.column_dimensions['A'].width = 8
    ws.column_dimensions['B'].width = 22
    ws.column_dimensions['C'].width = 35
    ws.column_dimensions['D'].width = 16
    ws.column_dimensions['E'].width = 22

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()

