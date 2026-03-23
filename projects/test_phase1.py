import pytest
from rest_framework.test import APIClient
from projects.models import User, Profile


# ===========================================================================
# FIXTURES
# ===========================================================================

@pytest.fixture
def api_client():
    """
    A bare, unauthenticated API client.
    Think of this as a browser that hasn't logged in yet.
    """
    return APIClient()


@pytest.fixture
def student_payload():
    """
    A valid, complete registration payload for a student.
    Defined once here so every test that needs it gets the same
    clean base data — no copy-pasting across tests.
    """
    return {
        'username': 'timi',
        'email': 'timi@test.com',
        'password': 'securepass123',
        'first_name': 'Timi',
        'last_name': 'Ade',
        'role': 'ST',
        'matric_no': 'ENG/2021/001',
        'institution': 'University of Lagos',
        'discipline': 'Computer Engineering',
        'academic_year': 100,
    }

@pytest.fixture
def teacher_payload():
    """
    A valid registration payload for a teacher.
    Teachers don't have matric numbers — that distinction
    is enforced by your RegisterSerializer validation logic.
    """
    return {
        'username': 'prof_john',
        'email': 'john@test.com',
        'password': 'securepass123',
        'first_name': 'John',
        'last_name': 'Doe',
        'role': 'TE',
        'institution': 'University of Lagos',
        'discipline': 'Computer Engineering',
    }


@pytest.fixture
def admin_payload():
    """A valid registration payload for an admin."""
    return {
        'username': 'admin_user',
        'email': 'admin@test.com',
        'password': 'securepass123',
        'first_name': 'Admin',
        'last_name': 'User',
        'role': 'AD',
        'institution': 'University of Lagos',
        'discipline': 'Administration',
    }

@pytest.fixture
def student_user(db, student_payload):
    """
    A fully created student User + Profile in the database.

    'db' is a built-in pytest-django fixture that does two things:
    1. Grants this fixture permission to touch the database
    2. Wraps each test in a transaction that rolls back when the test
       finishes — so every test starts with a clean slate, no leftover
       data from previous tests bleeding in.
    """
    user = User.objects.create_user(
        username=student_payload['username'],
        email=student_payload['email'],
        password=student_payload['password'],
        first_name=student_payload['first_name'],
        last_name=student_payload['last_name'],
        role=User.Role.STUDENT,
    )
    Profile.objects.create(
        user=user,
        matric_no=student_payload['matric_no'],
        institution=student_payload['institution'],
        discipline=student_payload['discipline'],
        academic_year=student_payload['academic_year'],
    )
    return user


@pytest.fixture
def teacher_user(db, teacher_payload):
    """A fully created teacher User + Profile in the database."""
    user = User.objects.create_user(
        username=teacher_payload['username'],
        email=teacher_payload['email'],
        password=teacher_payload['password'],
        first_name=teacher_payload['first_name'],
        last_name=teacher_payload['last_name'],
        role=User.Role.TEACHER,
    )
    Profile.objects.create(
        user=user,
        institution=teacher_payload['institution'],
        discipline=teacher_payload['discipline'],
    )
    return user


@pytest.fixture
def admin_user(db, admin_payload):
    """A fully created admin User + Profile in the database."""
    user = User.objects.create_user(
        username=admin_payload['username'],
        email=admin_payload['email'],
        password=admin_payload['password'],
        first_name=admin_payload['first_name'],
        last_name=admin_payload['last_name'],
        role=User.Role.ADMIN,
    )
    Profile.objects.create(
        user=user,
        institution=admin_payload['institution'],
        discipline=admin_payload['discipline'],
    )
    return user

@pytest.fixture
def auth_student_client(student_user):
    """
    An API client already authenticated as the student.

    force_authenticate() bypasses the JWT login flow entirely.
    This is intentional — we're not testing authentication here,
    we're testing endpoints that *require* authentication. We don't
    want a login failure to break an unrelated test.
    """
    client = APIClient()
    client.force_authenticate(user=student_user)
    return client


@pytest.fixture
def auth_teacher_client(teacher_user):
    """An API client already authenticated as the teacher."""
    client = APIClient()
    client.force_authenticate(user=teacher_user)
    return client


@pytest.fixture
def auth_admin_client(admin_user):
    """An API client already authenticated as the admin."""
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client



# ===========================================================================
# REGISTRATION TESTS
# Covers: RegisterView + RegisterSerializer validation logic
# ===========================================================================

@pytest.mark.django_db
class TestRegistration:
    """
    @pytest.mark.django_db on the class grants database access to
    every test method inside it. You don't need to declare 'db'
    as a parameter in each method when the class has this marker.
    """

    def test_student_registration_succeeds(self, api_client, student_payload):
        """
        Happy path: a complete, valid student payload returns 201
        and creates both a User and a linked Profile in the database.
        """
        # ACT
        response = api_client.post('/api/register/', student_payload)

        # ASSERT
        assert response.status_code == 201

        # Verify the User actually exists in the database
        assert User.objects.filter(username='timi').exists()

        # Verify the Profile was also created and linked correctly
        user = User.objects.get(username='timi')
        assert hasattr(user, 'profile')
        assert user.profile.matric_no == 'ENG/2021/001'

    def test_teacher_registration_succeeds(self, api_client, teacher_payload):
        """
        Happy path: a teacher with no matric number registers successfully.
        Confirms that matric_no is not a universal requirement — only for students.
        """
        response = api_client.post('/api/register/', teacher_payload)

        assert response.status_code == 201
        assert User.objects.filter(username='prof_john').exists()

    def test_student_without_matric_fails(self, api_client, student_payload):
        """
        Sad path: a student who omits their matric number should be rejected.
        This tests the 'Student Requirement Check' in RegisterSerializer.validate().
        """
        # Remove matric_no from an otherwise valid payload
        student_payload.pop('matric_no')

        response = api_client.post('/api/register/', student_payload)

        assert response.status_code == 400
        # Confirm the error points specifically at matric_no, not a generic 400
        assert 'matric_no' in response.data

    def test_non_student_with_matric_fails(self, api_client, teacher_payload):
        """
        Sad path: a teacher submitting a matric number should be rejected.
        This tests the 'Role-based Identifier Check' in RegisterSerializer.validate().
        """
        # Slip a matric number into an otherwise valid teacher payload
        teacher_payload['matric_no'] = 'ENG/2021/999'

        response = api_client.post('/api/register/', teacher_payload)

        assert response.status_code == 400
        assert 'matric_no' in response.data

