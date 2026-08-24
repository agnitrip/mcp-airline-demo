#!/usr/bin/env bash
# Point the reservations server at the CURRENT snapshot (fresh weather; Phoenix
# is a Storm today, San Diego is Sunny today). Used for Beats A and D.
# The reference SQLite server reconnects per query -- NO app restart.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cp -f "$ROOT/data/reservations-current.db" "$ROOT/data/reservations.db"
echo "[reservations] active = CURRENT (fresh weather). Next assistant message reads today's data."
