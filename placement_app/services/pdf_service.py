import os
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from django.conf import settings

def generate_selection_report_pdf(records, company_name, salary, drive_date, department_code):
    """
    Generates an official Selection Report PDF matching college format.
    SHREE VENKATESHWARA HI-TECH POLYTECHNIC COLLEGE
    TRAINING AND PLACEMENT CELL
    SALARY : ... NAME OF THE COMPANY : ...
    Table: S.No | Register Number | Student Name | Department | Student Photo
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    story = []

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CollegeTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        alignment=1, # Center
        textColor=colors.HexColor('#1F4E79')
    )

    subtitle_style = ParagraphStyle(
        'CollegeSubtitle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        alignment=1, # Center
        textColor=colors.HexColor('#D9534F')
    )

    meta_style = ParagraphStyle(
        'MetaText',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        alignment=0, # Left
        textColor=colors.HexColor('#2C3E50')
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=12,
        alignment=1,
        textColor=colors.white
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=11,
        alignment=1
    )

    # Header
    story.append(Paragraph("SHREE VENKATESHWARA HI-TECH POLYTECHNIC COLLEGE", title_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph("TRAINING AND PLACEMENT CELL", subtitle_style))
    story.append(Spacer(1, 15))

    # Meta banner table
    meta_data = [
        [
            Paragraph(f"<b>SALARY :</b> {salary}", meta_style),
            Paragraph(f"<b>NAME OF THE COMPANY :</b> {company_name}", meta_style)
        ],
        [
            Paragraph(f"<b>DRIVE DATE :</b> {drive_date}", meta_style),
            Paragraph(f"<b>DEPARTMENT :</b> {department_code or 'ALL'}", meta_style)
        ]
    ]

    meta_table = Table(meta_data, colWidths=[260, 260])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F2F4F7')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 15))

    # Selection Table Headers
    table_data = [
        [
            Paragraph("S.No", table_header_style),
            Paragraph("Register Number", table_header_style),
            Paragraph("Student Name", table_header_style),
            Paragraph("Department", table_header_style),
            Paragraph("Student Photo", table_header_style)
        ]
    ]

    for idx, rec in enumerate(records, start=1):
        s = rec.student
        
        # Photo handling
        photo_cell = Paragraph("Photo", table_cell_style)
        photo_path = s.get_photo_path()
        if photo_path and os.path.exists(photo_path):
            try:
                photo_cell = RLImage(photo_path, width=45, height=55)
            except Exception:
                photo_cell = Paragraph("Photo", table_cell_style)

        row = [
            Paragraph(str(idx), table_cell_style),
            Paragraph(s.register_number, table_cell_style),
            Paragraph(s.name, table_cell_style),
            Paragraph(s.department.code, table_cell_style),
            photo_cell
        ]
        table_data.append(row)

    col_widths = [40, 110, 190, 80, 100]
    sel_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    sel_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E79')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    story.append(sel_table)

    doc.build(story)
    pdf_value = buffer.getvalue()
    buffer.close()
    return pdf_value
