import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

# Create your models here.



#-----------------------------------------------------------------------------------------------
#SCHOOL ENTITIES
#-----------------------------------------------------------------------------------------------

class Institution(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        verbose_name = "Institution"
        verbose_name_plural = "Institutions"

    def __str__(self):
        return f"{self.name}"

class Faculty(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='faculties')
    name = models.CharField(max_length=150)

    class Meta:
        verbose_name = "Faculty"
        verbose_name_plural = "Faculties"

    def __str__(self):
        return f"{self.name}"

class Department(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name='departments')
    name = models.CharField(max_length=150)

    class Meta:
        verbose_name = "Department"
        verbose_name_plural = "Departments"

    def __str__(self):
        return f"{self.name}"
    
class Course(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='courses')
    title = models.CharField(max_length=200)
    course_code = models.CharField(max_length=15, unique=True)

    class Meta:
        verbose_name = "Course"
        verbose_name_plural = "Courses"

    def __str__(self):
        return f"{self.course_code} — {self.title}"
    
class Session(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='sessions')
    name = models.CharField(max_length=15)
    start_date = models.DateField()
    end_date = models.DateField()
    activated_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Session"
        verbose_name_plural = "Sessions"
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.name}"
    
class Semester(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='semesters')
    name = models.CharField(max_length=20)
    start_date = models.DateField()
    end_date = models.DateField()
    activated_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Semester"
        verbose_name_plural = "Semesters"
        ordering = ['start_date']

    def __str__(self):
        return f"{self.name}"
    

#------------------------------------------------------------------------------------
# VERIFICATION STATUS
#------------------------------------------------------------------------------------
class VerificationStatus(models.TextChoices):
    PENDING = 'PENDING', _('Pending')
    VERIFIED = 'VERIFIED', _('Verified')
    REJECTED = 'REJECTED', _('Rejected')


#--------------------------------------------------------------------------------------------------------------
# ACTOR ENTITIES
#--------------------------------------------------------------------------------------------------------------

class User(AbstractUser):
    # This overrides the default 'id' field
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )

    email = models.EmailField(max_length=254, unique=True)

    # Fields prompted for when running 'python manage.py createsuperuser' 
    # (username and password are required by default and shouldn't be included here)
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']

    def __str__(self):
        return self.username

#Model for user profile info    
class Profile(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )

    #User one-to-one relationship with Profile
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='profile', 
    )

    institution = models.ForeignKey(Institution, on_delete=models.SET_NULL, null=True, blank=True, related_name='institution_profiles')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='deparment_profiles')
    bio = models.TextField(blank=True, null=True)
    avatar_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def full_name(self):
        """
        Returns the user's full name from the related User model.
        Prevents data redundancy by not storing the name twice.
        """
        name = f"{self.user.first_name} {self.user.last_name}".strip()
        return name or self.user.username

    def __str__(self):
        return f"{self.full_name} ({self.user.username})"


    class Meta:
        verbose_name = "Profile"
        verbose_name_plural = "Profiles"
        #Order by most recent profile
        ordering = ['-created_at']

class Admin(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='admin')
    staff_number = models.CharField(max_length=30, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # 3. Should the admin table have a rank/title attribute?

    def __str__(self):
        return f"{self.profile.full_name}"
    
    class Meta:
        verbose_name = "Administrator"
        verbose_name_plural = "Administrators"
        ordering = ['-created_at']

class Teacher(models.Model):
    # Phase 1: Common ranks as a guide, not a restriction
    RANK_CHOICES = [
        ('Professor', 'Professor'),
        ('Associate Professor', 'Associate Professor / Reader'),
        ('Senior Lecturer', 'Senior Lecturer'),
        ('Lecturer I', 'Lecturer I'),
        ('Lecturer II', 'Lecturer II'),
        ('Assistant Lecturer', 'Assistant Lecturer'),
        ('Graduate Assistant', 'Graduate Assistant'),
        ('Other', 'Other'),
    ]

    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='teacher')
    title = models.CharField(max_length=50)
    rank = models.CharField(max_length=100, choices=RANK_CHOICES, default='Lecturer II')
    staff_number = models.CharField(max_length=30, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.profile.full_name}"
    
    class Meta:
        verbose_name = "Teacher"
        verbose_name_plural = "Teachers"
        ordering = ['-created_at']

class Student(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='student')
    matric_number = models.CharField(max_length=30, unique=True)
    # 1. remember to write a regex validator for the matric and staff number
    entry_date = models.DateField()

    # Verification Logic
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.matric_number} - {self.verification_status}"
    

#--------------------------------------
# VERIFICATION
#--------------------------------------
class Verification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # The student being verified
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verifications')
    
    # SET_NULL — record survives if verifier leaves the platform
    verifier = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='verifications_made')
    
    session = models.ForeignKey(Session, on_delete=models.SET_NULL, null=True, related_name='verifications')
    
    status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} — {self.status}"

    class Meta:
        verbose_name = "Verification"
        verbose_name_plural = "Verifications"
        ordering = ['-created_at']









# class RoleTransition(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     from_role = models.CharField(choices=Role.choices)
#     to_role = models.CharField(choices=Role.choices)
#     transitioned_at = models.DateTimeField(null=True, blank=True)
#     transitioned_by = models.ForeignKey(User, ...)

# Phase 8 — add RoleTransition table
# Reason: Student → Alumni transition on graduation (manual Admin action).
# Table uses FK not OneToOne because one user can have multiple 
# transition events over time.