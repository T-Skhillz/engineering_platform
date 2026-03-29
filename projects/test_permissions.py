import pytest
from unittest.mock import MagicMock
from projects.models import (
    User, Profile, Student, Teacher, Admin,
    Institution, Department, Faculty, Verification, VerificationStatus
)
from projects.permissions import IsAdminOrTeacher, check_teacher_can_verify_student
from rest_framework.test import APIClient


# ===========================================================================
# FIXTURES
# (Mirrors test_verification.py so both files can run independently)
# ===========================================================================

@pytest.fixture
def institution(db):
    return Institution.objects.create(name="University of Lagos", short_name="UNILAG")


@pytest.fixture
def faculty(db, institution):
    return Faculty.objects.create(name="Technology", institution=institution)


@pytest.fixture
def department(db, faculty):
    return Department.objects.create(name="Computer Science and Engineering", faculty=faculty)


@pytest.fixture
def other_department(db, faculty):
    return Department.objects.create(name="Mechanical Engineering", faculty=faculty)


@pytest.fixture
def student_user(db, institution, department):
    user = User.objects.create_user(
        username='timi', email='timi@test.com', password='securepass123',
        first_name='Timi', last_name='Ade', role=User.Role.STUDENT,
    )
    profile = Profile.objects.create(user=user, institution=institution, department=department)
    Student.objects.create(profile=profile, matric_number='ENG/2021/001', entry_date='2021-09-01')
    return user


@pytest.fixture
def teacher_user(db, institution, department):
    user = User.objects.create_user(
        username='prof_john', email='john@test.com', password='securepass123',
        first_name='John', last_name='Doe', role=User.Role.TEACHER,
    )
    profile = Profile.objects.create(user=user, institution=institution, department=department)
    Teacher.objects.create(profile=profile, staff_number='STAFF/001', title='Dr.', rank='Senior Lecturer')
    return user


@pytest.fixture
def teacher_other_dept(db, institution, other_department):
    user = User.objects.create_user(
        username='prof_mech', email='mech@test.com', password='securepass123',
        first_name='Mech', last_name='Teacher', role=User.Role.TEACHER,
    )
    profile = Profile.objects.create(user=user, institution=institution, department=other_department)
    Teacher.objects.create(profile=profile, staff_number='STAFF/002', title='Dr.', rank='Lecturer I')
    return user


@pytest.fixture
def admin_user(db, institution, department):
    user = User.objects.create_user(
        username='admin_user', email='admin@test.com', password='securepass123',
        first_name='Admin', last_name='User', role=User.Role.ADMIN,
    )
    profile = Profile.objects.create(user=user, institution=institution, department=department)
    Admin.objects.create(profile=profile, staff_number='ADMIN/001')
    return user


def make_request(user=None):
    """
    Builds a minimal mock request object.
    has_permission and has_object_permission only need request.user —
    we don't need a full HTTP cycle for unit testing the permission class.
    """
    request = MagicMock()
    request.user = user
    return request


# ===========================================================================
# IsAdminOrTeacher.has_permission
# Covers: line 16 (unauthenticated fallback)
# ===========================================================================

@pytest.mark.django_db
class TestHasPermission:

    def test_unauthenticated_user_is_denied(self):
        """
        Line 16: the early return False for unauthenticated users.
        This path is never hit by the API tests because the JWT
        middleware returns 401 before the permission class fires.
        We test it directly here to cover the branch.
        """
        permission = IsAdminOrTeacher()
        request = make_request(user=MagicMock(is_authenticated=False))
        assert permission.has_permission(request, view=None) is False

    def test_student_is_denied(self, student_user):
        """Students are not in the allowed role list — should return False."""
        permission = IsAdminOrTeacher()
        request = make_request(user=student_user)
        assert permission.has_permission(request, view=None) is False

    def test_teacher_is_allowed(self, teacher_user):
        permission = IsAdminOrTeacher()
        request = make_request(user=teacher_user)
        assert permission.has_permission(request, view=None) is True

    def test_admin_is_allowed(self, admin_user):
        permission = IsAdminOrTeacher()
        request = make_request(user=admin_user)
        assert permission.has_permission(request, view=None) is True


# ===========================================================================
# IsAdminOrTeacher.has_object_permission
# Covers: lines 29-43
# ===========================================================================

@pytest.mark.django_db
class TestHasObjectPermission:

    def _make_verification_obj(self, student_user):
        """
        Builds a minimal mock Verification object.
        has_object_permission only traverses obj.student.profile.department —
        a real Verification instance works fine here since we have the DB.
        """
        verification = MagicMock()
        verification.student = student_user
        return verification

    def test_admin_always_passes_object_check(self, admin_user, student_user):
        """
        Admins bypass all object-level checks.
        Covers the early return True on line 30.
        """
        permission = IsAdminOrTeacher()
        request = make_request(user=admin_user)
        obj = self._make_verification_obj(student_user)
        assert permission.has_object_permission(request, view=None, obj=obj) is True

    def test_teacher_same_department_passes(self, teacher_user, student_user):
        """
        Teacher and student share a department — should return True.
        Covers the happy path inside the teacher branch (lines 34-38).
        """
        permission = IsAdminOrTeacher()
        request = make_request(user=teacher_user)
        obj = self._make_verification_obj(student_user)
        assert permission.has_object_permission(request, view=None, obj=obj) is True

    def test_teacher_different_department_fails(self, teacher_other_dept, student_user):
        """
        Teacher and student are in different departments — should return False.
        Covers the department inequality branch.
        """
        permission = IsAdminOrTeacher()
        request = make_request(user=teacher_other_dept)
        obj = self._make_verification_obj(student_user)
        assert permission.has_object_permission(request, view=None, obj=obj) is False

    def test_attribute_error_returns_false(self, teacher_user):
        """
        If profile or department is missing from the object, the except
        AttributeError branch should catch it and return False instead of 500.
        Covers lines 40-42.
        """
        permission = IsAdminOrTeacher()
        request = make_request(user=teacher_user)

        # A broken object with no student attribute at all
        broken_obj = MagicMock(spec=[])  # spec=[] means no attributes exist
        assert permission.has_object_permission(request, view=None, obj=broken_obj) is False

    def test_non_admin_non_teacher_role_returns_false(self, student_user):
        """
        Covers the final return False on line 43 —
        a role that is neither ADMIN nor TEACHER hits this fallback.
        """
        permission = IsAdminOrTeacher()
        request = make_request(user=student_user)
        obj = self._make_verification_obj(student_user)
        assert permission.has_object_permission(request, view=None, obj=obj) is False


# ===========================================================================
# check_teacher_can_verify_student
# Covers: line 58 (the function itself and all its branches)
# ===========================================================================

@pytest.mark.django_db
class TestCheckTeacherCanVerifyStudent:

    def test_admin_bypasses_check(self, admin_user, student_user):
        """
        Admins are not TEACHER role — the function returns early.
        No exception should be raised.
        """
        # Should not raise
        check_teacher_can_verify_student(admin_user, student_user)

    def test_teacher_same_department_passes(self, teacher_user, student_user):
        """Happy path: same department, no exception raised."""
        check_teacher_can_verify_student(teacher_user, student_user)

    def test_teacher_different_department_raises(self, teacher_other_dept, student_user):
        """
        Core rule: different departments should raise ValueError
        with a descriptive message.
        """
        with pytest.raises(ValueError, match="department mismatch"):
            check_teacher_can_verify_student(teacher_other_dept, student_user)

    def test_teacher_without_department_raises(self, db, institution):
        """
        Edge case: a teacher with no department assigned.
        Should raise ValueError — not silently pass or 500.
        """
        user = User.objects.create_user(
            username='nodept_teacher', email='nodept@test.com', password='pass1234',
            role=User.Role.TEACHER,
        )
        # Profile with no department
        Profile.objects.create(user=user, institution=institution, department=None)

        other_user = User.objects.create_user(
            username='some_student', email='stu@test.com', password='pass1234',
            role=User.Role.STUDENT,
        )
        with pytest.raises(ValueError, match="not assigned to a department"):
            check_teacher_can_verify_student(user, other_user)