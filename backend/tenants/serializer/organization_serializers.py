from rest_framework import serializers

from tenants.models import Organization


class OrganizationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "type",
            "email",
            "phone",
            "city",
            "is_active",
            "llm_daily_call_cap",
            "llm_monthly_call_cap",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["type_display"] = instance.get_type_display()
        data["user_count"] = instance.users.count()
        return data


class OrganizationCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Organization
        fields = ["name", "type", "email", "phone", "city"]
