import logging

from django.http import Http404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.response import Response

from accounts.constants import Role
from core.filters import SearchFilter
from core.functioncall import Global_error_message, StandardResultsSetPagination
from core.permissions import HasAnyRole, IsAuthenticat
from questions.models import Question
from questions.serializer import (
    QuestionCreateSerializer,
    QuestionSerializer,
    QuestionUpdateSerializer,
)

logger = logging.getLogger("prepcheck.questions")


class QuestionViewSet(viewsets.ModelViewSet):

    permission_classes = [IsAuthenticat, HasAnyRole]
    allowed_roles = [Role.TEACHER, Role.MENTOR, Role.ORG_ADMIN]
    serializer_class = QuestionSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [SearchFilter, DjangoFilterBackend]
    filterset_fields = ["mode", "difficulty", "category", "source_material"]
    search_fields = ["question_text", "topic_or_category"]

    def get_queryset(self):
        return Question.objects.all().order_by("-pk")

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = QuestionSerializer(page, many=True, context={"request": request})
                return self.get_paginated_response(serializer.data)
            serializer = QuestionSerializer(queryset, many=True, context={"request": request})
            return Response(
                {"status": True, "message": "Questions retrieved successfully.", "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"status": False, "message": Global_error_message, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def create(self, request, *args, **kwargs):
        try:
            serializer = QuestionCreateSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            question = serializer.save()
            return Response(
                {
                    "status": True,
                    "message": "Question created successfully.",
                    "data": QuestionSerializer(question, context={"request": request}).data,
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
            serializer = QuestionSerializer(instance, context={"request": request})
            return Response(
                {"status": True, "message": "Question retrieved successfully.", "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        except Http404:
            return Response(
                {"status": False, "message": "Question not found.", "data": []},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"status": False, "message": Global_error_message, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()  # 404 if outside tenant
            serializer = QuestionUpdateSerializer(
                instance, data=request.data, partial=True, context={"request": request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                {
                    "status": True,
                    "message": "Question updated successfully.",
                    "data": QuestionSerializer(instance, context={"request": request}).data,
                },
                status=status.HTTP_200_OK,
            )
        except Http404:
            return Response(
                {"status": False, "message": "Question not found.", "data": []},
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
                {"status": True, "message": "Question deleted successfully.", "data": []},
                status=status.HTTP_200_OK,
            )
        except Http404:
            return Response(
                {"status": False, "message": "Question not found.", "data": []},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"status": False, "message": Global_error_message, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
