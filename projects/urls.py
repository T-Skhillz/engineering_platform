from django.urls import path
from .views import (
    RegisterAdminView, RegisterTeacherView, RegisterStudentView,
    ProfileView, VerificationView, ChangePasswordView, LogoutView
)

urlpatterns = [
    path('api/register/admin/', RegisterAdminView.as_view(), name='register-admin'),
    path('api/register/teacher/', RegisterTeacherView.as_view(), name='register-teacher'),
    path('api/register/student/', RegisterStudentView.as_view(), name='register-student'),
    path('api/me/', ProfileView.as_view(), name='user_profile'),
    path('api/verifications/', VerificationView.as_view(), name='verifications'),
    path('api/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('api/logout/', LogoutView.as_view(), name='logout'),
]