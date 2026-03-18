"""
PDF export + SHA-256 fingerprinting service.

Aligned with:
  - pdf-export.ts → sha256Hex(), fingerprintDocument(), exportAsPDF()
  - issue-modal.tsx → handleIssue() computes fingerprint on issue

Server-side PDF generation uses WeasyPrint (HTML → PDF).
SHA-256 uses hashlib (stdlib) — mirrors the Web Crypto API approach on the client.
"""

import hashlib
import json
from datetime import datetime, timezone
from io import BytesIO
from typing import Optional

from django.template.loader import render_to_string


def sha256_hex(data: bytes) -> str:
    """Compute SHA-256 hex digest. Mirrors pdf-export.ts sha256Hex()."""
    return hashlib.sha256(data).hexdigest()


def fingerprint_document(
    doc_id: str,
    title: str,
    doc_type: str,
    invoice_no: str = "",
    issue_date: str = "",
    total_amount: str = "",
) -> dict:
    """
    Generate a content fingerprint for a document.
    Mirrors pdf-export.ts fingerprintDocument().

    Returns: { sha256, generatedAt, contentSnippet }
    """
    generated_at = datetime.now(timezone.utc).isoformat()
    content = json.dumps({
        "docId": doc_id,
        "title": title,
        "docType": doc_type,
        "invoiceNo": invoice_no,
        "issueDate": issue_date,
        "totalAmount": total_amount,
        "generatedAt": generated_at,
    })
    sha256 = sha256_hex(content.encode("utf-8"))
    return {
        "sha256": sha256,
        "generatedAt": generated_at,
        "contentSnippet": content[:120],
    }


def generate_pdf(html_content: str) -> Optional[bytes]:
    """
    Generate PDF bytes from HTML content using WeasyPrint.

    Returns PDF bytes or None if WeasyPrint is not available.
    """
    try:
        from weasyprint import HTML

        pdf_buffer = BytesIO()
        HTML(string=html_content).write_pdf(pdf_buffer)
        return pdf_buffer.getvalue()
    except ImportError:
        return None


def generate_document_pdf(document) -> Optional[bytes]:
    """
    Generate a PDF for a Document model instance.

    Uses the document's canvas_data to render an HTML template,
    then converts to PDF via WeasyPrint.
    """
    canvas_data = document.canvas_data or {}
    template_name = document.template_name or "Tax Invoice"

    # Map template name to HTML template
    template_map = {
        "Tax Invoice": "export/tax_invoice.html",
        "Purchase Order": "export/purchase_order.html",
        "Credit Note": "export/credit_note.html",
        "Debit Note": "export/debit_note.html",
        "Bill of Supply": "export/bill_of_supply.html",
        "Self Invoice (RCM)": "export/self_invoice.html",
    }

    html_template = template_map.get(template_name, "export/generic.html")

    try:
        html_content = render_to_string(html_template, {
            "document": document,
            "canvas": canvas_data,
        })
    except Exception:
        # Fallback: render a basic document summary
        html_content = render_to_string("export/generic.html", {
            "document": document,
            "canvas": canvas_data,
        })

    return generate_pdf(html_content)
