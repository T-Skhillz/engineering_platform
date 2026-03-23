from django.db import transaction
from projects.models import User, Profile, Admin

def create_admin_user(*, validated_data):
    """
    Orchestrates the creation of a User, their Profile, and their Admin record.
    
    This function ensures that an Admin is never created without a corresponding 
    Profile and Staff Number. Using @transaction.atomic ensures that if any 
    part of this process fails, no partial data is saved.
    
    Args:
        validated_data (dict): Cleaned data from a serializer or form.
        
    Returns:
        User: The newly created User instance.
    """
    
    # We use 'atomic' so that if Profile creation fails, the User isn't left hanging.
    with transaction.atomic():
        
        # 1. Extract (pop) non-User fields. 
        # We remove these so we can pass the remaining dictionary directly to create_user().
        institution = validated_data.pop('institution')
        department = validated_data.pop('department')
        staff_number = validated_data.pop('staff_number')

        # 2. Create the base Identity (The User)
        # create_user handles password hashing automatically.
        user = User.objects.create_user(**validated_data)
        user.role = User.Role.ADMIN
        user.save()

        # 3. Create the Personal Data layer (The Profile)
        # Links the User to their organizational metadata.
        profile = Profile.objects.create(
            user=user,
            institution=institution,
            department=department,
        )

        # 4. Create the Professional Identity (The Admin)
        # Final step: assigning the staff number to the profile.
        Admin.objects.create(
            profile=profile,
            staff_number=staff_number,
        )

        return user