#!/usr/bin/env python3
"""
OPTIONAL fallback loyalty MCP server.

Use this ONLY if, during rehearsal, the file-swap trick in break-miles.sh
doesn't reliably surface as an error to the model. This server reads the same
loyalty.db and exposes a single lookup tool that fails on command via a flag
file -- a deterministic, restart-free way to trigger Beat C.

Beat C toggle with this server:
  touch  scripts/loyalty_fallback/OUTAGE   # -> next lookup errors
  rm     scripts/loyalty_fallback/OUTAGE   # -> healthy again

Run standalone (for the MCP host config):
  uv run --with mcp scripts/loyalty_fallback/server.py

Claude Desktop config entry (replaces the loyalty block):
  "loyalty": {
    "command": "/Users/agnitripathi/.local/bin/uv",
    "args": ["run", "--with", "mcp",
             "/Users/agnitripathi/mcp-airline-demo/scripts/loyalty_fallback/server.py"]
  }
"""
import sqlite3
from pathlib import Path

from mcp.server.fastmcp import FastMCP

HERE = Path(__file__).resolve().parent
DB = HERE.parent.parent / "data" / "loyalty.db"
FLAG = HERE / "OUTAGE"

mcp = FastMCP("loyalty")


@mcp.tool()
def lookup_member(name: str = "") -> str:
    """Look up a frequent-flyer member's miles balance and tier in the loyalty
    system. Columns: name, miles_balance, tier."""
    if FLAG.exists():
        raise RuntimeError(
            "loyalty request timed out: no response from loyalty backend"
        )
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    q = "SELECT name, miles_balance, tier FROM members WHERE 1=1"
    params = []
    if name:
        q += " AND name = ?"
        params.append(name)
    rows = [dict(r) for r in con.execute(q, params).fetchall()]
    con.close()
    if not rows:
        return "No matching member found."
    return "\n".join(str(r) for r in rows)


if __name__ == "__main__":
    mcp.run()
