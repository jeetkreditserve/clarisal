#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

echo "==> Tearing down existing containers and volumes..."
docker compose down -v

echo "==> Starting db, redis, mailpit..."
docker compose up -d db redis mailpit

echo "==> Waiting for database to be ready..."
until docker compose exec -T db pg_isready -U calrisal; do
  echo "  db not ready yet, retrying in 2s..."
  sleep 2
done

echo "==> Starting backend..."
docker compose up -d backend

echo "==> Waiting for Django to be ready (8s)..."
sleep 8

echo "==> Seeding control tower data..."
docker compose exec -T backend python manage.py seed_control_tower

echo "==> Starting frontend..."
docker compose up -d frontend

echo ""
echo "Done. Services are up. Run: cd frontend && npm run test:e2e"
