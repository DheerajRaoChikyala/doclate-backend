"""
PDF export and fingerprinting API endpoints.

Aligned with:
  - pdf-export.ts → exportAsPDF(), fingerprintDocument()
  - issue-modal.tsx → handleIssue() flow
"""

from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from documents.models import Document
from .services import fingerprint_document, generate_document_pdf, sha256_hex


class FingerprintView(APIView):
    """
    POST /api/v1/export/fingerprint/
    Compute SHA-256 fingerprint for a document.

    Body: { docId, title, docType, invoiceNo?, issueDate?, totalAmount? }
    Returns: { sha256, generatedAt, contentSnippet }
    """

    def post(self, request):
        fp = fingerprint_document(
            doc_id=request.data.get("docId", ""),
            title=request.data.get("title", ""),
            doc_type=request.data.get("docType", ""),
            invoice_no=request.data.get("invoiceNo", ""),
            issue_date=request.data.get("issueDate", ""),
            total_amount=request.data.get("totalAmount", ""),
        )
        return Response(fp)


class ExportPDFView(APIView):
    """
    POST /api/v1/export/pdf/<doc_id>/
    Generate and download PDF for a document.

    Returns: PDF file bytes with Content-Type application/pdf
    Also stores sha256 on the document and creates a version entry.
    """

    def post(self, request, doc_id):
        try:
            document = Document.objects.get(id=doc_id, owner=request.user)
        except Document.DoesNotExist:
            return Response(
                {"error": "Document not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        pdf_bytes = generate_document_pdf(document)

        if pdf_bytes is None:
            return Response(
                {"error": "PDF generation not available (WeasyPrint not installed)"},
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )

        # Compute SHA-256 of the actual PDF bytes
        pdf_sha256 = sha256_hex(pdf_bytes)

        # Update document with fingerprint
        document.sha256 = pdf_sha256
        document.save(update_fields=["sha256"])

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{document.title}.pdf"'
        response["X-Document-SHA256"] = pdf_sha256
        return response


class IssueDocumentView(APIView):
    """
    POST /api/v1/export/issue/<doc_id>/
    Issue a document: compute fingerprint, update status to 'issued',
    create version entry, and return the fingerprint.

    This mirrors the handleIssue() flow in issue-modal.tsx.
    """

    def post(self, request, doc_id):
        try:
            document = Document.objects.get(id=doc_id, owner=request.user)
        except Document.DoesNotExist:
            return Response(
                {"error": "Document not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if document.status not in ("draft", "in_review"):
            return Response(
                {"error": f"Cannot issue document in '{document.status}' status"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Compute content fingerprint
        canvas = document.canvas_data or {}
        fp = fingerprint_document(
            doc_id=document.doc_id,
            title=document.title,
            doc_type=document.template_name or "Unknown",
            invoice_no=canvas.get("documentNumberValue", ""),
            issue_date=canvas.get("documentDateValue", ""),
            total_amount=canvas.get("grandTotalValue", ""),
        )

        # Update document status
        from django.utils import timezone

        document.status = "issued"
        document.sha256 = fp["sha256"]
        document.issued_at = timezone.now()
        document.save(update_fields=["status", "sha256", "issued_at", "updated_at"])

        # Create version entry
        from documents.models import VersionEntry

        VersionEntry.objects.create(
            document=document,
            version=document.version,
            status="issued",
            actor=request.user.get_full_name() or request.user.username,
            note="Document issued",
            sha256=fp["sha256"],
            canvas_data_snapshot=document.canvas_data,
        )

        # Create audit event
        from documents.models import AuditEvent

        AuditEvent.objects.create(
            document=document,
            event_type="document.issued",
            actor=request.user.get_full_name() or request.user.username,
            description=f"Document issued with SHA-256: {fp['sha256'][:16]}...",
        )

        return Response({
            "status": "issued",
            "fingerprint": fp,
            "docId": document.doc_id,
        })
