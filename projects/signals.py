from django.db.models.signals import post_save
from django.dispatch import receiver
from projects.models import AcademicYearVerification

@receiver(post_save, sender=AcademicYearVerification)
def sync_profile_academic_year(sender, instance, **kwargs):
    """
    Signal to automatically update a User's Profile academic year 
    whenever a new AcademicYearVerification record is created.
    
    This ensures the Profile always reflects the most recent 
    officially granted year.

    We also mark their Matric Number as officially verified.
    """
    # Access the related profile via the User relationship
    profile = instance.user.profile
    
    # Sync the profile's year with the newly verified year
    profile.academic_year = instance.year_granted

    # Mark their Matric Number as officially verified.
    profile.is_matric_verified = True

    # Save the profile to persist the change in the database
    profile.save(update_fields=['academic_year', 'is_matric_verified'])