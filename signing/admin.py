from django.contrib import admin
from .models import (
    SigningRequest, Signer, SignatureRecord, SignEvent,
    SignEvidence, UvcCode, VerifyAttempt, SigningPolicy,
)


class SignerInline(admin.TabularInline):
    model = Signer
    extra = 0


class SignEventInline(admin.TabularInline):
    model = SignEvent
    extra = 0
    readonly_fields = ["event_type", "actor", "description", "created_at"]


@admin.register(SigningRequest)
class SigningRequestAdmin(admin.ModelAdmin):
    list_display = ["request_id", "document", "status", "owner", "created_at"]
    list_filter = ["status", "category"]
    search_fields = ["request_id", "document__title"]
    readonly_fields = ["request_id", "sha256", "display_fingerprint"]
    inlines = [SignerInline, SignEventInline]


@admin.register(Signer)
class SignerAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "role", "status", "signing_request"]
    list_filter = ["role", "status"]


@admin.register(SignatureRecord)
class SignatureRecordAdmin(admin.ModelAdmin):
    list_display = ["signer", "method_used", "signed_at"]
    readonly_fields = ["signature_hash"]


@admin.register(UvcCode)
class UvcCodeAdmin(admin.ModelAdmin):
    list_display = ["uvc", "signing_request", "status", "expires_at"]
    list_filter = ["status"]


@admin.register(VerifyAttempt)
class VerifyAttemptAdmin(admin.ModelAdmin):
    list_display = ["uvc", "result", "ip_masked", "created_at"]
    list_filter = ["result"]


@admin.register(SigningPolicy)
class SigningPolicyAdmin(admin.ModelAdmin):
    list_display = ["organization", "doc_category", "allow_otp", "allow_esign", "allow_dsc"]
    list_filter = ["doc_category"]
