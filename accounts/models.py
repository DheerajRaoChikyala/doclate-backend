"""
User and Organization models for Doclate.

Aligned with:
  - signing-data.ts → UserProfile interface
  - mock-data.ts → document.owner, document.ownerAvatar
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class Organization(models.Model):
    """Tenant — maps to BeyondTax / Aiyug Workspace org."""

    id = models.CharField(max_length=36, primary_key=True)
    name = models.CharField(max_length=255)
    gstin = models.CharField("GSTIN", max_length=15, blank=True, default="")
    pan = models.CharField("PAN", max_length=10, blank=True, default="")
    address = models.TextField(blank=True, default="")
    contact = models.CharField(max_length=255, blank=True, default="")
    logo = models.FileField(upload_to="org_logos/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "organizations"

    def __str__(self):
        return self.name


class User(AbstractUser):
    """
    Custom user model aligned with signing-data.ts UserProfile.

    Fields from frontend:
      id, email, emailVerified, fullName, designation, phone,
      phoneVerified, avatarInitials, signatureImageUrl, mfaEnabled
    """

    id = models.CharField(max_length=36, primary_key=True)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="members", null=True, blank=True
    )
    designation = models.CharField(max_length=128, blank=True, default="")
    phone = models.CharField(max_length=20, blank=True, default="")
    phone_verified = models.BooleanField(default=False)
    avatar_initials = models.CharField(max_length=4, blank=True, default="")
    signature_image = models.FileField(upload_to="signatures/", blank=True, null=True)
    mfa_enabled = models.BooleanField(default=False)

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def initials(self) -> str:
        if self.avatar_initials:
            return self.avatar_initials
        parts = self.get_full_name().split()
        return "".join(p[0].upper() for p in parts[:2]) if parts else self.username[:2].upper()
