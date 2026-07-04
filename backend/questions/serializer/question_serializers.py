from rest_framework import serializers

from materials.models import MaterialChunk, SourceMaterial
from questions.models import Question
from tenants.constants import PrepContext


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = [
            "id",
            "source_material",
            "source_chunk",
            "mode",
            "topic_or_category",
            "difficulty",
            "category",
            "question_text",
            "reference_answer",
            "created_at",
        ]
        read_only_fields = fields  # read serializer

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["mode_display"] = instance.get_mode_display()
        return data


class PracticeQuestionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Question
        fields = [
            "id",
            "source_material",
            "mode",
            "topic_or_category",
            "difficulty",
            "category",
            "question_text",
            "created_at",
        ]
        read_only_fields = fields


class QuestionUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Question
        fields = [
            "topic_or_category",
            "difficulty",
            "category",
            "question_text",
            "reference_answer",
        ]

    def validate_question_text(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Question text cannot be empty.")
        return value


class QuestionCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Question
        fields = [
            "source_material",
            "source_chunk",
            "topic_or_category",
            "difficulty",
            "category",
            "question_text",
            "reference_answer",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Bound now, at request time, so the tenant is already set by middleware.
        self.fields["source_material"].queryset = SourceMaterial.objects.all()
        self.fields["source_chunk"].queryset = MaterialChunk.objects.all()

    def validate(self, attrs):
        material = attrs["source_material"]
        mode = material.mode
        attrs["mode"] = mode

        chunk = attrs.get("source_chunk")
        if chunk is not None and chunk.source_material_id != material.id:
            raise serializers.ValidationError(
                {"source_chunk": "Chunk does not belong to the given source material."}
            )

        if mode == PrepContext.EXAM:
            if not attrs.get("difficulty"):
                raise serializers.ValidationError({"difficulty": "Exam questions require a difficulty."})
            attrs["category"] = None
        elif mode == PrepContext.INTERVIEW:
            if not attrs.get("category"):
                raise serializers.ValidationError({"category": "Interview questions require a category."})
            attrs["difficulty"] = None
        return attrs

    def create(self, validated_data):
        # tenant is auto-stamped in Model.save() from the request context.
        return Question.objects.create(**validated_data)
