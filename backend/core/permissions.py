from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission, IsAuthenticated


class IsAuthenticat(IsAuthenticated):

    def has_permission(self, request, view):
        is_authenticated = super().has_permission(request, view)
        if not is_authenticated:
            raise AuthenticationFailed("Credentials are invalid or expired.")
        return True


class HasAnyRole(BasePermission):

    message = "Your role is not permitted to perform this action."

    def has_permission(self, request, view):
        allowed = getattr(view, "allowed_roles", None)
        if not allowed:
            return True  # no role restriction declared
        user = request.user
        if not (user and user.is_authenticated):
            return False
        allowed_values = {getattr(r, "value", r) for r in allowed}
        return user.role in allowed_values

    def has_object_permission(self, request, view, obj):
        request_org = getattr(request.user, "organization_id", None)
        obj_org = getattr(obj, "organization_id", getattr(obj, "tenant_id", None))
        return obj_org is not None and obj_org == request_org


class IsOrgAdmin(HasAnyRole):

    def has_permission(self, request, view):
        from accounts.constants import Role

        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.role == Role.ORG_ADMIN
        )


class IsSuperUser(BasePermission):

    message = "Only a platform superadmin may perform this action."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_superuser)
