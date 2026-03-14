from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = 'ST', 'Student'
        TEACHER = 'TE', 'Teacher'
        ADMIN = 'AD', 'Administrator'

    email = models.EmailField(max_length=254, unique=True)

    role = models.CharField(
        max_length=2,
        choices=Role.choices,
        default=Role.STUDENT,
    )

    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']

    def __str__(self):
        return self.username
    
class Profile(models.Model):
    class AcademicYear(models.IntegerChoices):
        LEVEL_100 = 100, '100 Level'
        LEVEL_200 = 200, '200 Level'
        LEVEL_300 = 300, '300 Level'
        LEVEL_400 = 400, '400 Level'
        LEVEL_500 = 500, '500 Level'
        LEVEL_600 = 600, '600 Level'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=255)

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

    def __str__(self):
        return f"{self.full_name} ({self.user.username})"

class AcademicYearVerification(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='verification')
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="verifications_made")
    year_granted = models.PositiveSmallIntegerField(
        choices=Profile.AcademicYear.choices
    )
    note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} verified as {self.year_granted}"
    
class TokenBlacklist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blacklisted_tokens')
    jti = models.CharField(max_length=36, unique=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Revoked token for {self.user.username}"