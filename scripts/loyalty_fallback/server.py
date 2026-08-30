#!/usr/bin/env python3
"""
OPTIONAL deterministic fallback for the loyalty server (Beat C).

Use this ONLY if, during rehearsal, the file-swap trick in break-miles.sh
doesn't reliably surface as an error to the model. It is a drop-in replacement
for servers/loyalty_server.py: same server name (`loyalty`), same single domain
tool (`check_miles`), same {name, miles_balance, tier} return shape. The only
difference is HOW it breaks. Instead of swapping the DB for junk, it fails on
command via a flag file, so Beat C is fully deterministic and needs no restart.

Beat C toggle with this server:
  touch  scripts/loyalty_fallback/OUTAGE   # -> next check_miles errors
  rm     scripts/loyalty_fallback/OUTAGE   # -> healthy again

Like the primary loyalty server it FAILS CLOSED: on outage (or a missing DB or
unknown member) it RAISES so the host records a failed tool call. It never
returns a fake balance.

Run standalone (for the MCP host config):
  uv run --with "mcp[cli]<2" scripts/loyalty_fallback/server.py

Claude Desktop config entry (replaces the loyalty block):
  "loyalty": {
    "command": "/Users/agnitripathi/.local/bin/uv",
    "args": ["run", "--with", "mcp[cli]<2",
             "/Users/agnitripathi/mcp-airline-demo/scripts/loyalty_fallback/server.py"]
  }
"""
# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp[cli]<2"]
# ///
import sqlite3
from pathlib import Path

from mcp.server.fastmcp import FastMCP

HERE = Path(__file__).resolve().parent
DB = HERE.parent.parent / "data" / "loyalty.db"
FLAG = HERE / "OUTAGE"

mcp = FastMCP("loyalty")


@mcp.tool()
def check_miles(name: str) -> dict:
    """Look up a frequent-flyer member's miles balance and tier. READ ONLY.

    Returns: {name, miles_balance, tier}.

    Deterministic Beat C: while the OUTAGE flag file exists, this RAISES a
    timeout error instead of returning a value, so the host sees a failed tool
    call. It also raises if the DB is missing or the member is not found. It
    never mistakes "could not check" for "the miles are fine."
    """
    if FLAG.exists():
        raise RuntimeError(
            "loyalty request timed out: no response from loyalty backend"
        )
    if not DB.exists():
        raise FileNotFoundError(f"loyalty database not found at {DB}")

    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        row = con.execute(
            "SELECT name, miles_balance, tier FROM members WHERE name = ?",
            (name,),
        ).fetchone()
    finally:
        con.close()

    if row is None:
        raise ValueError(f"no loyalty member named {name!r}")
    return {
        "name": row["name"],
        "miles_balance": row["miles_balance"],
        "tier": row["tier"],
    }


if __name__ == "__main__":
    mcp.run()
