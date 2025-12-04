#!/bin/sh
set -e
mkdir -p /app/storage
python - <<'PY'
from app import app, init_db
with app.app_context():
    init_db()
PY
exec gunicorn -b 0.0.0.0:${PORT:-2222} app:app
