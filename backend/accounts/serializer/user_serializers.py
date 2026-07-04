from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from accounts.constants import Role
from accounts.models import User


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "role",
            "organization",
            "linked_learner",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "organization", "created_at", "updated_at"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["organization_name"] = (
            instance.organization.name if instance.organization_id else None
        )
        data["role_display"] = instance.get_role_display()
        return data


class UserCreateSerializer(serializers.ModelSerializer):

    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["email", "full_name", "role", "password", "linked_learner"]

    def validate_role(self, value):
        if value == Role.ORG_ADMIN:
            # Creating fellow admins is allowed, but keep it explicit/auditable.
            return value
        if value not in Role.values:
            raise serializers.ValidationError("Unknown role.")
        return value

    def validate_linked_learner(self, learner):
        request = self.context.get("request")
        if learner is not None and request is not None:
            if learner.organization_id != request.user.organization_id:
                raise serializers.ValidationError(
                    "Linked learner must belong to your organization."
                )
        return learner

    def create(self, validated_data):
        from accounts.services import create_user

        return create_user(**validated_data)
