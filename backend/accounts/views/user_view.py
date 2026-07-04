import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.response import Response

from accounts.constants import Role
from accounts.models import User
from accounts.serializer import UserCreateSerializer, UserSerializer
from accounts.services import deactivate_user, set_user_password
from core.filters import SearchFilter
from core.functioncall import Global_error_message, StandardResultsSetPagination
from core.permissions import IsAuthenticat, IsOrgAdmin

logger = logging.getLogger("prepcheck.accounts")


class UserViewSet(viewsets.ModelViewSet):

    permission_classes = [IsAuthenticat, IsOrgAdmin]
    allowed_roles = [Role.ORG_ADMIN]
    serializer_class = UserSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [SearchFilter, DjangoFilterBackend]
    filterset_fields = ["role", "is_active"]
    search_fields = ["email", "full_name"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return User.objects.none()  # schema generation has no real user
        return User.objects.filter(
            organization_id=self.request.user.organization_id
        ).order_by("pk")

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = UserSerializer(page, many=True, context={"request": request})
                return self.get_paginated_response(serializer.data)
            serializer = UserSerializer(queryset, many=True, context={"request": request})
            return Response(
                {"status": True, "message": "Users retrieved successfully.", "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"status": False, "message": Global_error_message, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def create(self, request, *args, **kwargs):
        try:
            serializer = UserCreateSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            # Inject the admin's org so the new user always lands in the same tenant.
            user = serializer.save(organization=request.user.organization)
            logger.info(
                "User created",
                extra={"user": request.user.id, "tenant": request.user.organization_id},
            )
            return Response(
                {
                    "status": True,
                    "message": "User created successfully.",
                    "data": UserSerializer(user, context={"request": request}).data,
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response(
                {"status": False, "message": Global_error_message, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()  # 404 if outside the admin's tenant
            serializer = UserSerializer(
                instance, data=request.data, partial=True, context={"request": request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                {"status": True, "message": "User updated successfully.", "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        except Http404:
            return Response(
                {"status": False, "message": "User not found.", "data": []},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"status": False, "message": Global_error_message, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()  # 404 if outside the admin's tenant
            deactivate_user(instance)  # soft-deactivate rather than hard delete
            return Response(
                {"status": True, "message": "User deactivated successfully.", "data": []},
                status=status.HTTP_200_OK,
            )
        except Http404:
            return Response(
                {"status": False, "message": "User not found.", "data": []},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"status": False, "message": Global_error_message, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def set_password(self, request, *args, **kwargs):
        try:
            instance = self.get_object()  # 404 if outside the admin's tenant
            new_password = (request.data or {}).get("password")
            if not new_password:
                return Response(
                    {"status": False, "message": "Password is required.", "data": []},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                set_user_password(instance, new_password)
            except DjangoValidationError as exc:
                return Response(
                    {"status": False, "message": " ".join(exc.messages), "data": []},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            logger.info(
                "User password reset by admin",
                extra={"user": request.user.id, "tenant": request.user.organization_id},
            )
            return Response(
                {"status": True, "message": "Password updated successfully.", "data": []},
                status=status.HTTP_200_OK,
            )
        except Http404:
            return Response(
                {"status": False, "message": "User not found.", "data": []},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"status": False, "message": Global_error_message, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()  # 404 if outside the admin's tenant
            serializer = UserSerializer(instance, context={"request": request})
            return Response(
                {"status": True, "message": "User retrieved successfully.", "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        except Http404:
            return Response(
                {"status": False, "message": "User not found.", "data": []},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"status": False, "message": Global_error_message, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
