# Evidence — obligations, authority, unknowns, bounded negatives (§E1–§E11)

Loaded after `reporting.md` and before the first finding is graded; in build mode, before the proof
is written. Shared verbatim by `cia` and `ecommerce-cia` (change both in the same commit, exactly as
`browser-walks.md`).

**Why this file exists (2026-10-12).** The ledger in `reporting.md` §11a says what the run can
**prove** about each capability the *map* found. It does not say what the *owner asked for*, and the
gap between those two is where the most expensive defects live: a promise with no code behind it, a
promise with two pieces of code behind it that disagree, and code behind which there is no promise
at all. Reverse engineering has to bridge exactly that gap with no source and no author to ask, so
its tools for it are strict; the rules below are borrowed from
[REA](https://github.com/morluto/rea) (its obligation ledgers, authority comparability, unknown
registry and fail-closed aggregation) and restated for an audit that *does* have the source and
still cannot trust it.

The direction of travel: **intent → obligation → owner → verifier → artefact.** The map in
`sweeps.md` step 0 walks the system from the code outward; this file walks it from the promise
inward. A run does both, and the two meet in the ledger.

---

## §E1 — Every claim is tagged: OBSERVED, INFERRED or UNKNOWN

Every factual sentence in a finding's Evidence field, in the map, and in a ledger row's fourth column
carries one tag:

- **OBSERVED** — this run produced the artefact that shows it: a command's output, a row read back,
  a response captured, a test run line. Cite the artefact path.
- **INFERRED** — reasoned from observed facts: "the handler is registered, so this route reaches it";
  "this `UPDATE` has no status predicate, so two callers can both win". Name the observed facts it
  rests on.
- **UNKNOWN** — not established either way. Goes to the unknown register (§E4) with the evidence that
  would settle it.

Reading source is an observation **about the source**, never about behaviour: "line 48 reads
`$settings->guest_checkout`" is OBSERVED; "a guest cannot check out when the switch is off" is
INFERRED until a run shows it. `doctrine.md` §1.2's CONFIRMED grade needs at least one OBSERVED fact about
behaviour; a chain of INFERRED links is HIGH-CONFIDENCE at best, however tight it reads.
**A static read never observed an execution, and a sentence that implies it did is a false claim
about the audit itself.**

## §E2 — Authority: who is allowed to close a claim

Evidence has a strength, and a claim can only be closed by evidence at least as strong as the claim.

| Level | Authority | Typical artefact | Can close |
|---|---|---|---|
| **A0** | Read | `path:line` quoted | claims about what the source *says* |
| **A1** | Unit | a test with fakes / stubs / mocks, in-process | the unit's own logic, given its inputs |
| **A2** | Integration | a test against the real store, framework, filesystem or queue | the unit plus its real neighbours |
| **A3** | Process | the built system driven through its front door: HTTP, the real form, the CLI, a browser | what a user or operator can do and see |
| **A4** | Deployed | the same, against the build actually served, identity matched (§E9) | what *this release* does |
| **A5** | Counterpart | the other side's own behaviour: vendor sandbox, published worked example, the partner's validator | that both sides agree |

Rules, each one a way a green check closed a claim it could not see:

1. **Every obligation (§E3) and every ledger row names the authority it requires.** "Admin sees a
   badge for a stuck order" requires A3. "The callback signature verifies" requires A5. "Stock never
   goes negative under concurrent checkout" requires A2 at least, A3 for the PASS that launches.
2. **A verifier closes a claim only at or above its required authority.** A unit test with a mocked
   gateway (A1) cannot close "the callback works" (A5): it proves the handler agrees with the mock,
   which is `sweeps.md` S21's self-consistent codec at a different height. A green unit suite cannot
   close a process claim; a sandbox walk cannot close a production-only claim (live keys, real
   settlement) and records it UNVERIFIED with that reason.
3. **Lower-authority evidence is still evidence — for a lower claim.** Write it on the row as what it
   is ("A1: handler maps `Status=SUCCESS` → paid") and leave the row open.
4. **The ledger in `reporting.md` §11a gains an Authority column:** the level required, then the level
   the cited artefact reached. A PASS where the second is lower than the first is a promotion, and
   §11a forbids promotions.

## §E3 — The obligation ledger: from what was promised to the line that keeps the promise

**Rows come from intent, not from code.** Sources, in order of weight: the owner's own words (in the
conversation, the register, a handoff); the invariant register (`doctrine.md` §8.0); design docs,
plans and ADRs; the vendor document cells S18 enumerates; and the promises a screen makes to a person
("refund within 7 days", "out of stock items cannot be ordered", a toggle labelled "Allow guest checkout").

| Field | What it holds |
|---|---|
| **ID** | `layer.family.name`, stable, with a version — `checkout.stock.no-oversell@1`, `admin.alert.stuck-order@1`, `gateway.newebpay.notify-idempotent@1` |
| **Statement** | one sentence that can be false (`doctrine.md` §8.0) |
| **Intent source** | the quote and where it lives — owner message, `docs/ARCHITECTURE.md` D7, manual §4.2, the screen |
| **Required authority** | A0–A5 (§E2) |
| **Case kinds** | which ways of being asked it must survive, from: `valid` · `refused` · `malformed` · `duplicate` · `out-of-order` · `late` · `concurrent` · `cancelled` · `fault-after-first-write` · `teardown` |
| **Owner** | exactly one `path:symbol` that keeps the promise |
| **Ingress type** | for anything that crosses a boundary: the parser / schema / typed DTO that validates it (S11) — or `none`, which is a finding |
| **Verifier** | the test or probe that proves it, **and names the obligation ID** (test name, docstring, or probe argument) |
| **Status** | `OPEN` · `CLOSED` · `FAILED` · `BLOCKED` · `OUT-OF-SCOPE`, with the artefact paths |

**Closure is strict.** An obligation is `CLOSED` only when: it has exactly one owner; every listed case
kind has an artefact from *this run* at or above the required authority; the verifier names the ID
and passed this run; no contradiction (§E7) touches it; and no unknown (§E4) is attached. Anything
less is `OPEN`. `BLOCKED` (the environment or a vendor stopped it) and `OUT-OF-SCOPE` (the owner
said so, quoted) are recorded and **never counted as verified** — a report that sums them into the
closed count has done what §E6 forbids.

**What the ledger finds by itself — no reading required, just the table:**

| Shape | Meaning | Sweep |
|---|---|---|
| obligation with **no owner** | promised, never built | S13 orphan, S6 deferred work |
| obligation with **two owners** | two pieces of code each believe they keep it, and will disagree | S13.1 second hand-rolled map, S9 |
| owner with **no verifier** | kept by luck | S8, S21 |
| verifier **below required authority** | proved against itself | S21, S24 |
| verifier that **does not name the ID** | nobody can tell which promise a red test broke | S21 |
| case kind with **no artefact** | the happy path passed, the capability did not | `reporting.md` §11a PARTIAL |
| **unowned behaviour** — code on the map that keeps no obligation | the system does something nobody asked for (POSIWID) | listed for an owner decision, not graded |

The last row is the reverse bridge. It is not automatically a defect — a cache, a retry, a log — but
a code path that **writes a primary quantity, sends a message, or charges money** with no obligation
behind it is presented to the owner as a question: *did you want this?*

**Obligations and the §11a ledger are two views of one system.** §11a's rows come from the map
(what the system *is*); these rows come from intent (what it was *meant to be*). Each obligation
links to the capability row its owner sits in. A capability with no obligation pointing at it is
unowned behaviour; an obligation with no capability is an orphan. **The audit is the join.**

In **build mode** (`build-standard.md` §3) the obligation row is written first, before the proof:
statement, case kinds, required authority, the one owner the new code will be. The proof's test names
carry the ID. The row closes from the proof's output, never from the code just written.

## §E4 — The unknown register: every open question carries its next step

Every UNKNOWN (§E1), every UNVERIFIED and UNPROVEN ledger row, and every OPEN obligation is one entry:

| Field | Example |
|---|---|
| **Question** | Does the nightly export skip rows edited while it runs? |
| **Authority needed** | A2 (real store, two processes) |
| **Next evidence** | the exact command or action: start the export, edit one row mid-run from a second process, then diff the file against the table |
| **Who can supply it** | the agent (rung 1–4) · the owner (rung 5, the one action) · the vendor (with date asked) |
| **For / against** | artefact paths that lean each way |
| **Blocks** | the obligations and findings that stay open until it resolves |

The register is written to where the next session will trip over it (`reporting.md` §13, "nothing
leaves the room unrecorded") — the project's handoff or gap register — so a resumed run **starts from
the next evidence**, not from re-reading. An unknown is resolved only by OBSERVED evidence at the
named authority; argument closes nothing.

## §E5 — Negative claims carry their search boundary

"Nothing reads this setting", "no other writer", "the job is never scheduled", "swept, 0 findings" —
every absence is a claim about **the whole of a search space**, and is only as good as the space.
So every negative claim states, in one line:

```
ABSENT within: roots <src/, app/, bin/> · patterns <guest_checkout, 'guest_checkout', GUEST_CHECKOUT> · read every hit: yes
  outside the boundary: <vendor/, generated/, DB triggers, crontab / systemd timers, n8n or Zapier flows,
  other repos or services, config outside the repo, names built from strings or reflection>
  boundary complete for this claim: yes | no — <which outside item could still hold it>
```

**If any item outside the boundary could hold what was not found, the claim is UNKNOWN, not
ABSENT.** Missing coverage is unknown, not absence. A database trigger is a writer; a crontab line is
a scheduler; a workflow tool calling a webhook is a reader. `sweeps.md` S13 learned the narrow form —
a multi-line `UPDATE … SET` hid a live writer from a too-clever grep — and this is the general form:
**a false absence costs exactly what a missed presence does**, because both send the next session the
wrong way.

## §E6 — Incomplete output, and the aggregation that never rounds up

1. **Output that was cut is a fragment, not a result.** A tool or client that truncated a result — a
   capped grep, `head`, a paged API, a log that rotated, a terminal that dropped lines, a response
   marked "… N more" — returned *part* of the answer. Say `TRUNCATED` on the line, narrow the query or
   page through it, and never parse a preview as the whole. A count taken from a truncated listing is
   not a count. Applies to the agent's own tool calls first: the most common truncated output in an
   audit is the auditor's.
2. **Fail-closed aggregation.** When results roll up — sweep lines into Step 2, ledger rows into a
   verdict, obligations into "ready" — any of `FAIL`, `UNKNOWN`, `UNPROVEN`, `UNVERIFIED`, `PARTIAL`,
   `TRUNCATED`, `SKIPPED`, `UNSUPPORTED`, `BLOCKED` in the group makes the group **not PASS**. They
   never average out, and a green majority does not outvote one of them. The summary line states the
   count of each.

## §E7 — Contradictions are recorded, not resolved by preference

When two sources disagree — the manual and the sandbox, the docs and the code, a comment and the line
under it, two observers of the §12 ladder, the code and the owner's stated rule — write a
contradiction row before doing anything else:

| Claim | Source A says (authority) | Source B says (authority) | Obligations affected |
|---|---|---|---|

Then: **block only the affected obligations and findings, and keep going** with everything the
contradiction does not touch. A higher authority wins **only within its own scope**: the sandbox's
behaviour beats the manual *for the sandbox*, and production may still differ, so the production claim
stays open. Never pick the convenient side silently, and never let one contradiction stop the audit
of unrelated channels. A contradiction the owner must decide goes to the owner-decisions block
(SKILL §0.11 item 5) with both quotes.

## §E8 — Order is a set of constraints, not a sequence

For anything concurrent or asynchronous — callbacks, webhooks, queues, two workers, a browser return
racing a server notify (`sweeps.md` S23) — write the expected behaviour as **partial-order
constraints**, not one exact sequence:

```
exactly one terminal state per order
paid  ≺  shipped                     (≺ = must happen before)
notify and browser-return: either order; the second is a no-op
cancel ≺ the single terminal response, or cancel is refused — never both
```

A test that asserts one total order over events the system does not order is over-specified: it is
flaky when it fails and vacuous when it passes (it proves the order the test happened to produce). When
an observed trace breaks a constraint, report the **first divergence** — the earliest event that
violates a constraint — not the last symptom.

## §E9 — Artefacts record what they observed: deployed is not HEAD

Every A3–A5 artefact records the identity of the thing it ran against:

- the commit (`git rev-parse HEAD`) and whether the working tree was clean;
- what was actually served: the hash of the main script and stylesheet bundles (`sha256` of the
  fetched bytes), their `?ver=` / build-id query, the plugin / theme / package versions the app reports;
- the schema or migration version the store is at.

A PASS whose observed identity differs from HEAD is **UNVERIFIED for HEAD**, with "stale deploy" as
the reason. A served bundle that does not match a fresh build of HEAD is itself a finding: either the
deploy is behind (S19/S20, nobody is told) or the build is not reproducible. Source maps, when served,
are compared against the repo's sources the same way.

## §E10 — Reverse trace: start from what the system visibly does

Use when the intent exists only in behaviour — "it does X and nobody knows why", "how does this
feature actually work", "make ours behave like theirs" — or when part of the system is closed:
a minified vendor SDK, a plugin zip that is not in the repo, a SaaS step in the middle of the flow.

1. **Seed** from an observation: a screen state, a recorded request, a log line, a row that changed.
2. **Trace inward** one edge at a time: entry point → handler → every state write → every message or
   call out → the result the seed showed. Tag every edge OBSERVED or INFERRED (§E1); keep unresolved
   edges in the trace as `?`, never drop them to make it read cleanly.
3. **Capture the traffic.** Export a HAR from the walk's browser (or the proxy) for the flow, group
   requests by method and path template, and compare each field against the authority (S4, S18) **and**
   against what the code believes it sends. A field present in the traffic and absent from the manual,
   or the reverse, is a contradiction row (§E7). Strip cookies, authorisation headers and card data
   before the HAR is stored as an artefact.
4. **Closed parts.** For shipped artefacts that are not in the source — bundles, Electron apps, native
   binaries — a reverse-engineering tool such as REA (`npx rea-agents setup`; rea.tools) returns modules,
   routes, IPC and call relationships with their evidence. Only for software the owner owns or is
   authorised to examine; never for the repo's own source, which is read directly. A bundle observed at
   runtime does not prove every module in it executed.
5. **Turn the trace into obligations.** Each behaviour the owner confirms they want becomes an §E3 row;
   each they did not want becomes a finding or a question.

## §E11 — A narrow question gets a checklist, and the checklist gets revisited

For any request narrower than the full protocol ("why does X happen", "does Y work", "check the
refund path"): before the first tool call, write the questions and the evidence each needs; at the
end, mark each **answered** (with the artefact), **partial** (with what is missing) or **unresolved**
(into §E4). A bounded search stays bounded in the reply (§E5). Never describe an investigation as
complete while a question on its own list is open.

---

## Report lines (Step 6 in cia, Step 7 in ecommerce-cia)

```
Obligations (evidence.md §E3): O from intent — C CLOSED / P OPEN / F FAILED / B BLOCKED / S OUT-OF-SCOPE; no owner N, two owners T, no verifier V, below authority L; unowned behaviours U (listed for owner)
Unknowns (§E4): N open, each with next evidence; contradictions (§E7): K, blocking J obligations; truncated outputs re-run: R
```

A run that cannot fill these lines says which part it skipped and why; a missing line is read the same
way a missing sweep line is.

---

**Reading receipt: _a promise needs one owner and a witness_.** Quote this phrase on the report's receipts line (Step 6 in cia, Step 7 in ecommerce-cia) to show this
file was read rather than inferred from the skill's index. It appears nowhere else.
