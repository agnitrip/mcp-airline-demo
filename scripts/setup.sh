#!/usr/bin/env bash
# One-time setup: seed the synthetic DBs, set the active reservations snapshot to
# CURRENT, and set policies to CURRENT. Safe to re-run any time to return to a
# clean baseline (Beat A start state).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[setup] seeding synthetic SQLite databases..."
python3 "$ROOT/data/seed.py"

echo "[setup] restoring healthy loyalty.db (in case a previous run left it broken)..."
[ -f "$ROOT/data/loyalty.db.real" ] && mv -f "$ROOT/data/loyalty.db.real" "$ROOT/data/loyalty.db" || true

echo "[setup] setting active reservations snapshot to CURRENT..."
cp -f "$ROOT/data/reservations-current.db" "$ROOT/data/reservations.db"

echo "[setup] setting active policies to CURRENT..."
cp -f "$ROOT/policy/current/refund-policy.md"  "$ROOT/policy/active/refund-policy.md"
cp -f "$ROOT/policy/current/baggage-policy.md" "$ROOT/policy/active/baggage-policy.md"

echo "[setup] done. State:"
"$ROOT/scripts/status.sh"
