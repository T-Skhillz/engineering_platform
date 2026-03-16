from rest_framework import serializers
from projects.models import User, Profile, AcademicYearVerification
from django.db import transaction

class RegisterSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, min_length=8)

     # Profile fields
    institution = serializers.CharField(required=False, allow_blank=True)
    discipline = serializers.CharField(required=False, allow_blank=True)
    academic_year = serializers.ChoiceField(
        choices=Profile.AcademicYear.choices,
        required=False,
        allow_null=True
    )

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password',
            'first_name', 'last_name', 'role',
            'institution', 'discipline', 'academic_year'
        ]
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        with transaction.atomic():
            # Extract profile-specific data
            # Use .pop() to remove them from validated_data so create_user doesn't get confused
            institution = validated_data.pop('institution', '')
            discipline = validated_data.pop('discipline', '')
            academic_year = validated_data.pop('academic_year', None)

            # 1. Create User (Hashed password)
            user = User.objects.create_user(**validated_data)

            # 2. Create Profile linked to User
            Profile.objects.create(
                user=user, 
                institution=institution,
                discipline=discipline,
                academic_year=academic_year
            )
            
            return user

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'email', 'first_name', 'last_name', 'role']
        extra_kwargs = {
            'role': {'read_only': True},  # Users can see their role, but not change it
            'password': {'write_only': True},
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True}
        }

    def update(self, instance, validated_data):
        """Used for PUT/PATCH requests (Profile Updates)"""
        password = validated_data.pop('password', None)
        
        # Update other fields (email, names, etc.)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # If a new password was provided, hash it properly
        if password:
            instance.set_password(password)
            
        instance.save()
        return instance

class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, read_only=True)
    full_name = serializers.ReadOnlyField() #From @property
    class Meta:
        model = Profile
        fields = [
            'id', 
            'user', 
            'full_name', 
            'academic_year', 
            'institution', 
            'discipline', 
            'bio', 
            'avatar_url', 
            'created_at'
            ]
        
class AcademicYearVerificationSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, read_only=True)
    verified_by = UserSerializer(many=False, read_only=True)
    class Meta:
        model = AcademicYearVerification
        fields = [
            'id', 
            'user', 
            'verified_by', 
            'year_granted',
            'note',
            'created_at'
            ]