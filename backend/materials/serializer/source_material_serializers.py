from rest_framework import serializers

from materials.models import SourceMaterial
from tenants.constants import PrepContext


class SourceMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourceMaterial
        fields = [
            "id",
            "mode",
            "subject_or_role",
            "topic",
            "file",
            "source_text",
            "ingestion_status",
            "ingestion_error",
            "uploaded_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "ingestion_status",
            "ingestion_error",
            "uploaded_by",
            "created_at",
            "updated_at",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["mode_display"] = instance.get_mode_display()
        data["is_ready"] = instance.is_ready
        return data


class SourceMaterialCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = SourceMaterial
        fields = ["mode", "subject_or_role", "topic", "file", "source_text"]

    MAX_FILE_MB = 10

    def validate_file(self, value):
        if not value:
            return value
        name = (getattr(value, "name", "") or "").lower()
        if not name.endswith(".pdf"):
            raise serializers.ValidationError("Only PDF files are supported.")
        size = getattr(value, "size", 0) or 0
        if size > self.MAX_FILE_MB * 1024 * 1024:
            raise serializers.ValidationError(
                f"File is too large (max {self.MAX_FILE_MB} MB)."
            )
        return value

    def validate(self, attrs):
        mode = attrs.get("mode")
        if mode == PrepContext.EXAM and not attrs.get("file"):
            raise serializers.ValidationError(
                {"file": "Exam material requires an uploaded PDF."}
            )
        if mode == PrepContext.INTERVIEW and not (attrs.get("source_text") or attrs.get("file")):
            raise serializers.ValidationError(
                {"source_text": "Interview material requires a job description or role text."}
            )
        return attrs
