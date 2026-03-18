"""
Celery tasks for signing workflows.

Async operations: send signing emails, schedule reminders,
check for expired signing requests.
"""

import uuid
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone


@shared_task
def send_signing_invitation(signing_request_id: str, signer_id: str):
    """Send signing invitation email to a signer."""
    from .models import SigningRequest, Signer, SignEvent

    try:
        signing_req = SigningRequest.objects.get(id=signing_request_id)
        signer = Signer.objects.get(id=signer_id)
    except (SigningRequest.DoesNotExist, Signer.DoesNotExist):
        return

    subject = f"Document signing request: {signing_req.document.title}"
    message = (
        f"Hello {signer.name},\n\n"
        f"{signing_req.owner} has requested your signature on "
        f'"{signing_req.document.title}".\n\n'
    )
    if signing_req.message:
        message += f"Message: {signing_req.message}\n\n"
    message += (
        f"Document ID: {signing_req.document.doc_id}\n"
        f"Request ID: {signing_req.request_id}\n"
        f"Expires: {signing_req.expires_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"— Doclate by Aiyug Technologies"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[signer.email],
        fail_silently=True,
    )

    signer.last_reminder_sent = timezone.now()
    signer.save(update_fields=["last_reminder_sent"])

    SignEvent.objects.create(
        id=str(uuid.uuid4()),
        signing_request=signing_req,
        event_type="invitation.sent",
        actor="system",
        description=f"Signing invitation sent to {signer.email}",
    )


@shared_task
def send_signing_reminder(signing_request_id: str):
    """Send reminder emails to all pending signers."""
    from .models import SigningRequest

    try:
        signing_req = SigningRequest.objects.get(id=signing_request_id)
    except SigningRequest.DoesNotExist:
        return

    if signing_req.status in ("completed", "revoked", "expired"):
        return

    pending_signers = signing_req.signers.exclude(status="signed")
    for signer in pending_signers:
        send_signing_invitation.delay(signing_request_id, str(signer.id))


@shared_task
def expire_stale_signing_requests():
    """
    Periodic task: mark expired signing requests.
    Schedule this via Celery Beat (e.g., every hour).
    """
    from .models import SigningRequest, UvcCode

    expired = SigningRequest.objects.filter(
        status__in=["awaiting", "in_progress"],
        expires_at__lt=timezone.now(),
    )

    count = 0
    for req in expired:
        req.status = "expired"
        req.save(update_fields=["status"])
        UvcCode.objects.filter(signing_request=req).update(status="expired")
        count += 1

    return f"Expired {count} signing requests"
