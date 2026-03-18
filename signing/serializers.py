"""
Signing serializers aligned with signing-data.ts interfaces.
"""

from rest_framework import serializers
from .models import (
    SigningRequest, Signer, SignatureRecord, SignEvent,
    SignEvidence, UvcCode, VerifyAttempt, SigningPolicy,
)


class SignerSerializer(serializers.ModelSerializer):
    methods_allowed = serializers.JSONField()

    class Meta:
        model = Signer
        fields = [
            "id", "name", "email", "phone", "role",
            "methods_allowed", "method_used", "status",
            "signed_at", "last_reminder_sent", "signature_hash", "color_code",
        ]
        read_only_fields = ["id", "signed_at", "signature_hash"]


class SignEventSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source="event_type")
    at = serializers.DateTimeField(source="created_at")

    class Meta:
        model = SignEvent
        fields = ["id", "type", "actor", "at", "description", "ip_masked"]
        read_only_fields = fields


class SigningRequestListSerializer(serializers.ModelSerializer):
    signers = SignerSerializer(many=True, read_only=True)
    doc_title = serializers.CharField(source="document.title", read_only=True)

    class Meta:
        model = SigningRequest
        fields = [
            "id", "request_id", "doc_title", "status", "category",
            "sha256", "display_fingerprint", "signers",
            "expires_at", "created_at", "completed_at",
            "owner", "uvc",
        ]
        read_only_fields = fields


class SigningRequestDetailSerializer(serializers.ModelSerializer):
    signers = SignerSerializer(many=True, read_only=True)
    events = SignEventSerializer(many=True, read_only=True)
    doc_title = serializers.CharField(source="document.title", read_only=True)
    doc_id = serializers.CharField(source="document.doc_id", read_only=True)

    class Meta:
        model = SigningRequest
        fields = [
            "id", "request_id", "doc_id", "doc_title", "doc_version_id",
            "status", "category", "sha256", "display_fingerprint",
            "signers", "events",
            "owner", "owner_email", "message",
            "reminder_schedule", "delivery_channels", "uvc",
            "expires_at", "created_at", "completed_at",
        ]
        read_only_fields = fields


class CreateSigningRequestSerializer(serializers.Serializer):
    """Create a signing request for a document."""

    document_id = serializers.CharField()
    category = serializers.ChoiceField(
        choices=["Legal", "HR", "Finance", "Internal", "Vendor", "Board"],
        default="Finance",
    )
    message = serializers.CharField(required=False, allow_blank=True, default="")
    signers = SignerSerializer(many=True)
    reminder_schedule = serializers.JSONField(required=False, default=[24, 48, 72])


class SignatureRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = SignatureRecord
        fields = [
            "id", "signer", "method_used", "signed_at",
            "signature_hash", "ip_masked", "user_agent",
        ]
        read_only_fields = fields


class UvcCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = UvcCode
        fields = ["uvc", "status", "expires_at", "created_at"]
        read_only_fields = fields


class VerifyAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerifyAttempt
        fields = ["id", "uvc", "result", "ip_masked", "created_at"]
        read_only_fields = fields


class SigningPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = SigningPolicy
        fields = [
            "id", "doc_category", "allow_otp", "allow_esign", "allow_dsc",
            "link_expiry_days", "require_review_checkbox",
            "disable_partial_download", "evidence_auto_attach",
            "otp_sends_per_hour", "verify_attempts_per_hour_per_ip",
            "file_upload_max_size_mb", "audit_log_retention_days",
            "signed_pdf_retention_days",
        ]
