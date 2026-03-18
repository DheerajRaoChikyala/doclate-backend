from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register("requests", views.SigningRequestViewSet, basename="signing-request")
router.register("policies", views.SigningPolicyViewSet, basename="signing-policy")

urlpatterns = [
    path("verify/", views.VerifyUvcView.as_view(), name="verify_uvc"),
    path("for-document/<str:doc_id>/", views.DocumentSigningView.as_view(), name="doc_signing"),
    path("", include(router.urls)),
]
