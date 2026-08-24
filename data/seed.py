#!/usr/bin/env python3
"""
Seed the synthetic SQLite databases for the MCP airline demo.

Builds three DB files (stdlib sqlite3 only, no extra deps):

  reservations-current.db  -> flights, airports (fresh weather), bookings
  reservations-stale.db    -> SAME flights, but a 5-day-old weather snapshot
                              where Phoenix still reads "Sunny" (it is now a
                              storm in the current data) -> Beat B failure
  loyalty.db               -> members (the traveler + a few others)

setup.sh then copies reservations-current.db -> reservations.db (the file the
`reservations` MCP server actually serves). use-stale.sh / use-current.sh swap
that active file with NO app restart (the reference SQLite server reconnects per
query).

All data is FAKE. No real people, no employer data. Safe to show live, record,
and post publicly.

Run:  python3 data/seed.py
Idempotent: drops and recreates every table on each run.
"""

import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent

TODAY = "2026-08-22"          # demo "today" (this weekend = 22-23 Aug 2026)
FIVE_DAYS_AGO = "2026-08-17"  # the stale snapshot's weather_as_of

# --- Flights out of San Jose (SJC) this weekend -----------------------------
# Same rows in BOTH snapshots. What differs between snapshots is the WEATHER
# (airports table), not the flights.
#   flight_id, airline,     origin, destination, date,        price_usd, seats_left
FLIGHTS = [
    ("AA88",  "American",  "SJC", "SAN", "2026-08-22", 149, 9),   # San Diego  <- correct pick (cheapest genuinely sunny)
    ("UA210", "United",    "SJC", "SEA", "2026-08-22", 118, 4),   # Seattle    (cheapest overall, but RAIN)
    ("DL455", "Delta",     "SJC", "PHX", "2026-08-23", 129, 6),   # Phoenix    (cheap; STORM now, but "Sunny" in stale snapshot -> Beat B trap)
    ("WN360", "Southwest", "SJC", "LAS", "2026-08-22", 176, 12),  # Las Vegas  (sunny but pricier)
    ("AS512", "Alaska",    "SJC", "PSP", "2026-08-23", 169, 3),   # Palm Springs (sunny but pricier)
]

# --- Airports + weather. This is the ONLY thing that changes between the -----
#     current and stale snapshots. -----------------------------------------
#   code, city,           weather,  weather_as_of
AIRPORTS_CURRENT = [
    ("SJC", "San Jose",     "Cloudy", TODAY),
    ("SAN", "San Diego",    "Sunny",  TODAY),   # cheapest sunny w/ fresh weather -> Beat A books this
    ("SEA", "Seattle",      "Rain",   TODAY),
    ("PHX", "Phoenix",      "Storm",  TODAY),   # genuinely storming TODAY (ground truth for Beat B)
    ("LAS", "Las Vegas",    "Sunny",  TODAY),
    ("PSP", "Palm Springs", "Sunny",  TODAY),
]

# Snapshot captured 5 days ago and never refreshed. Back then Phoenix WAS sunny.
# Since then a storm rolled in (see AIRPORTS_CURRENT) but this snapshot never
# caught up. Everything here is stamped 5 days old.
AIRPORTS_STALE = [
    ("SJC", "San Jose",     "Cloudy", FIVE_DAYS_AGO),
    ("SAN", "San Diego",    "Sunny",  FIVE_DAYS_AGO),
    ("SEA", "Seattle",      "Rain",   FIVE_DAYS_AGO),
    ("PHX", "Phoenix",      "Sunny",  FIVE_DAYS_AGO),  # <- the lie: reads Sunny, is really a Storm
    ("LAS", "Las Vegas",    "Sunny",  FIVE_DAYS_AGO),
    ("PSP", "Palm Springs", "Sunny",  FIVE_DAYS_AGO),
]

# --- A couple of pre-existing bookings for realism (other passengers). -------
#     The traveler (Jordan Rivera) has none yet; the assistant creates it live.
#   booking_id, flight_id, passenger,      miles_applied, status
BOOKINGS = [
    ("BKG-5001", "WN360", "Sam Delgado",   0,     "confirmed"),
    ("BKG-5002", "AS512", "Priya Anand",   8000,  "confirmed"),
]

# --- Loyalty members. Jordan Rivera is the traveler for the demo. ------------
#   name,            miles_balance, tier
MEMBERS = [
    ("Jordan Rivera",  45000, "Gold"),      # <- the traveler; plenty of miles to matter
    ("Sam Delgado",     2200, "Member"),
    ("Priya Anand",   132000, "Platinum"),
    ("Marcus Webb",     6100, "Silver"),
]


def build_reservations(path: Path, airports) -> None:
    con = sqlite3.connect(path)
    cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS flights")
    cur.execute("DROP TABLE IF EXISTS airports")
    cur.execute("DROP TABLE IF EXISTS bookings")
    cur.execute(
        """CREATE TABLE flights (
               flight_id   TEXT PRIMARY KEY,
               airline     TEXT NOT NULL,
               origin      TEXT NOT NULL,
               destination TEXT NOT NULL,
               date        TEXT NOT NULL,
               price_usd   INTEGER NOT NULL,
               seats_left  INTEGER NOT NULL
           )"""
    )
    cur.execute(
        """CREATE TABLE airports (
               code          TEXT PRIMARY KEY,
               city          TEXT NOT NULL,
               weather       TEXT NOT NULL,
               weather_as_of TEXT NOT NULL
           )"""
    )
    cur.execute(
        """CREATE TABLE bookings (
               booking_id    TEXT PRIMARY KEY,
               flight_id     TEXT NOT NULL,
               passenger     TEXT NOT NULL,
               miles_applied INTEGER NOT NULL DEFAULT 0,
               status        TEXT NOT NULL
           )"""
    )
    cur.executemany("INSERT INTO flights VALUES (?,?,?,?,?,?,?)", FLIGHTS)
    cur.executemany("INSERT INTO airports VALUES (?,?,?,?)", airports)
    cur.executemany("INSERT INTO bookings VALUES (?,?,?,?,?)", BOOKINGS)
    con.commit()
    con.close()


def build_loyalty(path: Path) -> None:
    con = sqlite3.connect(path)
    cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS members")
    cur.execute(
        """CREATE TABLE members (
               name          TEXT PRIMARY KEY,
               miles_balance INTEGER NOT NULL,
               tier          TEXT NOT NULL
           )"""
    )
    cur.executemany("INSERT INTO members VALUES (?,?,?)", MEMBERS)
    con.commit()
    con.close()


if __name__ == "__main__":
    print("Seeding synthetic airline data (all fake):")
    build_reservations(HERE / "reservations-current.db", AIRPORTS_CURRENT)
    print(f"  reservations-current.db -> {len(FLIGHTS)} flights, San Diego SUNNY (fresh, {TODAY}), Phoenix STORM")
    build_reservations(HERE / "reservations-stale.db", AIRPORTS_STALE)
    print(f"  reservations-stale.db   -> same flights, weather frozen {FIVE_DAYS_AGO}; Phoenix still reads SUNNY (trap)")
    build_loyalty(HERE / "loyalty.db")
    print(f"  loyalty.db              -> {len(MEMBERS)} members (traveler = Jordan Rivera, Gold, 45,000 miles)")
    print("Done. Run scripts/setup.sh to set the active reservations DB + policy.")
