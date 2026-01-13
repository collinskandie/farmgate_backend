class TenantQuerySetMixin:
    """
    Enforces account-level isolation.
    """
    def get_queryset(self):
        user = self.request.user

        if user.is_system_user():
            return self.queryset

        return self.queryset.filter(account=user.account)
