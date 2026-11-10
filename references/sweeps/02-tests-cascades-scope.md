# Sweeps S6–S14 — tests, cascades, orphans and scope

> Part of `references/sweeps/` (index: `README.md`). Split from the former `sweeps.md` on 2026-11-10 - text unchanged. Read every file in the folder per §0.9.

## S6 — Deferred-work comments are open gaps (deferred-work residue)

Grep the commerce roots for `TODO`, `FIXME`, `follow-up`, `follow up commit`, `until then`, `for now`, `temporary`, `pre-migration`. Each hit is either closed (prove it, cite the commit) or listed as an open gap in the report. A comment that promises a later commit which never landed is the most common shape of a shipped half-feature.

## S7 — Skipped tests are unverified, never green (vacuous pass)

Any suite result containing `Skipped: N` where the skipped tests are the DB-backed, gateway-backed, or browser-backed ones is reported as "N unverified", not as a pass. Before running DB suites, confirm the DB container is up and the test-DB env vars are exported in the same shell as the runner; a suite that skips because they are unset prints a happy `OK` that means nothing. If the skipped tests cannot be run this session, the report says which ones and why, by name.

## S8 — A written test is not a run test (vacuous pass)

Every test added or changed this session must appear in the report with the exact command and the exact `Tests: N, Assertions: M` line from an actual execution against the real backing store. "Added regression, unrun without DB" is an honest checkpoint note but it is not evidence; carry it forward as unverified and run it the moment the store is reachable. Expect some of these to fail on first real execution: a test written without running it encodes the author's assumption, not the system's behaviour.

## S9 — Rename residue

For every class, CSS selector, template, route or config key renamed in the git log since the last audit, grep both sides of the rename in every consumer (PHP, templates, CSS, JS, tests, docs). A selector left in the stylesheet after the markup moved on silently removes styling; a route left in a doc sends the owner to a 404. Architecture guard tests that enforce parity are to be kept red-visible, never excluded or whitelisted to make the suite pass.

## S10 — Environment truth before diagnosis (diagnosis without probe)

Before concluding "site not installed", "DB missing", "sandbox blocked", run the cheapest direct probe (container list, TCP connect, health endpoint) and record the result. A 503 from the app and a timeout on the DB port are consistent with a stopped container; they are not evidence of missing schema or lost data. Never provision, reset, or reinstall on the strength of an application error message alone. **Framework and opcode caches mask the code you just changed.** Before concluding that an edit had no effect — a form that still does not render, a branch that never runs — clear the framework's compiled cache and restart the runtime, then re-probe. ProcessWire's FileCompiler, opcache, template caches and CDN layers all serve a previous version of a file that looks correct on disk. A diagnosis made over a stale cache sends the next hour into the wrong file.

## S11 — Boundary contract / schema drift

For every payload that crosses a boundary into this system (gateway callback, webhook, logistics status push, import file, admin form, any JSON from an external API or a model), find the point where it is parsed and the point where it is first acted on. Between those two points there must be explicit validation of shape and type: required fields present, unexpected fields ignored or rejected deliberately, numeric amounts not accepted as strings without conversion, null where a list or object is expected refused, encoding and escape handling defined. A parser that hands a raw decoded array straight to business logic is a finding. Name the boundary in the finding as `producer → consumer`.

**An anchor that is not the end of the string is a validator with a hole.** In PCRE, `$` matches
*before a trailing newline* unless the `D` modifier is given, so `"Threads_connected\n"` passes a
`^[A-Za-z0-9_]+$` identifier check unchanged and reaches whatever the identifier is interpolated
into. Use `\z`, or `D`. The same trap has a name in most regex flavours and a different default in
each, so for every validator on the boundary, ask what its anchors actually anchor to — and note
that a validator exists at all only where a value could not be bound as a parameter: `SHOW`
statements, for one, accept no placeholder on either MySQL or MariaDB, which is exactly how a
hand-rolled identifier check comes to exist on a path that would otherwise never need one.

**S11.1 — the byte/character boundary, which a monolingual test suite cannot see (2026-09-24,
proved).** The boundary this sweep is usually about is between two systems. This one is inside a
single expression, and it is invisible until the content stops being ASCII.

`preg_split('/\R/', $text)` — PCRE's any-line-ending escape — **without the `u` modifier also
matches the raw byte `0x85`**, which is not a line ending in UTF-8 at all but an ordinary
continuation byte inside Traditional Chinese and Japanese characters. Run on `充全測試` it returns
**four fragments**: 充 is `e5 85 85`, so both of its continuation bytes are eaten as separators and
the character is cut into three pieces; 全 is `e5 85 a8` and loses one. The text is not
mis-split, it is **destroyed**, mid-codepoint, silently. With `/u` the same call returns one part.
An English corpus exercises none of it and every test written over one passes.

**And the obvious hardening removes the only evidence, which is what makes this worse than
ordinary silence.** Print the fragments rather than counting them and the four are
`[e5] [] [e5] [a8e6b8ace8a9a6]` — **one of them is empty**, and 充 has not been cut into pieces
that could in principle be rejoined: it is gone, leaving a bare `e5` and an empty string where its
two `0x85` bytes were. That empty fragment is the single visible trace that anything went wrong.
It is also exactly what a careful author discards on purpose — for a line parser,
`PREG_SPLIT_NO_EMPTY` or an `array_filter` over blank lines is the *correct-looking* idiom. Apply
it and three plausible non-empty “lines” come out of a four-character string, with no anomaly left
to notice and a part count nothing would call unreasonable. **So when looking for this class, check
what the code does with empty results before concluding a byte-level split is safe:** a defensive
filter downstream converts a detectable corruption into an undetectable one.

The shape generalises well beyond `\R`. **Any byte-oriented operation on text is a candidate
corruption site the moment the content is not ASCII** — `substr`, a truncation for a column width
or a preview, a padding, a length check used as a limit, a reverse, a regex without `u`, a
case-fold, a sort. Each is correct on its own terms and each is silent by construction, and the
symptom surfaces arbitrarily far downstream as mojibake, so the diagnosis starts in the wrong file.

**Method.** For every locale the system serves, take one non-ASCII string from its own content and
ask of each text operation on the path: *does this operate on bytes or on characters, and has it
been exercised against this string?* Where the language has both families — `strlen`/`mb_strlen`,
`substr`/`mb_substr`, a regex with and without `u` — the byte form on user-facing content is a
finding unless the byte semantics are what was wanted and the comment says so.

**The wider rule this is an instance of, and it is the one worth carrying:** a defect whose **test
surface and production surface differ by locale** is not reachable by adding coverage in the
language the suite is written in. A trilingual system needs at least one non-ASCII fixture on every
text path, for the same reason S21's non-emptiness sibling exists — the green run in English is not
evidence about `zh-TW`.

**And when a guard and the right engineering answer coincide, record the reason, not the
compliance.** The case that surfaced this parsed a `.env` file, where CRLF cannot be promised —
`.gitattributes` pins line endings *inside* the repository, not on a file hand-edited on a server —
so a line-ending-agnostic split is correct there independently of any lint rule. A comment saying
"a test requires this" invites the next person to simplify back to the broken form; a comment
saying *why* does not.

## S12 — Cascade, partial failure and retry storm

For every outbound call (gateway query, logistics API, mail, storage, queue) and every inbound retry source (provider re-sends a notification, cron re-runs, customer refreshes), answer: what happens when the call fails half-way, times out, or succeeds after the caller gave up? Is there a per-step timeout? Is retry bounded with backoff, and is the retried action idempotent? Is there a circuit breaker or a degrade path (offer fewer methods, queue for later) rather than a crash or an unbounded loop? A retry that repeats a non-idempotent write, or a failure in one step that silently leaves an earlier step's side effect in place, is a finding. Trace the chain end to end and state which downstream effect the upstream failure produces. **A wait with no ceiling is a leak.** Any order, parcel or payment that waits for an external signal the environment cannot guarantee (a callback the sandbox cannot emit, a store-to-store status push with no documented retry, a counter payment) must have a ceiling that routes to a human queue — never an automatic reversal, because the parcel may be at the counter — and a sweep that lists what is waiting. State the ceiling and the queue; "the callback will come" is not a design (§3 fulfilment rule 9). **A browser-returned result is not a server channel.** Gateways deliver a result twice: once to the customer's browser (a return URL, a `ClientBackURL` / `ReturnURL` form post) and once server-to-server (a `NotifyURL`), with different fields at different moments. Anything dispatch depends on — a consignment number, the chosen store, a virtual account — must reach the shop by the notify channel or a poll of the vendor's query API; a design that takes it only from the browser post loses it the moment the tab closes (§3 fulfilment rule 12).


**S12.1 — the failure-mode table.** Naming the failure is half the sweep; the other half is the
row. For every outbound call and every step of a money flow write one row: **failure mode**
(timeout, 5xx, refused, half-written, crash between step *k* and *k+1*, late success after the
caller gave up), **effect** (which downstream state is now wrong, in the system's own words —
"customer charged, no order row"), **detection** (which detector notices, and its liveness — S20),
**surface** (where a person sees it — S22; "log line" is not a surface), **recovery** (retry with
the idempotency key, compensate, or route to a human queue — S16; never an automatic reversal of
money). A row with an empty detection or surface cell is the finding, whatever the recovery says.
The table goes in the report; the six perturbations of S23 feed its rows for every inbound arrival.

**S12.2 — the failure shapes a cache and a chain of calls have names for (2026-09-17, from the
Taobao architecture-evolution notes).** Wherever the map shows a cache in front of the catalogue,
the cart or the session store, ask for the four by name — **penetration** (a product that never
existed, asked for forever, every miss a database read), **breakdown** (one hot product expiring
while a thousand requests wait on it), **avalanche** (many keys expiring together because a deploy
set them together), **hotspot** (one product so hot that one node carries the shop) — and for each,
what the shop does: a negative entry, a single-flight rebuild, staggered TTLs, a local tier. A
cache with none of these is a database with a delay in front of it. Wherever the map shows a chain
of calls — the checkout calling the gateway calling the bank — ask two things the retry-storm text
assumes and never states: **each hop's timeout is shorter than its caller's** (the reverse means
the checkout gives up first, the gateway keeps charging, and the money paths meet §8h), and
**concurrency toward a slow dependency is bounded** (a bulkhead), so one slow gateway cannot hold
every php worker and take the catalogue down with it. **And the degradation table, which is the
shop's own version of this sweep**: one row per dependency — gateway, carrier, search, mail, the
cache, the image store — *it is down → what the customer sees → what the operator sees → what
still sells*. "The gateway is down → the Pay button explains and the order waits → a red panel
on the order list → the catalogue and the basket" is a design; "→ a 500 → nothing → nothing" is
a finding graded on the money it loses. A row nobody can fill is a dependency nobody has thought
about failing.


**S12.3 — the two-step mutation whose restore is conditional on arriving at step two (2026-09-24).**
S12 asks what a half-way failure leaves behind. The commonest instance in operational tooling is a
script that **puts the system into a state and takes it out again**: close the shop, prove the
maintenance page, reopen; disable the index, backfill, re-enable; revoke the key, rehearse the
rotation, restore. If it dies in between — and it is a script, so it dies on a network blip, a
`Ctrl-C`, an OOM, a failing assertion halfway down — **the system stays in the first state**, and
nothing in the script is wrong when read top to bottom.

Three rules, in increasing order of how much they actually buy:

1. **The restore goes on an unconditional path** — a `finally`, a trap, a deferred call — never
   after the work, and never inside the branch that only runs on success.
2. **Announce what will be mutated before touching it**, naming the target, so a concurrent process
   or a person reading the log can tell a deliberate outage from a defect.
3. **Default to a disposable, isolated target, and put the shared or real one behind an explicit
   flag.** This is the one that survives contact with a tired person: safe-by-default beats
   safe-because-everybody-remembered-to-coordinate, and the moment a rehearsal needs coordination
   to be safe it will be run uncoordinated exactly once, on the day it matters most.

The tell when reading: a mutation and its inverse in the same function, with anything between them
that can throw, return early or be interrupted. Ask what the system looks like at that instant, and
who finds out.

**S12.4 — the self-inflicted vendor lockout: a reconciler that asks about orders the gateway never saw (2026-10-16).**
Some gateways punish the question "what happened to order X?" when X is unknown to them. NewebPay is the
worked example: repeated queries for a non-existent order trip `TRA10071`, a four-hour lock on the
query API (NDNF-1.2.5 p.95) — and during those four hours every **legitimate** reconciliation, settlement
check and "is this paid?" answer for the whole shop fails too. The shop does it to itself, by design, in
three ordinary ways: a poller that walks every `awaiting_payment` order including those abandoned
**before** the redirect (the gateway never received them); a reconciler pointed at a sandbox or shared
merchant id that also holds another environment's test orders, or the reverse; and a retry loop that
treats "no such order" as transient.

**Check every poller, reconciler, settlement job and operator "recheck" button that calls a gateway's
query API:**

1. **It queries only orders with a recorded gateway attempt** — a row written at redirect or form-post
   time naming the gateway, the merchant id and the environment. No attempt row, no query. An order
   that never left for the gateway is expired locally, not asked about.
2. **The environment is part of the key.** A stage query never carries a production order id and the
   reverse; the attempt row's environment must match the client's.
3. **One budget per gateway, shared by every caller** — cron, worker, admin button, CLI — counted in one
   place (a table or a lock-guarded counter), with a ceiling set below the vendor's documented threshold.
   Per-caller budgets add up to the lockout.
4. **The lockout code is a stop, not a retry.** On the vendor's lockout code every caller stops querying
   that gateway until the documented window passes, the stop is recorded with its expiry, and it reaches
   an order screen (S20/S22): "gateway queries paused until 15:40 — the gateway locked us out" is a
   state a person can account for; four hours of "unreachable" is not.
5. **"No such order" is an answer.** It ends the question for that order (expire, or route to a human
   if money may have moved by another channel); it never re-enters the queue on the next cycle.

**Grading.** A query path with no attempt-row guard on a gateway that documents a lockout: HIGH (the
shop can blind its own reconciliation for hours, during trading). No shared budget, or a lockout code
handled as a retry: HIGH. Lockout recorded but not shown: MEDIUM. Include the probe suites in the count:
a live sandbox probe that queries a deliberately unknown order is the same caller, and running it twice
inside the window is the lockout, not a signature fault.

Report line format: `S12.4 — Q gateway-query callers (cron, worker, admin, CLI, probes); guarded by an attempt row G/Q; environment-keyed E/Q; shared budget per gateway: yes/no; lockout codes handled as stop L of K documented; shown on an order screen: yes/no.`

## S13 — Orphan capability / designed-but-unbuilt

Three greps, one table. (a) For every class under the admin, control, settings or catalogue roots (payment-method matrix, carrier catalogue, shipping chains, fee tables), grep for a caller outside its own file and its tests; a control class with no page, controller or module that renders it is an orphan. (b) For every table column and enum added by a migration (`shipping_method`, `pickup_store_*`, `cod_*`, fee columns), grep for a writer in runtime code — checkout, admin, worker — not only a test; a column nobody writes is scaffolding, and scaffolding that a later reader treats as data is a finding. **Grep the identifier alone and read every hit — never the identifier plus an SQL keyword on the same line.** A column written by a multi-line `UPDATE … SET` whose `SET` sits six lines above the column name is invisible to `grep 'col.*SET'`, and most non-trivial SQL is multi-line. One pass reported a live column as having no writer anywhere and was one sentence from filing it as an orphan with five consumers treating it as scaffolding. **A false orphan costs exactly what a missed one does**, because it sends the next session to rebuild something that already works — so confirm an absence by reading the hits, not by trusting a narrower pattern that returned none. (c) For every design document, master plan or handoff note under `docs/` that names a component (a checkout method picker, a carrier admin page, an eligibility engine), check that the component exists on disk **or** that the gap register carries one row naming it as unbuilt with its blocker (vendor account family, 測標 approval, owner decision). Report each orphan with its three states — designed / coded / wired — and the owner-side blocker if any. A capability that is designed and coded but not wired, and whose absence the register does not record, is the most expensive shape of commerce gap: every document says shipping is handled and the customer has no way to choose how.

**S13.1 — a second hand-rolled copy of a list the shop already derives is a twin, and one of the two copies will rot (also an S5 shape, 2026-09-20).** A dashboard "everywhere else" index was a second, independently maintained map of the admin menu — seven headings covering about twenty of thirty-six pages, missing an entire desk (Customers) — sitting beside a proper map (`AdminNav::TABS`) that already enumerated every page correctly. Nobody wrote the dashboard index wrong; they wrote it once, from the menu as it stood that day, and it had no mechanism to stay current while the real menu kept moving. **Whenever a structure the shop already computes — a menu, a status table, a permission matrix, a route list — appears a second time as a literal, hand-typed list, grep for it.** It is an orphan capability already in progress even while both copies still agree, because the day one changes and the other does not, the second is silently wrong and nothing says so — a control-to-consumer gap (S5) where the "control" is the true source and the stale copy is a consumer reading the wrong one. The fix is never to edit the copy back into sync; it is to derive it, so there is exactly one place a future change can be forgotten.


**S13.1 — a grep proves the symbol resolves, never that it reaches the real thing (2026-09-25,
found by a cold run missing it).** The method above is three greps, and greps find a capability
with *no* caller. They do not find a capability wired to the **wrong store**, because every symbol
in it resolves and every call site is real. An operator command-line tool opened its
data store from a configuration key the configuration never set, so the lookup fell through to its
default and every invocation worked against a fresh, empty, immediately-discarded store. The
connect call exists. The config object exists. The command runs, prints a plausible empty result,
and exits 0. Nothing a grep can see is wrong.

An earlier run caught this by running the CLI in one process after enqueuing in another; a later
run, following the same doctrine, did not — because the doctrine asked for the greps and never
asked for that. **A capability found by initiative is a capability the next run will miss.**

So the orphan sweep has a fourth step after the three greps: **run the operator's own entry point
as a real process, against state something else created**, and check it sees that state. Enqueue
in one process and list in another; write through the admin and read through the CLI; create by
API and look on the screen. The defect class it catches has no grep signature at all — the
capability is present, called, and pointed somewhere nothing else is — and the only cheap way to
see it is that the thing one process wrote is missing from what the other reads. **The default a
missing config key falls back to is where to look first** (`:memory:`, `/tmp`, `localhost`,
`sqlite://`, a stub client): each is a working implementation of somewhere nothing else is.

**The general form of the false orphan (2026-10-12).** Every absence this sweep files — no caller, no
writer, no page — states its search boundary and what lies outside it (`evidence.md` §E5): DB triggers,
crontab and timers, workflow tools, other repos, names built from strings. And run the ledger the other
way: an obligation (§E3) with no owner is this sweep's finding even when no design doc names it, and an
obligation with **two** owners is S13.1's.

## S14 — Scope shadow

State the scope of this run in the first line of the report: whole shop, one subsystem, or one diff. When it is narrower than the VSM map, list the commerce domains on the map that were **not** walked this run — checkout, payment, shipping / fulfilment, refund, invoice, entitlement — and the date of the last run that did walk each (from the handoff or the register). A narrow-scope report that omits this list reads as shop-wide green and is itself a finding against the audit. Never let "0 findings" stand without the scope beside it.

### S14.1 — The launch plan is a scope claim, and an unmarked plan is a false one

S14 governs the audit's scope; the same failure lives in the launch plan, and costs more because
that document is trusted without re-reading.

1. **Enumerate tracks, not phases.** A shop's launch plan covered correctness, gateways and
   deploy — and omitted the catalogue migration (products, images, editorial copy from the old
   site) and the theming that **gated every end-to-end walk in a later phase**. Neither is code, so
   neither appeared in a plan written from the repository. For a shop, ask specifically: **is the
   catalogue actually migrated; are prices, stock and tax verified against the old system; are the
   provider accounts activated rather than merely created; who signs off the design; what physical
   or manual step (invoice books, packaging, carrier paperwork) has to exist on day one?**
2. **Three marks only** — done with evidence, open, or waiting on a named party with what it
   blocks. An item with no test and no citation is open, whatever it feels like.
3. **A dated external wait is not a task.** Gateway activation, carrier approval (測標), a
   support-desk reply, a bank's confirmation: record who, when, what it blocks and where the answer
   lands. An unrecorded wait looks exactly like work nobody did.

**Drift check:** a prerequisite outlives the decision that reversed it. One plan gated work on
pruning an asset tree; a later owner decision forbade deleting anything in it. Both were live, in
different files, and the stale gate was still stopping work. When a decision reverses an
assumption, grep the plans for the gate it created.
