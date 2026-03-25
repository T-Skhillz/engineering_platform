from django.shortcuts import get_object_or_404
from projects.models import Profile, Verification
from projects.serializers import RegisterAdminSerializer, RegisterTeacherSerializer, RegisterStudentSerializer, ProfileSerializer, VerificationSerializer, ChangePasswordSerializer
from rest_framework import generics, status

from rest_framework.permissions import AllowAny, IsAuthenticated
from projects.permissions import IsAdminOrTeacher

from rest_framework.response import Response

from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken





class RegisterAdminView(generics.CreateAPIView):
    serializer_class = RegisterAdminSerializer
    permission_classes = [AllowAny] #Allow anyone to register

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        #1. Validate data
        serializer.is_valid(raise_exception=True)

        #2. Trigger the create() method in RegisterAdminSerializer
        user = serializer.save()

        #3. Return a custom success message
        return Response({
            'user': {
                'username': user.username,
                'email': user.email,
                'role': user.role,
            },
            'message': 'User and Profile for Admin created successfully.'
        }, status=status.HTTP_201_CREATED)





class RegisterTeacherView(generics.CreateAPIView):
    serializer_class = RegisterTeacherSerializer
    permission_classes = [AllowAny] #Allow anyone to register

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        #1. Validate data
        serializer.is_valid(raise_exception=True)

        #2. Trigger the create() method in RegisterAdminSerializer
        user = serializer.save()

        #3. Return a custom success message
        return Response({
            'user': {
                'username': user.username,
                'email': user.email,
                'role': user.role,
            },
            'message': 'User and Profile for Teacher created successfully.'
        }, status=status.HTTP_201_CREATED)






class RegisterStudentView(generics.CreateAPIView):
    serializer_class = RegisterStudentSerializer
    permission_classes = [AllowAny] #Allow anyone to register

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        #1. Validate data
        serializer.is_valid(raise_exception=True)

        #2. Trigger the create() method in RegisterAdminSerializer
        user = serializer.save()

        #3. Return a custom success message
        return Response({
            'user': {
                'username': user.username,
                'email': user.email,
                'role': user.role,
            },
            'message': 'User and Profile for Student created successfully.'
        }, status=status.HTTP_201_CREATED)






class ProfileView(generics.RetrieveUpdateAPIView):
    """
    API endpoint for the current user to view or update their own profile.
    
    Methods:
    - GET: Retrieve profile details for the authenticated user.
    - PATCH: Partially update profile fields (e.g., bio, avatar).
    """

    # Explicitly restrict methods to prevent full PUT updates or deletions
    http_method_names = ['get', 'patch', 'head', 'options']

    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """
        Overrides the default behavior to ensure a user can only 
        access the profile associated with their account.
        
        This eliminates the need for a lookup URL kwarg (like /profile/<id>/)
        and prevents unauthorized access to other users' data.
        """
        # # Fetch the profile linked to the logged-in user
        profile = get_object_or_404(Profile, user=self.request.user)
        return profile





class VerificationView(generics.ListCreateAPIView):
    """
    Handles listing and creating verification records.
    - LIST: Returns records based on user role (Admin=All, Teacher=Department).
    - CREATE: Records a new verification and automatically logs the creator.
    """
    serializer_class = VerificationSerializer
    permission_classes = [IsAuthenticated, IsAdminOrTeacher]

    def get_queryset(self):
        """
        Dynamically filters the available records based on the user's role.
        This ensures data isolation between different departments.
        """
        user = self.request.user

        # Admin Override: Grant visibility into every record in the system
        if user.role == user.Role.ADMIN:
            return Verification.objects.all()

        # Departmental Filter: Restrict Teachers to seeing only 'their' students.
        # We traverse Verification -> User -> Profile -> Department.
        if user.role == user.Role.TEACHER:
            teacher_department = getattr(user.profile, 'department', None)
            return Verification.objects.filter(
                student__profile__department=teacher_department
            ).select_related('student__profile') # Optimization to reduce DB hits

        # Security Fallback: If role is undefined, return an empty set
        return Verification.objects.none()

    def perform_create(self, serializer):
        """
        Automatically assigns the currently logged-in Admin/Teacher 
        as the verifier for the record.
        """
        # Inject the current user into the 'verified_by' field during save
        serializer.save(verifier=self.request.user)


class ChangePasswordView(generics.UpdateAPIView):
    """
    Updates the user's password, invalidates the current session, 
    and returns fresh authentication tokens.
    
    ⚠️Security note: blacklisting is best-effort. If the client does not
    send 'refresh_token', the password still updates and fresh tokens
    are issued. This is intentional — we prioritise UX over forced
    session invalidation for this platform's threat model.
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


class LogoutView(generics.GenericAPIView):
    """
    An idempotent endpoint to terminate a user session by blacklisting
    the provided refresh token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            
            # If a token is provided, attempt to invalidate it in the database.
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()

            # Idempotent logout: all paths return 200 because the end
            # result is the same regardless of token state — session is over.
            return Response(
                {'message': 'Logged out successfully.'}, 
                status=status.HTTP_200_OK
            )

        except (TokenError, AttributeError):
            # We catch errors (like expired or malformed tokens) but still 
            # return 200. If the token is already invalid, the user is 
            # technically already "logged out."
            return Response(
                {'message': 'Session ended.'}, 
                status=status.HTTP_200_OK
            )