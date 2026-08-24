#!/usr/bin/env bash
# Beat B: point the reservations server at the STALE snapshot -- weather frozen
# 5 days ago, where Phoenix still reads "Sunny" (it is really a storm now, per
# the current snapshot). The naive assistant will book Phoenix on stale weather.
# The reference SQLite server reconnects per query -- NO app restart.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cp -f "$ROOT/data/reservations-stale.db" "$ROOT/data/reservations.db"
echo "[reservations] active = STALE (weather 5 days old). Next assistant message reads the OLD data."
