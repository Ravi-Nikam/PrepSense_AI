from django.urls import path

from .views import OrganizationViewSet

urlpatterns = [
    # Platform superadmin only — tenant onboarding.
    path(
        "organizations/",
        OrganizationViewSet.as_view({"get": "list", "post": "create"}),
        name="organization_list",
    ),
    path(
        "organizations/<int:pk>/",
        OrganizationViewSet.as_view({"get": "retrieve", "patch": "update"}),
        name="organization_detail",
    ),
]
