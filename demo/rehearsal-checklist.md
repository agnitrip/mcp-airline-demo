# Rehearsal + Backup Checklist

A demo-majority talk with live tool calls needs one clean end-to-end rehearsal
and a recorded backup. You present remotely, so **assume the venue wifi will
fail** and make the backup video non-negotiable. Budget ~1 evening.

## 0. Install + warm (once, on the presenting machine)
- [ ] `uv` present: `which uvx` (installer: `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- [ ] Node present: `node --version` (for the filesystem server via `npx`)
- [ ] Warm the server caches so nothing downloads on stage:
      `uvx mcp-server-sqlite --help` and
      `npx -y @modelcontextprotocol/server-filesystem /tmp` (Ctrl-C after it
      prints "running on stdio")
- [ ] `./scripts/setup.sh` runs clean; `./scripts/status.sh` shows
      reservations CURRENT, loyalty healthy, policies CURRENT
- [ ] Copy `config/claude_desktop_config.json` to
      `~/Library/Application Support/Claude/claude_desktop_config.json`
      (or add servers in Claude Code with `config/mcp.json`). Fix the paths if
      your home dir is not `/Users/agnitripathi`.
- [ ] Fully quit and reopen Claude Desktop. Confirm all three servers show as
      connected (the tools icon lists reservations, loyalty, policies).
- [ ] In Claude Desktop settings, set the three servers to **auto-approve** tool
      calls (or you'll click "allow" a dozen times live). If you'd rather show
      the approval prompts once, do it in Beat A only, then auto-approve.
- [ ] The `reservations` server can write (it creates the booking row). Confirm
      the write is allowed / auto-approved so Beat A completes the booking.

## 1. Full dry run (do all four beats, timed)
- [ ] Beat A → BOOKED San Diego, $149, 12,000 miles. Note the exact wording; time it.
- [ ] Beat B (`use-stale.sh`, new chat) → BOOKS Phoenix $129. Confirm it calls
      Phoenix sunny and does NOT notice the stale `weather_as_of`.
- [ ] Beat C (`use-current.sh` + `break-miles.sh`, new chat) → fails OPEN.
      **This is the one to watch.** Confirm the assistant actually proceeds after
      the loyalty error. If your model hedges, keep the Beat C narration fallback
      line handy (it's in demo-script.md).
- [ ] Beat D-1 (guardrailed, broken loyalty still on, new chat) → NOT BOOKED.
- [ ] Beat D-2 (`reset-miles.sh` + `use-stale.sh`, guardrailed, new chat) →
      refuses on stale weather, quoting `weather_as_of`.
- [ ] `./scripts/setup.sh` returns to baseline cleanly.
- [ ] Total demo time is ~18–22 min. Trim narration if over.

## 2. Reliability checks (the things that can bite live)
- [ ] **Loyalty error really fires without a restart.** After `break-miles.sh`,
      the next miles lookup must error. Verified at the data layer (`file is not
      a database`), but confirm the *model* sees it as an error in a fresh chat.
      If for any reason it doesn't, use the optional fallback server in
      `scripts/loyalty_fallback/` (see its README) — it errors on command via a
      flag file, independent of server internals.
- [ ] **Snapshot swap is picked up on the next message.** The SQLite server
      reconnects per query, but always run the toggle BEFORE opening the new
      chat, not during.
- [ ] **New chat per beat.** If an answer looks "too smart" (e.g. Beat B books
      San Diego or flags the storm), you probably reused a chat that still had
      the fresh data in context. Open a fresh chat and re-run.
- [ ] **Date sanity.** The seed uses a fixed synthetic "today" of 2026-08-22
      (weekend of 22–23 Aug 2026), and the guardrailed prompt references the same
      date. If your talk date drifts far from that, the "5 days stale" framing
      still holds (it only gets more stale) — but if you want it pixel-perfect,
      bump `TODAY`/`FIVE_DAYS_AGO` in `data/seed.py` and the date line in
      `prompts/assistant-guardrailed.md`, then re-run `setup.sh`.

## 3. Record the backup video (non-negotiable — you present remotely)
- [ ] Screen-record the full four-beat run once it's clean (QuickTime: File →
      New Screen Recording, or `Cmd-Shift-5`). Capture both windows.
- [ ] Narrate it as you'll present it, or add captions after. 8–12 min is fine
      for a backup — it only plays if the live run fails.
- [ ] Save as `demo/backup-run.mov` (gitignored) AND upload a copy somewhere you
      can reach offline (local file + phone/Drive). Venue/home wifi may drop.
- [ ] Test that the video plays fullscreen from the presenting machine with wifi
      OFF.
- [ ] Because you're remote: have the backup video on the SAME machine you screen-
      share from, and know how to switch your share to it in one click.

## 4. Stage-day quick reset
- [ ] `./scripts/setup.sh` + base Project instructions = clean slate.
- [ ] `./scripts/status.sh` in a side terminal, visible to you (or `watch -n1`).
- [ ] Monitor cheat-sheet (bottom of demo-script.md) taped to the monitor.
- [ ] If anything misbehaves in the first 20 seconds of a beat: stop, say "let me
      show you the recorded version," play the backup. Don't debug live.
