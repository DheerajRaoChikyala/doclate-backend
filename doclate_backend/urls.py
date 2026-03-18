"""
Doclate backend URL configuration.

All API endpoints live under /api/v1/.
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # JWT auth
    path("api/v1/auth/token/", TokenObtainPairView.as_view(), name="token_obtain"),
    path("api/v1/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # App APIs
    path("api/v1/accounts/", include("accounts.urls")),
    path("api/v1/documents/", include("documents.urls")),
    path("api/v1/templates/", include("templates_catalog.urls")),
    path("api/v1/signing/", include("signing.urls")),
    path("api/v1/export/", include("export.urls")),
]
