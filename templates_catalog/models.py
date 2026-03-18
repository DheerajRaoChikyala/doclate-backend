"""
Template and Block models for Doclate.

Aligned with:
  - mock-data.ts → Template interface
  - block-registry.ts → BlockDefinition, TAX_INVOICE_BLOCKS
  - template-structures.ts → StructureNode[], TemplateCanvasData
"""

import uuid
from django.db import models


class Template(models.Model):
    """
    Document template catalog entry.
    Frontend: Template { id, name, category, pack, estimatedTime, requiredFields,
              badges, version, updatedAt, description, preparedBy, preparedFor, summary }
    """

    CATEGORY_CHOICES = [
        ("GST", "GST"),
        ("Business", "Business"),
        ("Legal", "Legal"),
        ("HR", "HR"),
        ("Finance", "Finance"),
    ]

    id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=255, unique=True)
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, default="GST")
    pack = models.CharField(max_length=64, blank=True, default="")
    estimated_time = models.CharField(max_length=32, default="~3 min")
    required_fields = models.PositiveIntegerField(default=0)
    badges = models.JSONField(default=list, blank=True, help_text='e.g. ["GST","Rule 46"]')
    version = models.CharField(max_length=16, default="1.0")
    description = models.TextField(blank=True, default="")
    prepared_by = models.CharField(max_length=255, blank=True, default="")
    prepared_for = models.CharField(max_length=255, blank=True, default="")
    summary = models.TextField(blank=True, default="")

    # Default structure and canvas data for this template
    default_structure = models.JSONField(
        default=list, blank=True,
        help_text="Default StructureNode[] tree for new documents of this template",
    )
    default_canvas_data = models.JSONField(
        default=dict, blank=True,
        help_text="Default TemplateCanvasData for new documents of this template",
    )
    default_validations = models.JSONField(
        default=list, blank=True,
        help_text="Default ValidationRule[] for this template",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "templates"
        ordering = ["name"]

    def __str__(self):
        return self.name


class BlockDefinition(models.Model):
    """
    Canonical block definition for a template.
    Frontend: BlockDefinition { id, group, type, label, locked, defaultEnabled, isAddon }

    Canonical ID format: "group.kebab-case" (e.g., "billing.invoice-no")
    """

    BLOCK_TYPE_CHOICES = [
        ("header", "Header"),
        ("field", "Field"),
        ("table", "Table"),
        ("summary", "Summary"),
        ("signature", "Signature"),
        ("section", "Section"),
    ]

    id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4)
    template = models.ForeignKey(
        Template, on_delete=models.CASCADE, related_name="blocks"
    )
    canonical_id = models.CharField(
        max_length=64,
        help_text="Canonical ID in group.kebab-case format, e.g. billing.invoice-no",
    )
    group = models.CharField(max_length=32)
    block_type = models.CharField(max_length=16, choices=BLOCK_TYPE_CHOICES)
    label = models.CharField(max_length=128)
    locked = models.BooleanField(
        default=False,
        help_text="Locked blocks cannot be edited/removed by users",
    )
    default_enabled = models.BooleanField(default=True)
    is_addon = models.BooleanField(
        default=False,
        help_text="Addon blocks can be toggled on/off in the inspector",
    )

    class Meta:
        db_table = "block_definitions"
        unique_together = [("template", "canonical_id")]
        ordering = ["group", "canonical_id"]

    def __str__(self):
        return f"{self.template.name} → {self.canonical_id}"
