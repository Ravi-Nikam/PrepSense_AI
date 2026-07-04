from django.urls import path

from .views import SourceMaterialViewSet

urlpatterns = [
    path(
        "materials/",
        SourceMaterialViewSet.as_view({"get": "list", "post": "create"}),
        name="material_list",
    ),
    path(
        "materials/<int:pk>/",
        SourceMaterialViewSet.as_view({"get": "retrieve", "delete": "destroy"}),
        name="material_detail",
    ),
    path(
        "materials/<int:pk>/generate/",
        SourceMaterialViewSet.as_view({"post": "generate"}),
        name="material_generate",
    ),
]
