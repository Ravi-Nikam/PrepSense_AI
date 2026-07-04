from django.db import models

from tenants.managers import TenantScoped


class ScopedThing(TenantScoped):
    name = models.CharField(max_length=100)

    class Meta:
        db_table = "tests_scoped_thing"
        ordering = ("pk",)

    def __str__(self):
        return self.name
