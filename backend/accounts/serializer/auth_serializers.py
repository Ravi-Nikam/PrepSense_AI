from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["tenant_id"] = user.organization_id
        token["role"] = user.role
        token["email"] = user.email
        token["is_superuser"] = user.is_superuser
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        # Surface a little context so the client doesn't need to decode the JWT.
        data["role"] = self.user.role
        data["tenant_id"] = self.user.organization_id
        data["email"] = self.user.email
        data["full_name"] = self.user.full_name
        data["is_superuser"] = self.user.is_superuser
        return data
