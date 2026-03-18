from rest_framework import serializers
from .models import Template, BlockDefinition


class BlockDefinitionSerializer(serializers.ModelSerializer):
    canonical_id = serializers.CharField(source="canonical_id")

    class Meta:
        model = BlockDefinition
        fields = [
            "id", "canonical_id", "group", "block_type", "label",
            "locked", "default_enabled", "is_addon",
        ]
        read_only_fields = fields


class TemplateListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Template
        fields = [
            "id", "name", "category", "pack", "estimated_time",
            "required_fields", "badges", "version", "updated_at",
            "description", "prepared_by", "prepared_for", "summary",
        ]
        read_only_fields = fields


class TemplateDetailSerializer(serializers.ModelSerializer):
    blocks = BlockDefinitionSerializer(many=True, read_only=True)

    class Meta:
        model = Template
        fields = [
            "id", "name", "category", "pack", "estimated_time",
            "required_fields", "badges", "version", "updated_at",
            "description", "prepared_by", "prepared_for", "summary",
            "default_structure", "default_canvas_data", "default_validations",
            "blocks",
        ]
        read_only_fields = fields
