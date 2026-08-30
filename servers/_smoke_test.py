#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp[cli]<2"]
# ///
"""
Smoke test for the three purpose-built MCP servers. Launches each over real
stdio (as the host would), exercises its tools, and toggles the data files
MID-SESSION to prove the servers read fresh per call. Covers all four beats.

Run:  uv run --with "mcp[cli]<2" servers/_smoke_test.py
NOT shipped as part of the demo -- it's a dev verification harness.
"""
import asyncio
import json
import subprocess
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent.parent
SERVERS = ROOT / "servers"
UV = "/Users/agnitripathi/.local/bin/uv"

PASS, FAIL = "\033[32mPASS\033[0m", "\033[31mFAIL\033[0m"
_failures = []


def check(label, cond):
    print(f"  [{PASS if cond else FAIL}] {label}")
    if not cond:
        _failures.append(label)


def sh(script):
    subprocess.run([str(ROOT / "scripts" / script)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def params(server):
    return StdioServerParameters(
        command=UV,
        args=["run", "--with", "mcp[cli]<2", str(SERVERS / server)],
    )


def payload(result):
    """Return (isError, parsed) from a CallToolResult. FastMCP 1.x serializes a
    list return as one content block per element, so parse every block: a single
    block -> that value; multiple blocks -> a list."""
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


async def test_reservations():
    print("\n== reservations_server ==")
    async with stdio_client(params("reservations_server.py")) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            names = {t.name for t in (await s.list_tools()).tools}
            check("tools are search_flights + book_flight",
                  names == {"search_flights", "book_flight"})

            # Beat A: current snapshot
            err, flights = payload(await s.call_tool("search_flights", {"origin": "SJC"}))
            check("search_flights returns 5 flights", not err and len(flights) == 5)
            by_id = {f["flight_id"]: f for f in flights}
            aa = by_id.get("AA88", {})
            check("AA88 -> San Diego, $149, Sunny, has weather_as_of",
                  aa.get("destination") == "SAN" and aa.get("price_usd") == 149
                  and aa.get("weather") == "Sunny" and aa.get("city") == "San Diego"
                  and bool(aa.get("weather_as_of")))
            sunny = [f for f in flights if f["weather"] == "Sunny"]
            cheapest_sunny = min(sunny, key=lambda f: f["price_usd"])
            check("AA88 $149 is the cheapest SUNNY flight",
                  cheapest_sunny["flight_id"] == "AA88")
            check("Phoenix (PHX) reads Storm in CURRENT snapshot",
                  by_id["DL455"]["weather"] == "Storm")

            # Beat A: scoped write mints BKG-60xx and increments
            err1, b1 = payload(await s.call_tool(
                "book_flight", {"flight_id": "AA88", "passenger": "Jordan Rivera"}))
            check("book_flight -> BKG-6001, confirmed, 12000 miles",
                  not err1 and b1.get("booking_id") == "BKG-6001"
                  and b1.get("status") == "confirmed" and b1.get("miles_applied") == 12000)
            err2, b2 = payload(await s.call_tool(
                "book_flight", {"flight_id": "UA210", "passenger": "Jordan Rivera",
                                "miles_to_apply": 5000, "seat": "14C"}))
            check("second book_flight increments -> BKG-6002 (seat accepted)",
                  not err2 and b2.get("booking_id") == "BKG-6002"
                  and b2.get("miles_applied") == 5000)
            errx, bx = payload(await s.call_tool(
                "book_flight", {"flight_id": "NOPE", "passenger": "Jordan Rivera"}))
            check("book_flight refuses unknown flight (errors)", errx)

            # Beat B: swap to stale MID-SESSION -> next call sees stale weather
            sh("use-stale.sh")
            err, flights = payload(await s.call_tool("search_flights", {"origin": "SJC"}))
            phx = {f["flight_id"]: f for f in flights}["DL455"]
            check("Beat B: after use-stale.sh, PHX reads Sunny (the trap)",
                  phx["weather"] == "Sunny")
            check("Beat B: PHX weather_as_of is 2026-08-17 (5 days stale)",
                  phx["weather_as_of"] == "2026-08-17")
            sh("use-current.sh")


async def test_loyalty():
    print("\n== loyalty_server ==")
    async with stdio_client(params("loyalty_server.py")) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            names = {t.name for t in (await s.list_tools()).tools}
            check("tool is check_miles", names == {"check_miles"})

            err, m = payload(await s.call_tool("check_miles", {"name": "Jordan Rivera"}))
            check("check_miles(Jordan Rivera) -> 45000, Gold",
                  not err and m.get("miles_balance") == 45000 and m.get("tier") == "Gold")

            # Beat C: break the DB MID-SESSION -> next call MUST error, not fake
            sh("break-miles.sh")
            err, text = payload(await s.call_tool("check_miles", {"name": "Jordan Rivera"}))
            check("Beat C: check_miles ERRORS on broken DB (isError)", err)
            check("Beat C: error does NOT contain a fake balance number",
                  "45000" not in str(text))
            sh("reset-miles.sh")
            err, m = payload(await s.call_tool("check_miles", {"name": "Jordan Rivera"}))
            check("after reset-miles.sh, check_miles healthy again -> 45000",
                  not err and m.get("miles_balance") == 45000)


async def test_policies():
    print("\n== policies_server ==")
    async with stdio_client(params("policies_server.py")) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            names = {t.name for t in (await s.list_tools()).tools}
            check("tool is search_policies", names == {"search_policies"})

            err, p = payload(await s.call_tool(
                "search_policies", {"query": "refund miles redeposited cancel"}))
            check("search_policies finds a refund passage in CURRENT policy",
                  not err and p.get("source_file") == "refund-policy.md"
                  and p.get("version") == "2026.3" and bool(p.get("passage")))

            # RAG variant of Beat B: swap to superseded policy MID-SESSION
            sh("use-stale-policy.sh")
            err, p = payload(await s.call_tool(
                "search_policies", {"query": "refund fully refundable any time"}))
            check("after use-stale-policy.sh, version reads 2025.4 (superseded)",
                  not err and p.get("version") == "2025.4")
            sh("use-current-policy.sh")


async def main():
    sh("setup.sh")
    await test_reservations()
    await test_loyalty()
    await test_policies()
    print("\n" + ("=" * 40))
    if _failures:
        print(f"{FAIL}: {len(_failures)} check(s) failed:")
        for f in _failures:
            print(f"   - {f}")
        sys.exit(1)
    print(f"{PASS}: all checks passed.")


if __name__ == "__main__":
    asyncio.run(main())
