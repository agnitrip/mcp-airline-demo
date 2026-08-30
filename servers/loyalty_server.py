#!/usr/bin/env python3
"""
loyalty MCP server (thin, purpose-built) for the MCP airline demo.

Wraps the synthetic SQLite backend at data/loyalty.db and exposes ONE named,
READ-ONLY domain tool instead of generic SQL:

  check_miles(name) -> {name, miles_balance, tier}

Built on the official `mcp` Python SDK (FastMCP), pinned to mcp[cli]<2 by the
host config (see FIX-sqlite-server-pin.md).

Core demo trick + Beat C: the tool opens the DB FRESH on every call. Beat C
(scripts/break-miles.sh) swaps data/loyalty.db for a non-database junk file
between calls. When that happens this tool MUST fail loudly -- it raises so the
host records a failed tool call. It never swallows the error and never returns a
plausible fake balance. Absence of verification is not permission to proceed.

All data is synthetic. Run:  uv run --with "mcp[cli]<2" servers/loyalty_server.py
"""
# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp[cli]<2"]
# ///
import sqlite3
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Resolve the DB relative to this file so the server reads whichever repo (or
# worktree) it was launched from. servers/ sits at the repo root.
DB = Path(__file__).resolve().parent.parent / "data" / "loyalty.db"

mcp = FastMCP("loyalty")


@mcp.tool()
def check_miles(name: str) -> dict:
    """Look up a frequent-flyer member's miles balance and tier. READ ONLY.

    Returns: {name, miles_balance, tier}.

    Fails closed on purpose: if the loyalty database is missing, corrupt, or
    unreadable, or the member is not found, this RAISES instead of returning a
    value. The host sees a failed tool call -- it must never mistake "could not
    check" for "the miles are fine."
    """
    if not DB.exists():
        raise FileNotFoundError(f"loyalty database not found at {DB}")

    # mode=ro: never create or write the file. If data/loyalty.db has been
    # swapped for junk (Beat C), connect may open but the query below raises
    # sqlite3.DatabaseError ("file is not a database") -- which we let propagate.
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
