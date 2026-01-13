from rest_framework.permissions import BasePermission


class IsSystemUser(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in ["system_owner", "system_admin"]
        )

