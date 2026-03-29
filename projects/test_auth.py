import pytest
from rest_framework.test import APIClient
from projects.models import User, Profile, Student, Institution, Department, Faculty


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
def student_user(db, institution, department):
    """A student user we can log in as and manipulate."""
    user = User.objects.create_user(
        username='timi', email='timi@test.com', password='securepass123',
        first_name='Timi', last_name='Ade', role=User.Role.STUDENT,
    )
    profile = Profile.objects.create(user=user, institution=institution, department=department)
    Student.objects.create(profile=profile, matric_number='ENG/2021/001', entry_date='2021-09-01')
    return user


@pytest.fixture
def auth_student_client(student_user):
    """Authenticated client — skips the login flow."""
    client = APIClient()
    client.force_authenticate(user=student_user)
    return client


def get_tokens_for_user(api_client, username, password):
    """
    Helper function (not a fixture) that performs a real login and returns
    the access and refresh tokens.

    We need REAL tokens (not force_authenticate) for the tests in this file
    because we're testing the token blacklisting behaviour — you can't
    blacklist a token that was never actually issued.
    """
    response = api_client.post('/api/login/', {
        'username': username,
        'password': password,
    })
    return response.data['access'], response.data['refresh']


# ===========================================================================
# 1. CHANGE PASSWORD TESTS
# Endpoint: PATCH /api/change-password/
# ===========================================================================

@pytest.mark.django_db
class TestChangePassword:

    def test_unauthenticated_user_cannot_change_password(self, api_client):
        """No token = 401. The endpoint requires authentication."""
        response = api_client.patch('/api/change-password/', {
            'old_password': 'securepass123',
            'new_password': 'newpassword123',
        })
        assert response.status_code == 401

    def test_change_password_succeeds_with_correct_old_password(
        self, auth_student_client
    ):
        """
        Happy path: correct old password + valid new password returns 200
        and includes fresh access and refresh tokens in the response.
        """
        response = auth_student_client.patch('/api/change-password/', {
            'old_password': 'securepass123',
            'new_password': 'newpassword123',
        })
        assert response.status_code == 200
        # View should return fresh tokens so the user stays logged in
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_new_password_is_actually_saved(self, auth_student_client, student_user):
        """
        Confirms the password was genuinely updated in the database,
        not just acknowledged in the response.

        check_password() tests against the stored PBKDF2 hash — if this
        passes, the new password is what's actually saved.
        """
        auth_student_client.patch('/api/change-password/', {
            'old_password': 'securepass123',
            'new_password': 'newpassword123',
        })

        # Re-fetch the user from the DB — the in-memory object is stale
        student_user.refresh_from_db()
        assert student_user.check_password('newpassword123')

    def test_old_password_no_longer_works_after_change(
        self, api_client, auth_student_client, student_user
    ):
        """
        After a password change, the old credentials should be rejected
        by the login endpoint. Confirms the change is real, not cosmetic.
        """
        auth_student_client.patch('/api/change-password/', {
            'old_password': 'securepass123',
            'new_password': 'newpassword123',
        })

        # Try logging in with the OLD password
        response = api_client.post('/api/login/', {
            'username': 'timi',
            'password': 'securepass123',
        })
        assert response.status_code == 401

    def test_wrong_old_password_fails(self, auth_student_client):
        """
        Sad path: if old_password doesn't match what's in the DB,
        validate_old_password() raises a ValidationError → 400.
        """
        response = auth_student_client.patch('/api/change-password/', {
            'old_password': 'thisisthewrongpassword',
            'new_password': 'newpassword123',
        })
        assert response.status_code == 400
        assert 'old_password' in response.data

    def test_short_new_password_fails(self, auth_student_client):
        """
        Sad path: new_password has min_length=8 in the serializer.
        A password shorter than 8 characters should return 400.
        """
        response = auth_student_client.patch('/api/change-password/', {
            'old_password': 'securepass123',
            'new_password': '123',
        })
        assert response.status_code == 400

    def test_old_refresh_token_is_blacklisted_after_change(
        self, api_client, student_user
    ):
        """
        Security test: when a refresh_token is provided in the request,
        it should be blacklisted after the password changes.

        We verify this by trying to USE the old refresh token after the
        change — it should be rejected with 401.

        Why do we need a real login here instead of force_authenticate?
        Because force_authenticate never issues a real JWT. There's no
        token to blacklist. We need a token that actually exists in the
        database's outstanding token table.
        """
        access, refresh = get_tokens_for_user(api_client, 'timi', 'securepass123')

        # Attach the real access token and change the password, sending the
        # refresh token along so the view knows to blacklist it
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        api_client.patch('/api/change-password/', {
            'old_password': 'securepass123',
            'new_password': 'newpassword123',
            'refresh_token': refresh,
        })

        # Now try to use the OLD refresh token to get a new access token
        api_client.credentials()  # Clear the auth header
        response = api_client.post('/api/token/refresh/', {'refresh': refresh})
        assert response.status_code == 401

    def test_change_password_still_succeeds_without_refresh_token(
        self, auth_student_client
    ):
        """
        The view's docstring explicitly states that blacklisting is
        best-effort — if no refresh_token is sent, the password change
        still succeeds. This test locks that behaviour in.
        """
        response = auth_student_client.patch('/api/change-password/', {
            'old_password': 'securepass123',
            'new_password': 'newpassword123',
            # Deliberately omitting 'refresh_token'
        })
        assert response.status_code == 200


# ===========================================================================
# 2. LOGOUT TESTS
# Endpoint: POST /api/logout/
# ===========================================================================

@pytest.mark.django_db
class TestLogout:

    def test_unauthenticated_user_cannot_logout(self, api_client):
        """
        The logout endpoint requires authentication.
        An unauthenticated POST should return 401.
        """
        response = api_client.post('/api/logout/')
        assert response.status_code == 401

    def test_logout_with_valid_refresh_token_succeeds(
        self, api_client, student_user
    ):
        """
        Happy path: a valid refresh token gets blacklisted and
        the response is 200.
        """
        access, refresh = get_tokens_for_user(api_client, 'timi', 'securepass123')

        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        response = api_client.post('/api/logout/', {'refresh_token': refresh})
        assert response.status_code == 200

    def test_refresh_token_is_invalid_after_logout(
        self, api_client, student_user
    ):
        """
        After logout, the blacklisted refresh token should be rejected
        if someone tries to use it to get a new access token.
        This confirms the blacklist actually worked.
        """
        access, refresh = get_tokens_for_user(api_client, 'timi', 'securepass123')

        # Log out
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        api_client.post('/api/logout/', {'refresh_token': refresh})

        # Try to refresh with the now-blacklisted token
        api_client.credentials()
        response = api_client.post('/api/token/refresh/', {'refresh': refresh})
        assert response.status_code == 401

    def test_logout_without_refresh_token_still_returns_200(
        self, auth_student_client
    ):
        """
        Idempotent design: the view returns 200 even when no refresh
        token is provided. The session is considered ended either way.
        """
        response = auth_student_client.post('/api/logout/')
        assert response.status_code == 200

    def test_logout_with_already_blacklisted_token_still_returns_200(
        self, api_client, student_user
    ):
        """
        Idempotent design: logging out twice with the same token
        should still return 200, not 400 or 500.

        This matters for mobile clients that might fire the logout
        request more than once due to network retries.
        """
        access, refresh = get_tokens_for_user(api_client, 'timi', 'securepass123')
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

        # First logout — blacklists the token
        api_client.post('/api/logout/', {'refresh_token': refresh})

        # Second logout — token is already blacklisted, should still be 200
        response = api_client.post('/api/logout/', {'refresh_token': refresh})
        assert response.status_code == 200


# ===========================================================================
# 3. TOKEN REFRESH TESTS
# Endpoint: POST /api/token/refresh/
# ===========================================================================

@pytest.mark.django_db
class TestTokenRefresh:

    def test_valid_refresh_token_returns_new_access_token(
        self, api_client, student_user
    ):
        """
        Happy path: a valid refresh token should return a new access token.
        This is the core use case — keep the user logged in after the
        access token expires (your access tokens last 7 hours).
        """
        _, refresh = get_tokens_for_user(api_client, 'timi', 'securepass123')

        response = api_client.post('/api/token/refresh/', {'refresh': refresh})
        assert response.status_code == 200
        assert 'access' in response.data

    def test_token_rotation_issues_new_refresh_token(
        self, api_client, student_user
    ):
        """
        Your settings have ROTATE_REFRESH_TOKENS = True.
        This means every time you use a refresh token, you get a NEW
        refresh token back. The old one is consumed.

        This test confirms a new refresh token is included in the response.
        """
        _, refresh = get_tokens_for_user(api_client, 'timi', 'securepass123')

        response = api_client.post('/api/token/refresh/', {'refresh': refresh})
        assert response.status_code == 200
        # Rotation means a new refresh token is returned alongside the new access token
        assert 'refresh' in response.data
        # And it should be different from the one we sent
        assert response.data['refresh'] != refresh

    def test_used_refresh_token_cannot_be_reused(
        self, api_client, student_user
    ):
        """
        BLACKLIST_AFTER_ROTATION = True means using a refresh token
        blacklists it immediately. The same token cannot be used twice.

        This is an important security property — it prevents refresh
        token replay attacks.
        """
        _, refresh = get_tokens_for_user(api_client, 'timi', 'securepass123')

        # Use it once — valid
        api_client.post('/api/token/refresh/', {'refresh': refresh})

        # Use it again — should now be blacklisted
        response = api_client.post('/api/token/refresh/', {'refresh': refresh})
        assert response.status_code == 401

    def test_invalid_refresh_token_is_rejected(self, api_client):
        """Sad path: a garbage token string should return 401."""
        response = api_client.post('/api/token/refresh/', {
            'refresh': 'this.is.not.a.real.token'
        })
        assert response.status_code == 401

    def test_missing_refresh_token_returns_400(self, api_client):
        """Sad path: sending an empty body should return 400."""
        response = api_client.post('/api/token/refresh/', {})
        assert response.status_code == 400