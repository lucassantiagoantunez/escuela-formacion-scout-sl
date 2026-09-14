#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
if [ "${RENDER:-}" = "true" ]; then
  python scripts/install_office.py
fi
python manage.py collectstatic --no-input
python manage.py migrate
