"""
Signing workflow models for Doclate.

Aligned with signing-data.ts:
  - SigningRequest, Signer, SignatureRecord, SignEvent
  - SignEvidence, UvcCode, VerifyAttempt, SigningPolicy
"""

import uuid
from django.conf import settings
from django.db import models


# ─────────────────────────────────────────────────────────────────────────────
# SIGNING REQUEST
# ─────────────────────────────────────────────────────────────────────────────

class SigningRequest(models.Model):
    """
    A signing workflow for a specific document version.
    Frontend: SigningRequest interface from signing-data.ts
    """

    STATUS_CHOICES = [
        ("awaiting", "Awaiting"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("expired", "Expired"),
        ("revoked", "Revoked"),
    ]

    CATEGORY_CHOICES = [
        ("Legal", "Legal"),
        ("HR", "HR"),
        ("Finance", "Finance"),
        ("Internal", "Internal"),
        ("Vendor", "Vendor"),
        ("Board", "Board"),
    ]

    id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4)
    request_id = models.CharField(
        max_length=20, unique=True,
        help_text="Human-readable ID, e.g. SGN-2026-001",
    )
    document = models.ForeignKey(
        "documents.Document", on_delete=models.CASCADE, related_name="signing_requests"
    )
    doc_version_id = models.CharField(max_length=36, blank=True, default="")
    category = models.CharField(max_length=16, choices=CATEGORY_CHOICES, default="Finance")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="awaiting")
    sha256 = models.CharField("SHA-256", max_length=64)
    display_fingerprint = models.CharField(max_length=20, blank=True, default="")

    # Owner
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="signing_requests"
    )
    owner_email = models.EmailField()
    message = models.TextField(blank=True, default="")

    # Scheduling
    reminder_schedule = models.JSONField(
        default=list, blank=True,
        help_text="Array of hours, e.g. [24, 48, 72]",
    )
    delivery_channels = models.JSONField(
        default=list, blank=True,
        help_text='e.g. ["email"]',
    )

    # UVC (Unique Verification Code)
    uvc = models.CharField(max_length=20, blank=True, default="")

    # Timestamps
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "signing_requests"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.request_id} — {self.document.title}"

    def save(self, *args, **kwargs):
        if not self.request_id:
            self.request_id = self._generate_request_id()
        if not self.display_fingerprint and self.sha256:
            self.display_fingerprint = self.sha256[:12]
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_request_id() -> str:
        from django.utils import timezone

        year = timezone.now().year
        last = (
            SigningRequest.objects.filter(request_id__startswith=f"SGN-{year}-")
            .order_by("-request_id")
            .values_list("request_id", flat=True)
            .first()
        )
        seq = 1
        if last:
            try:
                seq = int(last.split("-")[-1]) + 1
            except ValueError:
                pass
        return f"SGN-{year}-{seq:03d}"


# ─────────────────────────────────────────────────────────────────────────────
# SIGNER
# ─────────────────────────────────────────────────────────────────────────────

class Signer(models.Model):
    """
    A participant in a signing workflow.
    Frontend: Signer interface from signing-data.ts
    """

    STATUS_CHOICES = [
        ("not_viewed", "Not Viewed"),
        ("viewed", "Viewed"),
        ("started", "Started"),
        ("signed", "Signed"),
        ("failed", "Failed"),
        ("declined", "Declined"),
    ]

    ROLE_CHOICES = [
        ("signer", "Signer"),
        ("approver", "Approver"),
        ("cc", "CC"),
    ]

    METHOD_CHOICES = [
        ("otp_verified", "OTP Verified"),
        ("aadhaar_esign", "Aadhaar eSign"),
        ("dsc", "DSC"),
    ]

    id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4)
    signing_request = models.ForeignKey(
        SigningRequest, on_delete=models.CASCADE, related_name="signers"
    )
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, default="")
    role = models.CharField(max_length=16, choices=ROLE_CHOICES, default="signer")
    methods_allowed = models.JSONField(
        default=list,
        help_text='e.g. ["otp_verified", "aadhaar_esign"]',
    )
    method_used = models.CharField(max_length=16, choices=METHOD_CHOICES, blank=True, default="")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="not_viewed")
    signed_at = models.DateTimeField(null=True, blank=True)
    last_reminder_sent = models.DateTimeField(null=True, blank=True)
    signature_hash = models.CharField(max_length=64, blank=True, default="")
    color_code = models.CharField(max_length=7, default="#6366f1")

    class Meta:
        db_table = "signers"
        ordering = ["id"]

    def __str__(self):
        return f"{self.name} ({self.role}) — {self.signing_request.request_id}"


# ─────────────────────────────────────────────────────────────────────────────
# SIGNATURE RECORD (cryptographic proof)
# ─────────────────────────────────────────────────────────────────────────────

class SignatureRecord(models.Model):
    """
    Immutable record of a completed signature action.
    Frontend: SignatureRecord from signing-data.ts
    """

    id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4)
    signer = models.ForeignKey(Signer, on_delete=models.CASCADE, related_name="signatures")
    signing_request = models.ForeignKey(
        SigningRequest, on_delete=models.CASCADE, related_name="signature_records"
    )
    method_used = models.CharField(max_length=16)
    signed_at = models.DateTimeField()
    signature_hash = models.CharField(max_length=64)
    ip_masked = models.CharField(max_length=32)
    user_agent = models.TextField(blank=True, default="")

    class Meta:
        db_table = "signature_records"
        ordering = ["-signed_at"]

    def __str__(self):
        return f"Signature by {self.signer.name} at {self.signed_at}"


# ─────────────────────────────────────────────────────────────────────────────
# SIGN EVENT (audit timeline)
# ─────────────────────────────────────────────────────────────────────────────

class SignEvent(models.Model):
    """
    Signing workflow timeline event.
    Frontend: SignEvent from signing-data.ts
    Types: request.created, signer.viewed, signature.completed, etc.
    """

    id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4)
    signing_request = models.ForeignKey(
        SigningRequest, on_delete=models.CASCADE, related_name="events"
    )
    event_type = models.CharField(max_length=64)
    actor = models.CharField(max_length=255)
    description = models.TextField()
    ip_masked = models.CharField(max_length=32, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sign_events"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_type} — {self.signing_request.request_id}"


# ─────────────────────────────────────────────────────────────────────────────
# SIGN EVIDENCE (certificate chain references)
# ─────────────────────────────────────────────────────────────────────────────

class SignEvidence(models.Model):
    """
    Evidence chain for a signature — certificate, OCSP, CRL, TSA references.
    Frontend: SignEvidence from signing-data.ts
    """

    id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4)
    signature = models.OneToOneField(
        SignatureRecord, on_delete=models.CASCADE, related_name="evidence"
    )
    cert_chain_ref = models.TextField(blank=True, default="")
    ocsp_ref = models.TextField(blank=True, default="")
    crl_ref = models.TextField(blank=True, default="")
    tsa_ref = models.TextField(blank=True, default="")

    class Meta:
        db_table = "sign_evidence"

    def __str__(self):
        return f"Evidence for {self.signature}"


# ─────────────────────────────────────────────────────────────────────────────
# UVC (Unique Verification Code)
# ─────────────────────────────────────────────────────────────────────────────

class UvcCode(models.Model):
    """
    Unique Verification Code for document authenticity.
    Frontend: UvcCode from signing-data.ts
    """

    STATUS_CHOICES = [
        ("active", "Active"),
        ("expired", "Expired"),
        ("revoked", "Revoked"),
    ]

    uvc = models.CharField(max_length=20, primary_key=True)
    signing_request = models.OneToOneField(
        SigningRequest, on_delete=models.CASCADE, related_name="uvc_code"
    )
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="active")
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "uvc_codes"

    def __str__(self):
        return self.uvc


class VerifyAttempt(models.Model):
    """
    Log of UVC verification attempts.
    Frontend: VerifyAttempt from signing-data.ts
    """

    RESULT_CHOICES = [
        ("valid", "Valid"),
        ("expired", "Expired"),
        ("revoked", "Revoked"),
        ("not_found", "Not Found"),
    ]

    id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4)
    uvc = models.CharField(max_length=20)
    result = models.CharField(max_length=16, choices=RESULT_CHOICES)
    ip_masked = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "verify_attempts"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Verify {self.uvc} → {self.result}"


# ─────────────────────────────────────────────────────────────────────────────
# SIGNING POLICY (tenant-level configuration)
# ─────────────────────────────────────────────────────────────────────────────

class SigningPolicy(models.Model):
    """
    Tenant-level signing rules.
    Frontend: SigningPolicy from signing-data.ts
    """

    id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4)
    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE, related_name="signing_policies"
    )
    doc_category = models.CharField(max_length=16)
    allow_otp = models.BooleanField(default=True)
    allow_esign = models.BooleanField(default=True)
    allow_dsc = models.BooleanField(default=False)
    link_expiry_days = models.PositiveIntegerField(default=7)
    require_review_checkbox = models.BooleanField(default=True)
    disable_partial_download = models.BooleanField(default=False)
    evidence_auto_attach = models.BooleanField(default=True)
    otp_sends_per_hour = models.PositiveIntegerField(default=5)
    verify_attempts_per_hour_per_ip = models.PositiveIntegerField(default=10)
    file_upload_max_size_mb = models.PositiveIntegerField(default=25)
    audit_log_retention_days = models.PositiveIntegerField(default=2555)
    signed_pdf_retention_days = models.PositiveIntegerField(default=2555)

    class Meta:
        db_table = "signing_policies"
        unique_together = [("organization", "doc_category")]

    def __str__(self):
        return f"{self.organization.name} — {self.doc_category}"
