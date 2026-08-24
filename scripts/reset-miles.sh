#!/usr/bin/env bash
# Restore the healthy loyalty DB after Beat C.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB="$ROOT/data/loyalty.db"
if [ -f "$ROOT/data/loyalty.db.real" ]; then
  mv -f "$ROOT/data/loyalty.db.real" "$DB"
  echo "[loyalty] restored. loyalty server healthy again."
else
  echo "[loyalty] nothing to restore (already healthy)."
fi
