from django.contrib import admin
from .models import Document, Folder, VersionEntry, AuditEvent


class VersionEntryInline(admin.TabularInline):
    model = VersionEntry
    extra = 0
    readonly_fields = ["version", "status", "actor", "sha256", "created_at"]


class AuditEventInline(admin.TabularInline):
    model = AuditEvent
    extra = 0
    readonly_fields = ["event_type", "actor", "description", "created_at"]


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["doc_id", "title", "status", "template_name", "owner", "updated_at"]
    list_filter = ["status", "template_name", "category"]
    search_fields = ["doc_id", "title"]
    readonly_fields = ["doc_id", "sha256", "issued_at", "created_at", "updated_at"]
    inlines = [VersionEntryInline, AuditEventInline]


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ["name", "color", "parent", "owner", "created_at"]
    list_filter = ["color"]
    search_fields = ["name"]


@admin.register(VersionEntry)
class VersionEntryAdmin(admin.ModelAdmin):
    list_display = ["document", "version", "status", "actor", "created_at"]
    list_filter = ["status"]


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ["document", "event_type", "actor", "created_at"]
    list_filter = ["event_type"]
