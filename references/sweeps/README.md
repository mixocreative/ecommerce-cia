# Sweeps — index and method

> Split from the former `references/sweeps.md` on 2026-11-10, the cut `cia` took on 2026-11-09. Text unchanged; the sweep-to-file map is at the foot of this file.

# §0.9 Mandatory Sweeps — Cross-Boundary Invariant Violations a Green Suite Does Not Catch

Loaded by `ecommerce-cia` at Step 3, read in full, every run. Sweeps S1–S24 each end in one report line; a sweep with no line in the report was not done. Each sweep line names its sites, not a count: a path list (`path:line` or `path` per site) that the reader can open. `swept, 0 findings, 14 sites` is a claim; the fourteen paths are the evidence, and a line without them is the vacuous pass this skill exists to catch (S8), filed by the auditor. **Add one quoted line from one of those sites** — the predicate, the catch, the setting read, verbatim with its `path:line` — as proof the site was read and not merely listed by a grep.

**A sweep line is an index, never a place to report.** When the line says something is wrong at a site (two readers of one value disagree, a check is missing, a write has no predicate), that site is a numbered finding and the line names its ID (`S1 - sites: ... - F7`). A defect written only on a sweep line is unreported: the owner acts on findings, and the answer keys count it as missed (2026-11-10, RUNS: a cold run described a defect on its sweep line, filed nothing, and lost the row).

Every item below was a real commerce gap that sat under a green fast suite, a clean static analyser and a clean linter, and was found only by a second auditor tracing the code by hand. None is optional. Each sweep produces either a numbered finding or an explicit "swept, 0 findings, N sites inspected" line in the Step 7 report. A sweep with no line in the report was not done.

## Step 0 — Map the codebase onto the Viable System Model before sweeping

The sweeps are not a grep list; they walk the channels of a VSM map of *this* codebase. Before S1 runs, produce and report a table with one row per module, directory, service, cron job, config surface and test suite:

| Component (path) | Primary VSM system | Channels (`producer → consumer`, with the system on each side) |
|---|---|---|

Systems: **1** primary operations (the code that does the work: checkout, order, fulfilment, request handlers); **2** coordination / anti-oscillation (locks, queues, idempotency keys, deadlines, ordering); **3** control (settings, feature flags, admin pages, config files, the values that tell System 1 what to do); **3\*** independent audit (test suites, verification scripts, reconciliation, probes); **4** intelligence / environment (vendor specs, external APIs, webhooks, callbacks, imports); **5** policy / identity / emergency (defaults, catch-block posture, kill switches, fail-closed rules). Report the map as line 2b / 3b of the Step 6 report: "VSM map: N components, M channels". Missing map = the sweeps had no site list and are not done.

Every sweep then enumerates its sites from the map's channels, and each defect class is a broken channel between two systems (column four of the taxonomy table below):

- every **System 3 → System 1** channel (a setting, flag, admin control or config value → the runtime code that must obey it) is a site for S5 and S6;
- every **System 1 → System 1 across time** handoff (value frozen at one step, read at a later step; SELECT then UPDATE) is a site for S1 and S2, and its missing System 2 coordinator is the finding;
- every **System 4 ↔ environment** boundary (vendor field, external payload, model output) is a site for S4 and S11;
- every **System 3\* → System 3** channel (what the suite or probe actually verifies about the control state) is a site for S7, S8 and S10;
- every **System 5 default** (catch block, fallback, absent kill switch) is a site for S3 and S12;
- every rename or refactor is a **System 1 ↔ System 1 binding** and a site for S9.
- every **design document, master plan, handoff note or migration** that names a component, table or control is a **System 3 → System 1 promise** and a site for S13;
- every audit whose scope is narrower than the map (one diff, one module) is a **System 3\* channel narrower than the system** and a site for S14;
- every order, shipment, refund and invoice that crosses **customer → operator → logistics provider → payment gateway** is the site for S15, the sweep this skill exists for: four parties hold four partial truths about one order, and the shop's row claims to speak for all of them.

A channel on the map with no sweep site named against it is unswept; say so in the report line rather than omitting it. The reverse also holds: a sweep whose site set on the map is empty — no hosted surface for S17, no scheduled detector for S20, no operator screen for S22 in a library or CLI — reports `no sites on the map` in one line, with the map row that proves it, and does not spend the run proving an absence twice.

## Taxonomy

**These are cross-boundary invariant violations (integration-level, emergent defects).** No single function is wrong; the defect lives in the relationship between two correct pieces, across time or across a layer. Code review sees functions and misses them by construction. Finding them requires behavioural tracing: follow one value from where it is written to every place it is later read, and follow one control from the admin screen or config file to the line of code that obeys it. Name the class in every finding:

| Term | Meaning | Sweep | VSM channel that is broken |
|---|---|---|---|
| **TOCTOU race** (time-of-check to time-of-use) | a predicate checked at one step and silently dropped at the step that acts | S2 | System 1 → System 1 across time, no System 2 coordinator |
| **Temporal coupling / stale snapshot** | a value frozen at one moment while a later reader re-reads live state | S1 | System 3 → System 1 read at two different times |
| **Semantic drift** | code's understanding of an external field diverges from the vendor's source of truth | S4 | System 4 ↔ environment (vendor) |
| **Dead control / broken control-to-consumer wiring** | an admin toggle, flag or setting that no runtime path reads | S5 | System 3 → System 1 command channel absent |
| **Fail-open default** | an error path that proceeds as if the failed read had succeeded | S3 | System 5 policy default missing or wrong |
| **Vacuous pass** | a suite that reports OK because the meaningful tests skipped or never ran | S7, S8 | System 3\* reading System 3's own conclusion |
| **Deferred-work residue** | a comment promising a follow-up that never landed | S6 | System 3 → System 1 channel promised, never built |
| **Rename residue** | a consumer still bound to the old name after a rename | S9 | System 1 ↔ System 1 binding broken |
| **Diagnosis without probe** | concluding a cause from an error message instead of a direct check | S10 | System 3\* without an independent channel |
| **Boundary schema drift** | a payload crossing a boundary is acted on before its shape and type are validated | S11 | System 4 ingress unvalidated |
| **Cascade / retry storm** | one step's failure or retry propagates as crash, duplicate write, or orphaned side effect | S12 | System 2 anti-oscillation absent, System 5 no circuit breaker |
| **Orphan capability / designed-but-unbuilt** | a class, table, column, admin control or design document that exists with no caller, no writer, no page and no gap-register row — capability promised, channel never built | S13 | System 3 capability with no System 1 consumer and no System 3\* register entry |
| **Scope shadow** | an audit run on one diff or subsystem whose report reads as whole-system green | S14 | System 3\* channel narrower than the map it reports on |
| **Corner disagreement / unreachable capability** | customer, operator, logistics provider and payment gateway describe one order differently, or a built payment or delivery method is not offerable under the shipped seed | S15 | System 1 ↔ System 3 ↔ System 4, all four corners of one order |
| **Hosted-surface control** | a shop setting claims to restrict a choice the buyer makes on the gateway's or carrier's own page, where the request cannot express it and the provider's back-office decides | S17 | System 3 control whose System 1 is on somebody else's server |
| **Sampled where it should have been enumerated** | one payment or delivery cell read and the conclusion generalised to the grid; a later finding in that class proves the method wrong, not just the answer | S18 | System 3\* measuring a subset and reporting on the whole |
| **Environment constraint never crossed** | a gateway's or carrier's requirement on the host — fixed egress IP, cron, persistent disk, inbound reachability — and the launch host's capabilities are both written down and never multiplied; usually because the requirement was filed as an owner checklist task | S19 | System 4 reading the environment, never compared with System 3's plan for it |
| **Service-variant confusion** | 取貨付款 vs 取貨不付款, platform vs direct, B2C vs C2C — same carrier, different caps, fees, templates and payout rules, audited as if one | S18 | System 4 read at brand resolution when the environment distinguishes services |
| **Blind instrument / dead watchdog** | the settlement reconcile, the capture sweep, the parcel trace or the retention purge stopped running or verified nothing, and the report looked identical to a clean one | S20 | System 3\* with no liveness signal — the channel that reports on the others, unmonitored itself |
| **Unrendered / undesigned surface** | a state the system can reach has no screen, or one nobody has rendered, or one that cannot be dismissed by a person - so an exception is caught, logged, and decided by nobody | S22 | System 1 producing an event System 3 has no channel to see |
| **Vacuous or too-late proof** | a test asserting emptiness passes because the subject returns nothing for an unrelated reason; or the guard exists but sits so deep in a slow suite that nobody reaches it | S21 | System 3\* instrument that reports without measuring |
| **Order-dependent outcome / unhandled arrival** | two arrivals that can interleave leave a different final state depending on which came first; or an arrival that can come twice, late, early or never has no handler for that case | S23 | System 2 ordering absent; System 4 arrival with no System 1 branch |
| **Self-agreeing fake** | the only test on a boundary feeds the parser a fixture the parser's author wrote, so both sides of the contract are ours; or a fixture with no authority citation or version | S24 | System 3\* measuring System 1 against itself instead of System 4 |

When the user asks for "code integrity", "audit", "review the wiring", "trace state across time", "every control to its consumer", or names any term above, the sweeps are the first thing that runs, before any function-level reading.

### Reading these sweeps at the size you actually have: mechanism clauses and instance clauses

Two cold runs on 2026-09-24/25, on fixtures of a few hundred lines, independently reported the
same friction and proposed the same fix. **A sub-clause that names a mechanism earns its reading
at any size; a sub-clause that names a domain instance costs a reading and returns nothing where
its precondition does not hold.** The node run's words: S16.1's lettered rules "were directly
load-bearing" — they name a *distinction* (a transition guarded by its own predicate versus a
value edit that is not) that applies to any state machine — while S11.1's byte/character trap was
"pure noise — could not find a site no matter how carefully I looked" on an ASCII-only fixture.

So every sub-clause below that assumes something about the system carries its **precondition in
the first sentence**, and a run that does not meet it writes one line saying so and moves on.
`no sites on the map: <the map row>` is the report format for exactly this, and using it is not a
skipped sweep — it is the sweep, answered.

The three that cost the most reading at small size, named by the runs rather than guessed:
**S11.1** (needs non-ASCII content), **S18.1** (needs a vendor manual or an external authority
document), and **S22.1–S22.9's convention library** (needs an admin surface of more than a few
screens). None of them is wrong; all three are written for a system an order of magnitude larger
than a fixture, and a small run should skip them **by rule**, having checked the precondition,
rather than by reading all of it and deciding.

**This is a rule about reading order, never about coverage.** A precondition that is *unverified*
is not a precondition that is absent: a run that has not looked for non-ASCII content has not
established that there is none. Check the precondition, then skip — the two steps are the whole
of it, and the second without the first is S14 scope shadow.

---

## Which file holds which sweep

| File | Sweeps | Channel it audits |
|---|---|---|
| `01-state-and-boundaries.md` | S1–S5 | snapshot reads, TOCTOU, fail-open catches, vendor field semantics, dead controls |
| `02-tests-cascades-scope.md` | S6–S14 | deferred-work residue, skipped and unrun tests, rename residue, environment truth, boundary contracts, cascades, orphan capabilities, scope shadow |
| `03-flows-and-terminal-states.md` | S15–S17 | the four-corner walk, terminal-state accountability, the hosted surface |
| `04-enumeration-environment-liveness.md` | S18–S21 | the provider-contract matrix, host requirements, liveness of the safety net, the suite as instrument |
| `05-surface-completeness.md` | S22 | step × outcome × audience, dead buttons, unrendered screens |
| `06-event-flow-and-contracts.md` | S23–S24 | event flow and arrivals, contract tests at boundaries; the folder's reading receipt |
