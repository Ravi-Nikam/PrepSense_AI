

class UnscopedTenantAdmin:
    def get_queryset(self, request):
        return self.model.all_objects.all()

    def has_add_permission(self, request):
        return False
