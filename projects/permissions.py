from rest_framework import permissions

class IsAdminOrTeacher(permissions.BasePermission):
    """
    Custom permission to allow access to Admins or Teachers.
    - Admins have full access.
    - Teachers can only access objects belonging to students in their own department.
    """

    def has_permission(self, request, view):
        """
        Global check: Is the user authenticated and assigned a valid role?
        """
        # Ensure the user is logged in before checking roles
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Grant access if the user's role is either ADMIN or TEACHER
        return request.user.role in [
            request.user.Role.ADMIN, 
            request.user.Role.TEACHER
        ]

    def has_object_permission(self, request, view, obj):
        """
        Object-level check: Determine if the specific record can be accessed.
        """
        # Admins bypass specific object ownership/department checks
        if request.user.role == request.user.Role.ADMIN:
            return True

        # Teacher Logic: Only allow access if the teacher and student share a department
        if request.user.role == request.user.Role.TEACHER:
            try:
                teacher_dept = request.user.profile.department
                student_dept = obj.student.profile.department
                
                return teacher_dept == student_dept
            except AttributeError:
                # Fallback if a profile or department is missing to prevent 500 errors
                return False

        return False