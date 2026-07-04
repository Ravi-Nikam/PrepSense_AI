from django.urls import path

from .views import (
    NextQuestionView,
    PracticeQuestionsView,
    QuestionViewSet,
    RefreshQuestionView,
)

urlpatterns = [
    path(
        "questions/",
        QuestionViewSet.as_view({"get": "list", "post": "create"}),
        name="question_list",
    ),
    path(
        "questions/<int:pk>/",
        QuestionViewSet.as_view(
            {"get": "retrieve", "patch": "update", "delete": "destroy"}
        ),
        name="question_detail",
    ),
    # Learner-facing practice loop.
    path("practice/questions/", PracticeQuestionsView.as_view(), name="practice_questions"),
    path("practice/next/", NextQuestionView.as_view(), name="practice_next"),
    path("practice/refresh/", RefreshQuestionView.as_view(), name="practice_refresh"),
]
