"""
Document API views aligned with app-context.tsx operations.

Every operation from the frontend AppState interface has a corresponding endpoint.
"""

import uuid
from django.utils import timezone
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Document, Folder, VersionEntry, AuditEvent
from .serializers import (
    DocumentListSerializer,
    DocumentDetailSerializer,
    DocumentCreateSerializer,
    EditorStateSerializer,
    FolderSerializer,
    AuditEventSerializer,
)


# ─────────────────────────────────────────────────────────────────────────────
# DOCUMENT VIEWSET
# ─────────────────────────────────────────────────────────────────────────────

class DocumentViewSet(viewsets.ModelViewSet):
    """
    CRUD + lifecycle operations for documents.

    GET    /api/v1/documents/                     — list
    POST   /api/v1/documents/                     — create
    GET    /api/v1/documents/<id>/                 — detail
    PATCH  /api/v1/documents/<id>/                 — update
    DELETE /api/v1/documents/<id>/                 — delete

    POST   /api/v1/documents/<id>/duplicate/       — duplicateDocument
    POST   /api/v1/documents/<id>/archive/         — archiveDocument
    POST   /api/v1/documents/<id>/restore/         — restoreDocument
    POST   /api/v1/documents/<id>/lock/            — lockDocument
    POST   /api/v1/documents/<id>/unlock/          — unlockDocument
    POST   /api/v1/documents/<id>/star/            — starDocument
    POST   /api/v1/documents/<id>/unstar/          — unstarDocument
    POST   /api/v1/documents/<id>/send-to-review/  — sendToReview
    POST   /api/v1/documents/<id>/send-to-signing/ — sendToSigning
    POST   /api/v1/documents/<id>/revoke/          — revokeDocument
    POST   /api/v1/documents/<id>/create-version/  — createVersion
    PATCH  /api/v1/documents/<id>/editor-state/    — save editor state
    POST   /api/v1/documents/<id>/move-to-folder/  — moveDocumentToFolder
    POST   /api/v1/documents/<id>/tags/            — add/remove tags
    """

    filterset_fields = ["status", "category", "template_name", "starred", "locked", "folder"]
    search_fields = ["title", "doc_id", "tags"]
    ordering_fields = ["updated_at", "created_at", "title", "status"]

    def get_queryset(self):
        return Document.objects.filter(owner=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return DocumentListSerializer
        if self.action == "create":
            return DocumentCreateSerializer
        return DocumentDetailSerializer

    def perform_create(self, serializer):
        """Mirrors createDocumentFromTemplate(templateId, title)."""
        data = serializer.validated_data
        template_id = data.get("template_id", "")
        title = data["title"]

        doc = Document(
            id=str(uuid.uuid4()),
            title=title,
            owner=self.request.user,
            organization=self.request.user.organization,
        )

        if template_id:
            from templates_catalog.models import Template

            try:
                template = Template.objects.get(id=template_id)
                doc.template = template
                doc.template_name = template.name
                doc.canvas_data = template.default_canvas_data
                doc.structure = template.default_structure
                doc.category = template.category
            except Template.DoesNotExist:
                pass

        doc.save()

        # Audit
        AuditEvent.objects.create(
            document=doc,
            event_type="document.created",
            actor=self.request.user.get_full_name() or self.request.user.username,
            description=f"Document created: {title}",
        )

        # Return full detail
        self.serializer_class = DocumentDetailSerializer
        return doc

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doc = self.perform_create(serializer)
        return Response(
            DocumentDetailSerializer(doc).data,
            status=status.HTTP_201_CREATED,
        )

    # ── Lifecycle actions ──

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        doc = self.get_object()
        new_doc = Document(
            id=str(uuid.uuid4()),
            title=f"{doc.title} (Copy)",
            category=doc.category,
            owner=request.user,
            organization=doc.organization,
            template=doc.template,
            template_name=doc.template_name,
            editor_mode=doc.editor_mode,
            canvas_data=doc.canvas_data,
            structure=doc.structure,
            enabled_blocks=doc.enabled_blocks,
            added_block_ids=doc.added_block_ids,
            tags=doc.tags,
        )
        new_doc.save()
        return Response(DocumentDetailSerializer(new_doc).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        doc = self.get_object()
        doc.status = "archived"
        doc.save(update_fields=["status", "updated_at"])
        self._audit(doc, "document.archived", "Document archived")
        return Response({"status": "archived"})

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        doc = self.get_object()
        doc.status = "draft"
        doc.save(update_fields=["status", "updated_at"])
        self._audit(doc, "document.restored", "Document restored to draft")
        return Response({"status": "draft"})

    @action(detail=True, methods=["post"])
    def lock(self, request, pk=None):
        doc = self.get_object()
        doc.locked = True
        doc.save(update_fields=["locked", "updated_at"])
        return Response({"locked": True})

    @action(detail=True, methods=["post"])
    def unlock(self, request, pk=None):
        doc = self.get_object()
        doc.locked = False
        doc.save(update_fields=["locked", "updated_at"])
        return Response({"locked": False})

    @action(detail=True, methods=["post"])
    def star(self, request, pk=None):
        doc = self.get_object()
        doc.starred = True
        doc.save(update_fields=["starred", "updated_at"])
        return Response({"starred": True})

    @action(detail=True, methods=["post"])
    def unstar(self, request, pk=None):
        doc = self.get_object()
        doc.starred = False
        doc.save(update_fields=["starred", "updated_at"])
        return Response({"starred": False})

    @action(detail=True, methods=["post"], url_path="send-to-review")
    def send_to_review(self, request, pk=None):
        doc = self.get_object()
        doc.status = "in_review"
        doc.save(update_fields=["status", "updated_at"])
        self._audit(doc, "document.sent_to_review", "Document sent for review")
        return Response({"status": "in_review"})

    @action(detail=True, methods=["post"], url_path="send-to-signing")
    def send_to_signing(self, request, pk=None):
        doc = self.get_object()
        self._audit(doc, "document.sent_to_signing", "Document sent for signing")
        return Response({"status": doc.status})

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        doc = self.get_object()
        doc.status = "draft"
        doc.sha256 = ""
        doc.issued_at = None
        doc.save(update_fields=["status", "sha256", "issued_at", "updated_at"])
        self._audit(doc, "document.revoked", "Document revoked")
        return Response({"status": "draft"})

    @action(detail=True, methods=["post"], url_path="create-version")
    def create_version(self, request, pk=None):
        doc = self.get_object()
        doc.version += 1
        doc.save(update_fields=["version", "updated_at"])

        entry = VersionEntry.objects.create(
            document=doc,
            version=doc.version,
            status=doc.status,
            actor=request.user.get_full_name() or request.user.username,
            note=request.data.get("note", f"Version {doc.version} created"),
            sha256=doc.sha256,
            canvas_data_snapshot=doc.canvas_data,
        )
        return Response({"version": doc.version})

    @action(detail=True, methods=["patch"], url_path="editor-state")
    def editor_state(self, request, pk=None):
        """Save editor state (canvas_data, structure, enabled_blocks, added_block_ids)."""
        doc = self.get_object()
        serializer = EditorStateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        update_fields = ["updated_at"]
        for field in ("canvas_data", "structure", "enabled_blocks", "added_block_ids"):
            if field in serializer.validated_data:
                setattr(doc, field, serializer.validated_data[field])
                update_fields.append(field)

        doc.save(update_fields=update_fields)
        return Response({"saved": True})

    @action(detail=True, methods=["post"], url_path="move-to-folder")
    def move_to_folder(self, request, pk=None):
        doc = self.get_object()
        folder_id = request.data.get("folder_id")
        if folder_id:
            try:
                folder = Folder.objects.get(id=folder_id, owner=request.user)
                doc.folder = folder
            except Folder.DoesNotExist:
                return Response({"error": "Folder not found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            doc.folder = None
        doc.save(update_fields=["folder", "updated_at"])
        return Response({"folder_id": folder_id})

    @action(detail=True, methods=["post"])
    def tags(self, request, pk=None):
        """Add or remove tags: { action: "add"|"remove", tag: "..." }"""
        doc = self.get_object()
        tag_action = request.data.get("action")
        tag = request.data.get("tag", "")

        if not tag:
            return Response({"error": "tag is required"}, status=status.HTTP_400_BAD_REQUEST)

        current_tags = doc.tags or []
        if tag_action == "add" and tag not in current_tags:
            current_tags.append(tag)
        elif tag_action == "remove" and tag in current_tags:
            current_tags.remove(tag)

        doc.tags = current_tags
        doc.save(update_fields=["tags", "updated_at"])
        return Response({"tags": doc.tags})

    def _audit(self, doc, event_type, description):
        AuditEvent.objects.create(
            document=doc,
            event_type=event_type,
            actor=self.request.user.get_full_name() or self.request.user.username,
            description=description,
        )


# ─────────────────────────────────────────────────────────────────────────────
# BULK OPERATIONS
# ─────────────────────────────────────────────────────────────────────────────

class BulkOperationsView(APIView):
    """
    POST /api/v1/documents/bulk/
    Body: { action: "delete"|"archive"|"move_to_folder"|"export", ids: [...], ... }
    """

    def post(self, request):
        action = request.data.get("action")
        ids = request.data.get("ids", [])

        if not ids:
            return Response({"error": "ids required"}, status=status.HTTP_400_BAD_REQUEST)

        docs = Document.objects.filter(id__in=ids, owner=request.user)

        if action == "delete":
            count = docs.count()
            docs.delete()
            return Response({"deleted": count})

        if action == "archive":
            count = docs.update(status="archived")
            return Response({"archived": count})

        if action == "move_to_folder":
            folder_id = request.data.get("folder_id")
            if folder_id:
                try:
                    Folder.objects.get(id=folder_id, owner=request.user)
                except Folder.DoesNotExist:
                    return Response({"error": "Folder not found"}, status=status.HTTP_404_NOT_FOUND)
            count = docs.update(folder_id=folder_id)
            return Response({"moved": count})

        return Response({"error": f"Unknown action: {action}"}, status=status.HTTP_400_BAD_REQUEST)


# ─────────────────────────────────────────────────────────────────────────────
# FOLDER VIEWSET
# ─────────────────────────────────────────────────────────────────────────────

class FolderViewSet(viewsets.ModelViewSet):
    """
    CRUD for folders.

    GET    /api/v1/documents/folders/           — list
    POST   /api/v1/documents/folders/           — create
    PATCH  /api/v1/documents/folders/<id>/      — update (rename, recolor)
    DELETE /api/v1/documents/folders/<id>/      — delete

    POST   /api/v1/documents/folders/<id>/copy/ — copyFolder
    POST   /api/v1/documents/folders/<id>/move/ — moveFolderToFolder
    """

    serializer_class = FolderSerializer

    def get_queryset(self):
        return Folder.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user, id=str(uuid.uuid4()))

    @action(detail=True, methods=["post"])
    def copy(self, request, pk=None):
        folder = self.get_object()
        new_folder = Folder.objects.create(
            id=str(uuid.uuid4()),
            owner=request.user,
            name=f"{folder.name} (Copy)",
            color=folder.color,
            parent=folder.parent,
            description=folder.description,
        )
        return Response(FolderSerializer(new_folder).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def move(self, request, pk=None):
        folder = self.get_object()
        target_parent_id = request.data.get("parent_id")
        if target_parent_id:
            try:
                parent = Folder.objects.get(id=target_parent_id, owner=request.user)
                folder.parent = parent
            except Folder.DoesNotExist:
                return Response({"error": "Target folder not found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            folder.parent = None
        folder.save(update_fields=["parent", "updated_at"])
        return Response(FolderSerializer(folder).data)


# ─────────────────────────────────────────────────────────────────────────────
# IMPORT
# ─────────────────────────────────────────────────────────────────────────────

class ImportDocumentView(APIView):
    """
    POST /api/v1/documents/import/
    Body: { fileName, templateName, tags?, folderId?, file (multipart) }
    """

    def post(self, request):
        file_name = request.data.get("fileName", "Imported Document")
        template_name = request.data.get("templateName", "")
        tags = request.data.get("tags", [])
        folder_id = request.data.get("folderId")

        doc = Document(
            id=str(uuid.uuid4()),
            title=file_name,
            owner=request.user,
            organization=request.user.organization,
            template_name=template_name,
            tags=tags if isinstance(tags, list) else [],
            source_file=file_name,
            imported_from=file_name.rsplit(".", 1)[-1] if "." in file_name else "",
        )

        if folder_id:
            try:
                folder = Folder.objects.get(id=folder_id, owner=request.user)
                doc.folder = folder
            except Folder.DoesNotExist:
                pass

        # Handle uploaded file
        uploaded_file = request.FILES.get("file")
        if uploaded_file:
            doc.pdf_file = uploaded_file

        doc.save()

        return Response(
            DocumentDetailSerializer(doc).data,
            status=status.HTTP_201_CREATED,
        )
