"""
Document serializers aligned with frontend interfaces.

Maps Django models ↔ JSON shapes expected by the React frontend.
"""

from rest_framework import serializers
from .models import Document, Folder, VersionEntry, AuditEvent


class FolderSerializer(serializers.ModelSerializer):
    parent_id = serializers.CharField(source="parent_id", allow_null=True, required=False)

    class Meta:
        model = Folder
        fields = [
            "id", "name", "color", "parent_id", "description",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class VersionEntrySerializer(serializers.ModelSerializer):
    updated_at = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = VersionEntry
        fields = ["version", "status", "updated_at", "actor", "note", "sha256"]
        read_only_fields = fields


class AuditEventSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source="event_type")
    at = serializers.DateTimeField(source="created_at")

    class Meta:
        model = AuditEvent
        fields = ["id", "type", "actor", "at", "description"]
        read_only_fields = fields


class DocumentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for document list views."""

    owner_avatar = serializers.SerializerMethodField()
    folder_id = serializers.CharField(source="folder_id", allow_null=True, required=False)

    class Meta:
        model = Document
        fields = [
            "id", "doc_id", "title", "category", "status", "version",
            "updated_at", "owner", "owner_avatar", "template_name",
            "project_name", "sha256", "issued_at", "locked", "starred",
            "tags", "folder_id", "editor_mode", "source_file", "imported_from",
        ]
        read_only_fields = ["id", "doc_id", "sha256", "issued_at", "created_at", "updated_at"]

    def get_owner_avatar(self, obj):
        return obj.owner.initials if obj.owner else ""


class DocumentDetailSerializer(serializers.ModelSerializer):
    """Full serializer with version history, audit events, and editor state."""

    owner_avatar = serializers.SerializerMethodField()
    version_history = VersionEntrySerializer(many=True, read_only=True)
    audit_events = AuditEventSerializer(many=True, read_only=True)
    folder_id = serializers.CharField(source="folder_id", allow_null=True, required=False)

    class Meta:
        model = Document
        fields = [
            "id", "doc_id", "title", "category", "status", "version",
            "updated_at", "created_at", "owner", "owner_avatar",
            "template_name", "editor_mode",
            "canvas_data", "structure", "enabled_blocks", "added_block_ids",
            "project_name", "sha256", "issued_at", "locked", "starred",
            "tags", "folder_id", "source_file", "imported_from",
            "version_history", "audit_events",
        ]
        read_only_fields = [
            "id", "doc_id", "sha256", "issued_at",
            "created_at", "updated_at", "version_history", "audit_events",
        ]

    def get_owner_avatar(self, obj):
        return obj.owner.initials if obj.owner else ""


class DocumentCreateSerializer(serializers.Serializer):
    """Mirrors app-context.tsx createDocumentFromTemplate(templateId, title)."""

    template_id = serializers.CharField(required=False, allow_blank=True)
    title = serializers.CharField(max_length=512)


class EditorStateSerializer(serializers.Serializer):
    """
    Partial update for editor state — saves canvas_data, structure,
    enabled_blocks, and added_block_ids without touching other fields.
    """

    canvas_data = serializers.JSONField(required=False)
    structure = serializers.JSONField(required=False)
    enabled_blocks = serializers.JSONField(required=False)
    added_block_ids = serializers.JSONField(required=False)
