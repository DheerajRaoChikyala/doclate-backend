"""
Template catalog API — read-only for regular users, admin-editable.
"""

from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Template, BlockDefinition
from .serializers import (
    TemplateListSerializer,
    TemplateDetailSerializer,
    BlockDefinitionSerializer,
)


class TemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/v1/templates/              — list all templates
    GET /api/v1/templates/<id>/         — template detail with blocks
    GET /api/v1/templates/<id>/blocks/  — block definitions for template
    """

    queryset = Template.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["category", "pack"]
    search_fields = ["name", "description"]

    def get_serializer_class(self):
        if self.action == "list":
            return TemplateListSerializer
        return TemplateDetailSerializer

    @action(detail=True, methods=["get"])
    def blocks(self, request, pk=None):
        template = self.get_object()
        blocks = BlockDefinition.objects.filter(template=template)
        return Response(BlockDefinitionSerializer(blocks, many=True).data)
