from django.db.models import Count, Q, F
from django.db.models.functions import Least
from projects.models import Profile

def get_profile_with_metadata(user):
    """
    Retrieves a Profile with optimized joins and calculates the student's current 
    academic year based on institution session history and program constraints.
    """
    return Profile.objects.select_related(
        'user', 
        'institution', 
        'department', 
        'student_profile', 
        'teacher_profile', 
        'admin_profile',
        'student_profile__profile__department' # Join path required for duration capping
    ).annotate(
        # 1. Calculate how many school sessions have started after the student's entry date.
        # We traverse: Profile -> Student -> Institution -> Sessions.
        calc_academic_year=Count(
            'student_profile__profile__institution__sessions',
            filter=Q(
                student_profile__profile__institution__sessions__start_date__gt=F('student_profile__entry_date')
            ),
            distinct=True
        )
    ).annotate(
        # 2. Cap the academic year so it doesn't exceed the department's program duration.
        # e.g., A 5th-year student in a 4-year course stays 'Year 4' for logic purposes.
        academic_year=Least(
            F('calc_academic_year'),
            F('student_profile__profile__department__programme_duration')
        )
    ).get(user=user)