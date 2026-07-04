import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.constants import Role
from attempts.models import Attempt
from core.functioncall import Global_error_message
from core.permissions import IsAuthenticat
from core.throttling import PerTenantDailyLLMThrottle
from materials.models import SourceMaterial
from questions.models import Question
from questions.serializer import PracticeQuestionSerializer
from tenants.constants import PrepContext

logger = logging.getLogger("prepcheck.questions")

LEARNER_ROLES = {Role.STUDENT, Role.CANDIDATE}
PRACTICE_LIST_CAP = 1000  # bound the payload of the practice-questions list


class NextQuestionView(APIView):

    permission_classes = [IsAuthenticat]

    def get(self, request, *args, **kwargs):
        try:
            if request.user.role not in LEARNER_ROLES:
                return Response(
                    {"status": False, "message": "Only learners practise.", "data": []},
                    status=status.HTTP_403_FORBIDDEN,
                )

            qs = Question.objects.all()  # tenant-scoped
            material_id = request.query_params.get("material")
            topic = request.query_params.get("topic")
            if material_id:
                qs = qs.filter(source_material_id=material_id)
            if topic:
                qs = qs.filter(topic_or_category=topic)

            attempted = Attempt.objects.filter(learner=request.user).values_list(
                "question_id", flat=True
            )
            question = qs.exclude(id__in=attempted).order_by("pk").first()
            if question is None:
                return Response(
                    {
                        "status": True,
                        "message": "No unattempted questions available. Try refresh.",
                        "data": None,
                    },
                    status=status.HTTP_200_OK,
                )
            return Response(
                {
                    "status": True,
                    "message": "Next question.",
                    "data": PracticeQuestionSerializer(question, context={"request": request}).data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"status": False, "message": Global_error_message, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class PracticeQuestionsView(APIView):

    permission_classes = [IsAuthenticat]

    def get(self, request, *args, **kwargs):
        try:
            if request.user.role not in LEARNER_ROLES:
                return Response(
                    {"status": False, "message": "Only learners practise.", "data": []},
                    status=status.HTTP_403_FORBIDDEN,
                )

            qs = Question.objects.all().order_by("source_material_id", "pk")  # tenant-scoped
            material_id = request.query_params.get("material")
            if material_id:
                qs = qs.filter(source_material_id=material_id)

            attempted = set(
                Attempt.objects.filter(learner=request.user).values_list(
                    "question_id", flat=True
                )
            )
            data = [
                {
                    "id": q.id,
                    "question_text": q.question_text,
                    "topic_or_category": q.topic_or_category,
                    "difficulty": q.difficulty,
                    "category": q.category,
                    "material_id": q.source_material_id,
                    "subject_or_role": q.source_material.subject_or_role,
                    "topic": q.source_material.topic or "general",
                    "mode": q.mode,
                    "attempted": q.id in attempted,
                }
                for q in qs.select_related("source_material")[:PRACTICE_LIST_CAP]
            ]
            return Response(
                {"status": True, "message": "Practice questions.", "data": data},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"status": False, "message": Global_error_message, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class RefreshQuestionView(APIView):

    permission_classes = [IsAuthenticat]
    throttle_classes = [PerTenantDailyLLMThrottle]

    def post(self, request, *args, **kwargs):
        try:
            if request.user.role not in LEARNER_ROLES:
                return Response(
                    {"status": False, "message": "Only learners practise.", "data": []},
                    status=status.HTTP_403_FORBIDDEN,
                )

            material_id = request.data.get("material")
            if not material_id:
                return Response(
                    {"status": False, "message": "material is required.", "data": []},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            material = SourceMaterial.objects.filter(id=material_id).first()  # tenant-scoped
            if material is None:
                return Response(
                    {"status": False, "message": "Source material not found.", "data": []},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if not material.is_ready:
                return Response(
                    {"status": False, "message": "Material is not ready.", "data": []},
                    status=status.HTTP_409_CONFLICT,
                )

            # Import here to avoid a heavy import chain at module load.
            from questions.services.generation import generate_for_material

            difficulty = request.data.get("difficulty")
            category = request.data.get("category")
            created = generate_for_material(
                material, count=1, difficulty=difficulty, category=category
            )
            if not created:
                return Response(
                    {"status": True, "message": "Could not produce a new question; try again.", "data": None},
                    status=status.HTTP_200_OK,
                )
            logger.info(
                "Refreshed question",
                extra={"user": request.user.id, "tenant": request.user.organization_id},
            )
            return Response(
                {
                    "status": True,
                    "message": "New question generated.",
                    "data": PracticeQuestionSerializer(created[0], context={"request": request}).data,
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response(
                {"status": False, "message": Global_error_message, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
