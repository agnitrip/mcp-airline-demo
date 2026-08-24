# Fix: SQLite MCP servers failed with "Server disconnected" (2026-08-23)

## Symptom
In Claude Desktop, `reservations` and `loyalty` showed **failed / Server
disconnected**; `policies` (filesystem) worked fine.

## Root cause
`uvx mcp-server-sqlite` pulls its dependency `mcp[cli]>=1.6.0` and resolved to
**mcp 2.0.0**. The archived reference `mcp-server-sqlite` was written for the 1.x
low-level SDK and crashes at startup on 2.x:
`AttributeError: 'Server' object has no attribute 'list_resources'`
(see `~/Library/Logs/Claude/mcp-server-reservations.log`). The filesystem server
does not use that SDK, so it was unaffected.

## Fix (applied)
Pin the SDK to 1.x by adding `--with "mcp[cli]<2"` before the package in BOTH
SQLite server args, in the LIVE config
`~/Library/Application Support/Claude/claude_desktop_config.json` and this kit's
`config/claude_desktop_config.json`. Example:

```json
"reservations": {
  "command": "/Users/agnitripathi/.local/bin/uvx",
  "args": ["--with", "mcp[cli]<2", "mcp-server-sqlite",
           "--db-path", "/Users/agnitripathi/mcp-airline-demo/data/reservations.db"]
}
```

Verified: the server responds to `initialize` with `serverInfo.name = "sqlite"`
and no traceback. **Fully quit and reopen Claude Desktop** for the config change
to take effect.

## Note for rehearsal / other machines
Any machine running this demo needs the same pin. If `mcp-server-sqlite` ever
breaks again, either keep pinning `mcp[cli]<2`, or replace it with a tiny
FastMCP server we control (pattern exists in the access kit at
`~/mcp-iget-demo/scripts/ticketing_fallback/server.py`), which avoids the
SDK-version fragility entirely.
