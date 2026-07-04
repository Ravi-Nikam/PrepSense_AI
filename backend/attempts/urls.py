from django.urls import path

from .views import AttemptViewSet

urlpatterns = [
    path(
        "attempts/",
        AttemptViewSet.as_view({"get": "list", "post": "create"}),
        name="attempt_list",
    ),
    path(
        "attempts/<int:pk>/",
        AttemptViewSet.as_view({"get": "retrieve"}),
        name="attempt_detail",
    ),
]
