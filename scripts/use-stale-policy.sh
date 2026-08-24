#!/usr/bin/env bash
# OPTIONAL (RAG variant of Beat B): serve the SUPERSEDED fare rules, which
# falsely promise "all fares fully refundable any time." Ask the assistant a
# refund question and it will quote the stale rule. The filesystem server reads
# fresh -- NO app restart.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cp -f "$ROOT/policy/stale/refund-policy.md"  "$ROOT/policy/active/refund-policy.md"
cp -f "$ROOT/policy/stale/baggage-policy.md" "$ROOT/policy/active/baggage-policy.md"
echo "[policies] active = STALE (v2025.4, superseded). Next refund answer quotes the OLD rule."
