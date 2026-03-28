from django.db import transaction
from django.utils import timezone
from projects.models import Verification, Student, VerificationStatus

# Defines the valid state machine transitions to ensure data integrity
ALLOWED_TRANSITIONS = {
    VerificationStatus.PENDING: {
        VerificationStatus.VERIFIED,
        VerificationStatus.REJECTED,
    },
    VerificationStatus.REJECTED: {
        VerificationStatus.VERIFIED,
    },
    VerificationStatus.VERIFIED: set(), # Terminal state; no further changes allowed
}

def process_student_verification(user, status, verifier=None, session=None):
    """
    Updates a student's verification status, enforces state transitions, 
    and logs the history.
    """
    if status not in VerificationStatus.values:
        raise ValueError(f"Invalid status: {status}")

    # Use atomic transaction to ensure the log entry and status update are bundled
    with transaction.atomic():
        # Lock the student row to prevent race conditions during status updates
        student_profile = Student.objects.select_for_update().get(profile__user=user)
        current_status = student_profile.verification_status

        # Validate against the state machine logic
        if status not in ALLOWED_TRANSITIONS.get(current_status, set()):
            raise ValueError(
                f"Invalid transition from {current_status} to {status}"
            )

        # Idempotency check: avoid creating redundant logs for the same state
        if current_status == status:
            raise ValueError(f"Student is already {status}")

        # Create an audit trail entry for this verification action
        verification = Verification.objects.create(
            student=user,
            verifier=verifier,
            session=session,
            status=status
        )

        # Synchronize the Student record with the new state
        student_profile.verification_status = status
        student_profile.verified_at = (
            timezone.now() if status == VerificationStatus.VERIFIED else None
        )
        student_profile.save()

        return verification, student_profile