from django.contrib import admin
from .models import Template, BlockDefinition


class BlockDefinitionInline(admin.TabularInline):
    model = BlockDefinition
    extra = 0


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "pack", "required_fields", "version", "updated_at"]
    list_filter = ["category", "pack"]
    search_fields = ["name"]
    inlines = [BlockDefinitionInline]


@admin.register(BlockDefinition)
class BlockDefinitionAdmin(admin.ModelAdmin):
    list_display = ["canonical_id", "template", "group", "block_type", "locked", "is_addon"]
    list_filter = ["template", "group", "block_type", "locked", "is_addon"]
