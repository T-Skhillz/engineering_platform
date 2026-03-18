from django.shortcuts import get_object_or_404
from projects.models import Profile, AcademicYearVerification
from projects.serializers import RegisterSerializer, ProfileSerializer, AcademicYearVerificationSerializer, ChangePasswordSerializer
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from projects.permissions import IsAdminOrTeacher
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny] #Allow anyone to register

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        #1. Validate data
        serializer.is_valid(raise_exception=True)

        #2. Trigger the create() method in RegisterSerializer
        user = serializer.save()

        #3. Return a custom success message
        return Response({
            'user': {
                'username': user.username,
                'email': user.email,
                'role': user.role,
            },
            'message': 'User and Profile created successfully.'
        }, status=status.HTTP_201_CREATED)
    
class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    GET: Returns the logged-in user's profile.
    PATCH: Allows the user to update their own profile.
    """
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        # It finds the profile where the 'user' matches the person logged in.
        profile = get_object_or_404(Profile, user=self.request.user)
        return profile
    
class AcademicYearVerificationView(generics.ListCreateAPIView):
    """
    GET:  Admin/Teacher views verifications.
    POST: Admin/Teacher creates a verification for a student.
    """
    serializer_class = AcademicYearVerificationSerializer
    permission_classes = [IsAuthenticated, IsAdminOrTeacher]

    def get_queryset(self):
        # Get the currently authenticated user making the request
        user = self.request.user

        # Admins can view all academic year verification records
        if user.role == user.Role.ADMIN:
            return AcademicYearVerification.objects.all()

        # Teachers can only view verification records belonging
        # to users within the same academic discipline
        if user.role == user.Role.TEACHER:
            teacher_discipline = getattr(user.profile, 'discipline', None)
            return AcademicYearVerification.objects.filter(
                user__profile__discipline=teacher_discipline
            )

        # Any other role has no permission to view these records
        return AcademicYearVerification.objects.none()

    def perform_create(self, serializer):
        serializer.save(verified_by=self.request.user)


class ChangePasswordView(generics.UpdateAPIView):
    """
    Updates the user's password, invalidates the current session, 
    and returns fresh authentication tokens.
    """
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        # 1. Validate 'old_password' and hash/save 'new_password'
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # 2. Security: Invalidate the old session to prevent replay attacks
        try:
            old_refresh_token = request.data.get('refresh_token')
            if old_refresh_token:
                token = RefreshToken(old_refresh_token)
                token.blacklist()
        except (TokenError, AttributeError):
            # If token is missing, expired, or invalid, we skip blacklisting
            pass

        # 3. UX: Issue fresh tokens so the user remains logged in seamlessly
        new_refresh = RefreshToken.for_user(request.user)

        return Response({
            'message': 'Password updated successfully.',
            'access': str(new_refresh.access_token),
            'refresh': str(new_refresh),
        }, status=status.HTTP_200_OK)
    