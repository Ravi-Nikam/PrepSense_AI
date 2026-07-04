import logging

from django.http import Http404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.response import Response

from accounts.constants import Role
from core.filters import SearchFilter
from core.functioncall import Global_error_message, StandardResultsSetPagination
from core.permissions import HasAnyRole, IsAuthenticat
from core.throttling import PerTenantDailyLLMThrottle
from materials.models import SourceMaterial
from materials.serializer import (
    SourceMaterialCreateSerializer,
    SourceMaterialSerializer,
)
from materials.tasks import ingest_material_task
from questions.constants import Difficulty, QuestionCategory
from questions.tasks import generate_questions_task
from tenants.constants import PrepContext

logger = logging.getLogger("prepcheck.materials")


class SourceMaterialViewSet(viewsets.ModelViewSet):

    permission_classes = [IsAuthenticat, HasAnyRole]
    allowed_roles = [Role.TEACHER, Role.MENTOR, Role.ORG_ADMIN]
    serializer_class = SourceMaterialSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [SearchFilter, DjangoFilterBackend]
    filterset_fields = ["mode", "ingestion_status"]
    search_fields = ["subject_or_role", "topic"]

    def get_queryset(self):
        # Already tenant-scoped by the manager; ordering for stable pagination.
        return SourceMaterial.objects.all().order_by("-pk")

    def get_throttles(self):
        # The per-tenant LLM cost cap applies only to the generation trigger.
        if self.action == "generate":
            return [PerTenantDailyLLMThrottle()]
        return super().get_throttles()

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = SourceMaterialSerializer(page, many=True, context={"request": request})
                return self.get_paginated_response(serializer.data)
            serializer = SourceMaterialSerializer(queryset, many=True, context={"request": request})
            return Response(
                {"status": True, "message": "Source materials retrieved successfully.", "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"status": False, "message": Global_error_message, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def create(self, request, *args, **kwargs):
        try:
            serializer = SourceMaterialCreateSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            # tenant auto-stamped from context; uploader recorded explicitly.
            material = serializer.save(uploaded_by=request.user)
            logger.info(
                "Source material uploaded",
                extra={"user": request.user.id, "tenant": request.user.organization_id},
            )
            # Ingest asynchronously so the upload response returns immediately.
            ingest_material_task.delay(material.id, request.user.organization_id)
            return Response(
                {
                    "status": True,
                    "message": "Source material created successfully. Ingestion queued.",
                    "data": SourceMaterialSerializer(material, context={"request": request}).data,
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response(
                {"status": False, "message": Global_error_message, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = SourceMaterialSerializer(instance, context={"request": request})
            return Response(
                {"status": True, "message": "Source material retrieved successfully.", "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        except Http404:
            return Response(
                {"status": False, "message": "Source material not found.", "data": []},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"status": False, "message": Global_error_message, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def generate(self, request, *args, **kwargs):
        try:
            material = self.get_object()  # 404 if outside tenant
            if not material.is_ready:
                return Response(
                    {
                        "status": False,
                        "message": f"Material is not ready (status={material.ingestion_status}).",
                        "data": [],
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            count = int(request.data.get("count", 5))
            count = max(1, min(count, 100))  # up to a full 100-question paper
            difficulty = request.data.get("difficulty")
            category = request.data.get("category")

            # Validate the mode-appropriate tag if provided.
            if material.mode == PrepContext.EXAM and difficulty and difficulty not in Difficulty.values:
                return Response(
                    {"status": False, "message": "Invalid difficulty.", "data": []},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if material.mode == PrepContext.INTERVIEW and category and category not in QuestionCategory.values:
                return Response(
                    {"status": False, "message": "Invalid category.", "data": []},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            logger.info(
                "Question generation requested (count=%s)",
                count,
                extra={"user": request.user.id, "tenant": request.user.organization_id},
            )
            result = generate_questions_task.delay(
                material.id, request.user.organization_id, count, difficulty, category
            )
            created = getattr(result, "result", None)
            created = created if isinstance(created, int) else count
            return Response(
                {
                    "status": True,
                    "message": f"Paper generation done: {created} question(s) created.",
                    "data": {"material": material.id, "requested": count, "created": created},
                },
                status=status.HTTP_202_ACCEPTED,
            )
        except Http404:
            return Response(
                {"status": False, "message": "Source material not found.", "data": []},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"status": False, "message": Global_error_message, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.delete()
            return Response(
                {"status": True, "message": "Source material deleted successfully.", "data": []},
                status=status.HTTP_200_OK,
            )
        except Http404:
            return Response(
                {"status": False, "message": "Source material not found.", "data": []},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"status": False, "message": Global_error_message, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
