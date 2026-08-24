#!/usr/bin/env bash
# Restore the CURRENT fare rules (v2026.3) after the optional RAG variant.
# The filesystem server reads fresh -- NO app restart.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cp -f "$ROOT/policy/current/refund-policy.md"  "$ROOT/policy/active/refund-policy.md"
cp -f "$ROOT/policy/current/baggage-policy.md" "$ROOT/policy/active/baggage-policy.md"
echo "[policies] active = CURRENT (v2026.3). Next refund answer quotes the new rule."
