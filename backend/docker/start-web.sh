#!/bin/sh
set -eu

echo "==> Waiting for database connectivity..."
python - <<'PY'
import os
import time
from urllib.parse import urlparse

import psycopg2


database_url = os.environ.get(
    "DATABASE_URL",
    "postgresql://clarisal:clarisal_dev_password@db:5432/clarisal",
)
parsed = urlparse(database_url)
database_name = (parsed.path or "/clarisal").lstrip("/")

for attempt in range(60):
    try:
        connection = psycopg2.connect(
            dbname=database_name,
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname,
            port=parsed.port or 5432,
        )
        connection.close()
        print("Database is ready.")
        break
    except Exception as exc:  # pragma: no cover - startup path only
        print(f"Database not ready yet ({attempt + 1}/60): {exc}")
        time.sleep(2)
else:
    raise SystemExit("Database did not become ready in time.")
PY

echo "==> Applying database migrations..."
python manage.py migrate --noinput

echo "==> Seeding statutory masters (idempotent)..."
python manage.py seed_statutory_masters

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

echo "==> Starting web process: $*"
exec "$@"
