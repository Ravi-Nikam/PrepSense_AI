# Production image: installs deps, collects static, runs under gunicorn as non-root.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# libpq for psycopg; build-essential for any wheels that need compiling.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Collect static (admin + DRF) into STATIC_ROOT for WhiteNoise. DEBUG must be off
# so the hashed/compressed manifest storage is used; a throwaway key is fine here.
RUN DJANGO_SECRET_KEY=build-only DJANGO_DEBUG=False \
    python manage.py collectstatic --noinput

RUN chmod +x entrypoint.sh \
    && adduser --disabled-password --gecos "" appuser \
    && chown -R appuser /app
USER appuser

EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "prepcheck.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60"]
