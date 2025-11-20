#!/bin/bash
set -e

# wait for Postgres
python manage.py migrate --noinput
python manage.py collectstatic --noinput || true
# run development server (change for production)
gunicorn api.wsgi:application --bind 0.0.0.0:8300 --workers 1 --log-level debug
