#!/usr/bin/env sh
# Apply migrations, then hand off to the container's command (gunicorn / celery).
set -e

python manage.py migrate --noinput

# Optionally seed demo data on first boot: set SEED_ON_START=1 in the environment.
if [ "${SEED_ON_START:-0}" = "1" ]; then
  python manage.py seed_demo || true
fi

exec "$@"
