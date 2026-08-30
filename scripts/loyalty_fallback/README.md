# Optional deterministic fallback loyalty server (Beat C)

The primary demo runs the purpose-built `servers/loyalty_server.py` (the
`check_miles` domain tool), and Beat C breaks it with `scripts/break-miles.sh`
(swaps the DB for a non-database file; the server errors on its next call). That
path is verified by the smoke test and is the default.

**Only reach for this if** rehearsal shows the file-swap error not landing as a
clear error to the model. This server is a drop-in replacement for the primary
one: same server name (`loyalty`), same single domain tool (`check_miles`), same
`{name, miles_balance, tier}` return shape. It reads the same `data/loyalty.db`
but fails on command via a flag file, so Beat C is deterministic with no restart.
Like the primary server it fails closed and never returns a fake balance.

## Toggle
```
touch scripts/loyalty_fallback/OUTAGE   # Beat C: next check_miles raises a timeout error
rm    scripts/loyalty_fallback/OUTAGE   # healthy again
```

## Wire it in (replaces the loyalty block in the host config)
```json
"loyalty": {
  "command": "/Users/agnitripathi/.local/bin/uv",
  "args": ["run", "--with", "mcp[cli]<2",
           "/Users/agnitripathi/mcp-airline-demo/scripts/loyalty_fallback/server.py"]
}
```
Restart the host once after swapping configs. After that, Beat C is the
`touch`/`rm` above — no restart, same as the rest of the demo.

Trade-off: the file-swap breaks the real server from the outside (nothing custom
in the failure path), while this triggers the outage from inside a server we
wrote. Both surface the same failed `check_miles` call. Prefer the file-swap;
keep this in your pocket.
