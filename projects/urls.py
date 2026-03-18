from django.urls import path
from .views import RegisterView, UserProfileView, AcademicYearVerificationView, ChangePasswordView

urlpatterns = [
    path('api/register/', RegisterView.as_view(), name='auth_register'),   
    path('api/me/', UserProfileView.as_view(), name='user_profile'),
    path('api/verifications/', AcademicYearVerificationView.as_view(), name='verifications'),
    path('api/change-password/', ChangePasswordView.as_view(), name='change-password'),
]
