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

- **[uv](https://docs.astral.sh/uv/)** — runs the SQLite MCP server via `uvx`
  (`curl -LsSf https://astral.sh/uv/install.sh | sh`).
- **[Node.js](https://nodejs.org/)** — runs the filesystem MCP server via `npx`.
- **An MCP client** — e.g. [Claude Desktop](https://claude.ai/download) or
  [Claude Code](https://docs.claude.com/en/docs/claude-code). Any MCP host works.
- **Python 3** (stdlib only) — seeds the synthetic databases.

## What's wired

Three off-the-shelf MCP servers, one MCP host (Claude Desktop or Claude Code):

| Server (public name) | Off-the-shelf package | Serves |
|---|---|---|
| `reservations` | `mcp-server-sqlite` (reference, via `uvx`) | `data/reservations.db` — flights, per-airport weather, bookings |
| `loyalty`      | `mcp-server-sqlite` (reference, via `uvx`) | `data/loyalty.db` — frequent-flyer members (traveler = Jordan Rivera) |
| `policies`     | `@modelcontextprotocol/server-filesystem` (via `npx`) | `policy/active/` — refund + baggage rules (markdown, for the RAG beat) |

The two failures are simple toggles, **no app restart** (the SQLite server
reconnects to the DB file per query; the filesystem server reads fresh per call):

- **Beat B (stale source):** `use-stale.sh` swaps `reservations.db` for a
  5-day-old weather snapshot in which Phoenix still reads *Sunny* — it's really a
  storm now. The assistant confidently books Phoenix.
- **Beat C (tool failure):** `break-miles.sh` swaps the loyalty DB for a
  non-database file; the SQLite server errors on its next query. The naive
  assistant books anyway (fail open).

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
│  └─ assistant-guardrailed.md   # guardrail (Beat D)
├─ config/
│  ├─ claude_desktop_config.json # Claude Desktop host config (absolute uvx path)
│  └─ mcp.json                   # Claude Code (.mcp.json) host config
├─ scripts/
│  ├─ setup.sh  status.sh
│  ├─ use-current.sh  use-stale.sh           # Beat B (reservations snapshot)
│  ├─ break-miles.sh  reset-miles.sh         # Beat C (loyalty outage)
│  ├─ use-current-policy.sh  use-stale-policy.sh   # optional RAG variant of B
│  └─ loyalty_fallback/          # OPTIONAL server if the file-swap needs a backup
├─ demo/
│  ├─ demo-script.md             # per-beat prompts + narration + monitor cheat-sheet
│  └─ rehearsal-checklist.md     # dry-run + backup-video checklist
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
`/ABSOLUTE/PATH/TO/mcp-airline-demo` with the real path (SQLite needs absolute
paths). The `--with "mcp[cli]<2"` pin is **required** — see
[Troubleshooting](#troubleshooting).

```jsonc
{
  "mcpServers": {
    "reservations": {
      "command": "uvx",
      "args": ["--with", "mcp[cli]<2", "mcp-server-sqlite",
               "--db-path", "/ABSOLUTE/PATH/TO/mcp-airline-demo/data/reservations.db"]
    },
    "loyalty": {
      "command": "uvx",
      "args": ["--with", "mcp[cli]<2", "mcp-server-sqlite",
               "--db-path", "/ABSOLUTE/PATH/TO/mcp-airline-demo/data/loyalty.db"]
    },
    "policies": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem",
               "/ABSOLUTE/PATH/TO/mcp-airline-demo/policy/active"]
    }
  }
}
```

- **Claude Desktop:** put this in `~/Library/Application Support/Claude/claude_desktop_config.json`
  (macOS). A ready copy is in [`config/claude_desktop_config.json`](config/claude_desktop_config.json).
  If the host can't find `uvx`, use its absolute path (`which uvx`).
- **Claude Code:** save as `.mcp.json` in the project root — see [`config/mcp.json`](config/mcp.json).

Then **fully quit and reopen** the host and confirm all three servers connect.

**4. Set the assistant instructions** to [`prompts/assistant-base.md`](prompts/assistant-base.md)
(the naive build) and follow [`demo/demo-script.md`](demo/demo-script.md).

The traveler's request, typed verbatim each beat:
> `Book me a cheap flight somewhere sunny this weekend and use my miles. I'm Jordan Rivera.`

## The two prompts

- **[`prompts/assistant-base.md`](prompts/assistant-base.md)** — the naive build.
  No guardrail; it can be fooled by a stale source (Beat B) and a failed tool
  (Beat C). Used for A, B, C.
- **[`prompts/assistant-guardrailed.md`](prompts/assistant-guardrailed.md)** — same
  assistant plus a system-prompt guardrail: *quote your source* and *fail closed*
  on missing / errored / stale data. Used for Beat D; it catches both failures.

## Troubleshooting

**SQLite servers show "Server disconnected" / fail to start.** `uvx
mcp-server-sqlite` pulls the `mcp` SDK, which now resolves to 2.x, and the
archived reference server crashes on it
(`AttributeError: 'Server' object has no attribute 'list_resources'`). Pin the
SDK to 1.x by adding `--with "mcp[cli]<2"` before `mcp-server-sqlite` in the args
(already done in the config above). Full note:
[`FIX-sqlite-server-pin.md`](FIX-sqlite-server-pin.md). The filesystem server is
unaffected.

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
