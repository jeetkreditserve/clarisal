#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

docker compose exec -T backend env DJANGO_SETTINGS_MODULE=clarisal.settings.test pytest "$@"
