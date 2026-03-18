"""
Management command to seed the template catalog with Doclate's built-in templates.

Mirrors the template data from:
  - mock-data.ts → templates array
  - block-registry.ts → TAX_INVOICE_BLOCKS
  - template-structures.ts → templateStructures, templateCanvasData

Usage:
  python manage.py seed_templates
"""

import uuid
from django.core.management.base import BaseCommand
from templates_catalog.models import Template, BlockDefinition


TEMPLATES = [
    {
        "id": "tax-invoice",
        "name": "Tax Invoice",
        "category": "GST",
        "pack": "GST Compliance",
        "estimated_time": "~3 min",
        "required_fields": 12,
        "badges": ["GST", "Rule 46"],
        "version": "1.0",
        "description": "Standard GST-compliant tax invoice under Rule 46 of the CGST Rules, 2017.",
        "prepared_by": "Aiyug Technologies",
        "prepared_for": "Indian businesses registered under GST",
        "summary": "Includes supplier/recipient details, HSN-wise line items, CGST/SGST/IGST breakup, and digital signature block.",
    },
    {
        "id": "purchase-order",
        "name": "Purchase Order",
        "category": "Business",
        "pack": "Procurement",
        "estimated_time": "~5 min",
        "required_fields": 10,
        "badges": ["Business"],
        "version": "1.0",
        "description": "Standard purchase order for goods/services procurement.",
        "prepared_by": "Aiyug Technologies",
        "prepared_for": "Procurement teams",
        "summary": "Vendor details, line items, delivery terms, payment conditions.",
    },
    {
        "id": "credit-note",
        "name": "Credit Note",
        "category": "GST",
        "pack": "GST Compliance",
        "estimated_time": "~3 min",
        "required_fields": 10,
        "badges": ["GST", "Section 34"],
        "version": "1.0",
        "description": "GST credit note for sales returns, rate corrections, or post-sale discounts.",
        "prepared_by": "Aiyug Technologies",
        "prepared_for": "Indian businesses registered under GST",
        "summary": "References original invoice, adjusted line items, reversed tax.",
    },
    {
        "id": "debit-note",
        "name": "Debit Note",
        "category": "GST",
        "pack": "GST Compliance",
        "estimated_time": "~3 min",
        "required_fields": 10,
        "badges": ["GST"],
        "version": "1.0",
        "description": "GST debit note for supplementary invoices and upward price revisions.",
        "prepared_by": "Aiyug Technologies",
        "prepared_for": "Indian businesses registered under GST",
        "summary": "References original invoice with additional charges and tax.",
    },
    {
        "id": "bill-of-supply",
        "name": "Bill of Supply",
        "category": "GST",
        "pack": "GST Compliance",
        "estimated_time": "~3 min",
        "required_fields": 8,
        "badges": ["GST", "Section 31(3)(c)"],
        "version": "1.0",
        "description": "Bill of supply for exempt supplies or composition scheme dealers.",
        "prepared_by": "Aiyug Technologies",
        "prepared_for": "Composition scheme dealers and exempt suppliers",
        "summary": "No tax breakup — used for exempt or nil-rated supplies.",
    },
    {
        "id": "self-invoice-rcm",
        "name": "Self Invoice (RCM)",
        "category": "GST",
        "pack": "GST Compliance",
        "estimated_time": "~4 min",
        "required_fields": 11,
        "badges": ["GST", "RCM", "Section 31(3)(f)"],
        "version": "1.0",
        "description": "Self-invoice for reverse charge mechanism under Section 9(3)/9(4) CGST Act.",
        "prepared_by": "Aiyug Technologies",
        "prepared_for": "GST registrants receiving supplies under RCM",
        "summary": "Buyer issues invoice on behalf of unregistered supplier.",
    },
]

TAX_INVOICE_BLOCKS = [
    ("billing.company-header", "billing", "header", "Company Header", True, True, False),
    ("billing.invoice-no", "billing", "field", "Invoice Number", True, True, False),
    ("billing.invoice-date", "billing", "field", "Invoice Date", True, True, False),
    ("billing.terms", "billing", "field", "Payment Terms", False, True, False),
    ("billing.due-date", "billing", "field", "Due Date", False, True, False),
    ("billing.place-of-supply", "billing", "field", "Place of Supply", True, True, False),
    ("billing.billing-address", "billing", "section", "Billing Address", False, True, False),
    ("billing.shipping-address", "billing", "section", "Shipping Address", False, False, True),
    ("items.product-grid", "items", "table", "Product Grid", True, True, False),
    ("items.tax-summary", "items", "summary", "Tax Summary", True, True, False),
    ("closing.payment-details", "closing", "section", "Payment Details", False, False, True),
    ("closing.signature", "closing", "signature", "Digital Signature", False, False, True),
    ("closing.authorized-by", "closing", "field", "Authorized Signatory", False, True, False),
]


class Command(BaseCommand):
    help = "Seed the template catalog with built-in Doclate templates and block definitions."

    def handle(self, *args, **options):
        created_count = 0
        for tpl_data in TEMPLATES:
            tpl, created = Template.objects.update_or_create(
                id=tpl_data["id"],
                defaults={
                    "name": tpl_data["name"],
                    "category": tpl_data["category"],
                    "pack": tpl_data["pack"],
                    "estimated_time": tpl_data["estimated_time"],
                    "required_fields": tpl_data["required_fields"],
                    "badges": tpl_data["badges"],
                    "version": tpl_data["version"],
                    "description": tpl_data["description"],
                    "prepared_by": tpl_data["prepared_by"],
                    "prepared_for": tpl_data["prepared_for"],
                    "summary": tpl_data["summary"],
                },
            )
            if created:
                created_count += 1
                self.stdout.write(f"  Created template: {tpl.name}")
            else:
                self.stdout.write(f"  Updated template: {tpl.name}")

        # Seed block definitions for Tax Invoice
        tax_invoice = Template.objects.filter(id="tax-invoice").first()
        if tax_invoice:
            block_count = 0
            for canonical_id, group, btype, label, locked, default_enabled, is_addon in TAX_INVOICE_BLOCKS:
                _, created = BlockDefinition.objects.update_or_create(
                    template=tax_invoice,
                    canonical_id=canonical_id,
                    defaults={
                        "group": group,
                        "block_type": btype,
                        "label": label,
                        "locked": locked,
                        "default_enabled": default_enabled,
                        "is_addon": is_addon,
                    },
                )
                if created:
                    block_count += 1
            self.stdout.write(f"  Tax Invoice blocks: {block_count} created")

        self.stdout.write(self.style.SUCCESS(
            f"Done. {created_count} templates created, {len(TEMPLATES)} total."
        ))
