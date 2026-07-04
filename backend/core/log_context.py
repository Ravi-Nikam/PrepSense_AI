import contextvars

_request_id = contextvars.ContextVar("log_request_id", default=None)
_user_id = contextvars.ContextVar("log_user_id", default=None)


def set_request_id(value):
    return _request_id.set(value)


def get_request_id():
    return _request_id.get()


def reset_request_id(token):
    _request_id.reset(token)


def set_user_id(value):
    return _user_id.set(value)


def get_user_id():
    return _user_id.get()


def reset_user_id(token):
    _user_id.reset(token)
