#!/usr/bin/env bash
# Glance at the current demo state: which reservations snapshot is active,
# whether loyalty is broken, and which policy is active. Keep this in a side
# terminal during the talk (optionally: watch -n1 ./scripts/status.sh).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Reservations: read Phoenix weather + its as_of from the ACTIVE db.
# Current snapshot -> PHX Storm, as_of today. Stale snapshot -> PHX Sunny, 5 days old.
RES="$(python3 - "$ROOT/data/reservations.db" <<'PY'
import sqlite3, sys
try:
    con = sqlite3.connect(sys.argv[1])
    w, asof = con.execute("SELECT weather, weather_as_of FROM airports WHERE code='PHX'").fetchone()
    con.close()
    if w == "Storm":
        print(f"CURRENT  (Phoenix={w}, weather_as_of={asof})")
    else:
        print(f"STALE    (Phoenix={w} <- but really a storm; weather_as_of={asof})")
except Exception as e:
    print(f"UNREADABLE ({e})")
PY
)"

if [ -f "$ROOT/data/loyalty.db.real" ]; then LOY="BROKEN (will error on next query)"; else LOY="healthy"; fi

POL="unknown"
grep -q "Status:\*\* CURRENT" "$ROOT/policy/active/refund-policy.md" 2>/dev/null && POL="CURRENT (v2026.3)"
grep -q "SUPERSEDED"        "$ROOT/policy/active/refund-policy.md" 2>/dev/null && POL="STALE (v2025.4)"

echo "-------------------------------------------------------------"
echo " reservations : $RES"
echo " loyalty      : $LOY"
echo " policies     : $POL"
echo "-------------------------------------------------------------"
