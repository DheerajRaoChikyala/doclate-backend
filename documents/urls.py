from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register("", views.DocumentViewSet, basename="document")

# Nested router for folders
folder_router = DefaultRouter()
folder_router.register("", views.FolderViewSet, basename="folder")

urlpatterns = [
    path("bulk/", views.BulkOperationsView.as_view(), name="bulk_operations"),
    path("import/", views.ImportDocumentView.as_view(), name="import_document"),
    path("folders/", include(folder_router.urls)),
    path("", include(router.urls)),
]
