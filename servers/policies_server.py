#!/usr/bin/env python3
"""
policies MCP server (thin, purpose-built) for the MCP airline demo.

Wraps the synthetic markdown backend in policy/active/ and exposes ONE named
domain tool instead of generic filesystem reads:

  search_policies(query) -> {passage, source_file, version, last_updated}

Built on the official `mcp` Python SDK (FastMCP), pinned to mcp[cli]<2 by the
host config for consistency with the other two servers.

Core demo trick + the RAG variant of Beat B: the tool globs policy/active/ and
reads the .md files FRESH on every call. The toggle scripts
(use-current-policy.sh / use-stale-policy.sh) swap the files under
policy/active/ between calls, and the next search sees the new version and the
new Version / Last updated header -- no app restart.

It returns the best-matching passage quoted VERBATIM, plus the owning file's
Version and Last updated header so the caller can cite source + freshness.

All data is synthetic. Run:  uv run --with "mcp[cli]<2" servers/policies_server.py
"""
# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp[cli]<2"]
# ///
import re
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Resolve the policy dir relative to this file so the server reads whichever
# repo (or worktree) it was launched from. servers/ sits at the repo root.
POLICY_DIR = Path(__file__).resolve().parent.parent / "policy" / "active"

mcp = FastMCP("policies")


def _header_field(text: str, label: str) -> str | None:
    """Pull a value out of a '**Label:** value' markdown header line."""
    m = re.search(rf"\*\*{re.escape(label)}:\*\*\s*([^\s*]+)", text)
    return m.group(1) if m else None


@mcp.tool()
def search_policies(query: str) -> dict:
    """Keyword-search the active fare-rule / policy markdown files and return the
    best-matching passage, quoted verbatim, with its source file's version and
    freshness.

    Returns: {passage, source_file, version, last_updated}. If nothing matches,
    `passage` explains that and `source_file` is null.

    Reads policy/active/*.md fresh on every call, so swapping the active policy
    (current <-> superseded) is reflected on the next search.
    """
    terms = [t for t in re.findall(r"[a-z0-9]+", query.lower()) if t]

    best = None  # (score, source_file, version, last_updated, passage)
    for md in sorted(POLICY_DIR.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        version = _header_field(text, "Version")
        last_updated = _header_field(text, "Last updated")
        # Split into paragraph blocks (verbatim) and score each by keyword hits.
        for block in re.split(r"\n\s*\n", text):
            passage = block.strip()
            if not passage:
                continue
            low = passage.lower()
            score = sum(low.count(term) for term in terms) if terms else 0
            if best is None or score > best[0]:
                best = (score, md.name, version, last_updated, passage)

    if best is None:
        return {
            "passage": "(no policy files available)",
            "source_file": None,
            "version": None,
            "last_updated": None,
        }
    if best[0] == 0:
        return {
            "passage": f"(no passage matched {query!r})",
            "source_file": None,
            "version": None,
            "last_updated": None,
        }
    return {
        "passage": best[4],
        "source_file": best[1],
        "version": best[2],
        "last_updated": best[3],
    }


if __name__ == "__main__":
    mcp.run()
