from rest_framework.pagination import PageNumberPagination

Global_error_message = "Something went wrong!"


class StandardResultsSetPagination(PageNumberPagination):

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


def verify_id(model, id):
    try:
        instance = model.objects.get(id=int(id))
        return instance, None
    except (model.DoesNotExist, ValueError, TypeError):
        return None, f"{model.__name__} id {id} not found."


def check_required_fields(required_fields, request_data):
    missing = [
        f for f in required_fields
        if f not in request_data or request_data[f] in (None, "")
    ]
    if missing:
        return f"{', '.join(missing)} is required."
    return None
