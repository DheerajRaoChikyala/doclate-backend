"""
Signing API views aligned with signing-data.ts workflows.

Covers: create signing request, track signer progress, verify UVC,
record signatures, manage signing policies.
"""

import uuid
import secrets
from datetime import timedelta

from django.conf import settings as django_settings
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from documents.models import Document
from .models import (
    SigningRequest, Signer, SignatureRecord, SignEvent,
    UvcCode, VerifyAttempt, SigningPolicy,
)
from .serializers import (
    SigningRequestListSerializer,
    SigningRequestDetailSerializer,
    CreateSigningRequestSerializer,
    SignerSerializer,
    SignEventSerializer,
    UvcCodeSerializer,
    VerifyAttemptSerializer,
    SigningPolicySerializer,
)


# ─────────────────────────────────────────────────────────────────────────────
# SIGNING REQUEST VIEWSET
# ─────────────────────────────────────────────────────────────────────────────

class SigningRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET  /api/v1/signing/requests/             — list signing requests
    GET  /api/v1/signing/requests/<id>/        — detail with signers + events
    POST /api/v1/signing/requests/create/      — create new signing request
    POST /api/v1/signing/requests/<id>/revoke/ — revoke signing request
    """

    filterset_fields = ["status", "category"]
    search_fields = ["request_id", "document__title"]

    def get_queryset(self):
        return SigningRequest.objects.filter(owner=self.request.user).select_related("document")

    def get_serializer_class(self):
        if self.action == "list":
            return SigningRequestListSerializer
        return SigningRequestDetailSerializer

    @action(detail=False, methods=["post"], url_path="create")
    def create_request(self, request):
        """Create a signing request for a document."""
        serializer = CreateSigningRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            document = Document.objects.get(
                id=data["document_id"], owner=request.user
            )
        except Document.DoesNotExist:
            return Response(
                {"error": "Document not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Generate UVC
        uvc = f"UVC-{secrets.token_hex(4).upper()}"

        # Create signing request
        expiry_days = getattr(django_settings, "SIGNING_LINK_EXPIRY_DAYS", 7)
        signing_req = SigningRequest.objects.create(
            id=str(uuid.uuid4()),
            document=document,
            category=data.get("category", "Finance"),
            sha256=document.sha256 or "",
            owner=request.user,
            owner_email=request.user.email,
            message=data.get("message", ""),
            reminder_schedule=data.get("reminder_schedule", [24, 48, 72]),
            delivery_channels=["email"],
            uvc=uvc,
            expires_at=timezone.now() + timedelta(days=expiry_days),
        )

        # Create signers
        for signer_data in data["signers"]:
            Signer.objects.create(
                id=str(uuid.uuid4()),
                signing_request=signing_req,
                name=signer_data["name"],
                email=signer_data["email"],
                phone=signer_data.get("phone", ""),
                role=signer_data.get("role", "signer"),
                methods_allowed=signer_data.get("methods_allowed", ["otp_verified"]),
                color_code=signer_data.get("color_code", "#6366f1"),
            )

        # Create UVC code record
        UvcCode.objects.create(
            uvc=uvc,
            signing_request=signing_req,
            expires_at=signing_req.expires_at,
        )

        # Audit event
        SignEvent.objects.create(
            id=str(uuid.uuid4()),
            signing_request=signing_req,
            event_type="request.created",
            actor=request.user.get_full_name() or request.user.username,
            description=f"Signing request created for {document.title}",
        )

        # Update document status
        document.status = "in_review"
        document.save(update_fields=["status", "updated_at"])

        return Response(
            SigningRequestDetailSerializer(signing_req).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        signing_req = self.get_object()
        signing_req.status = "revoked"
        signing_req.save(update_fields=["status"])

        # Revoke UVC
        UvcCode.objects.filter(signing_request=signing_req).update(status="revoked")

        SignEvent.objects.create(
            id=str(uuid.uuid4()),
            signing_request=signing_req,
            event_type="request.revoked",
            actor=request.user.get_full_name() or request.user.username,
            description="Signing request revoked",
        )

        return Response({"status": "revoked"})

    @action(detail=True, methods=["get"])
    def events(self, request, pk=None):
        signing_req = self.get_object()
        events = signing_req.events.all()
        return Response(SignEventSerializer(events, many=True).data)


# ─────────────────────────────────────────────────────────────────────────────
# UVC VERIFICATION (public endpoint)
# ─────────────────────────────────────────────────────────────────────────────

class VerifyUvcView(APIView):
    """
    POST /api/v1/signing/verify/
    Body: { uvc: "UVC-XXXXXXXX" }

    Public endpoint — no auth required.
    Returns verification result: valid, expired, revoked, or not_found.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        uvc_code = request.data.get("uvc", "").strip()

        if not uvc_code:
            return Response({"error": "uvc is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Mask IP for privacy
        ip = request.META.get("REMOTE_ADDR", "")
        ip_masked = ".".join(ip.split(".")[:2]) + ".x.x" if ip else "unknown"

        try:
            uvc = UvcCode.objects.select_related("signing_request__document").get(uvc=uvc_code)
        except UvcCode.DoesNotExist:
            VerifyAttempt.objects.create(
                id=str(uuid.uuid4()),
                uvc=uvc_code,
                result="not_found",
                ip_masked=ip_masked,
            )
            return Response({"result": "not_found", "uvc": uvc_code})

        # Check status
        if uvc.status == "revoked":
            result = "revoked"
        elif uvc.expires_at < timezone.now():
            result = "expired"
            uvc.status = "expired"
            uvc.save(update_fields=["status"])
        else:
            result = "valid"

        # Log attempt
        VerifyAttempt.objects.create(
            id=str(uuid.uuid4()),
            uvc=uvc_code,
            result=result,
            ip_masked=ip_masked,
        )

        response_data = {
            "result": result,
            "uvc": uvc_code,
        }

        if result == "valid":
            sr = uvc.signing_request
            response_data.update({
                "documentTitle": sr.document.title,
                "documentId": sr.document.doc_id,
                "sha256": sr.sha256,
                "issuedAt": sr.created_at.isoformat(),
                "signers": [
                    {"name": s.name, "status": s.status, "signedAt": s.signed_at}
                    for s in sr.signers.all()
                ],
            })

        return Response(response_data)


# ─────────────────────────────────────────────────────────────────────────────
# SIGNING POLICY
# ─────────────────────────────────────────────────────────────────────────────

class SigningPolicyViewSet(viewsets.ModelViewSet):
    """
    CRUD for signing policies (tenant-level).

    GET   /api/v1/signing/policies/
    POST  /api/v1/signing/policies/
    PATCH /api/v1/signing/policies/<id>/
    """

    serializer_class = SigningPolicySerializer

    def get_queryset(self):
        if self.request.user.organization:
            return SigningPolicy.objects.filter(organization=self.request.user.organization)
        return SigningPolicy.objects.none()

    def perform_create(self, serializer):
        serializer.save(
            id=str(uuid.uuid4()),
            organization=self.request.user.organization,
        )


# ─────────────────────────────────────────────────────────────────────────────
# DOCUMENT SIGNING REQUESTS (filter by doc)
# ─────────────────────────────────────────────────────────────────────────────

class DocumentSigningView(APIView):
    """
    GET /api/v1/signing/for-document/<doc_id>/
    Returns all signing requests for a specific document.
    Mirrors getSigningRequestsForDoc(docId) from signing-data.ts.
    """

    def get(self, request, doc_id):
        requests = SigningRequest.objects.filter(
            document__id=doc_id, owner=request.user
        )
        return Response(SigningRequestListSerializer(requests, many=True).data)
