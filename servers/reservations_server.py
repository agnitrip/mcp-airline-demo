#!/usr/bin/env python3
"""
reservations MCP server (thin, purpose-built) for the MCP airline demo.

Wraps the synthetic SQLite backend at data/reservations.db and exposes two
NAMED DOMAIN TOOLS instead of generic SQL:

  search_flights(origin, date)  -> list of flights, each carrying its
                                   destination's weather + weather_as_of
  book_flight(flight_id, ...)   -> a SCOPED WRITE: inserts exactly one
                                   confirmed booking row and nothing else

Built on the official `mcp` Python SDK (FastMCP), pinned to mcp[cli]<2 by the
host config (see FIX-sqlite-server-pin.md) to avoid the 1.x-vs-2.x breakage.

Core demo trick: every tool opens the SQLite connection FRESH on each call and
closes it. Nothing is cached. The toggle scripts swap data/reservations.db
between calls (current <-> stale snapshot) with no app restart, and the next
tool call sees the new file.

All data is synthetic. Run:  uv run --with "mcp[cli]<2" servers/reservations_server.py
"""
# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp[cli]<2"]
# ///
import re
import sqlite3
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Resolve the DB relative to this file so the server reads whichever repo (or
# worktree) it was launched from. servers/ sits at the repo root.
DB = Path(__file__).resolve().parent.parent / "data" / "reservations.db"

mcp = FastMCP("reservations")


def _connect() -> sqlite3.Connection:
    """Open the reservations DB fresh, read the current file off disk every
    time. Fails loudly if the file is missing or not a database."""
    if not DB.exists():
        raise FileNotFoundError(f"reservations database not found at {DB}")
    con = sqlite3.connect(f"file:{DB}?mode=rw", uri=True)
    con.row_factory = sqlite3.Row
    return con


@mcp.tool()
def search_flights(origin: str = "SJC", date: str | None = None) -> list[dict]:
    """Search this weekend's flights leaving `origin` (default SJC), each row
    carrying the DESTINATION's current weather from the reservations backend.

    Returns a list of dicts:
      {flight_id, airline, origin, destination, city, date, price_usd,
       seats_left, weather, weather_as_of}

    `city`, `weather`, and `weather_as_of` come from a LEFT JOIN of airports on
    destination = code, so every flight reports its destination's weather and
    how fresh that reading is (weather_as_of). Pass `date` (YYYY-MM-DD) to
    filter to a single day; omit it to see the whole weekend.
    """
    con = _connect()
    try:
        q = (
            "SELECT f.flight_id, f.airline, f.origin, f.destination, "
            "       a.city AS city, f.date, f.price_usd, f.seats_left, "
            "       a.weather AS weather, a.weather_as_of AS weather_as_of "
            "FROM flights f "
            "LEFT JOIN airports a ON f.destination = a.code "
            "WHERE f.origin = ?"
        )
        params: list = [origin]
        if date:
            q += " AND f.date = ?"
            params.append(date)
        q += " ORDER BY f.price_usd ASC"
        rows = [dict(r) for r in con.execute(q, params).fetchall()]
    finally:
        con.close()
    return rows


@mcp.tool()
def book_flight(
    flight_id: str,
    passenger: str,
    miles_to_apply: int = 12000,
    seat: str | None = None,
) -> dict:
    """Book one flight. SCOPED WRITE: this inserts exactly ONE row into the
    `bookings` table (a fresh BKG-60xx id, the given flight_id and passenger,
    miles_to_apply, status 'confirmed') and does nothing else. It does not
    expose arbitrary SQL and cannot read or modify anything but this one insert.

    `seat` is accepted for interface completeness but not persisted (the demo
    bookings schema has no seat column).

    Returns: {booking_id, flight_id, passenger, miles_applied, status}.
    """
    con = _connect()
    try:
        # Refuse to book a flight that does not exist (scoped validation on the
        # same backend -- still not arbitrary SQL).
        if con.execute(
            "SELECT 1 FROM flights WHERE flight_id = ?", (flight_id,)
        ).fetchone() is None:
            raise ValueError(f"no such flight: {flight_id}")

        # Mint a fresh BKG-60xx id: max existing 60xx booking + 1, else 6001.
        next_num = 6001
        for (bid,) in con.execute(
            "SELECT booking_id FROM bookings WHERE booking_id LIKE 'BKG-6%'"
        ).fetchall():
            m = re.fullmatch(r"BKG-(\d+)", bid)
            if m:
                next_num = max(next_num, int(m.group(1)) + 1)
        booking_id = f"BKG-{next_num}"

        con.execute(
            "INSERT INTO bookings "
            "(booking_id, flight_id, passenger, miles_applied, status) "
            "VALUES (?, ?, ?, ?, 'confirmed')",
            (booking_id, flight_id, passenger, miles_to_apply),
        )
        con.commit()
    finally:
        con.close()
    return {
        "booking_id": booking_id,
        "flight_id": flight_id,
        "passenger": passenger,
        "miles_applied": miles_to_apply,
        "status": "confirmed",
    }


if __name__ == "__main__":
    mcp.run()
