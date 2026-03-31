#!/bin/sh
set -eu

APP_DIR="/app"
LOCKFILE="$APP_DIR/package-lock.json"
STAMP_FILE="$APP_DIR/node_modules/.package-lock.sha256"

mkdir -p "$APP_DIR/node_modules"

current_checksum="$(sha256sum "$LOCKFILE" | awk '{print $1}')"
installed_checksum=""

if [ -f "$STAMP_FILE" ]; then
  installed_checksum="$(cat "$STAMP_FILE")"
fi

if [ "$current_checksum" != "$installed_checksum" ]; then
  echo "Frontend dependencies are out of date. Running npm install..."
  cd "$APP_DIR"
  npm install
  printf '%s\n' "$current_checksum" > "$STAMP_FILE"
fi

exec "$@"
