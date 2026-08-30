# MCP Airline Demo Kit

Runnable demo for the IEEE talk *"Connecting Enterprise AI Using MCP."* One
scenario — a traveler types **"Book me a cheap flight somewhere sunny this
weekend and use my miles"** — run four ways: happy path, two failures, and the
catch. Built so anyone can reproduce it in about five minutes.

**▶ Run it in 5 minutes:** https://agnitrip.github.io/mcp-airline-demo/

Everything here is **synthetic and open-source** (MIT). No real people, no
proprietary anything — the traveler "Jordan Rivera" and all airline data are
fake. Safe to run, record, and post publicly. The framing is *a common
enterprise pattern*: an assistant composing several back-end systems over MCP.

It is tool-neutral — **any MCP-capable client works**. The demo uses Claude
Desktop because it is a convenient off-the-shelf host.

## Prerequisites

- **[uv](https://docs.astral.sh/uv/)** — runs the three Python MCP servers via
  `uv run` (`curl -LsSf https://astral.sh/uv/install.sh | sh`). It also
  provisions the pinned `mcp` SDK on first launch — no manual `pip install`.
- **An MCP client** — e.g. [Claude Desktop](https://claude.ai/download) or
  [Claude Code](https://docs.claude.com/en/docs/claude-code). Any MCP host works.
- **Python 3** (stdlib only) — seeds the synthetic databases.

## What's wired

Three thin, purpose-built MCP servers (Python, `mcp` SDK), one MCP host (Claude
Desktop or Claude Code). Each wraps a synthetic backend and exposes **named
domain tools** — the shape the talk slides teach — instead of generic SQL:

| Server (public name) | Code | Tools | Wraps |
|---|---|---|---|
| `reservations` | [`servers/reservations_server.py`](servers/reservations_server.py) | `search_flights`, `book_flight` | `data/reservations.db` — flights, per-airport weather, bookings |
| `loyalty`      | [`servers/loyalty_server.py`](servers/loyalty_server.py) | `check_miles` | `data/loyalty.db` — frequent-flyer members (traveler = Jordan Rivera) |
| `policies`     | [`servers/policies_server.py`](servers/policies_server.py) | `search_policies` | `policy/active/` — refund + baggage rules (markdown, for the RAG beat) |

Each tool opens its backend **fresh on every call** (a new SQLite connection, or
a fresh directory read) and closes it. Nothing is cached — that is what makes the
file-swap toggles work with **no app restart**:

- **Beat B (stale source):** `use-stale.sh` swaps `reservations.db` for a
  5-day-old weather snapshot in which Phoenix still reads *Sunny* — it's really a
  storm now. `search_flights` returns that stale `weather_as_of`; the naive
  assistant confidently books Phoenix.
- **Beat C (tool failure):** `break-miles.sh` swaps the loyalty DB for a
  non-database file; `check_miles` **raises** on its next call (it never returns
  a fake balance). The naive assistant books anyway (fail open).

> **Off-the-shelf fallback.** A proven all-off-the-shelf variant (reference
> `mcp-server-sqlite` + `@modelcontextprotocol/server-filesystem`, generic SQL
> tools) is committed as `config/*.generic.json` and `prompts/*.generic.md`. See
> [Fallback](#fallback-off-the-shelf-servers) to switch to it.

The guardrail (Beat D) is a **system-prompt rule** — the thinnest thing that
reliably shows *quote-your-source + fail-closed*, with nothing extra to crash on
stage. In production you'd enforce the same two rules in code (the talk's
"instrument the workflow" point).

## The scenario, four beats

| Beat | Toggle | Assistant | Outcome |
|------|--------|-----------|---------|
| A | baseline | naive | **BOOKED San Diego $149**, sunny, 12,000 miles — correct |
| B | `use-stale.sh` | naive | **BOOKED Phoenix $129** on 5-day-old weather — wrong (storm) |
| C | `use-current.sh` + `break-miles.sh` | naive | loyalty errors → **books anyway** (fail open) |
| D | swap to guardrailed prompt | guardrailed | catches both: **NOT BOOKED** on the error, **refuses** the stale weather |

## Layout
```
mcp-airline-demo/
├─ README.md
├─ servers/
│  ├─ reservations_server.py     # search_flights, book_flight  (wraps reservations.db)
│  ├─ loyalty_server.py          # check_miles                  (wraps loyalty.db)
│  └─ policies_server.py         # search_policies              (wraps policy/active/)
├─ data/
│  ├─ seed.py                    # builds all DBs (stdlib sqlite3 only)
│  ├─ reservations-current.db    # generated: fresh weather (San Diego sunny, Phoenix storm)
│  ├─ reservations-stale.db      # generated: 5-day-old snapshot (Phoenix still "sunny")
│  ├─ reservations.db            # active file the server serves (copied in by scripts)
│  └─ loyalty.db                 # generated: members
├─ policy/
│  ├─ current/  refund-policy.md  baggage-policy.md   # v2026.3 CURRENT
│  ├─ stale/    refund-policy.md  baggage-policy.md   # v2025.4 SUPERSEDED (optional RAG beat)
│  └─ active/   ...                                    # what policies serves (copied in)
├─ prompts/
│  ├─ assistant-base.md          # naive assistant (Beats A/B/C)
│  ├─ assistant-guardrailed.md   # guardrail (Beat D)
│  └─ *.generic.md               # fallback prompts for the off-the-shelf setup
├─ config/
│  ├─ claude_desktop_config.json # Claude Desktop host config (purpose-built servers)
│  ├─ mcp.json                   # Claude Code (.mcp.json) host config
│  └─ *.generic.json             # fallback config for the off-the-shelf setup
├─ scripts/
│  ├─ setup.sh  status.sh
│  ├─ use-current.sh  use-stale.sh           # Beat B (reservations snapshot)
│  ├─ break-miles.sh  reset-miles.sh         # Beat C (loyalty outage)
│  ├─ use-current-policy.sh  use-stale-policy.sh   # optional RAG variant of B
│  └─ loyalty_fallback/          # OPTIONAL server if the file-swap needs a backup
├─ docs/                         # the "run it in 5 minutes" GitHub Pages one-pager
├─ FIX-sqlite-server-pin.md      # why the config pins mcp[cli]<2
└─ LICENSE                       # MIT
```

## Quick start

```bash
# 1. Clone
git clone https://github.com/agnitrip/mcp-airline-demo.git
cd mcp-airline-demo

# 2. Seed data + set clean baseline
./scripts/setup.sh
./scripts/status.sh        # -> reservations CURRENT, loyalty healthy, policies CURRENT
```

**3. Wire the MCP host.** Add the three servers to your client's config. Replace
`/ABSOLUTE/PATH/TO/mcp-airline-demo` with the real path (the servers resolve
their data files relative to their own location, but the host needs the absolute
path to each script). The `--with "mcp[cli]<2"` pin keeps the SDK on 1.x — see
[Troubleshooting](#troubleshooting). (Each server also declares that pin inline
via [PEP 723](https://peps.python.org/pep-0723/) metadata, so `uv run` provisions
it automatically.)

```jsonc
{
  "mcpServers": {
    "reservations": {
      "command": "uv",
      "args": ["run", "--with", "mcp[cli]<2",
               "/ABSOLUTE/PATH/TO/mcp-airline-demo/servers/reservations_server.py"]
    },
    "loyalty": {
      "command": "uv",
      "args": ["run", "--with", "mcp[cli]<2",
               "/ABSOLUTE/PATH/TO/mcp-airline-demo/servers/loyalty_server.py"]
    },
    "policies": {
      "command": "uv",
      "args": ["run", "--with", "mcp[cli]<2",
               "/ABSOLUTE/PATH/TO/mcp-airline-demo/servers/policies_server.py"]
    }
  }
}
```

- **Claude Desktop:** put this in `~/Library/Application Support/Claude/claude_desktop_config.json`
  (macOS). A ready copy is in [`config/claude_desktop_config.json`](config/claude_desktop_config.json).
  If the host can't find `uv`, use its absolute path (`which uv`).
- **Claude Code:** save as `.mcp.json` in the project root — see [`config/mcp.json`](config/mcp.json).

Then **fully quit and reopen** the host and confirm all three servers connect.

**4. Set the assistant instructions** to [`prompts/assistant-base.md`](prompts/assistant-base.md)
(the naive build), then run the four beats from the table above — one toggle, a new chat, and the
same request each time. Swap to [`prompts/assistant-guardrailed.md`](prompts/assistant-guardrailed.md)
for Beat D.

The traveler's request, typed verbatim each beat:
> `Book me a cheap flight somewhere sunny this weekend and use my miles. I'm Jordan Rivera.`

## The two prompts

- **[`prompts/assistant-base.md`](prompts/assistant-base.md)** — the naive build.
  No guardrail; it can be fooled by a stale source (Beat B) and a failed tool
  (Beat C). Used for A, B, C.
- **[`prompts/assistant-guardrailed.md`](prompts/assistant-guardrailed.md)** — same
  assistant plus a system-prompt guardrail: *quote your source* and *fail closed*
  on missing / errored / stale data. Used for Beat D; it catches both failures.

## Fallback (off-the-shelf servers)

If a purpose-built server misbehaves on stage, switch back to the proven
all-off-the-shelf setup (reference `mcp-server-sqlite` + filesystem server,
generic SQL/file tools) in seconds — it's committed:

```bash
cp config/claude_desktop_config.generic.json config/claude_desktop_config.json  # Claude Desktop
cp config/mcp.generic.json                    config/mcp.json                    # Claude Code
```

Then use `prompts/assistant-base.generic.md` / `prompts/assistant-guardrailed.generic.md`
(they drive the generic `read_query` / `read_file` tools), copy the config into
the host's live location, and fully restart the host. The `@modelcontextprotocol/server-filesystem`
fallback needs Node.js (`npx`); the reference SQLite server needs `uvx`. The
demo beats behave identically — only the tool names differ.

## Troubleshooting

**Servers show "Server disconnected" / fail to start.** The `mcp` SDK now
resolves to 2.x, and 1.x-era servers crash on it
(`AttributeError: 'Server' object has no attribute 'list_resources'`). The three
purpose-built servers here target the 1.x low-level SDK, so the config pins it
with `--with "mcp[cli]<2"` (and each script repeats that pin inline via PEP 723
metadata). Keep the pin. Full note:
[`FIX-sqlite-server-pin.md`](FIX-sqlite-server-pin.md).

**A beat gives the "too smart" answer** (e.g. Beat B books San Diego, or flags
the storm). You probably reused a chat that still had fresh data in context.
Start a **new chat** for each beat.

## Reset between runs
```bash
./scripts/setup.sh    # reseed + CURRENT snapshot + healthy loyalty + CURRENT policy
```
Then switch the assistant instructions back to `prompts/assistant-base.md`.

## Notes
- All dates are a fixed synthetic "today" = **2026-08-22** (weekend of 22–23 Aug
  2026). To re-date, edit `TODAY`/`FIVE_DAYS_AGO` in `data/seed.py` and the date
  line in `prompts/assistant-guardrailed.md`, then re-run `setup.sh`.
- Generated `.db` files are gitignored; `./scripts/setup.sh` regenerates them
  from [`data/seed.py`](data/seed.py) (Python stdlib only, no dependencies).

## License

MIT — see [`LICENSE`](LICENSE). All data is synthetic; reuse freely.
