import contextvars
from contextlib import contextmanager

_current_tenant = contextvars.ContextVar("current_tenant", default=None)


def set_current_tenant(tenant):
    return _current_tenant.set(tenant)


def get_current_tenant():
    return _current_tenant.get()


def clear_current_tenant(token=None):
    if token is not None:
        _current_tenant.reset(token)
    else:
        _current_tenant.set(None)


@contextmanager
def tenant_context(tenant):
    token = set_current_tenant(tenant)
    try:
        yield tenant
    finally:
        clear_current_tenant(token)
