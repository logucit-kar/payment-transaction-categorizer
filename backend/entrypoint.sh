#!/bin/bash
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput || true
exec gunicorn config.wsgi:application --bind 0.0.0.0:8300 --workers 2
