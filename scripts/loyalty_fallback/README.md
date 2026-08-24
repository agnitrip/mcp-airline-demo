# Optional fallback loyalty server

The primary demo uses the off-the-shelf `mcp-server-sqlite` for the loyalty
server, and Beat C breaks it with `scripts/break-miles.sh` (swaps the DB for a
non-database file; the server errors on its next query). That path is verified
and needs no code from us.

**Only reach for this if** rehearsal shows the file-swap error not landing as a
clear error to the model. This little server (built on the official `mcp` Python
SDK) reads the same `data/loyalty.db` and fails on command via a flag file —
deterministic, no restart.

## Toggle
```
touch scripts/loyalty_fallback/OUTAGE   # Beat C: next lookup raises a timeout error
rm    scripts/loyalty_fallback/OUTAGE   # healthy again
```

## Wire it in (replaces the loyalty block in the host config)
```json
"loyalty": {
  "command": "/Users/agnitripathi/.local/bin/uv",
  "args": ["run", "--with", "mcp",
           "/Users/agnitripathi/mcp-airline-demo/scripts/loyalty_fallback/server.py"]
}
```
Restart the host once after swapping configs. After that, Beat C is the
`touch`/`rm` above — no restart, same as the rest of the demo.

Trade-off: this server is one we wrote (still open source, ~50 lines on the
official SDK), so it's slightly less "purely off-the-shelf" than the file-swap.
Prefer the file-swap; keep this in your pocket.
