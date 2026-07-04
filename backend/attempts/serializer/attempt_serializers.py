from rest_framework import serializers

from attempts.models import Attempt
from questions.models import Question


class AttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attempt
        fields = [
            "id",
            "learner",
            "question",
            "submitted_answer",
            "score",
            "feedback",
            "graded_at",
            "created_at",
        ]
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["is_graded"] = instance.is_graded
        data["topic_or_category"] = instance.question.topic_or_category
        return data


class AttemptCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Attempt
        fields = ["question", "submitted_answer"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["question"].queryset = Question.objects.all()

    def create(self, validated_data):
        # tenant auto-stamped from context; learner passed by the view via save().
        return Attempt.objects.create(**validated_data)
