import logging

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.http import Http404
from rest_framework import status, viewsets
from rest_framework.response import Response

from accounts.constants import Role
from accounts.models import User
from core.functioncall import Global_error_message, StandardResultsSetPagination
from core.permissions import IsAuthenticat, IsSuperUser
from tenants.models import Organization
from tenants.serializer import OrganizationCreateSerializer, OrganizationSerializer

logger = logging.getLogger("prepcheck.tenants")


class OrganizationViewSet(viewsets.ModelViewSet):

    permission_classes = [IsAuthenticat, IsSuperUser]
    serializer_class = OrganizationSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return Organization.objects.all().order_by("pk")

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = OrganizationSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = OrganizationSerializer(queryset, many=True)
            return Response(
                {"status": True, "message": "Organizations retrieved successfully.", "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"status": False, "message": Global_error_message, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def create(self, request, *args, **kwargs):
        try:
            data = request.data or {}
            admin_email = (data.get("admin_email") or "").strip().lower()
            admin_password = data.get("admin_password") or ""
            admin_full_name = data.get("admin_full_name") or "Org Admin"

            if not admin_email or not admin_password:
                return Response(
                    {"status": False, "message": "admin_email and admin_password are required.", "data": []},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if User.objects.filter(email=admin_email).exists():
                return Response(
                    {"status": False, "message": "A user with that admin email already exists.", "data": []},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                validate_password(admin_password)
            except DjangoValidationError as exc:
                return Response(
                    {"status": False, "message": " ".join(exc.messages), "data": []},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serializer = OrganizationCreateSerializer(data=data)
            serializer.is_valid(raise_exception=True)

            with transaction.atomic():
                org = serializer.save(created_by=request.user)
                admin = User.objects.create_user(
                    email=admin_email,
                    password=admin_password,
                    organization=org,
                    role=Role.ORG_ADMIN,
                    full_name=admin_full_name,
                )
            logger.info(
                "Organization + first admin created",
                extra={"user": request.user.id, "org": org.id},
            )
            return Response(
                {
                    "status": True,
                    "message": "Organization and its admin created successfully.",
                    "data": {
                        **OrganizationSerializer(org).data,
                        "admin_email": admin.email,
                    },
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
            serializer = OrganizationSerializer(instance)
            return Response(
                {"status": True, "message": "Organization retrieved successfully.", "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        except Http404:
            return Response(
                {"status": False, "message": "Organization not found.", "data": []},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"status": False, "message": Global_error_message, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = OrganizationSerializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save(updated_by=request.user)
            return Response(
                {"status": True, "message": "Organization updated successfully.", "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        except Http404:
            return Response(
                {"status": False, "message": "Organization not found.", "data": []},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"status": False, "message": Global_error_message, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
