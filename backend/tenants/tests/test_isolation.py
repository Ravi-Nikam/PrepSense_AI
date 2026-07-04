import pytest

from tenants.context import get_current_tenant, set_current_tenant, tenant_context
from tests_support.models import ScopedThing

pytestmark = pytest.mark.django_db


# --- the default manager auto-filters by the ambient tenant ------------------

def test_default_manager_returns_only_current_tenant_rows(org_a, org_b):
    with tenant_context(org_a):
        ScopedThing.objects.create(name="a1")
        ScopedThing.objects.create(name="a2")
    with tenant_context(org_b):
        ScopedThing.objects.create(name="b1")

    with tenant_context(org_a):
        assert set(ScopedThing.objects.values_list("name", flat=True)) == {"a1", "a2"}
    with tenant_context(org_b):
        assert set(ScopedThing.objects.values_list("name", flat=True)) == {"b1"}


def test_cross_tenant_get_by_id_is_not_found(org_a, org_b):
    with tenant_context(org_a):
        thing = ScopedThing.objects.create(name="secret")

    with tenant_context(org_b):
        with pytest.raises(ScopedThing.DoesNotExist):
            ScopedThing.objects.get(id=thing.id)


def test_cross_tenant_update_touches_no_rows(org_a, org_b):
    with tenant_context(org_a):
        ScopedThing.objects.create(name="orig")

    # Tenant B tries a bulk update; the scoped queryset matches nothing.
    with tenant_context(org_b):
        updated = ScopedThing.objects.filter(name="orig").update(name="hacked")
    assert updated == 0

    with tenant_context(org_a):
        assert ScopedThing.objects.get(name="orig")  # unchanged


def test_cross_tenant_delete_touches_no_rows(org_a, org_b):
    with tenant_context(org_a):
        ScopedThing.objects.create(name="keep")

    with tenant_context(org_b):
        deleted, _ = ScopedThing.objects.all().delete()
    assert deleted == 0

    with tenant_context(org_a):
        assert ScopedThing.objects.count() == 1


# --- fail-closed when no tenant is bound -------------------------------------

def test_no_tenant_bound_returns_nothing(org_a):
    with tenant_context(org_a):
        ScopedThing.objects.create(name="a1")

    # Outside any tenant context, the strict default manager yields no rows.
    assert ScopedThing.objects.count() == 0
    assert list(ScopedThing.objects.all()) == []


# --- writes are stamped and guarded ------------------------------------------

def test_save_auto_stamps_tenant_from_context(org_a):
    with tenant_context(org_a):
        thing = ScopedThing.objects.create(name="x")
    assert thing.tenant_id == org_a.id


def test_save_without_tenant_raises(org_a):
    # No context bound and no explicit tenant => refuse to save.
    with pytest.raises(ValueError):
        ScopedThing(name="orphan").save()


# --- explicit escape hatches --------------------------------------------------

def test_for_tenant_scopes_regardless_of_context(org_a, org_b):
    with tenant_context(org_a):
        ScopedThing.objects.create(name="a1")
    with tenant_context(org_b):
        ScopedThing.objects.create(name="b1")

    # From B's context, explicitly ask for A's rows.
    with tenant_context(org_b):
        names = set(ScopedThing.objects.for_tenant(org_a).values_list("name", flat=True))
    assert names == {"a1"}


def test_unscoped_sees_all_tenants(org_a, org_b):
    with tenant_context(org_a):
        ScopedThing.objects.create(name="a1")
    with tenant_context(org_b):
        ScopedThing.objects.create(name="b1")

    assert ScopedThing.objects.unscoped().count() == 2


# --- context propagation is clean --------------------------------------------

def test_tenant_context_resets_on_exit(org_a):
    assert get_current_tenant() is None
    with tenant_context(org_a):
        assert get_current_tenant() == org_a
    assert get_current_tenant() is None


def test_nested_context_restores_outer(org_a, org_b):
    token = set_current_tenant(org_a)
    try:
        with tenant_context(org_b):
            assert get_current_tenant() == org_b
        assert get_current_tenant() == org_a
    finally:
        from tenants.context import clear_current_tenant
        clear_current_tenant(token)
