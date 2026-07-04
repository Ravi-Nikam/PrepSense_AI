import json

from django.db import models

try:  # Production: pgvector + psycopg present.
    from pgvector.django import VectorField as _PGVectorField

    _HAS_PGVECTOR = True
except Exception:  # sqlite test env: psycopg/pgvector unavailable.
    _PGVectorField = None
    _HAS_PGVECTOR = False


if _HAS_PGVECTOR:

    class VectorField(_PGVectorField):

        def db_type(self, connection):
            if connection.vendor == "postgresql":
                return super().db_type(connection)
            return "text"

else:

    class VectorField(models.TextField):

        def __init__(self, *args, dimensions=None, **kwargs):
            self.dimensions = dimensions
            super().__init__(*args, **kwargs)

        def deconstruct(self):
            name, path, args, kwargs = super().deconstruct()
            if self.dimensions is not None:
                kwargs["dimensions"] = self.dimensions
            # Normalise the path so migrations are identical on both backends.
            return name, "core.fields.VectorField", args, kwargs

        def from_db_value(self, value, expression, connection):
            if value is None:
                return None
            try:
                return json.loads(value)
            except (TypeError, ValueError):
                return value

        def to_python(self, value):
            if value is None or isinstance(value, list):
                return value
            try:
                return json.loads(value)
            except (TypeError, ValueError):
                return value

        def get_prep_value(self, value):
            if value is None:
                return None
            if isinstance(value, str):
                return value
            return json.dumps(list(value))
