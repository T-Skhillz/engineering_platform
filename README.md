# Engineering Social Platform — Phase 1

Phase 1 delivers the foundational layer of the platform: user identity, role-based registration, authentication, and student verification. It is intentionally scoped — no posts, no feeds, no social graph. Just the infrastructure everything else will sit on.

---

## What's in Phase 1

- Role-based user registration (Admin, Teacher, Student)
- JWT authentication with token blacklisting and rotation
- Password change with session invalidation
- Idempotent logout
- Profile retrieval and partial update
- Student verification with state machine enforcement
- Department-scoped access control for Teachers
- Academic year calculation from institutional session history

---

## Project Structure

```
core/                        # Django project root
├── settings.py
└── urls.py

projects/                    # Main app
├── models.py
├── serializers.py
├── views.py
├── permissions.py
├── urls.py
└── services/
    ├── admin_service.py
    ├── teacher_service.py
    ├── student_service.py
    ├── verification_status_service.py
    └── academic_year_service.py

tests/
├── test_auth.py
├── test_permissions.py
├── test_registration.py
└── test_verification.py
```

---

## Data Model

### School Entities
`Institution → Faculty → Department → Course`  
`Session → Semester`

### User Entities
Every user has a `User` record (auth identity) and a `Profile` record (organizational metadata). Role-specific data lives in separate tables linked to the profile.

```
User (AbstractUser)
└── Profile
    ├── Student      (matric_number, entry_date, verification_status)
    ├── Teacher      (staff_number, title, rank)
    └── Admin        (staff_number)
```

All primary keys are UUIDs. `User.email` is unique.

### Verification
`Verification` is an audit log. Every status change on a `Student` record creates a `Verification` entry. The student's current status is mirrored on the `Student` model for fast reads.

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/register/admin/` | None | Register an Admin |
| POST | `/api/register/teacher/` | None | Register a Teacher |
| POST | `/api/register/student/` | None | Register a Student |
| POST | `/api/login/` | None | Obtain JWT access + refresh tokens |
| POST | `/api/token/refresh/` | None | Rotate refresh token, get new access token |
| GET | `/api/me/` | Bearer | Get own profile with metadata |
| PATCH | `/api/me/` | Bearer | Update own profile (bio, avatar) |
| GET | `/api/verifications/` | Bearer (Admin/Teacher) | List verification records |
| POST | `/api/verifications/` | Bearer (Admin/Teacher) | Create a verification record |
| PATCH | `/api/change-password/` | Bearer | Change password, invalidate session |
| POST | `/api/logout/` | Bearer | Blacklist refresh token |

---

## Registration Payloads

**Admin**
```json
{
  "username": "admin01",
  "email": "admin@uni.edu",
  "password": "securepass",
  "first_name": "Ada",
  "last_name": "Obi",
  "institution": "<institution-uuid>",
  "department": "<department-uuid>",
  "staff_number": "ADMIN/001"
}
```

**Teacher** — same as Admin plus `title` and `rank`.

**Student** — same as Admin but with `matric_number` and `entry_date` instead of `staff_number`.

Institution/Department relationship is validated at registration: a department that doesn't belong to the selected institution is rejected with 400.

---

## Authentication

Uses `djangorestframework-simplejwt`.

- Access token lifetime: **7 hours**
- Refresh token lifetime: **1 day**
- Refresh tokens rotate on use (`ROTATE_REFRESH_TOKENS = True`)
- Used tokens are blacklisted immediately (`BLACKLIST_AFTER_ROTATION = True`)

**Login**
```
POST /api/login/
{ "username": "...", "password": "..." }
→ { "access": "...", "refresh": "..." }
```

**Authenticated requests**
```
Authorization: Bearer <access_token>
```

---

## Permissions

**`IsAdminOrTeacher`** — guards the verification endpoints.
- Admins: full access to all records.
- Teachers: can only view/create verifications for students in their own department. Enforced at the object level.
- Students: denied entirely.

**`check_teacher_can_verify_student`** — a service-layer guard called before any DB write. Raises `ValueError` if teacher and student departments don't match.

---

## Verification State Machine

```
PENDING → VERIFIED
PENDING → REJECTED
REJECTED → VERIFIED
VERIFIED → (terminal)
```

Enforced in `verification_status_service.py` using `select_for_update()` to prevent race conditions. Each transition creates an audit log entry in `Verification` and updates `Student.verification_status` atomically.

---

## Academic Year Calculation

`GET /api/me/` for a student includes a computed `academic_year` field calculated via ORM annotation:

1. Count institution sessions that started after the student's `entry_date`.
2. Cap the result at `department.programme_duration` using `Least()`.

No stored field — recalculates on every profile fetch.

---

## Setup

**Requirements**: Python 3.10+, PostgreSQL (or SQLite for development)

**Environment variables** (`.env`)
```
SECRET_KEY=
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_TYPE=sqlite          # or postgres
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=
```

**Install and run**
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

**Run tests**
```bash
pytest
```

---

## Notes

- `CORS_ALLOW_ALL_ORIGINS = True` is set for development. Lock this down before any deployment.
- Registration endpoints are open (`AllowAny`). Revisit if the platform moves to invite-only accounts.
- `RoleTransition` model is stubbed in `models.py` for Phase 8 (Student → Alumni transition).