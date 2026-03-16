import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

#Model for user with roles(student, teacher, and admin)
class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = 'ST', 'Student'
        TEACHER = 'TE', 'Teacher'
        ADMIN = 'AD', 'Administrator'

    # This overrides the default 'id' field
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )

    email = models.EmailField(max_length=254, unique=True)

    role = models.CharField(
        max_length=2,
        choices=Role.choices,
        default=Role.STUDENT,
    )

    # Fields prompted for when running 'python manage.py createsuperuser' 
    # (username and password are required by default and shouldn't be included here)
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']

    def __str__(self):
        return self.username

#Model for user profile info    
class Profile(models.Model):
    class AcademicYear(models.IntegerChoices):
        LEVEL_100 = 100, '100 Level'
        LEVEL_200 = 200, '200 Level'
        LEVEL_300 = 300, '300 Level'
        LEVEL_400 = 400, '400 Level'
        LEVEL_500 = 500, '500 Level'
        LEVEL_600 = 600, '600 Level'

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

    academic_year = models.PositiveSmallIntegerField(
        choices=AcademicYear.choices,
        null=True,
        blank=True,
    )

    institution = models.CharField(max_length=255, blank=True)
    discipline = models.CharField(max_length=150, blank=True)
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

#Model for verification of user by admin
class AcademicYearVerification(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='verification')
    
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )

    #NOTE: verified_by must have Role.Admin or Role.Teacher status
    #Using SET_NULL on verified_by ensures that even if a Teacher leaves the platform, the Student's verification record remains intact.
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="verifications_made")
    
    year_granted = models.PositiveSmallIntegerField(
        choices=Profile.AcademicYear.choices
    )
    note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} verified as {self.year_granted}"
    
    class Meta:
        verbose_name = "Academic Verification"
        verbose_name_plural = "Academic Verifications"
        #Order by most recent verification
        ordering = ['-created_at']