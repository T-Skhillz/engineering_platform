from rest_framework import serializers
from projects.models import User, Admin, Teacher, Student, Institution, Department

from projects.services.admin_service import create_admin_user
from projects.services.teacher_service import create_teacher_user
from projects.services.student_service import create_student_user


class RegisterAdminSerializer(serializers.ModelSerializer):
    # Explicitly defining these fields to make them 'required' at the API level
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    
    # write_only ensures the password is never sent back in an API response
    password = serializers.CharField(write_only=True, min_length=8)

    # Relational fields to link the Admin to existing Database objects
    institution = serializers.PrimaryKeyRelatedField(
        queryset=Institution.objects.all()
    )
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all()
    )

    staff_number = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 
            'first_name', 'last_name', 
            'institution', 'department', 
            'staff_number',
        ]

    def validate_staff_number(self, value):
        """
        Field-level validation: Ensures staff numbers are unique in the Admin table.
        """
        if Admin.objects.filter(staff_number=value).exists():
            raise serializers.ValidationError(
                "An admin with this staff number already exists."
            )
        return value

    def validate(self, data):
        """
        Object-level validation: Checks the relationship between Institution and Department.
        Prevents a user from picking a Department that doesn't belong to the selected Institution.
        """
        institution = data.get('institution')
        department = data.get('department')

        if department and institution:
            # Check the 'chain': Department -> Faculty -> Institution
            if not department.faculty or department.faculty.institution != institution:
                raise serializers.ValidationError({
                    "department": "This department does not belong to the selected institution."
                })

        return data

    def create(self, validated_data):
        """
        Hands off the actual database insertion to the service function.
        """
        return create_admin_user(validated_data=validated_data)





class RegisterTeacherSerializer(serializers.ModelSerializer):
    # Explicitly defining these fields to make them 'required' at the API level
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    
    # write_only ensures the password is never sent back in an API response
    password = serializers.CharField(write_only=True, min_length=8)

    # Relational fields to link the Teacher to existing Database objects
    institution = serializers.PrimaryKeyRelatedField(
        queryset=Institution.objects.all()
    )
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all()
    )

    staff_number = serializers.CharField(required=True)

    title = serializers.CharField(required=True)
    rank = serializers.ChoiceField(choices=Teacher.RANK_CHOICES, required=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 
            'first_name', 'last_name', 
            'institution', 'department', 
            'staff_number', 'title', 'rank',
        ]

    def validate_staff_number(self, value):
        """
        Field-level validation: Ensures staff numbers are unique in the Teacher table.
        """
        if Teacher.objects.filter(staff_number=value).exists():
            raise serializers.ValidationError(
                "A Teacher with this staff number already exists"
            )
        return value
    
    def validate(self, data):
        """
        Object-level validation: Checks the relationship between Institution and Department.
        Prevents a user from picking a Department that doesn't belong to the selected Institution.
        """
        institution = data.get('institution')
        department = data.get('department')

        if department and institution:
            # Check the 'chain': Department -> Faculty -> Institution
            if department.faculty.institution_id != institution.id:
                raise serializers.ValidationError({
                    "department": "This department does not belong to the selected institution."
                })
        
        return data
    
    def create(self, validated_data):
        """
        Hands off the actual database insertion to the service function.
        """
        return create_teacher_user(validated_data=validated_data)





class RegisterStudentSerializer(serializers.ModelSerializer):
    # Explicitly defining these fields to make them 'required' at the API level
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    
    # write_only ensures the password is never sent back in an API response
    password = serializers.CharField(write_only=True, min_length=8)

    # Relational fields to link the Student to existing Database objects
    institution = serializers.PrimaryKeyRelatedField(
        queryset=Institution.objects.all()
    )
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all()
    )

    matric_number = serializers.CharField(required=True)
    entry_date = serializers.DateField()

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 
            'first_name', 'last_name', 
            'institution', 'department', 
            'matric_number', 'entry_date',
        ]

    def validate_matric_number(self, value):
        """
        Field-level validation: Ensures matric numbers are unique in the Student table.
        """
        if Student.objects.filter(staff_number=value).exists():
            raise serializers.ValidationError(
                "A Student with this matric number already exists"
            )
        return value
    
    def validate(self, data):
        """
        Object-level validation: Checks the relationship between Institution and Department.
        Prevents a user from picking a Department that doesn't belong to the selected Institution.
        """
        institution = data.get('institution')
        department = data.get('department')

        if department and institution:
            # Check the 'chain': Department -> Faculty -> Institution
            if department.faculty.institution_id != institution.id:
                raise serializers.ValidationError({
                    "department": "This department does not belong to the selected institution."
                })
        
        return data
    
    def create(self, validated_data):
        """
        Hands off the actual database insertion to the service function.
        """
        return create_student_user(validated_data=validated_data)











































    # def validate(self, data):
    #     """
    #     Final integrity check before saving to the database.
    #     Ensures roles match identifiers and prevents duplicate matric numbers.
    #     """
    #     role = data.get('role', User.Role.STUDENT)
    #     matric_no = data.get('matric_no', None)

    #     # 1. Role-based Identifier Check
    #     if matric_no and role != User.Role.STUDENT:
    #         raise serializers.ValidationError({
    #             "matric_no": "Only students can have a matriculation number."
    #         })

    #     # 2. Student Requirement Check
    #     if role == User.Role.STUDENT and not matric_no:
    #         raise serializers.ValidationError({
    #             "matric_no": "Students must provide a matriculation number to register."
    #         })

    #     # 3. Manual Uniqueness Check (The "Double Lock")
    #     # We check the Profile table to see if this matric_no is already taken.
    #     if matric_no:
    #         exists = Profile.objects.filter(matric_no=matric_no).exists()
    #         if exists:
    #             raise serializers.ValidationError({
    #                 "matric_no": "A student with this matric number is already registered."
    #             })

    #     return data

    # def create(self, validated_data):
    #     with transaction.atomic():
    #         # Extract profile-specific data
    #         # Use .pop() to remove them from validated_data so create_user doesn't get confused
    #         institution = validated_data.pop('institution', '')
    #         discipline = validated_data.pop('discipline', '')
    #         academic_year = validated_data.pop('academic_year', None)
    #         matric_no = validated_data.pop('matric_no', None)

    #         # 1. Create User (Hashed password)
    #         user = User.objects.create_user(**validated_data)

    #         # 2. Create Profile linked to User
    #         Profile.objects.create(
    #             user=user, 
    #             institution=institution,
    #             discipline=discipline,
    #             academic_year=academic_year,
    #             matric_no=matric_no
    #         )
            
    #         return user

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role']
        extra_kwargs = {
            'role': {'read_only': True},  # Users can see their role, but not change it
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True} 
        }

# class ProfileSerializer(serializers.ModelSerializer):
#     user = UserSerializer(many=False, read_only=True)
#     full_name = serializers.ReadOnlyField() #From @property
#     class Meta:
#         model = Profile
#         fields = [
#             'id', 
#             'user', 
#             'full_name', 
#             'matric_no',
#             'academic_year', 
#             'institution', 
#             'discipline', 
#             'is_matric_verified',
#             'bio', 
#             'avatar_url', 
#             'created_at'
#             ]
#         read_only_fields = ['matric_no']
        
# class AcademicYearVerificationSerializer(serializers.ModelSerializer):
#     user = UserSerializer(many=False, read_only=True)
#     verified_by = UserSerializer(many=False, read_only=True)
    
#     # 'matric_no' is write_only because we only need it to look up the student 
#     # during creation. In the response, the full 'user' object is returned instead.
#     matric_no = serializers.CharField(write_only=True)
#     profile = ProfileSerializer(many=False, read_only=True)

#     class Meta:
#         model = AcademicYearVerification
#         fields = [
#             'id', 
#             'user', 
#             'matric_no',
#             'verified_by', 
#             'year_granted',
#             'note',
#             'created_at',
#             'profile'
#             ]
        
#     def validate_matric_no(self, value):
#         """
#         Field-level validation to resolve a Matric Number string into a User instance.
        
#         This ensures that the provided matric number actually belongs to an 
#         existing student before we attempt to create a verification record.
#         """
#         try:
#             # We perform a reverse lookup: Profile -> User
#             # Using select_related here would optimize this if needed
#             user = User.objects.get(profile__matric_no=value)
            
#         except User.DoesNotExist:
#             # A clear, specific error for the Admin/Teacher
#             raise serializers.ValidationError("No student found with that matric number.")
        
#         # Check if the user already has an associated verification record.
#         # 'verification' is the related_name defined in your AcademicYearVerification model.
#         if hasattr(user, 'verification'):
#             # Prevent duplicate verifications to maintain data integrity.
#             # In a real university system, a student should only have one active 
#             # status per academic cycle.
#             raise serializers.ValidationError(
#                 "This student has already been officially verified for the current period."
#                 )
        
#         # We return the actual User object. DRF is smart enough to pass 
#         # this object into 'validated_data' instead of the raw string.
#         return user

#     def create(self, validated_data):
#         """
#         Custom create method to handle the linked User object and 
#         persist the Verification record.
#         """
#         # Pull the User object we resolved in 'validate_matric_no'
#         user = validated_data.pop('matric_no')
        
#         # Create the verification record linked to the verified student
#         # Note: 'verified_by' is usually passed from the view's perform_create
#         return AcademicYearVerification.objects.create(user=user, **validated_data)
    

class ChangePasswordSerializer(serializers.Serializer):
    """
    Handles secure password updates by validating the current credentials
    before applying the new hashed password.
    """
    # write_only=True ensures passwords never leak into outgoing API responses
    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True, min_length=8)

    def validate_old_password(self, value):
        """
        Security Check: Verifies that the 'old_password' matches the current 
        authenticated user's password in the database.
        """
        user = self.context['request'].user
        
        # Django's check_password() handles the heavy lifting of 
        # comparing the input against the stored PBKDF2 hash.
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def save(self):
        """
        Persists the new password. set_password() automatically handles 
        salting and hashing before saving to the database.
        """
        user = self.context['request'].user
        
        # We use set_password to ensure the new password is encrypted 
        # and not stored as plain text.
        user.set_password(self.validated_data['new_password'])
        user.save()