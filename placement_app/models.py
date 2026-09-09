import os
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User

class Department(models.Model):
    code = models.CharField(max_length=10, unique=True, help_text="e.g. DME, EEE, ECE, CSE, CIVIL")
    name = models.CharField(max_length=100, help_text="e.g. Diploma in Mechanical Engineering")

    def __str__(self):
        return f"{self.code} - {self.name}"

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('ADMIN', 'Admin / Placement Officer'),
        ('STAFF', 'Staff / Department Coordinator'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='ADMIN')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    phone = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_placement_officer(self):
        return self.role == 'ADMIN' or self.user.is_superuser

def student_photo_upload_path(instance, filename):
    """
    Saves student photo as Register Number filename e.g., 24213946.jpg inside student_photos folder.
    This guarantees compatibility with Google Drive photo sync folders.
    """
    ext = filename.split('.')[-1].lower() if '.' in filename else 'jpg'
    if ext not in ['jpg', 'jpeg', 'png', 'webp']:
        ext = 'jpg'
    return f"student_photos/{instance.register_number}.{ext}"

class Student(models.Model):
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('UNPLACED', 'Unplaced'),
        ('PLACED', 'Placed'),
        ('HIGHER_STUDIES', 'Higher Studies'),
        ('ENTREPRENEUR', 'Entrepreneur'),
    ]

    s_no = models.AutoField(primary_key=True)
    register_number = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='students')
    batch = models.CharField(max_length=20, default="2024-2027", help_text="e.g. 2024-2027")
    passout_year = models.IntegerField(default=2026)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='Male')
    
    # Contact
    email = models.EmailField(blank=True, null=True)
    student_mobile = models.CharField(max_length=15, blank=True)
    parent_mobile = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    
    # Personal
    dob = models.DateField(null=True, blank=True)
    aadhar_number = models.CharField(max_length=20, blank=True)
    
    # Academic
    history_of_arrears = models.BooleanField(default=False, verbose_name="History of Arrears (Yes/No)")
    no_of_arrears = models.IntegerField(default=0, verbose_name="No. of Arrears")
    sem1_perc = models.FloatField(default=0.0, verbose_name="I Semester Marks %")
    sem2_perc = models.FloatField(default=0.0, verbose_name="II Semester Marks %")
    sem3_perc = models.FloatField(default=0.0, verbose_name="III Semester Marks %")
    sem4_perc = models.FloatField(default=0.0, verbose_name="IV Semester Marks %")
    sem5_perc = models.FloatField(default=0.0, verbose_name="V Semester Marks %")
    sem6_perc = models.FloatField(default=0.0, verbose_name="VI Semester Marks %")
    x_perc = models.FloatField(default=0.0, verbose_name="X Marks %")
    xii_perc = models.FloatField(default=0.0, verbose_name="XII Marks %")
    iti = models.BooleanField(default=False, verbose_name="ITI (Yes/No)")
    
    # Profile & Status
    skills = models.TextField(blank=True)
    photo = models.ImageField(upload_to=student_photo_upload_path, blank=True, null=True)
    resume = models.FileField(upload_to='student_resumes/', blank=True, null=True)
    placement_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UNPLACED')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['register_number']

    def __str__(self):
        return f"{self.register_number} - {self.name} ({self.department.code})"

    @property
    def avg_sem_perc(self):
        sems = [self.sem1_perc, self.sem2_perc, self.sem3_perc, self.sem4_perc, self.sem5_perc, self.sem6_perc]
        valid_sems = [s for s in sems if s > 0]
        if valid_sems:
            return round(sum(valid_sems) / len(valid_sems), 2)
        return 0.0

    def get_photo_path(self):
        """
        Returns full local filesystem path to student's photo if present.
        Auto-detects photo matching register_number in media/student_photos/ if DB field is empty or missing.
        """
        if self.photo:
            try:
                if os.path.exists(self.photo.path):
                    return self.photo.path
            except Exception:
                pass

        # Check external Google Drive folder if configured in settings
        gdrive_dir = getattr(settings, 'GOOGLE_DRIVE_PHOTOS_DIR', None)
        if gdrive_dir and os.path.exists(gdrive_dir):
            for ext in ['png', 'jpg', 'jpeg', 'webp', 'PNG', 'JPG', 'JPEG']:
                full_path = os.path.join(gdrive_dir, f"{self.register_number}.{ext}")
                if os.path.exists(full_path):
                    return full_path

        photos_dir = os.path.join(settings.MEDIA_ROOT, 'student_photos')
        if os.path.exists(photos_dir):
            for ext in ['png', 'jpg', 'jpeg', 'webp', 'PNG', 'JPG', 'JPEG']:
                rel_path = f"student_photos/{self.register_number}.{ext}"
                full_path = os.path.join(settings.MEDIA_ROOT, rel_path)
                if os.path.exists(full_path):
                    try:
                        self.photo = rel_path
                        self.save(update_fields=['photo'])
                    except Exception:
                        pass
                    return full_path
        return None

    @property
    def has_photo(self):
        return self.get_photo_path() is not None

    @property
    def photo_url(self):
        path = self.get_photo_path()
        if path:
            if self.photo and hasattr(self.photo, 'url') and self.photo.name:
                return self.photo.url
            rel_name = os.path.basename(path)
            return f"{settings.MEDIA_URL}student_photos/{rel_name}"
        return '/static/images/default_avatar.png'

class Company(models.Model):
    company_id = models.CharField(max_length=20, unique=True, help_text="e.g. COMP-001")
    name = models.CharField(max_length=150)
    address = models.TextField(blank=True)
    hr_name = models.CharField(max_length=100, blank=True)
    hr_contact = models.CharField(max_length=15, blank=True)
    hr_email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    industry = models.CharField(max_length=100, blank=True, help_text="e.g. Automotive, Electronics, Manufacturing")
    job_role = models.CharField(max_length=100, default="Diploma Trainee")
    eligible_departments = models.ManyToManyField(Department, related_name='eligible_companies')
    qualification = models.CharField(max_length=100, default="Diploma")
    min_percentage = models.FloatField(default=0.0, help_text="Minimum Semester % required")
    max_arrears = models.IntegerField(default=0, help_text="Maximum allowed arrears")
    salary_ctc = models.CharField(max_length=50, help_text="e.g. ₹2.80 LPA")
    job_location = models.CharField(max_length=100, default="Chennai")
    drive_date = models.DateField()
    last_date_registration = models.DateField(null=True, blank=True)
    selection_process = models.TextField(blank=True, default="1. Aptitude Test\n2. Technical Interview\n3. HR Interview")
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Companies"
        ordering = ['-drive_date']

    def __str__(self):
        return f"{self.name} ({self.salary_ctc})"

class PlacementDrive(models.Model):
    STATUS_CHOICES = [
        ('UPCOMING', 'Upcoming'),
        ('ONGOING', 'Ongoing'),
        ('COMPLETED', 'Completed'),
    ]
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='drives')
    title = models.CharField(max_length=200, help_text="e.g. HYUNDAI Campus Drive 2026")
    drive_date = models.DateField()
    salary_ctc = models.CharField(max_length=50, help_text="e.g. 2.80 LPA")
    job_role = models.CharField(max_length=100, default="Diploma Trainee")
    eligible_departments = models.ManyToManyField(Department, related_name='drives')
    min_percentage = models.FloatField(default=0.0)
    max_arrears = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ONGOING')
    remarks = models.TextField(blank=True)

    def __str__(self):
        return f"{self.company.name} - {self.job_role} ({self.drive_date})"

class InterviewRecord(models.Model):
    STAGE_CHOICES = [
        ('REGISTERED', 'Registered'),
        ('ATTENDED', 'Attended'),
        ('SELECTED', 'Selected'),
        ('REJECTED', 'Rejected'),
        ('JOINED', 'Joined'),
        ('OPTED_OUT', 'Opted Out'),
    ]

    ROUND_RESULT = [
        ('PENDING', 'Pending'),
        ('PASS', 'Pass'),
        ('FAIL', 'Fail'),
        ('NA', 'N/A'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='interview_records')
    drive = models.ForeignKey(PlacementDrive, on_delete=models.CASCADE, related_name='interview_records')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='interview_records')
    
    interview_attended = models.BooleanField(default=True, verbose_name="Interview Attended (Yes/No)")
    aptitude = models.CharField(max_length=10, choices=ROUND_RESULT, default='PENDING')
    technical = models.CharField(max_length=10, choices=ROUND_RESULT, default='PENDING')
    hr = models.CharField(max_length=10, choices=ROUND_RESULT, default='PENDING')
    final_result = models.CharField(max_length=20, choices=STAGE_CHOICES, default='SELECTED')
    
    salary = models.CharField(max_length=50, blank=True, help_text="e.g. 2.80 LPA")
    job_role = models.CharField(max_length=100, blank=True, help_text="e.g. Trainee")
    location = models.CharField(max_length=100, blank=True, help_text="e.g. Chennai")
    joining_date = models.DateField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'drive')
        ordering = ['student__register_number']

    def __str__(self):
        return f"{self.student.register_number} - {self.company.name} ({self.final_result})"
