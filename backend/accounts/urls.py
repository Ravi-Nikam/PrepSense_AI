from django.urls import path

from .views import (
    LoginView,
    MeView,
    TokenRefreshEnvelopeView,
    UserViewSet,
)

urlpatterns = [
    # --- auth ---
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/refresh/", TokenRefreshEnvelopeView.as_view(), name="token_refresh"),
    path("auth/me/", MeView.as_view(), name="me"),
    # --- user management (ORG_ADMIN, own tenant only) ---
    path("users/", UserViewSet.as_view({"get": "list", "post": "create"}), name="user_list"),
    path(
        "users/<int:pk>/",
        UserViewSet.as_view(
            {"get": "retrieve", "patch": "update", "delete": "destroy"}
        ),
        name="user_detail",
    ),
    path(
        "users/<int:pk>/password/",
        UserViewSet.as_view({"post": "set_password"}),
        name="user_set_password",
    ),
]
