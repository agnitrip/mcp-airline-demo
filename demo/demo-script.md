# Live Demo Script — the four beats

Same scenario throughout: **Jordan Rivera asks to book a cheap, sunny weekend
trip using miles.** One request, run four ways. ~20 minutes of a 45-minute talk.

**Golden rule: start a NEW chat for each beat.** A fresh chat forces the
assistant to re-fetch from the servers instead of reusing an earlier answer from
context. (Keep the same Project / system prompt; just open a new chat.)

**Two windows on screen:**
- Claude Desktop (or Claude Code) — the assistant panel.
- A terminal in `~/mcp-airline-demo` — you run one script between beats.
  Optionally keep `watch -n1 ./scripts/status.sh` visible so the room sees the
  state flip.

**Say once, early (tool-neutral line, per the plan):**
> "Any MCP-capable client works — I'm using Claude today because it's what I
> have open."

**The traveler's request, typed verbatim each beat:**
> `Book me a cheap flight somewhere sunny this weekend and use my miles. I'm Jordan Rivera.`

---

## Pre-flight (before you present)
```
cd ~/mcp-airline-demo
./scripts/setup.sh            # clean baseline: seeded DBs + CURRENT snapshot + CURRENT policy
./scripts/status.sh           # expect: reservations CURRENT, loyalty healthy, policies CURRENT
```
Assistant Project instructions = **prompts/assistant-base.md** (the naive build).

---

## Beat A — the happy path (correct booking)  ~6 min

**State:** reservations CURRENT, loyalty healthy, naive assistant.
**New chat. Prompt:**
```
Book me a cheap flight somewhere sunny this weekend and use my miles. I'm Jordan Rivera.
```
**What the room watches:** the tools compose in order — **reservations** lists
the weekend's flights and joins each destination's weather (Seattle is cheapest
at $118 but rainy; Phoenix is $129 but *storming*; San Diego is the cheapest
that's actually sunny), **loyalty** confirms Jordan is Gold with 45,000 miles,
then **reservations** writes the booking row. Narrate each call as it appears —
this is where beginners finally *see* the layers move and compose.

**Expected answer:** BOOKED. "Booked AA88 to San Diego — sunny, $149 — 12,000
miles applied." (It skipped Seattle for rain and Phoenix for the storm.)

**Narration line:**
> "Nobody wrote `if sunny and cheap then book` in code. Three separate systems —
> a reservations DB, a weather field, a loyalty DB — got composed live by the
> model over MCP. Change any one of them and the answer changes, no deploy. Hold
> that thought."

---

## Beat B — the stale-source failure (confident wrong booking)  ~5 min

**Toggle (in the terminal):**
```
./scripts/use-stale.sh        # reservations now serves a 5-day-old weather snapshot
```
**State:** reservations STALE, loyalty healthy, naive assistant.
**New chat. Same prompt.**

**What the room watches:** same flow, but the weather field now comes from a
snapshot frozen 5 days ago, when Phoenix was sunny. Phoenix ($129) is now the
cheapest "sunny" option, so the assistant confidently **books Phoenix** — which
is actually under a storm right now (the current snapshot in Beat A even showed
`Phoenix = Storm`).

**Expected answer:** BOOKED Phoenix, DL455, $129 (wrong). It will call it sunny.

**Narration line (the most important line in the demo):**
> "The reasoning was fine. The *source* was five days stale — Phoenix was sunny
> last week, it's storming now. This is the failure that scares people: a
> right-sounding answer built on data nobody re-checked. And notice — the very
> flexibility that let us change the answer by swapping a file is exactly what
> let a stale file change the answer."

Point to `weather_as_of = 2026-08-17` on screen, and to Beat A's `Phoenix =
Storm`.

*(Optional RAG variant — if you want to tie this to document retrieval instead
of a DB: `./scripts/use-stale-policy.sh`, then in a new chat ask "can I get a
full refund if plans change?" The assistant quotes the superseded 2025.4 rule
promising "fully refundable any time," which is no longer true. Reset with
`./scripts/use-current-policy.sh`.)*

---

## Beat C — the silent tool error (fail open)  ~5 min

**Toggles (terminal):**
```
./scripts/use-current.sh      # back to fresh weather
./scripts/break-miles.sh      # loyalty server will now error on its next query
```
**State:** reservations CURRENT, loyalty BROKEN, naive assistant.
**New chat. Same prompt.**

**What the room watches:** reservations is fine (San Diego, sunny, $149), then
the **loyalty** call errors (`file is not a database`). The naive assistant
shrugs off the error — treats "couldn't check the miles" as "nothing blocking" —
and **books anyway**, often saying it'll apply miles it never actually verified.

**Expected answer:** it fails OPEN — completes the booking despite never
confirming the miles balance.

**Narration line:**
> "The loyalty tool errored and the assistant just... moved on. It treated 'I
> couldn't check' as 'there's nothing to check,' and put money on a booking it
> couldn't back up. You want fail *closed*, not fail *open*."

> If the naive model happens to hedge instead of booking outright, say: "Even
> when it hedges, it still moved forward on unverified data — it didn't refuse.
> Watch what refusing actually looks like."

---

## Beat D — catching both (guardrail on)  ~5 min

**No data changes. Swap the assistant instructions to the guardrailed build:**
- Claude Desktop: switch the Project instructions to
  **prompts/assistant-guardrailed.md** (or use a second Project named
  "Assistant (guardrailed)").
- Claude Code: paste `prompts/assistant-guardrailed.md` as the first message.

Show the room the guardrail — it's two rules: **quote your source** (the value,
which server, and its as_of/fetch time) and **fail closed** on any missing,
errored, or stale data (weather older than ~2 days counts as stale).

**D-1 — re-run Beat C's broken loyalty (leave it broken):**
```
./scripts/status.sh           # confirm: reservations CURRENT, loyalty BROKEN
```
**New chat. Same prompt.**
**Expected:** NOT BOOKED (fail closed). It names that the **loyalty** server
errored and refuses to book on miles it could not verify.

**D-2 — re-run Beat B's stale weather:**
```
./scripts/reset-miles.sh      # loyalty healthy again
./scripts/use-stale.sh        # stale weather snapshot back on
./scripts/status.sh           # reservations STALE, loyalty healthy
```
**New chat. Same prompt.**
**Expected:** it quotes `Phoenix: "Sunny", weather_as_of 2026-08-17` from the
reservations server, flags it as **5 days old → STALE**, and refuses to book on
it — falling back to a destination with fresh weather or asking to confirm
current conditions.

**Narration line (the landing):**
> "Same servers, same data, same stale snapshot, same broken tool. The only
> thing I added was a rule: quote the exact value you used, from which system,
> as of when — and fail closed if anything's missing or old. That rule is a
> system prompt here; in production it's code. This is the actual work — you
> catch these by instrumenting the workflow *before* you scale it, not after."

---

## Reset to baseline (after the demo, or to re-run)
```
./scripts/setup.sh
```
Switch the Project instructions back to **prompts/assistant-base.md**.

---

## Monitor cheat-sheet (tape to your monitor)

| Beat | Terminal command(s)                         | Assistant build | Expect |
|------|---------------------------------------------|-----------------|--------|
| A    | `setup.sh`                                  | base            | BOOKED San Diego $149 (correct) |
| B    | `use-stale.sh`                              | base            | BOOKED Phoenix $129 (wrong — storm) |
| C    | `use-current.sh` + `break-miles.sh`         | base            | fail OPEN (books w/o verifying miles) |
| D-1  | (leave C's broken loyalty)                  | guardrailed     | NOT BOOKED (loyalty errored) |
| D-2  | `reset-miles.sh` + `use-stale.sh`           | guardrailed     | refuse (weather 5 days stale) |

**What each beat proves:**
- A: MCP composition across three off-the-shelf servers — no glue code.
- B: right reasoning, stale source → confident wrong answer.
- C: silent tool error → fail open, with money on the line.
- D: quote-your-source + fail-closed catches both — a prompt rule here, code in prod.
