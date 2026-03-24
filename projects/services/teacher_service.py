from django.db import transaction
from projects.models import User, Profile, Teacher

def create_teacher_user(*, validated_data):
    """
    Handles the creation of a User, their Profile, and their Teacher record.

    This function ensures that a teacher is never created without a corresponding
    Profile and Staff Number. Using @transaction.atomic ensures that if any part
    of this proces fails, no partial data is saved 

    Args:
         validated_data (dict): Cleaned data from a serializer or form.

    Returns:
        User: The newly created User instance.
    """

    with transaction.atomic():

        # 1. Pop non-User fields.
        institution = validated_data.pop('institution', None)
        department = validated_data.pop('department', None)
        staff_number = validated_data.pop('staff_number', None)
        title = validated_data.pop('title', None)
        rank = validated_data.pop('rank', None)

        # 2. Validation check to ensure all three pieces of data are present
        if not all([institution, department, staff_number]):
            raise ValueError("Missing required teacher fields")

        # 3. Create the base Identity (The User)
        user = User.objects.create_user(
            **validated_data,
            role=User.Role.TEACHER
            )

        # 4. Create the Personal Data layer (The profile)
        profile = Profile.objects.create(
            user=user,
            institution=institution,
            department=department,
        )

        # 5. Create the professional Identity (The Teacher)
        Teacher.objects.create(
            profile=profile,
            staff_number=staff_number,
            title=title,
            rank=rank,
        )

        return user