#!/usr/bin/env bash
# Beat C: make the loyalty (miles) server FAIL on its next query. We swap the
# real DB aside and drop a non-database file in its place. The reference SQLite
# MCP server reconnects per query, so the next miles lookup errors ("file is not
# a database") -- NO app restart needed.
#
# The naive assistant treats that error as "no blocker" and books anyway (fail
# open). The guardrailed assistant (Beat D) refuses (fail closed).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB="$ROOT/data/loyalty.db"
if [ -f "$ROOT/data/loyalty.db.real" ]; then
  echo "[loyalty] already broken (loyalty.db.real exists). No change."
else
  mv -f "$DB" "$ROOT/data/loyalty.db.real"
  printf 'LOYALTY SYSTEM TEMPORARILY UNAVAILABLE\n' > "$DB"
  echo "[loyalty] BROKEN. loyalty server will error on next query."
fi
