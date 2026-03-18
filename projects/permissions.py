from rest_framework import permissions

class IsAdminOrTeacher(permissions.BasePermission):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Check against the Choice codes defined in your User model
        return request.user.role in [
            request.user.Role.ADMIN, 
            request.user.Role.TEACHER
        ]