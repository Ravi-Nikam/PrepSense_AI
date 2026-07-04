from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

from core.health import HealthView

urlpatterns = [
    path("admin/", admin.site.urls),
    # Liveness/readiness probe for load balancers and container healthchecks.
    path("healthz/", HealthView.as_view(), name="health"),
    # OpenAPI schema + browsable docs.
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    # Auth + user management.
    path("api/", include("accounts.urls")),
    # Platform superadmin: organization (tenant) onboarding.
    path("api/", include("tenants.urls")),
    # Core prep loop.
    path("api/", include("materials.urls")),
    path("api/", include("questions.urls")),
    path("api/", include("attempts.urls")),
    path("api/", include("reports.urls")),
]
