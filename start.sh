#!/usr/bin/env bash
# Production start script (used by Render).
# Applies migrations, bootstraps the app, then launches Gunicorn.
set -e

flask db upgrade
flask init-app

# Render provides $PORT. Gunicorn must bind to 0.0.0.0 on that port.
exec gunicorn run:app --bind "0.0.0.0:${PORT:-8000}" --workers 2 --timeout 120
