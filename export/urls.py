from django.urls import path
from . import views

urlpatterns = [
    path("fingerprint/", views.FingerprintView.as_view(), name="fingerprint"),
    path("pdf/<str:doc_id>/", views.ExportPDFView.as_view(), name="export_pdf"),
    path("issue/<str:doc_id>/", views.IssueDocumentView.as_view(), name="issue_document"),
]
