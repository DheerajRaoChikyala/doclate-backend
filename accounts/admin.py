from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "gstin", "created_at"]
    search_fields = ["name", "gstin"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["email", "first_name", "last_name", "organization", "is_active"]
    list_filter = ["is_active", "organization"]
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Doclate", {"fields": ("organization", "designation", "phone", "phone_verified", "avatar_initials", "signature_image", "mfa_enabled")}),
    )
