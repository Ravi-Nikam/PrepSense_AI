import logging

from django.http import Http404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.response import Response

from accounts.constants import Role
from attempts.models import Attempt
from attempts.serializer import AttemptCreateSerializer, AttemptSerializer
from attempts.tasks import grade_attempt_task
from core.filters import SearchFilter
from core.functioncall import Global_error_message, StandardResultsSetPagination
from core.permissions import IsAuthenticat

logger = logging.getLogger("prepcheck.attempts")


class AttemptViewSet(viewsets.ModelViewSet):

    permission_classes = [IsAuthenticat]
    serializer_class = AttemptSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [SearchFilter, DjangoFilterBackend]
    filterset_fields = ["learner", "question", "score"]
    search_fields = ["submitted_answer"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Attempt.objects.none()  # schema generation has no real user
        qs = Attempt.objects.all().order_by("-created_at")  # tenant-scoped already
        user = self.request.user
        if user.role in {Role.STUDENT, Role.CANDIDATE}:
            return qs.filter(learner=user)
        if user.role == Role.PARENT:
            # Parent sees only their linked learner (nobody if unlinked).
            return qs.filter(learner_id=user.linked_learner_id)
        # Observers with tenant-wide view: TEACHER / MENTOR / ORG_ADMIN.
        return qs

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = AttemptSerializer(page, many=True, context={"request": request})
                return self.get_paginated_response(serializer.data)
            serializer = AttemptSerializer(queryset, many=True, context={"request": request})
            return Response(
                {"status": True, "message": "Attempts retrieved successfully.", "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"status": False, "message": Global_error_message, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def create(self, request, *args, **kwargs):
        try:
            if request.user.role not in {Role.STUDENT, Role.CANDIDATE}:
                return Response(
                    {"status": False, "message": "Only learners may submit answers.", "data": []},
                    status=status.HTTP_403_FORBIDDEN,
                )
            serializer = AttemptCreateSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            attempt = serializer.save(learner=request.user)
            logger.info(
                "Answer submitted",
                extra={"user": request.user.id, "tenant": request.user.organization_id},
            )
            data = AttemptSerializer(attempt, context={"request": request}).data
            grade_attempt_task.delay(attempt.id, request.user.organization_id)
            return Response(
                {"status": True, "message": "Answer submitted successfully. Grading in progress.", "data": data},
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response(
                {"status": False, "message": Global_error_message, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()  # 404 if outside caller's visible scope
            serializer = AttemptSerializer(instance, context={"request": request})
            return Response(
                {"status": True, "message": "Attempt retrieved successfully.", "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        except Http404:
            return Response(
                {"status": False, "message": "Attempt not found.", "data": []},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"status": False, "message": Global_error_message, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
