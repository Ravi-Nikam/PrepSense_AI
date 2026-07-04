import logging

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from accounts.serializer import CustomTokenObtainPairSerializer, UserSerializer
from core.functioncall import Global_error_message

logger = logging.getLogger("prepcheck.accounts")


class LoginView(TokenObtainPairView):

    permission_classes = [AllowAny]
    serializer_class = CustomTokenObtainPairSerializer
    # Brute-force protection: cap login attempts per client IP (rate from env).
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except (InvalidToken, TokenError):
            logger.warning("Failed login for email=%s", request.data.get("email"))
            return Response(
                {"status": False, "message": "Invalid credentials.", "data": []},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except Exception as e:
            logger.warning("Failed login for email=%s", request.data.get("email"))
            return Response(
                {"status": False, "message": "Invalid credentials.", "error": str(e)},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        logger.info(
            "Login success",
            extra={
                "user": serializer.user.id,
                "tenant": serializer.user.organization_id,
            },
        )
        return Response(
            {
                "status": True,
                "message": "Login successful.",
                "data": serializer.validated_data,
            },
            status=status.HTTP_200_OK,
        )


class TokenRefreshEnvelopeView(TokenRefreshView):

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except (InvalidToken, TokenError):
            return Response(
                {"status": False, "message": "Invalid or expired refresh token.", "data": []},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return Response(
            {"status": True, "message": "Token refreshed.", "data": serializer.validated_data},
            status=status.HTTP_200_OK,
        )


class MeView(APIView):

    def get(self, request, *args, **kwargs):
        try:
            serializer = UserSerializer(request.user)
            return Response(
                {"status": True, "message": "Current user.", "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"status": False, "message": Global_error_message, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
