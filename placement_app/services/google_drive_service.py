import os
import shutil
from django.conf import settings
from placement_app.models import Student

def get_google_drive_photos_dir():
    """
    Returns the designated Google Drive sync directory for student photos.
    Default: media/google_drive_sync/ or custom Google Drive Desktop path.
    """
    drive_dir = getattr(settings, 'GOOGLE_DRIVE_PHOTOS_DIR', os.path.join(settings.MEDIA_ROOT, 'google_drive_photos'))
    os.makedirs(drive_dir, exist_ok=True)
    return drive_dir

def sync_student_photo_to_google_drive(student):
    """
    Ensures the student's photo is saved in the Google Drive folder named as <Register_Number>.<ext>
    e.g. 24213946.jpg
    """
    if not student.photo or not os.path.exists(student.photo.path):
        return None

    gdrive_dir = get_google_drive_photos_dir()
    ext = os.path.splitext(student.photo.path)[1].lower() or '.jpg'
    gdrive_filename = f"{student.register_number}{ext}"
    target_path = os.path.join(gdrive_dir, gdrive_filename)

    shutil.copy2(student.photo.path, target_path)
    return target_path

def sync_all_photos_to_google_drive():
    """
    Syncs all existing student photos into Google Drive folder structure.
    """
    students = Student.objects.exclude(photo='')
    synced_count = 0
    for s in students:
        if sync_student_photo_to_google_drive(s):
            synced_count += 1
    return synced_count
