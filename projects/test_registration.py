import pytest
from rest_framework.test import APIClient
from projects.models import User, Profile, Student, Teacher, Admin, Institution, Department, Faculty


# ===========================================================================
# FIXTURES
# ===========================================================================
# Think of fixtures as the "setup" work you'd otherwise repeat in every test.
# pytest runs them automatically when a test function lists them as parameters.

@pytest.fixture
def api_client():
    """A bare, unauthenticated API client — like a browser that hasn't logged in."""
    return APIClient()


# --- Database Object Fixtures ---
# These create real rows in the test database so our registration endpoints
# have valid Institution and Department IDs to point at.

@pytest.fixture
def institution(db):
    """A real Institution row in the test database."""
    return Institution.objects.create(name="University of Lagos", short_name="UNILAG")


@pytest.fixture
def faculty(db, institution):
    """A Faculty that belongs to the institution above."""
    return Faculty.objects.create(name="Technology", institution=institution)


@pytest.fixture
def department(db, faculty):
    """A Department that belongs to the faculty above.
    
    Chain: Department -> Faculty -> Institution.
    This chain is what the serializer validates — a department must
    belong to the institution the user selected.
    """
    return Department.objects.create(name="Computer Science and Engineering", faculty=faculty)


# --- Payload Fixtures ---
# These are the raw dictionaries that get sent as POST request bodies.
# Defined as fixtures so every test gets a fresh, independent copy.

@pytest.fixture
def student_payload(institution, department):
    """A valid, complete payload for registering a student."""
    return {
        'username': 'timi',
        'email': 'timi@test.com',
        'password': 'securepass123',
        'first_name': 'Timi',
        'last_name': 'Ade',
        'institution': str(institution.id),   # The API expects UUID strings
        'department': str(department.id),
        'matric_number': 'ENG/2021/001',
        'entry_date': '2021-09-01',
    }


@pytest.fixture
def teacher_payload(institution, department):
    """A valid, complete payload for registering a teacher."""
    return {
        'username': 'prof_john',
        'email': 'john@test.com',
        'password': 'securepass123',
        'first_name': 'John',
        'last_name': 'Doe',
        'institution': str(institution.id),
        'department': str(department.id),
        'staff_number': 'STAFF/001',
        'title': 'Dr.',
        'rank': 'Senior Lecturer',
    }


@pytest.fixture
def admin_payload(institution, department):
    """A valid, complete payload for registering an admin."""
    return {
        'username': 'admin_user',
        'email': 'admin@test.com',
        'password': 'securepass123',
        'first_name': 'Admin',
        'last_name': 'User',
        'institution': str(institution.id),
        'department': str(department.id),
        'staff_number': 'ADMIN/001',
    }


# --- Pre-built User Fixtures ---
# These create a fully registered user directly in the DB (bypassing the API).
# Used for tests that need an existing user to already exist, e.g. login or
# permission tests. We use create_user() so passwords are hashed correctly.

@pytest.fixture
def student_user(db, institution, department):
    """A fully created Student User + Profile + Student record in the DB."""
    user = User.objects.create_user(
        username='timi',
        email='timi@test.com',
        password='securepass123',
        first_name='Timi',
        last_name='Ade',
        role=User.Role.STUDENT,
    )
    profile = Profile.objects.create(
        user=user,
        institution=institution,
        department=department,
    )
    Student.objects.create(
        profile=profile,
        matric_number='ENG/2021/001',
        entry_date='2021-09-01',
    )
    return user


@pytest.fixture
def teacher_user(db, institution, department):
    """A fully created Teacher User + Profile + Teacher record in the DB."""
    user = User.objects.create_user(
        username='prof_john',
        email='john@test.com',
        password='securepass123',
        first_name='John',
        last_name='Doe',
        role=User.Role.TEACHER,
    )
    profile = Profile.objects.create(
        user=user,
        institution=institution,
        department=department,
    )
    Teacher.objects.create(
        profile=profile,
        staff_number='STAFF/001',
        title='Dr.',
        rank='Senior Lecturer',
    )
    return user


@pytest.fixture
def admin_user(db, institution, department):
    """A fully created Admin User + Profile + Admin record in the DB."""
    user = User.objects.create_user(
        username='admin_user',
        email='admin@test.com',
        password='securepass123',
        first_name='Admin',
        last_name='User',
        role=User.Role.ADMIN,
    )
    profile = Profile.objects.create(
        user=user,
        institution=institution,
        department=department,
    )
    Admin.objects.create(
        profile=profile,
        staff_number='ADMIN/001',
    )
    return user


# --- Authenticated Client Fixtures ---
# These skip the login flow entirely. We're not testing authentication here —
# we're testing endpoints that *require* an already-authenticated user.
# force_authenticate() tells DRF to trust us that this user is logged in.

@pytest.fixture
def auth_student_client(student_user):
    client = APIClient()
    client.force_authenticate(user=student_user)
    return client


@pytest.fixture
def auth_teacher_client(teacher_user):
    client = APIClient()
    client.force_authenticate(user=teacher_user)
    return client


@pytest.fixture
def auth_admin_client(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client



# ===========================================================================
# 1. STUDENT REGISTRATION TESTS
# Endpoint: POST /api/register/student/
# Covers: RegisterStudentView + RegisterStudentSerializer + create_student_user()
# ===========================================================================

@pytest.mark.django_db
class TestStudentRegistration:
    """
    Tests for the student registration endpoint.
    
    Each test is independent — the database is reset between tests, so
    creating a user in one test never affects the next.
    """

    def test_student_registration_succeeds(self, api_client, student_payload):
        """
        Happy path: a complete, valid payload should return 201 and
        create a User, a Profile, AND a Student record — all three.
        
        Why test all three? Because the service uses transaction.atomic().
        If any layer fails, none are created. We want to confirm all three
        succeeded, not just the outer HTTP response.
        """
        response = api_client.post('/api/register/student/', student_payload)

        # Did the HTTP layer respond correctly?
        assert response.status_code == 201

        # Did the User get created?
        assert User.objects.filter(username='timi').exists()

        # Did the Profile get linked?
        user = User.objects.get(username='timi')
        assert hasattr(user, 'profile')

        # Did the Student record get created with the right matric number?
        assert hasattr(user.profile, 'student_profile')
        assert user.profile.student_profile.matric_number == 'ENG/2021/001'

    def test_student_role_is_set_correctly(self, api_client, student_payload):
        """
        Confirms that the role field is set to STUDENT by the service,
        not passed in from (or overridable by) the client.
        """
        api_client.post('/api/register/student/', student_payload)
        user = User.objects.get(username='timi')
        assert user.role == User.Role.STUDENT

    def test_duplicate_username_fails(self, api_client, student_payload, student_user):
        """
        Sad path: trying to register with a username that already exists
        should return 400. 'student_user' fixture creates the user first.
        """
        response = api_client.post('/api/register/student/', student_payload)
        assert response.status_code == 400

    def test_duplicate_email_fails(self, api_client, student_payload, student_user):
        """
        Sad path: the email field is unique in the User model.
        Re-using the same email should return 400.
        """
        # Change the username so only email collides
        student_payload['username'] = 'timi_2'
        response = api_client.post('/api/register/student/', student_payload)
        assert response.status_code == 400

    def test_duplicate_matric_number_fails(self, api_client, student_payload, student_user):
        """
        Sad path: matric numbers must be unique. The serializer's
        validate_matric_number() method enforces this.
        """
        # Use a completely different identity but the same matric number
        student_payload['username'] = 'timi_2'
        student_payload['email'] = 'timi2@test.com'
        response = api_client.post('/api/register/student/', student_payload)
        assert response.status_code == 400
        assert 'matric_number' in response.data

    def test_missing_matric_number_fails(self, api_client, student_payload):
        """
        Sad path: matric_number is a required field for students.
        Omitting it should return 400 with a specific error on that field.
        """
        student_payload.pop('matric_number')
        response = api_client.post('/api/register/student/', student_payload)
        assert response.status_code == 400
        assert 'matric_number' in response.data

    def test_missing_entry_date_fails(self, api_client, student_payload):
        """Sad path: entry_date is also required."""
        student_payload.pop('entry_date')
        response = api_client.post('/api/register/student/', student_payload)
        assert response.status_code == 400
        assert 'entry_date' in response.data

    def test_department_from_wrong_institution_fails(self, api_client, student_payload, db):
        """
        Sad path: the serializer validates that the chosen department actually 
        belongs to the chosen institution. This tests the cross-field validation
        in RegisterStudentSerializer.validate().

        We create a *second* institution and use its department ID with the 
        first institution's ID — an invalid combination.
        """
        # Set up a completely separate institution + department chain
        other_institution = Institution.objects.create(name="University of Ibadan", short_name="UI")
        other_faculty = Faculty.objects.create(name="Science", institution=other_institution)
        other_department = Department.objects.create(name="Physics", faculty=other_faculty)

        # Mix: use institution from fixture, but department from the other institution
        student_payload['department'] = str(other_department.id)

        response = api_client.post('/api/register/student/', student_payload)
        assert response.status_code == 400
        assert 'department' in response.data

    def test_short_password_fails(self, api_client, student_payload):
        """Sad path: password has a min_length=8 constraint in the serializer."""
        student_payload['password'] = '123'
        response = api_client.post('/api/register/student/', student_payload)
        assert response.status_code == 400


# ===========================================================================
# 2. TEACHER REGISTRATION TESTS
# Endpoint: POST /api/register/teacher/
# ===========================================================================

@pytest.mark.django_db
class TestTeacherRegistration:

    def test_teacher_registration_succeeds(self, api_client, teacher_payload):
        """
        Happy path: a complete teacher payload should create User + Profile + Teacher.
        """
        response = api_client.post('/api/register/teacher/', teacher_payload)
        assert response.status_code == 201

        user = User.objects.get(username='prof_john')
        assert user.role == User.Role.TEACHER
        assert hasattr(user.profile, 'teacher_profile')
        assert user.profile.teacher_profile.staff_number == 'STAFF/001'

    def test_duplicate_staff_number_fails(self, api_client, teacher_payload, teacher_user):
        """Sad path: staff numbers must be unique in the Teacher table."""
        teacher_payload['username'] = 'prof_jane'
        teacher_payload['email'] = 'jane@test.com'
        response = api_client.post('/api/register/teacher/', teacher_payload)
        assert response.status_code == 400
        assert 'staff_number' in response.data

    def test_missing_title_fails(self, api_client, teacher_payload):
        """Sad path: title is required for teachers."""
        teacher_payload.pop('title')
        response = api_client.post('/api/register/teacher/', teacher_payload)
        assert response.status_code == 400

    def test_missing_rank_fails(self, api_client, teacher_payload):
        """Sad path: rank is required for teachers."""
        teacher_payload.pop('rank')
        response = api_client.post('/api/register/teacher/', teacher_payload)
        assert response.status_code == 400


# ===========================================================================
# 3. ADMIN REGISTRATION TESTS
# Endpoint: POST /api/register/admin/
# ===========================================================================

@pytest.mark.django_db
class TestAdminRegistration:

    def test_admin_registration_succeeds(self, api_client, admin_payload):
        """
        Happy path: a complete admin payload should create User + Profile + Admin.
        """
        response = api_client.post('/api/register/admin/', admin_payload)
        assert response.status_code == 201

        user = User.objects.get(username='admin_user')
        assert user.role == User.Role.ADMIN
        assert hasattr(user.profile, 'admin_profile')
        assert user.profile.admin_profile.staff_number == 'ADMIN/001'

    def test_duplicate_admin_staff_number_fails(self, api_client, admin_payload, admin_user):
        """Sad path: staff numbers must be unique in the Admin table."""
        admin_payload['username'] = 'admin_user_2'
        admin_payload['email'] = 'admin2@test.com'
        response = api_client.post('/api/register/admin/', admin_payload)
        assert response.status_code == 400
        assert 'staff_number' in response.data


# ===========================================================================
# 4. LOGIN TESTS
# Endpoint: POST /api/login/
# This endpoint is provided by SimpleJWT — we're just confirming it works
# correctly with our custom User model (UUID pk, email-based auth).
# ===========================================================================

@pytest.mark.django_db
class TestLogin:

    def test_login_with_valid_credentials_returns_tokens(self, api_client, student_user):
        """
        Happy path: correct username + password should return both
        an access token and a refresh token.
        """
        response = api_client.post('/api/login/', {
            'username': 'timi',
            'password': 'securepass123',
        })
        assert response.status_code == 200
        # SimpleJWT returns these two keys on success
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_login_with_wrong_password_fails(self, api_client, student_user):
        """Sad path: wrong password should return 401 Unauthorized."""
        response = api_client.post('/api/login/', {
            'username': 'timi',
            'password': 'wrongpassword',
        })
        assert response.status_code == 401

    def test_login_with_nonexistent_user_fails(self, api_client):
        """Sad path: username doesn't exist in the database."""
        response = api_client.post('/api/login/', {
            'username': 'ghost_user',
            'password': 'securepass123',
        })
        assert response.status_code == 401


# ===========================================================================
# 5. PROFILE TESTS
# Endpoint: GET /api/me/ and PATCH /api/me/
# ===========================================================================

@pytest.mark.django_db
class TestProfile:

    def test_authenticated_user_can_view_their_profile(self, auth_student_client):
        """
        Happy path: an authenticated user GETting /api/me/ should receive
        their own profile data with a 200 response.
        """
        response = auth_student_client.get('/api/me/')
        assert response.status_code == 200
        # The response should contain their username nested inside 'user'
        assert response.data['user']['username'] == 'timi'

    def test_unauthenticated_user_cannot_view_profile(self, api_client):
        """
        Sad path: no token = no access. Should return 401 Unauthorized.
        This confirms the IsAuthenticated permission class is working.
        """
        response = api_client.get('/api/me/')
        assert response.status_code == 401

    def test_authenticated_user_can_update_bio(self, auth_student_client):
        """
        Happy path: a PATCH request with a new bio value should update
        the profile and return 200.
        """
        response = auth_student_client.patch('/api/me/', {'bio': 'I build things.'})
        assert response.status_code == 200
        assert response.data['bio'] == 'I build things.'

    def test_profile_contains_student_specific_data(self, auth_student_client):
        """
        Confirms that the nested 'student_profile' block appears in the 
        response for a student user, containing their matric number.
        This tests the ProfileSerializer's nested serializer logic.
        """
        response = auth_student_client.get('/api/me/')
        assert response.status_code == 200
        assert response.data['student_profile'] is not None
        assert response.data['student_profile']['matric_number'] == 'ENG/2021/001'

    def test_student_profile_has_no_teacher_data(self, auth_student_client):
        """
        Confirms that a student's profile response does NOT include
        teacher-specific data. Role isolation check.
        """
        response = auth_student_client.get('/api/me/')
        assert response.data['teacher_profile'] is None

    def test_put_method_is_not_allowed(self, auth_student_client):
        """
        Confirms that the view blocks full PUT updates as intended.
        Only PATCH (partial update) is allowed.
        """
        response = auth_student_client.put('/api/me/', {'bio': 'attempt full replace'})
        assert response.status_code == 405  # Method Not Allowed