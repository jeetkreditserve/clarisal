#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

echo "==> Tearing down existing containers and volumes..."
docker compose down -v

echo "==> Building and starting the full stack..."
docker compose up -d --build

echo "==> Waiting for backend health..."
until docker compose exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/')" >/dev/null 2>&1; do
  echo "  backend not ready yet, retrying in 2s..."
  sleep 2
done

echo "==> Waiting for edge proxy health..."
until docker compose exec -T edge-proxy wget -q -O /dev/null http://127.0.0.1/__proxy_health; do
  echo "  edge proxy not ready yet, retrying in 2s..."
  sleep 2
done

echo "==> Seeding control tower data..."
docker compose exec -T backend python manage.py seed_control_tower

echo ""
echo "Done. Services are up at http://localhost:${EDGE_PROXY_PORT:-8080}"
