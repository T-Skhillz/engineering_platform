from django.db import transaction
from projects.models import User, Profile, Student

def create_student_user(*, validated_data):
    """
    Handles the creation of a User, their Profile, and their Student record.

    This function ensures that a student is never created without a corresponding
    Profile and Matric Number. Using @transaction.atomic ensures that if any part
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
        matric_number = validated_data.pop('matric_number', None)
        entry_date = validated_data.pop('entry_date', None)

        # 2. Validation check to ensure all pieces of data are present
        if not all([institution, department, matric_number, entry_date]):
            raise ValueError("Missing required student fields")

        # 3. Create the base Identity (The User)
        user = User.objects.create_user(
            **validated_data,
            role=User.Role.STUDENT
            )
        
        # 4. Create the Personal Data layer (The profile)
        profile = Profile.objects.create(
            user=user,
            institution=institution,
            department=department,
        )

        # 5. Create the academic Identity (The Student)
        Student.objects.create(
            profile=profile,            
            matric_number=matric_number,
            entry_date=entry_date,
        )

        return user