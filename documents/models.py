"""
Document, Folder, Version, AuditEvent, and Block models for Doclate.

Aligned with:
  - mock-data.ts → Document, VersionEntry, Folder, AuditEvent interfaces
  - block-registry.ts → BlockDefinition, TAX_INVOICE_BLOCKS
  - template-structures.ts → StructureNode, TemplateCanvasData
  - app-context.tsx → all document lifecycle operations
"""

import uuid
from django.conf import settings
from django.db import models


# ─────────────────────────────────────────────────────────────────────────────
# FOLDER (hierarchical document organization)
# ─────────────────────────────────────────────────────────────────────────────

class Folder(models.Model):
    """
    Hierarchical folder structure.
    Frontend: Folder { id, name, color, parentId, createdAt, updatedAt, description }
    """

    COLOR_CHOICES = [
        ("indigo", "Indigo"),
        ("emerald", "Emerald"),
        ("amber", "Amber"),
        ("rose", "Rose"),
        ("violet", "Violet"),
        ("cyan", "Cyan"),
        ("gray", "Gray"),
    ]

    id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="folders"
    )
    name = models.CharField(max_length=255)
    color = models.CharField(max_length=16, choices=COLOR_CHOICES, default="indigo")
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "folders"
        ordering = ["name"]

    def __str__(self):
        return self.name


# ─────────────────────────────────────────────────────────────────────────────
# DOCUMENT
# ─────────────────────────────────────────────────────────────────────────────

class Document(models.Model):
    """
    Core document model — the central entity of Doclate.

    Frontend: Document interface from mock-data.ts
    Status workflow: draft → in_review → issued → signed → archived
    """

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("in_review", "In Review"),
        ("issued", "Issued"),
        ("signed", "Signed"),
        ("archived", "Archived"),
    ]

    EDITOR_MODE_CHOICES = [
        ("structured", "Structured"),
        ("canvas", "Canvas"),
    ]

    id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4)
    doc_id = models.CharField(
        "Document ID", max_length=20, unique=True,
        help_text="Human-readable ID, e.g. DOC-2026-001",
    )
    title = models.CharField(max_length=512)
    category = models.CharField(max_length=64, default="GST")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="draft")
    version = models.PositiveIntegerField(default=1)

    # Ownership
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="documents"
    )
    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE, related_name="documents",
        null=True, blank=True,
    )

    # Template linkage
    template = models.ForeignKey(
        "templates_catalog.Template", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="documents",
    )
    template_name = models.CharField(max_length=128, blank=True, default="")

    # Editor state
    editor_mode = models.CharField(max_length=16, choices=EDITOR_MODE_CHOICES, default="structured")
    canvas_data = models.JSONField(
        "Canvas Data",
        default=dict, blank=True,
        help_text="JSON blob matching TemplateCanvasData from frontend",
    )
    structure = models.JSONField(
        "Structure Tree",
        default=list, blank=True,
        help_text="JSON array matching StructureNode[] from frontend",
    )
    enabled_blocks = models.JSONField(
        "Enabled Blocks",
        default=dict, blank=True,
        help_text="Record<string, boolean> — addon block toggle state",
    )
    added_block_ids = models.JSONField(
        "Added Block IDs",
        default=list, blank=True,
        help_text="Array of block IDs added via inspector recommendations",
    )

    # Filing & organization
    folder = models.ForeignKey(
        Folder, on_delete=models.SET_NULL, null=True, blank=True, related_name="documents"
    )
    project_name = models.CharField(max_length=255, blank=True, default="")
    tags = models.JSONField(default=list, blank=True)
    starred = models.BooleanField(default=False)
    locked = models.BooleanField(default=False)

    # Issuance & integrity
    sha256 = models.CharField("SHA-256", max_length=64, blank=True, default="")
    issued_at = models.DateTimeField(null=True, blank=True)

    # Import tracking
    source_file = models.CharField(max_length=512, blank=True, default="")
    imported_from = models.CharField(
        max_length=16, blank=True, default="",
        help_text="Original file format: pdf, docx, xlsx, etc.",
    )

    # PDF file (S3 in production)
    pdf_file = models.FileField(upload_to="documents/pdfs/", blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "documents"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.doc_id} — {self.title}"

    def save(self, *args, **kwargs):
        if not self.doc_id:
            self.doc_id = self._generate_doc_id()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_doc_id() -> str:
        from django.utils import timezone

        year = timezone.now().year
        last = (
            Document.objects.filter(doc_id__startswith=f"DOC-{year}-")
            .order_by("-doc_id")
            .values_list("doc_id", flat=True)
            .first()
        )
        seq = 1
        if last:
            try:
                seq = int(last.split("-")[-1]) + 1
            except ValueError:
                pass
        return f"DOC-{year}-{seq:03d}"


# ─────────────────────────────────────────────────────────────────────────────
# VERSION HISTORY
# ─────────────────────────────────────────────────────────────────────────────

class VersionEntry(models.Model):
    """
    Immutable version snapshot for audit trail.
    Frontend: VersionEntry { version, status, updatedAt, actor, note, sha256 }
    """

    id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4)
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="version_history"
    )
    version = models.PositiveIntegerField()
    status = models.CharField(max_length=16)
    actor = models.CharField(max_length=255)
    note = models.TextField(blank=True, default="")
    sha256 = models.CharField(max_length=64, blank=True, default="")

    # Snapshot of canvas_data at this version
    canvas_data_snapshot = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "version_entries"
        ordering = ["-version"]
        unique_together = [("document", "version")]

    def __str__(self):
        return f"{self.document.doc_id} v{self.version}"


# ─────────────────────────────────────────────────────────────────────────────
# AUDIT LOG
# ─────────────────────────────────────────────────────────────────────────────

class AuditEvent(models.Model):
    """
    Document activity log.
    Frontend: AuditEvent { id, type, actor, at, description }
    """

    id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4)
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="audit_events"
    )
    event_type = models.CharField(max_length=64)
    actor = models.CharField(max_length=255)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_events"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_type} on {self.document.doc_id}"
