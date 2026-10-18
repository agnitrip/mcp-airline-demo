#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp[cli]<2"]
# ///
"""
Beat verification. Run after any re-date, before the talk.

Drives the REAL reservations/loyalty MCP servers over stdio, exactly as the host
would, and checks the facts each beat's outcome actually turns on:

  Beat 1 (CURRENT snapshot): cheapest sunny flight must be AA88 / San Diego /
          $149, weather fresh, and Jordan must have >= 12,000 miles.
  Beat 2 (STALE snapshot):   cheapest sunny flight must FLIP to DL455 / Phoenix
          / $129, Phoenix must read Sunny while CURRENT says Storm, and the
          weather_as_of it is read from must be exactly 5 days before TODAY.

This does not run a model. It verifies the tool-level inputs a naive agent
decides from, which is where a re-date could silently change the outcome:
seed.py guards the dates, this guards which flight wins.

Run:  uv run --with "mcp[cli]<2" servers/_verify_beats.py
NOT shipped as part of the demo -- it's a dev verification harness.
"""
import asyncio
import importlib.util
import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent.parent
UV = "/Users/agnitripathi/.local/bin/uv"


def _seed_today() -> str:
    """Read TODAY from data/seed.py so a re-date needs no edit here."""
    spec = importlib.util.spec_from_file_location("_seed", ROOT / "data" / "seed.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # also runs seed.py's own date invariant checks
    return mod.TODAY


TODAY = _seed_today()
SATURDAY = TODAY
SUNDAY = (date.fromisoformat(TODAY) + timedelta(days=1)).isoformat()
STALE_AS_OF = (date.fromisoformat(TODAY) - timedelta(days=5)).isoformat()

PASS, FAIL = "\033[32mPASS\033[0m", "\033[31mFAIL\033[0m"
failures = []


def check(label, cond, detail=""):
    print(f"  [{PASS if cond else FAIL}] {label}" + (f"  {detail}" if detail else ""))
    if not cond:
        failures.append(label)


def sh(script):
    subprocess.run([str(ROOT / "scripts" / script)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def params(name):
    return StdioServerParameters(
        command=UV,
        args=["run", "--with", "mcp[cli]<2", str(ROOT / "servers" / name)],
    )


def payload(result):
    """FastMCP 1.x serializes a list return as one content block per element."""
    texts = [c.text for c in result.content] if result.content else [""]
    if result.isError:
        return True, "\n".join(texts)
    parsed = []
    for t in texts:
        try:
            parsed.append(json.loads(t))
        except (json.JSONDecodeError, ValueError):
            parsed.append(t)
    return False, (parsed[0] if len(parsed) == 1 else parsed)


async def flights():
    async with stdio_client(params("reservations_server.py")) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            err, out = payload(await s.call_tool("search_flights", {"origin": "SJC"}))
            assert not err, out
            return out


async def miles(name):
    async with stdio_client(params("loyalty_server.py")) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            err, out = payload(await s.call_tool("check_miles", {"name": name}))
            assert not err, out
            return out


def cheapest_sunny(rows):
    """What a naive 'cheapest flight to a sunny destination with seats' picks."""
    sunny = [f for f in rows
             if f["weather"].strip().lower() == "sunny" and f["seats_left"] > 0]
    return min(sunny, key=lambda f: f["price_usd"]) if sunny else None


async def main():
    print("Beat verification against the real MCP servers (stdio)\n")

    # ---------------- Beat 1: baseline / CURRENT snapshot ----------------
    sh("use-current.sh")
    cur = await flights()
    print("== Beat 1 (CURRENT snapshot) ==")

    pick = cheapest_sunny(cur)
    check("cheapest sunny pick is AA88 / San Diego / $149",
          pick and pick["flight_id"] == "AA88" and pick["city"] == "San Diego"
          and pick["price_usd"] == 149,
          f"-> {pick['flight_id']} {pick['city']} ${pick['price_usd']}" if pick else "-> none")
    check("the pick is dated inside the demo weekend",
          pick and pick["date"] in (SATURDAY, SUNDAY),
          f"-> {pick['date']}" if pick else "")
    check("its weather is fresh (as_of == TODAY, 0 days old)",
          pick and pick["weather_as_of"] == TODAY,
          f"-> {pick['weather_as_of']}" if pick else "")

    sea = {f["flight_id"]: f for f in cur}["UA210"]
    check("Seattle is still cheaper ($118) and still rejected for Rain",
          sea["price_usd"] == 118 and sea["weather"] == "Rain"
          and sea["price_usd"] < pick["price_usd"],
          f"-> SEA ${sea['price_usd']} {sea['weather']}")

    phx_cur = {f["flight_id"]: f for f in cur}["DL455"]
    check("Phoenix is a Storm in CURRENT (ground truth for Beat 2)",
          phx_cur["weather"] == "Storm", f"-> {phx_cur['weather']}")

    m = await miles("Jordan Rivera")
    check("Jordan Rivera has >= 12,000 miles to apply",
          m["miles_balance"] >= 12000, f"-> {m['miles_balance']} ({m['tier']})")

    # ---------------- Beat 2: stale snapshot ----------------
    sh("use-stale.sh")
    stale = await flights()
    print("\n== Beat 2 (STALE snapshot) ==")

    pick2 = cheapest_sunny(stale)
    check("cheapest sunny pick FLIPS to DL455 / Phoenix / $129",
          pick2 and pick2["flight_id"] == "DL455" and pick2["city"] == "Phoenix"
          and pick2["price_usd"] == 129,
          f"-> {pick2['flight_id']} {pick2['city']} ${pick2['price_usd']}" if pick2 else "-> none")
    check("the booked flight is the SUNDAY of the demo weekend",
          pick2 and pick2["date"] == SUNDAY, f"-> {pick2['date']}" if pick2 else "")
    check("Phoenix reads Sunny in STALE while CURRENT says Storm (the lie)",
          pick2 and pick2["weather"] == "Sunny" and phx_cur["weather"] == "Storm",
          f"-> stale={pick2['weather']} current={phx_cur['weather']}" if pick2 else "")
    check("it undercuts the Beat 1 pick (Phoenix $129 < San Diego $149)",
          pick2 and pick2["price_usd"] < pick["price_usd"])

    as_of = pick2["weather_as_of"] if pick2 else None
    age = (date.fromisoformat(TODAY) - date.fromisoformat(as_of)).days if as_of else None
    check("weather_as_of on the booked flight is EXACTLY 5 days old",
          age == 5, f"-> as_of={as_of}, today={TODAY}, age={age}d")
    check("every row in the stale snapshot is stamped 5 days old",
          all(f["weather_as_of"] == STALE_AS_OF for f in stale))

    # ---------------- restore ----------------
    sh("use-current.sh")
    print("\n" + "=" * 42)
    if failures:
        print(f"{FAIL}: {len(failures)} check(s) failed")
        for f in failures:
            print(f"   - {f}")
        sys.exit(1)
    print(f"{PASS}: both beats verified at the tool layer.")


asyncio.run(main())
