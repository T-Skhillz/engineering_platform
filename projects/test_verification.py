import pytest
from rest_framework.test import APIClient
from projects.models import (
    User, Profile, Student, Teacher, Admin,
    Institution, Department, Faculty, Verification, VerificationStatus
)


# ===========================================================================
# FIXTURES
# ===========================================================================

@pytest.fixture
def api_client():
    return APIClient()


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
    """
    A second department in the SAME faculty/institution.
    Used to test the teacher department-mismatch rule.
    A teacher from this department should NOT be able to verify
    a student from 'department'.
    """
    return Department.objects.create(name="Mechanical Engineering", faculty=faculty)


# --- User Fixtures ---

@pytest.fixture
def student_user(db, institution, department):
    """A pending student — the default verification_status is PENDING."""
    user = User.objects.create_user(
        username='timi', email='timi@test.com', password='securepass123',
        first_name='Timi', last_name='Ade', role=User.Role.STUDENT,
    )
    profile = Profile.objects.create(user=user, institution=institution, department=department)
    Student.objects.create(profile=profile, matric_number='ENG/2021/001', entry_date='2021-09-01')
    return user


@pytest.fixture
def teacher_user(db, institution, department):
    """A teacher in the SAME department as the student."""
    user = User.objects.create_user(
        username='prof_john', email='john@test.com', password='securepass123',
        first_name='John', last_name='Doe', role=User.Role.TEACHER,
    )
    profile = Profile.objects.create(user=user, institution=institution, department=department)
    Teacher.objects.create(profile=profile, staff_number='STAFF/001', title='Dr.', rank='Senior Lecturer')
    return user


@pytest.fixture
def teacher_other_dept(db, institution, other_department):
    """
    A teacher in a DIFFERENT department from the student.
    Tests the core department isolation rule.
    """
    user = User.objects.create_user(
        username='prof_mech', email='mech@test.com', password='securepass123',
        first_name='Mech', last_name='Teacher', role=User.Role.TEACHER,
    )
    profile = Profile.objects.create(user=user, institution=institution, department=other_department)
    Teacher.objects.create(profile=profile, staff_number='STAFF/002', title='Dr.', rank='Lecturer I')
    return user


@pytest.fixture
def admin_user(db, institution, department):
    """An admin — should be able to verify ANY student regardless of department."""
    user = User.objects.create_user(
        username='admin_user', email='admin@test.com', password='securepass123',
        first_name='Admin', last_name='User', role=User.Role.ADMIN,
    )
    profile = Profile.objects.create(user=user, institution=institution, department=department)
    Admin.objects.create(profile=profile, staff_number='ADMIN/001')
    return user


# --- Authenticated Client Fixtures ---

@pytest.fixture
def auth_teacher_client(teacher_user):
    client = APIClient()
    client.force_authenticate(user=teacher_user)
    return client


@pytest.fixture
def auth_teacher_other_dept_client(teacher_other_dept):
    client = APIClient()
    client.force_authenticate(user=teacher_other_dept)
    return client


@pytest.fixture
def auth_admin_client(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def auth_student_client(student_user):
    client = APIClient()
    client.force_authenticate(user=student_user)
    return client


# --- Payload Fixture ---

@pytest.fixture
def verify_payload(student_user):
    """
    The minimal valid payload for a VERIFY action.
    We identify the student by matric_number (write-only field),
    not by their User ID — this is by design in your serializer.
    """
    return {
        'matric_number': 'ENG/2021/001',
        'status': VerificationStatus.VERIFIED,
    }


@pytest.fixture
def reject_payload(student_user):
    """A valid payload for a REJECT action."""
    return {
        'matric_number': 'ENG/2021/001',
        'status': VerificationStatus.REJECTED,
    }


# ===========================================================================
# 1. PERMISSION TESTS
# Who is and isn't allowed to touch /api/verifications/?
# ===========================================================================

@pytest.mark.django_db
class TestVerificationPermissions:

    def test_unauthenticated_user_cannot_access(self, api_client, student_user):
        """No token = 401. The endpoint is not public."""
        response = api_client.get('/api/verifications/')
        assert response.status_code == 401

    def test_student_cannot_access_verifications(self, auth_student_client):
        """
        A student hitting this endpoint should get 403 Forbidden.
        IsAdminOrTeacher.has_permission() blocks any role that isn't
        ADMIN or TEACHER — including STUDENT.
        """
        response = auth_student_client.get('/api/verifications/')
        assert response.status_code == 403

    def test_teacher_can_access_verifications(self, auth_teacher_client):
        """Teachers are allowed — should return 200 (even if the list is empty)."""
        response = auth_teacher_client.get('/api/verifications/')
        assert response.status_code == 200

    def test_admin_can_access_verifications(self, auth_admin_client):
        """Admins are allowed — should return 200."""
        response = auth_admin_client.get('/api/verifications/')
        assert response.status_code == 200


# ===========================================================================
# 2. CREATE VERIFICATION TESTS
# POST /api/verifications/
# Tests the happy path, state machine rules, and department isolation.
# ===========================================================================

@pytest.mark.django_db
class TestCreateVerification:

    def test_teacher_can_verify_student_in_same_department(
        self, auth_teacher_client, verify_payload, student_user
    ):
        """
        Happy path: Teacher and Student share the same department.
        Should return 201 and create a Verification record.
        """
        response = auth_teacher_client.post('/api/verifications/', verify_payload)

        assert response.status_code == 201

        # Confirm the record was actually written to the database
        assert Verification.objects.filter(
            student=student_user,
            status=VerificationStatus.VERIFIED
        ).exists()

    def test_verification_updates_student_status(
        self, auth_teacher_client, verify_payload, student_user
    ):
        """
        The service should update the Student row's verification_status
        field alongside creating the Verification log entry.
        This tests the atomicity of process_student_verification().
        """
        auth_teacher_client.post('/api/verifications/', verify_payload)

        # Refresh the student from the database — in-memory object is stale
        student_user.profile.student_profile.refresh_from_db()
        assert student_user.profile.student_profile.verification_status == VerificationStatus.VERIFIED

    def test_teacher_can_reject_student(
        self, auth_teacher_client, reject_payload, student_user
    ):
        """Happy path: PENDING → REJECTED is a valid transition."""
        response = auth_teacher_client.post('/api/verifications/', reject_payload)
        assert response.status_code == 201

        student_user.profile.student_profile.refresh_from_db()
        assert student_user.profile.student_profile.verification_status == VerificationStatus.REJECTED

    def test_admin_can_verify_student(
        self, auth_admin_client, verify_payload, student_user
    ):
        """
        Admins bypass the department check entirely.
        Should succeed regardless of department alignment.
        """
        response = auth_admin_client.post('/api/verifications/', verify_payload)
        assert response.status_code == 201

    def test_teacher_cannot_verify_student_from_different_department(
        self, auth_teacher_other_dept_client, verify_payload, student_user
    ):
        """
        Core isolation rule: a teacher from Mechanical Engineering
        cannot verify a student from Computer Science.
        
        The rejection comes from check_teacher_can_verify_student()
        in the service layer, which raises ValueError → converted to 400
        by the serializer.
        """
        response = auth_teacher_other_dept_client.post('/api/verifications/', verify_payload)
        assert response.status_code == 400

    def test_nonexistent_matric_number_fails(self, auth_teacher_client):
        """
        Sad path: if the matric_number doesn't match any student,
        the serializer's validate() method should return 400.
        """
        response = auth_teacher_client.post('/api/verifications/', {
            'matric_number': 'FAKE/0000/000',
            'status': VerificationStatus.VERIFIED,
        })
        assert response.status_code == 400
        assert 'matric_number' in response.data


# ===========================================================================
# 3. STATE MACHINE TESTS
# These test the transition rules defined in ALLOWED_TRANSITIONS.
# They require setting up a student at a specific starting status first.
# ===========================================================================

@pytest.mark.django_db
class TestVerificationStateMachine:

    def _set_student_status(self, student_user, status):
        """
        Helper method (not a test) to directly force a student into a
        specific status in the database, bypassing the API.
        
        Why bypass the API here? Because we want to TEST one specific
        transition in isolation. We don't want a prior API call's
        logic to affect our test — we just need to start from a known state.
        """
        student = student_user.profile.student_profile
        student.verification_status = status
        student.save()

    def test_cannot_verify_already_verified_student(
        self, auth_teacher_client, verify_payload, student_user
    ):
        """
        VERIFIED is a terminal state. No transitions out of it are allowed.
        Attempting to verify an already-verified student should return 400.
        """
        # Force the student into VERIFIED state first
        self._set_student_status(student_user, VerificationStatus.VERIFIED)

        response = auth_teacher_client.post('/api/verifications/', verify_payload)
        assert response.status_code == 400

    def test_cannot_reject_already_verified_student(
        self, auth_teacher_client, reject_payload, student_user
    ):
        """VERIFIED → REJECTED is not in ALLOWED_TRANSITIONS. Should return 400."""
        self._set_student_status(student_user, VerificationStatus.VERIFIED)

        response = auth_teacher_client.post('/api/verifications/', reject_payload)
        assert response.status_code == 400

    def test_can_verify_a_rejected_student(
        self, auth_teacher_client, verify_payload, student_user
    ):
        """
        REJECTED → VERIFIED is explicitly allowed.
        This covers the re-submission / appeal flow.
        """
        self._set_student_status(student_user, VerificationStatus.REJECTED)

        response = auth_teacher_client.post('/api/verifications/', verify_payload)
        assert response.status_code == 201

        student_user.profile.student_profile.refresh_from_db()
        assert student_user.profile.student_profile.verification_status == VerificationStatus.VERIFIED

    def test_cannot_reject_an_already_rejected_student(
        self, auth_teacher_client, reject_payload, student_user
    ):
        """
        REJECTED → REJECTED is not a valid transition.
        The idempotency check in the service should block this.
        """
        self._set_student_status(student_user, VerificationStatus.REJECTED)

        response = auth_teacher_client.post('/api/verifications/', reject_payload)
        assert response.status_code == 400


# ===========================================================================
# 4. LIST VERIFICATION TESTS
# GET /api/verifications/
# Tests the queryset filtering logic — Admins see all, Teachers see their dept.
# ===========================================================================

@pytest.mark.django_db
class TestListVerifications:

    def _create_verification(self, student, verifier, status=VerificationStatus.VERIFIED):
        """
        Helper: directly create a Verification record in the DB.
        We bypass the API here because we're testing the LIST endpoint,
        not the CREATE endpoint — no need to test both simultaneously.
        """
        # Also update the student's status to match
        student_record = student.profile.student_profile
        student_record.verification_status = status
        student_record.save()

        return Verification.objects.create(
            student=student,
            verifier=verifier,
            status=status,
        )

    def test_admin_sees_all_verifications(
        self, auth_admin_client, admin_user, student_user, teacher_user, department, other_department, faculty, institution
    ):
        """
        Admin should see ALL verification records in the system,
        regardless of which department they belong to.
        """
        # Create a student in the OTHER department
        other_user = User.objects.create_user(
            username='other_student', email='other@test.com', password='pass1234',
            role=User.Role.STUDENT,
        )
        other_profile = Profile.objects.create(user=other_user, institution=institution, department=other_department)
        Student.objects.create(profile=other_profile, matric_number='MECH/2021/001', entry_date='2021-09-01')

        # Create one verification per student
        self._create_verification(student_user, admin_user)
        self._create_verification(other_user, admin_user)

        response = auth_admin_client.get('/api/verifications/')
        assert response.status_code == 200
        assert len(response.data) == 2  # Sees both

    def test_teacher_only_sees_their_department_verifications(
        self, auth_teacher_client, auth_teacher_other_dept_client,
        teacher_user, teacher_other_dept, student_user,
        institution, other_department
    ):
        """
        A teacher from CSE should only see verifications for CSE students.
        They should NOT see verifications for Mechanical Engineering students.
        """
        # Create a student in the OTHER department
        other_user = User.objects.create_user(
            username='mech_student', email='mech_s@test.com', password='pass1234',
            role=User.Role.STUDENT,
        )
        other_profile = Profile.objects.create(user=other_user, institution=institution, department=other_department)
        Student.objects.create(profile=other_profile, matric_number='MECH/2021/002', entry_date='2021-09-01')

        # CSE verification (should be visible to CSE teacher)
        self._create_verification(student_user, teacher_user)
        # Mech verification (should NOT be visible to CSE teacher)
        self._create_verification(other_user, teacher_other_dept)

        cse_teacher_response = auth_teacher_client.get('/api/verifications/')
        assert cse_teacher_response.status_code == 200
        assert len(cse_teacher_response.data) == 1  # Only sees CSE student
        assert cse_teacher_response.data[0]['student'] == student_user.id