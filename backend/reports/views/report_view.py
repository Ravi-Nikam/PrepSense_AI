import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.constants import Role
from accounts.models import User
from core.functioncall import Global_error_message
from core.permissions import IsAuthenticat
from reports.services.progress import dashboard_rows, learner_report, student_papers

logger = logging.getLogger("prepcheck.reports")

OBSERVER_ROLES = {Role.TEACHER, Role.MENTOR, Role.ORG_ADMIN}
LEARNER_ROLES = {Role.STUDENT, Role.CANDIDATE}


def _resolve_learner(request, learner_id):
    return (
        User.objects.filter(
            organization_id=request.user.organization_id,
            id=learner_id,
            role__in=[Role.STUDENT, Role.CANDIDATE],
        )
        .first()
    )


def _can_view(user, learner):
    if user.id == learner.id:
        return True
    if user.role in OBSERVER_ROLES:
        return True
    if user.role == Role.PARENT:
        return user.linked_learner_id == learner.id
    return False


class LearnerReportView(APIView):

    permission_classes = [IsAuthenticat]

    def get(self, request, learner_id, *args, **kwargs):
        try:
            learner = _resolve_learner(request, learner_id)
            if learner is None:
                return Response(
                    {"status": False, "message": "Learner not found.", "data": []},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if not _can_view(request.user, learner):
                return Response(
                    {"status": False, "message": "You may not view this learner's report.", "data": []},
                    status=status.HTTP_403_FORBIDDEN,
                )
            return Response(
                {"status": True, "message": "Learner report.", "data": learner_report(learner)},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"status": False, "message": Global_error_message, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class MyPapersView(APIView):

    permission_classes = [IsAuthenticat]

    def get(self, request, *args, **kwargs):
        try:
            if request.user.role not in LEARNER_ROLES:
                return Response(
                    {"status": False, "message": "Only learners have a marks sheet.", "data": []},
                    status=status.HTTP_403_FORBIDDEN,
                )
            return Response(
                {"status": True, "message": "Your papers.", "data": student_papers(request.user)},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"status": False, "message": Global_error_message, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ObserverDashboardView(APIView):

    permission_classes = [IsAuthenticat]

    def get(self, request, *args, **kwargs):
        try:
            user = request.user
            if user.role in OBSERVER_ROLES:
                learners = list(
                    User.objects.filter(
                        organization_id=user.organization_id,
                        role__in=[Role.STUDENT, Role.CANDIDATE],
                    ).order_by("pk")
                )
            elif user.role == Role.PARENT:
                learners = (
                    [user.linked_learner] if user.linked_learner_id else []
                )
            elif user.role in LEARNER_ROLES:
                learners = [user]  # a learner sees their own summary
            else:
                learners = []

            return Response(
                {"status": True, "message": "Dashboard.", "data": dashboard_rows(learners)},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"status": False, "message": Global_error_message, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
