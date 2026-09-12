# §0.9 Mandatory Sweeps — Cross-Boundary Invariant Violations a Green Suite Does Not Catch

Loaded by `ecommerce-cia` at Step 3, read in full, every run. Sweeps S1–S22 each end in one report line; a sweep with no line in the report was not done. Each sweep line names its sites, not a count: a path list (`path:line` or `path` per site) that the reader can open. `swept, 0 findings, 14 sites` is a claim; the fourteen paths are the evidence, and a line without them is the vacuous pass this skill exists to catch (S8), filed by the auditor. **Add one quoted line from one of those sites** — the predicate, the catch, the setting read, verbatim with its `path:line` — as proof the site was read and not merely listed by a grep.

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

When the user asks for "code integrity", "audit", "review the wiring", "trace state across time", "every control to its consumer", or names any term above, the sweeps are the first thing that runs, before any function-level reading.

## S1 — Snapshot-vs-live reread (temporal coupling / stale snapshot)

For every value persisted at a moment in time (payment deadline, reserved stock, offered payment methods, price, tax rate, shipping quote, coupon eligibility), enumerate every later reader of the same concept. Classify each reader as "reads the snapshot" or "re-reads live settings/config". Any pair where a later reader re-reads live while an earlier writer froze a snapshot is a finding, because the two can disagree after an admin change or a config edit. Example: a reservation deadline computed from settings at placement, then a payment page that re-reads the enabled methods on every GET and offers a days-long method against a 30-minute hold.

## S2 — Select-then-act predicate loss (TOCTOU race)

For every worker, cron, or batch that SELECTs candidate rows and then mutates them one by one (expire unpaid, release stock, void invoice, revoke entitlement, retry notification), read the per-row UPDATE/DELETE. The mutation's WHERE clause must re-state the full selection predicate, not only the status column. A predicate that is checked at SELECT and dropped at UPDATE is a time-of-check/time-of-use finding: a callback that lands between the two steps (deadline extension, payment arrival, manual hold) is silently ignored.

## S3 — Catch-block failure posture (fail-open default)

For every `catch` in a payment, checkout, entitlement, refund or inventory path, write one line: what is caught, what the code does next, and whether that is fail-open (proceeds as if the read succeeded) or fail-closed (refuses the action). Fail-open on a configuration or feature-flag read in a money path is a finding unless an owner decision in project memory or an ADR names that exact choice and its reason. "Default on because that was the pre-migration behaviour" is a reason to record, not a reason to keep. **A secret derived from the environment's identity is a time bomb.** Any salt, key or token with a computed fallback — `hash(hostname)`, `hash(__DIR__)`, the container id, an ephemeral machine name — silently changes when the environment is rebuilt, and everything hashed against it stops verifying with no error anywhere. Check three things for each: production fails closed when it is unset rather than computing one; the value survives a container recreation; and every process that reads it (web, CLI tool, worker, test) computes the *same* one. A password written by a host-side CLI that cannot verify inside the container is this defect, and it reads as "wrong password" forever. Fail-open is not one posture: name the axis. On a **display or read path** (a listing, a search, a recommendation) fail-open to an empty or degraded result may be the right System 5 policy, provided the degradation is visible on a screen (S22) and counted by a detector (S20). On a **money, entitlement, permission, or configuration path** fail-open is a finding unless an owner decision or ADR names that exact choice and its reason. Grade the two axes separately, and say which one each `catch` sits on.

## S4 — Vendor field semantics from the spec, not from the mapper (semantic drift)

For every provider callback field the code branches on (payment type, method, status, sub-status, error code), open the vendor's specification document that is checked into the repo or referenced in project memory and cite the page or section that defines the field. If the spec distinguishes a family field from a subtype field (for example a shared `PaymentType` and a card-only `PaymentMethod`), confirm the parser reads the one that is present for every family, not only for cards. A mapper whose comment says what a field means is not evidence; the spec page is. No spec read this session → the Step 7 line for the gateway carries "field semantics unverified against spec". **Sample code is not a specification.** A vendor's runnable example (a `createShipment.php` with a form and a curl) proves the envelope it exercises and nothing else — no response fields, no status-code table, no retry or acknowledgement rule, no fee, no amount cap. When the only vendor source on disk is a sample pack, say so, name the manual that is missing, and fetch it if the vendor publishes it before writing a line against that boundary. A handoff note claiming "the sample folder is the complete authority" is an S4 finding. **Check the hosted page before building a picker.** Before designing any store-selection, address-selection or method-selection round-trip of the shop's own, read the payment gateway's hosted-page parameters: a gateway that already collects the convenience-store choice on its payment page (NewebPay MPG `CVSCOM` + `LgsType`, which returns `StoreCode/StoreName/StoreAddr/LgsNo` in the ordinary payment callback) removes the whole map integration from the customer path; the logistics API is then label, trace and modify only. Building the map anyway is unrequested variety. **Gates must exist for every payment family that reaches them.** For every predicate a payment reducer or settlement path branches on (close status, capture flag, sub-code), list every method family that can arrive there — card, virtual account, convenience-store code, barcode, wallet, pickup-with-payment — and confirm the vendor defines the field for each. A gate on a card-only field leaves every non-card order `awaiting_payment` forever with a NULL or spent deadline, stock held, no error and no alarm. Fixture-test the reducer with one real-shaped result body per family the shop offers. **The vendor's recap is not the field table.** A manual's own summary list — a 注意事項 note, a changelog, a quick-reference — can omit a field the full request table defines (NDNF-1.2.5 p.40 lists every method flag except `TWQR`, which p.38 defines). Transcribe from the table and use the recap only as a cross-check; record any difference as a finding against the recap, not the table. **Same field name, per-family numbering.** A status field several families share may number its values differently per family (NDNF `CloseStatus` 3 = 請款完成 for cards and wallets but 請款失敗 for BNPL; the payment callback's integer `StoreType` numbers OK as 3 where the logistics `ShipType` numbers it 4). Keep one value table per family keyed on the family field, refuse a value that is not on its family's table, and never derive one document's code from another's integer.

## S5 — Admin control to runtime consumer (dead control / control-to-consumer wiring)

For every admin toggle, feature flag, or settings row (payment method enabled, gateway state, shipping option, tax mode, digital delivery switch), grep for the runtime consumer in the customer-facing path. A control the admin can change that no checkout, offer, window, or delivery code reads is a finding: the owner believes they turned something off and the shop keeps selling it. **The form is part of the control, and so is the queue.** When a gate is widened — a method that used to accept only one state now accepts two — every surface that leads to it must be widened in the same commit: the renderer that draws the button, the queue whose predicate lists the work, the filter on the desk. Widening the handler alone leaves a capability that exists, passes its unit test, and cannot be reached by the person it was built for (a dispatch control that accepted a cash-on-pickup order while the form that calls it still rendered only for `paid`). Sweep by predicate, not by method name: grep the old condition across renderers, queries and tests, and confirm each hit was considered. Also list every consumer that still reads a legacy source (yaml, CSV, constant) the admin control was meant to replace. **The host's whitelist is a consumer.** When a module copies the request into a named field list before the controller sees it, every field the page posts and the list omits is a dead control that answers with a success notice (a `Turn ON` toggle whose `feature`/`enabled` fields were dropped by `stringsFrom()` for three weeks); a controller test that bypasses the host module proves nothing about it. Walk the whitelist against every `name=` the page renders, and treat a module that hands the request over another way as an exemption to be named, never as silence.

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

## S12 — Cascade, partial failure and retry storm

For every outbound call (gateway query, logistics API, mail, storage, queue) and every inbound retry source (provider re-sends a notification, cron re-runs, customer refreshes), answer: what happens when the call fails half-way, times out, or succeeds after the caller gave up? Is there a per-step timeout? Is retry bounded with backoff, and is the retried action idempotent? Is there a circuit breaker or a degrade path (offer fewer methods, queue for later) rather than a crash or an unbounded loop? A retry that repeats a non-idempotent write, or a failure in one step that silently leaves an earlier step's side effect in place, is a finding. Trace the chain end to end and state which downstream effect the upstream failure produces. **A wait with no ceiling is a leak.** Any order, parcel or payment that waits for an external signal the environment cannot guarantee (a callback the sandbox cannot emit, a store-to-store status push with no documented retry, a counter payment) must have a ceiling that routes to a human queue — never an automatic reversal, because the parcel may be at the counter — and a sweep that lists what is waiting. State the ceiling and the queue; "the callback will come" is not a design (§3 fulfilment rule 9). **A browser-returned result is not a server channel.** Gateways deliver a result twice: once to the customer's browser (a return URL, a `ClientBackURL` / `ReturnURL` form post) and once server-to-server (a `NotifyURL`), with different fields at different moments. Anything dispatch depends on — a consignment number, the chosen store, a virtual account — must reach the shop by the notify channel or a poll of the vendor's query API; a design that takes it only from the browser post loses it the moment the tab closes (§3 fulfilment rule 12).

## S13 — Orphan capability / designed-but-unbuilt

Three greps, one table. (a) For every class under the admin, control, settings or catalogue roots (payment-method matrix, carrier catalogue, shipping chains, fee tables), grep for a caller outside its own file and its tests; a control class with no page, controller or module that renders it is an orphan. (b) For every table column and enum added by a migration (`shipping_method`, `pickup_store_*`, `cod_*`, fee columns), grep for a writer in runtime code — checkout, admin, worker — not only a test; a column nobody writes is scaffolding, and scaffolding that a later reader treats as data is a finding. **Grep the identifier alone and read every hit — never the identifier plus an SQL keyword on the same line.** A column written by a multi-line `UPDATE … SET` whose `SET` sits six lines above the column name is invisible to `grep 'col.*SET'`, and most non-trivial SQL is multi-line. One pass reported a live column as having no writer anywhere and was one sentence from filing it as an orphan with five consumers treating it as scaffolding. **A false orphan costs exactly what a missed one does**, because it sends the next session to rebuild something that already works — so confirm an absence by reading the hits, not by trusting a narrower pattern that returned none. (c) For every design document, master plan or handoff note under `docs/` that names a component (a checkout method picker, a carrier admin page, an eligibility engine), check that the component exists on disk **or** that the gap register carries one row naming it as unbuilt with its blocker (vendor account family, 測標 approval, owner decision). Report each orphan with its three states — designed / coded / wired — and the owner-side blocker if any. A capability that is designed and coded but not wired, and whose absence the register does not record, is the most expensive shape of commerce gap: every document says shipping is handled and the customer has no way to choose how.

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

## S15 — The four-corner end-to-end walk: customer × admin × shipment × payment gateway. THIS IS THE MOST IMPORTANT DATA INTERACTION IN A SHOP AND IT OUTRANKS EVERY OTHER SWEEP WHEN TIME IS SHORT

One order is described at the same instant by four parties — the **customer** on their order page and in their mail, the **operator** in the admin, the **logistics provider** holding the parcel, and the **payment gateway** holding the money — and by the shop's own database, which claims to be the system of record for all four. Commerce defects of consequence live in the disagreements between those five, not inside any one of them. Walk the object, not the module.

Method, per money-or-goods flow (checkout → payment → fulfilment → collection/delivery → invoice → refund/return; run it for **each** payment family and **each** delivery method the shop offers, because the families differ):

1. **Enumerate the states** the order can occupy end to end, including the ones only a provider can cause (instruction issued, parcel at store, collected, uncollected, returned, settled, charged back).
2. **Fill the four-corner table.** For every state, one row, four cells plus the database:

   | State | Customer sees | Operator sees / can do | Logistics provider believes | Payment provider believes | Row of record |

   Cite `file:line` for the customer and operator cells and the vendor field, callback or report for the provider cells. A cell you cannot fill from code and vendor document is itself the finding.
3. **Disagreements are findings.** Customer copy that contradicts the badge above it; an admin queue whose predicate excludes a state the order legitimately occupies; a shipment the provider has moved and the shop has not; money the gateway has settled that the order does not show. Name the class (status-symmetry gap, stale snapshot, dead control, TOCTOU) and the two corners.
4. **Unanswerable states are findings.** Any state with no operator control, no queue row, no instruction and no ceiling: the shop can enter it and no human can get it out. Say which desk should own it.
5. **Reachability under the shipped configuration is a CRITICAL check.** Walk the flow against the seed, migration defaults and feature flags as they will ship, not a fixture. A payment method, delivery method or refund path that is built, tested and *not offerable* under the shipped configuration is CRITICAL: the register says shipped, the customer cannot use it, and no unit test can see it. Report it above every other finding.
6. **Money evidence, per state.** For each state claiming money moved, name the single artefact that proves it (verified server callback, reconciliation query, operator-recorded settlement reference) and confirm nothing weaker (a browser return, a parcel event, a shipping status) is allowed to set it.
7. **Both directions.** Also walk backwards: refund, return, cancellation, chargeback and invoice correction cross the same four corners in reverse and are where the corners most often part company.

**Test consequence — binding on every test written for this shop.** Any test touching a flow that crosses corners states which corners it covers, and **every money path carries at least one four-corner end-to-end test**: customer action → gateway request → signed provider callback → local state → operator surface, with the provider faked at its own boundary (a real-shaped signed callback body, a real-shaped query response) and never by calling the local handler directly. Single-corner tests are allowed but never sufficient, and a suite of them can be wholly green while the four corners disagree. The project's end-to-end walk matrix (headless scripts, browser walks, scenario list) belongs to this sweep: its written coverage **and the scenarios it has not written yet** go in this sweep's report line, so "the suite is green" can never be said over a matrix that is mostly unwritten.

**The environment must be able to render what the sweep claims to have walked.** Before reporting a four-corner walk as done, confirm the running system can actually reach each corner: the pages exist (a catalogue with no page rows makes every product URL a 404 and no walk of the customer corner is possible), the operator can sign in, the provider sandbox answers. Seed gaps are findings of this sweep, not excuses for skipping it — they block the owner's own sign-off as surely as a bug, and they are usually one seeder run from fixed. Walk the corners in the running app, not only in the suite: a test renders a class in isolation, a browser renders what the operator will actually see.

Report line format: `S15 — walked N flows × M states across customer/admin/logistics/gateway; four-corner table in the report; K disagreements, J unanswerable states, R reachability findings; E2E matrix: W written / U unwritten.`

## S16 — Terminal-state accountability. EVERY ORDER AND EVERY PARCEL MUST END SOMEWHERE A PERSON CAN ACCOUNT FOR

Where S15 asks whether the four corners *agree*, this asks whether the object ever *ends*, and whether anybody is told when it ends badly. The owner's instruction, which is really an audit rule: *"No delivery or transaction should allow go dead quietly with loose ends, all ends must be tied and traceable"*, and *"anything system cannot handle must hv badge or flag in admin panel of order management page to let admin handle and notice."*

In a commerce system this is where real money is lost with a green test suite. Every function on the path is correct; there is simply no further event, and no disagreement for S15 to catch. The shop keeps selling and one order sits in a state nobody is looking at.

Method, per money-or-goods flow:

1. **Enumerate the terminal states, then the non-terminal ones.** For every state that is neither terminal nor guaranteed to advance, name the thing that advances it: a gateway callback, a logistics push, a worker, a clock, a human. "The provider will tell us" is not an answer; name the endpoint and the code that reads it.
2. **Kill each advancer and ask what happens.** The callback never arrives (the provider retried four times into a 500 and gave up). The push URL was never entered in the provider's console. The worker is not in the crontab, or dies on its third row. The customer never collects. The shop never looks. For each: does the order reach a state somebody can act on, or does it sit?
3. **Walk the commerce-specific silent deaths by name.** A payment authorised and never captured inside the acquirer's window. A parcel that reached the store and was never collected, whose return leg nobody watched. A refund begun and never confirmed. A cash-on-collection order collected, where the settlement never arrived. An invoice obligation opened and never written. An entitlement granted against a payment later reversed. Stock reserved by a cart that was abandoned. Each is a state that can persist forever and costs money quietly.
4. **Check both halves of a two-fact truth, separately.** For 取貨付款 and every cash-on-collection scheme the owner named the two facts exactly: *(a)* the goods were picked up, and *(b)* the money actually reached us. These must be two records that can disagree — a collection event from the logistics side, a settlement from the payment side — and a disagreement must raise something. A shop that infers payment from collection cannot detect the case where only one is true, which is the case that costs the shop the goods.
5. **Then check the notice lands where the operator already works.** Usually the missing half. An alert table with no page, a log line, a digest email, a status nothing filters on — none is a notice. The test is whether the condition becomes visible on the **order list and the order page**, which is the screen a shopkeeper opens every day. The owner's own words: a badge or a flag on the order management page. A handler that exists on a page nobody opens is a dead control (S6) wearing a different hat.
6. **Report the unattended set** as a table: state, what should have advanced it, what the operator would see, how they would ever find out, and what it costs per occurrence. An empty table is a real result; an absent table means the sweep was not run.

**Grading.** Money or goods that can be lost with no signal: **CRITICAL**. An order that can sit forever but is recoverable once noticed: **HIGH**. A notice that exists only in a log, or in a table with no screen: **HIGH** — by the owner's rule that is not a notice. A notice on a screen nobody has a reason to open: **MEDIUM**.

Report line format: `S16 — N flows × M non-terminal states; K silent deaths, J notices that reach no screen; unattended-state table in the report.`

### S16.1 — Every non-terminal state deserves a queue, and the queue is where the bulk action lives

S16 asks whether a state has a **badge**. The badge is the minimum and the **queue** is the useful
form: an operator opens *"what needs doing next"*, not *"records, filtered by status"*. The rules
below came out of designing one operator desk and apply to every desk.

**Check, per non-terminal state:** is there a queue that lists the items sitting in it, and does that
queue carry the action that moves them on? A state whose only surface is a per-record badge makes the
operator hunt for the records one at a time, and **a worker that already computes the list and writes
it to a log or an exit code is the queue's missing half**.

**Four rules, for any desk:**

1. **The single action is a batch of one.** Two code paths drift, and the one that drifts is the one
   without the precondition. Write the batch; let the single case call it with a selection of one.
2. **Carry the precondition in the `WHERE`, always.** `UPDATE … WHERE id = ? AND <what made this row
   eligible>`, then read the affected-row count. Closes the select-then-commit race, makes double
   clicks harmless, needs no lock and no version column. **Never `UPDATE … WHERE id = ?` alone** —
   in a desk or anywhere else.
**2a. A state transition and a value edit need different preconditions, and conflating them is a silent data loss.** Rule 2 above is not one rule but two, and the second is the one that gets missed:

| | Precondition | Why it is enough, or is not |
|---|---|---|
| **State transition** — mark dispatched, mark paid, cancel | `WHERE id = ? AND dispatched_at IS NULL` | **Self-protecting.** The condition can only be true once, so the second writer matches zero rows and learns it lost. The row count *is* the answer |
| **Value edit** — price, stock, a note, a cost | `WHERE id = ?` | **Not enough, and it fails silently.** There is no natural once-only condition on a value. Two operators editing the same price both match, both succeed, and the first edit vanishes with nobody told |

**For a value edit, carry the value you read**: `WHERE id = ? AND price = ?` — compare-and-swap — or
a `version` / `updated_at` token if several fields move together. A zero row count then means
*"somebody changed this while you were looking at it"*, which is a sentence the operator can act on,
and **the alternative is not a conflict, it is a disappearance.**

This matters most in exactly the place it is least expected: a **bulk editor** feels like typing in a
spreadsheet, so nobody thinks about concurrency — and it is the surface where one operator can
silently discard fifty of another's edits in a single click.

**2c. `rowCount()` may mean *matched*, not *changed* — check the connection before trusting the number.** MySQL's default reports rows the `SET` actually changed; with `PDO::MYSQL_ATTR_FOUND_ROWS` it reports rows the `WHERE` matched, and a codebase may enable that deliberately — one did, to stop idempotent re-saves reading as *"not there"* (`fb64069e`). Rules 2 and 2a survive either setting **only because the precondition is in the `WHERE`**: a row that no longer qualifies is not matched, so it is not counted, whichever semantic is on. What does *not* survive is any code reading `rowCount() === 0` as *"nothing changed"* — under `FOUND_ROWS` a no-op re-save matches and reports 1. A test asserting the old semantic was found red, unreached, at about test 4700 of a six-hour suite. **Grep the connection for `FOUND_ROWS` before writing or auditing any row-count logic, and if the contract needs "nothing to change" to read as zero, put that in the `WHERE` too** — NULL-safely, with `<=>`, because the columns compared are usually the ones that start NULL.

**2b. Validate per cell, not per submission.** One bad value must not reject the other forty-nine.
Same rule as showing ineligible rows with their reason: the batch reports per row, and the rows that
were fine are saved.

3. **If two rows could legitimately differ, it cannot be a header field.** One shared field for a
   per-item value writes the same tracking number, refund amount or invoice number onto every row in
   the selection. The test is one sentence: *could two selected rows honestly want different values?*
4. **Ineligible is explained, never silently dropped and never blocked.** Show the excluded rows with
   their reason. **Generalised to every disabled control in the product**: a greyed button says why it
   is grey — an S22 surface kind of its own, and the cheapest operator-experience win in most
   codebases.

**And the one that is about people rather than rows:** an operator action that can reach a customer
gets a **"tell them" checkbox, defaulted on, with the unchecking recorded — who and when.** A
customer who was never told must be distinguishable from one somebody decided not to tell. The
checkbox writes *intent*; the sending stays with whatever durable sweep already sends, because a
send-inside-the-click makes the customer's message depend on the operator's browser staying open.

## S17 — The hosted surface: every choice the buyer makes on a page you do not render. A SHOP SETTING THAT CANNOT REACH THE GATEWAY'S OWN PAGE IS A LABEL, NOT A CONTROL

The owner's question that defines this sweep: *"How do we restrict user use which chain by toggle? Or do we trust our toggle auto reflects payment gateway setting?"*

Modern commerce hands the buyer to somebody else at the most important moment. A hosted checkout takes the card. A hosted **store picker** takes the convenience-store choice. A carrier's page takes the locker. An app store takes the purchase. **The shop's settings stop at the redirect**, and S6 (dead control) and S13 (orphan capability) both search the shop's own code, so both pass while the setting governs nothing.

The canonical shape, because the pattern repeats: the shop had a per-chain delivery toggle — 7-ELEVEN, 全家, 萊爾富, OK — in its own table, read by its own storefront, covered by tests, and reported as built. The buyer chose their store on the **payment gateway's** map. The gateway's request field for that flow has exactly two values, "one chain" or "all four", and the manual states that what is actually enabled is decided in **the merchant's back-office**, not in the request. So the toggle could not restrict anything, and a chain switched off in the admin could still come back on the callback and be recorded as a normal order.

Method, for every hand-off to a hosted surface:

1. **List the redirects.** Hosted payment page, store or locker picker, wallet consent, carrier booking, instalment underwriting, app-store flow. For each, find the request builder in your code. That request is your whole influence over what the buyer sees.
2. **List the shop settings that claim to shape it.** Delivery-method toggles, offered-payment-method sets, carrier catalogues, instalment term lists, currency menus.
3. **Open the provider's manual at the request-field table and check the claim, field by field.** Quote the field, its permitted values and its defaulting rule into the finding, with the page number. Ask whether the request can express what the setting promises. The usual answer: the field is coarser than the setting by a factor of four.
4. **Find the sentence naming the real enforcement point.** It is nearly always there and nearly always unread — *"must first enable the service and configure X in the member area"*, *"approval is per sub-type"*, *"if neither is enabled in the merchant settings the option does not appear"*. Whatever it names is outside your repository, outside your tests and outside your deploy.
5. **Classify and report as one of three:** **(a) enforceable** — wire the setting to the field, test it, done; **(b) unenforceable, so the setting is a lie** — delete it, or redefine it as "what we accept" and then apply S16: an out-of-set value arriving on the callback must raise a badge, never be accepted silently; **(c) enforced in the provider's console** — document the setting as a mirror, put the console step in the deploy prerequisites, and name what reconciles the two.
6. **Walk the return path with a value your settings exclude.** Place the order, have the provider return the excluded chain, method or locker, and follow it to the admin. Silent acceptance is a HIGH finding: the operator now has an order in a state their configuration says is impossible, and no badge tells them.
7. **Check the money variants separately.** Pay-now and pay-on-collection are often the *same* hosted flow with one different integer, and the fee, the settlement date and the refund route all differ. A setting that switches one on frequently cannot express the other.

**Grading.** A setting that claims to restrict carriers, payment methods or fulfilment and provably cannot: **HIGH**. Silent acceptance of an excluded value on the callback: **HIGH**. A console-mirror setting with nothing reconciling it and no deploy step: **MEDIUM**, HIGH once both sides are editable by different people. A cosmetic setting documented as cosmetic: not a finding.

**The reading rule.** When the provider's manual is on disk — and in this domain it usually is, as a PDF nobody has opened — **read the field table for every field the shop sends, before describing what any of them do.** A docblock in your own integration describing a gateway field is your summary of their document and carries none of its authority; three of the defects behind this sweep were confident summaries written by the same hands that later audited them.

Report line format: `S17 — N hosted surfaces; K shop settings tested against the provider's field table; findings by shape (enforceable / lie / console-mirror); return-path walk: done/not done.`

## S18 — The provider-contract matrix: every payment × delivery combination, every field, cited to the manual. A SPOT CHECK THAT FINDS A HOLE HAS DISPROVED THE METHOD, NOT JUST THE ANSWER

In the owner's words: *"One hole of that shape means the method that found it was wrong, not just the answer — so the fix is to walk every combination against the manuals rather than spot-check."*

A shop is a grid, and defects live in the cells nobody visited. Payment method × delivery method × destination × cart shape × pay-now-or-pay-later, each cell sending different fields to a different gateway and coming back by a different route. Reading one cell and generalising is how an auditor concludes that a per-carrier toggle works when it cannot work for any carrier.

**Two rules, and the first is the one that gets skipped.**

**Rule 1 — a confirmed finding invalidates the sweep that missed it.** One control that does not reach the gateway means re-walking **every** control of that shape; one state with no badge means re-walking **every** state; one field misread from a manual means re-reading **every** field that manual governs. Fix the instance, then report the count you re-walked. The instance was found by a user; the rest of the class is still shipping.

**Rule 2 — build the matrix, and cite the manual per cell.**

1. **Name the authority per provider.** The gateway's integration manual, the carrier's logistics manual, the tax authority's text. **If a PDF is in the repository, that PDF is the authority** — not your integration's docblocks, which are a summary written by somebody who may also have been wrong.
2. **Enumerate what the shipped seed can actually produce.** Read the payment-method matrix, the delivery-method offer rows and the feature flags as they ship, and list the combinations a real buyer can reach — not the theoretical product. A method seeded off is one row of the matrix ("not offerable, seed"), not an excuse to skip its column.
3. **For every reachable cell, answer six questions with citations:** which request field carries this choice and what values may it take (manual, page); what the buyer sees on whose page; what comes back, by which route — callback, redirect, query, push; where it lands in our code; what order and shipment state results; **what the operator sees when it goes wrong.** The last one is where S16 and this sweep meet.
4. **A cell with no page citation is `UNVERIFIED`, never `OK`.** Report the count. Nine unverified cells stated plainly is a better result than a paragraph concluding the integration looks correct.
5. **Include the money variants as separate cells.** Pay-now and pay-on-collection are frequently one hosted flow with one different integer, and the fee, the settlement date, the refund route and the invoice timing all differ. They are two cells, not one.
6. **Report the matrix itself.**

**Grading.** A cell contradicting the manual: on its own consequence, and money-moving cells start at HIGH. A class re-walked after a confirmed finding and turning up more: each on its own consequence, and the original is raised one level for being systemic. Unverified cells: not a finding — but calling the integration clean while they exist is.

### S18.1 — Run the carrier's validator, and trust its artefacts over its FAQ

Three rules a carrier's own tooling teaches that its manuals do not (learned by posting real
parcels through a Taiwanese convenience-store service after its manuals had been read):

1. **The carrier's import validator states rules no manual does.** Its wizard rejected a row with
   「寄件人姓名不可超過五個中文字」 — a five-character cap on both the sender's and the collector's
   name. Nothing in the service pages says it, and it decides which customers can use the delivery
   method at all: a 證件姓名 of six characters means checkout must not offer it. **Where a carrier
   or gateway gives you a preview, a validator, a sandbox or a dry run, run it and read its
   refusals into the matrix.**

2. **The printed label beats the FAQ.** The label said 繳費期限 four days; the FAQ said seven days
   to ship. The label is what the store obeys, so it is what the clock in our state machine obeys.
   **Rank the authorities: emitted artefact (label, receipt, callback, generated file) > integration
   manual > help centre > our own wrapper's docblock.**

3. **One carrier is several services.** 取貨付款 and 取貨不付款 under the same brand had different
   pages, different upload templates, different value caps (10,000 vs 5,000 vs a platform's 20,000)
   and different freight tables (flat 65 vs a 60/70/80/90/100 band). The right file on the wrong
   page failed with a format error that named none of this. **Every variant is its own matrix row,
   with its own cap, fee, page and payout rule** — and a shop that offers "超商取貨付款" without
   naming which variant has not decided anything yet.

And three rules with teeth for any shop:

- **A store picker is a promise.** The carrier's own store directory returns branches that do not
  offer the service — 台鐵/高鐵 stores in this case. Filter the list by service availability, not
  existence, or the failure lands on a customer at a counter.
- **The fee table belongs in the product, not in a document.** Freight, collection fee, cross-bank
  transfer fee, return-handling fee, payout day and the value caps each go beside the switch that
  turns the method on, each with the URL it was read from and the date it was read, and a staleness
  prompt when that date ages. `fee_kind` / `fee_source` / `fee_read_on` already exist for exactly
  this; a rate a shopkeeper cannot see is a rate nobody re-checks, and carriers change them with
  thirty days' notice on a page nobody has bookmarked.

- **A citation that does not resolve is not a citation, and money citations are the ones that get
  re-derived.** Page numbers from a PDF reader, folios printed in footers and contents-page section
  numbers are three different coordinates, and carrier and gateway manuals routinely print a folio
  one lower than the PDF page. The cells this matters most for are the ones somebody will re-check
  under pressure: a value cap, a fee, a payment-window limit, a rate-limit lockout code. **State
  the coordinate system in the document, verify each citation by extracting that page and grepping
  it for what you claimed, and when a finding forces a re-walk of its class, re-walk the citations
  too** — including in patches not yet applied, so the docblock that ships names a real page.
  Extract tables with the layout preserved (`pdftotext -layout` or your tool's equivalent): a
  collapsed two-column code/message table binds a cap to the wrong error code, and the
  `UNVERIFIED` that follows is your tooling, not the manual.
  **And when `-layout` and the raw extract disagree, the raw one preserves row order — read
  both.** `-layout` keeps columns but can shift a cell one row on a multi-line table; a
  column-shifted read once put a gateway's 4-hour lockout sentence beside the wrong code and
  was one step from "correcting" shipped software that was already right. For any
  code-to-meaning binding you are about to act on, confirm it in the raw extract — or find the
  vendor's own prose naming both together, which a manual's FAQ usually does.
  **And count a table by its cells, never by a column read.** A `-layout` count of one column
  once said 79 codes; the PDF's own ruling lines (`pymupdf` `find_tables`, or any extractor
  that reads cell borders) said 125, because a fifth of the table was a second code column
  the first read never saw. Extract cells, count rows, then cross-check the raw order.

Report line format: `S18 — P payment × D delivery cells enumerated from the shipped seed; M verified against manuals with page citations, U unverified; matrix in the report. Re-walks triggered by findings this run: K.`

## S19 — Can the host this shop is launching on actually meet what the gateways and carriers require? A REQUIREMENT THE HOST MUST SATISFY, NEVER CHECKED AGAINST THE HOST THAT WAS CHOSEN

The owner's question: *"does [this] also need whitelist IP…? If so our shared hosting launch won't make it."* Both facts were already written down, **in the same document** — the carrier's IP-allowlist requirement in the deploy prerequisites, the shared-hosting launch target in the section above it. Nobody multiplied them.

**Why it hid, and the mechanism is nearly universal in commerce work:** the requirement had been written as *a task for the owner*. "Register the outbound IP in the carrier's console" became a tidy row in a deploy checklist — and **a requirement that becomes a checklist item leaves the audit.** Everyone tracks whether the box is ticked; nobody asks whether the box *can* be ticked on this host.

**The commerce-specific list. Ask every one of these of every provider, cite the page, then ask it of the host:**

| Requirement | Who typically imposes it | What a shared or ephemeral host does to it |
|---|---|---|
| **Fixed or allowlisted egress IP** | logistics and label APIs, refund and query APIs, some acquirers | shared hosting may rotate it or share it; serverless and container platforms usually rotate it. **Refusals are per-call and often logged, not badged** |
| **Inbound webhook reachable on 443, public, with a valid chain** | every gateway's callback | fine on most hosts; broken behind basic auth, an IP allowlist of your own, or a staging password |
| **Minimum TLS version / cipher / SNI** | acquirers, 3-D Secure | old shared stacks still ship TLS 1.0-1.1 |
| **Cron granularity and reliability** | settlement, capture windows, parcel tracing, retry drains | shared hosts cap frequency; some have no cron at all, only a pseudo-cron on page hits |
| **Long-running or background processes** | queue drains, batch label printing | forbidden on most shared plans |
| **Persistent local filesystem** | invoice PDFs, label files, export spools | ephemeral on containers and serverless |
| **Clock accuracy** | request signatures with a timestamp window (±N seconds) | usually fine; catastrophic and baffling when not |
| **Fixed timezone** | settlement cut-offs, invoice periods, statutory day boundaries | host default is rarely the shop's jurisdiction |
| **Outbound ports other than 443** | SMTP, some bank or carrier endpoints | commonly blocked on shared hosting |

Method:

1. **Extract the preconditions from the manuals, not from your own notes**, with page citations, exactly as S18 requires.
2. **Name the target environments** — the launch host and its plan, plus any host the shop is planning to move to. Both get a column, because a requirement satisfied on one and not the other is a migration that silently breaks fulfilment.
3. **Cross them, one row per requirement per environment**, verdict **satisfied / not satisfied / unknown**, with how it is known.
4. **Unknown is a finding.** "The host may or may not keep a stable egress IP" is the state in which a launch gets planned around a capability nobody confirmed.
5. **State the consequence in the shop's terms**: not "IP allowlisting may be required" but "parcels cannot be booked, the provider refuses per call, and today that refusal is logged rather than badged — so the shop keeps selling pickup orders it cannot ship."
6. **Re-run on any host change.** A migration invalidates every row, because every row described an environment that no longer exists.

**Then feed it back into S18**, where the environment is a dimension and not a footnote: **a payment or delivery cell verified against the manual, on a host that cannot meet the manual's precondition, is a verified cell about nothing.**

**Grading.** A requirement the launch host provably cannot meet, on a money or fulfilment path: **CRITICAL**. One it can meet only unreliably — a shared egress IP that may rotate: **HIGH**, because intermittent failures are the ones nobody reproduces and the shop keeps taking orders through them. An unknown on a money path: **HIGH** until answered. Satisfied but undocumented, so the next host move loses it: **MEDIUM**.

**The rule this leaves behind:** when an audit hands the owner a task, it must also record *what makes the task possible* and check that. Otherwise the deploy checklist reaches 100% on a host where one of its boxes was never tickable.

Report line format: `S19 — R provider requirements extracted and cited; E environments crossed (launch + planned); satisfied/not-satisfied/unknown = A/B/C; table in the report.`

## S20 — Liveness of the safety net itself. ZERO FINDINGS AND ZERO LOOKING ARE THE SAME REPORT UNLESS SOMEBODY DESIGNED THEM APART

The First Law — *"Nothing should die silently!!"* — applied to the watchdogs themselves.

S16 asks whether an **order or a parcel** can stop moving unnoticed. **S20 asks it of the machinery that was supposed to notice**: the settlement reconcile, the capture sweep, the callback drain, the parcel trace, the refund poll, the retention purge, the stock re-count. In a shop these are not monitoring niceties — they are the only reason the books match the acquirer's. Their failure is uniquely quiet, because **a reconcile that verified nothing prints the same line as a reconcile that verified everything and found it all correct**: no discrepancies, no error, exit 0.

The three that happen, all three found in one shop:

1. **It ran and verified nothing.** A nightly settlement audit asked two gateways about every recent order; every answer came back unreachable. It counted the unknowns, raised nothing, exited 0. The most likely cause — an outbound IP the acquirer had stopped accepting (S19) — would have left every order back on a single unverified callback, *with nothing anywhere saying the second witness had stopped*.
2. **It stopped running at all.** Every worker wrote a heartbeat and nothing read one. A crontab lost in a host migration, a dispatcher throwing on its first line, a job flag switched off during an incident and never switched back — each is silent, because nothing runs to produce the error. A shop whose capture sweep stopped keeps taking authorisations it never collects, and finds out when they expire.
3. **It ran, found a discrepancy, and told a table.** An alarm with no badge on the order list is a detector whose output dies where it lands (S16 step 5).

Method:

1. **Enumerate the shop's detectors.** Everything scheduled or reactive whose job is to notice: settlement reconcile, authorisation capture before expiry, callback and queue drains, refund and chargeback polls, parcel and pickup-expiry traces, inventory re-count, entitlement expiry, statutory retention purge, fraud-review queue. If the list cannot be produced from the code, that is finding one.
2. **Demand two numbers from each: coverage and findings.** "0 discrepancies" means nothing without "out of N orders examined". Where coverage can legitimately be zero — no orders in the window, no credentials configured, every gateway refusing — that state must be **named and raised** (*blind*, *degraded*, *nothing verified*), never folded into success.
3. **Give every scheduled job a heartbeat, and make something read it.** A heartbeat nobody queries is theatre. Compare last-run against the job's own schedule, allow a few intervals of grace so one late run is not an alarm, and treat **never ran** as the loudest case rather than the quietest — on a fresh deploy it means the crontab was never installed, which is precisely the launch-day failure nobody sees.
4. **Walk each detector's output to a screen a shopkeeper opens** — the order list and the order page, per §0.10. A log file, an alert table, an exit code and mail to an unread address are the same answer: nowhere.
5. **Name the outermost check, and confirm it is outside the shop.** "Who watches the watcher" terminates only by leaving the system: a cron that mails non-zero exits to a person, an external uptime probe, a dead-man's switch a third party trips when the nightly ping stops arriving. A monitor living inside the application shares the application's outages. If there is none, say so plainly — that is the owner's call, and it must be a made one.
6. **Test the blind case.** Every detector's suite needs "it examined nothing and said so". The test feels like testing the absence of work; it is testing the difference between silence and safety.

**Grading.** A money-path detector that cannot distinguish blind from clean: **HIGH** — every run it has ever made is uninterpretable, including the ones already filed as green. A money-critical scheduled job with no liveness signal: **HIGH**. A detector whose output reaches no order screen: **HIGH**. No outermost check outside the shop: **MEDIUM**, stated plainly rather than buried.

**The sentence to carry out of this sweep:** *a green report from an instrument nobody has proved is looking is not evidence of health — it is evidence of a report.*

Report line format: `S20 — D detectors enumerated; C report coverage separately from findings; H have a liveness signal something reads; E escalate to an order screen; outermost check: <named, or NONE>.`

## S21 — The suite is an instrument too. A PASSING ASSERTION THAT SOMETHING IS EMPTY PROVES NOTHING UNTIL SOMETHING PROVES IT CAN BE NON-EMPTY

S20 asks whether the detectors are looking. **S21 asks it of the test suite**, which is the detector everything else is trusted on. Four shapes, all four confirmed in one codebase:

1. **The vacuous pass.** A query used by four tests returned nothing at all, because of a defect none of them was about. The two tests asserting *"and the result is empty"* passed — that is what they asked for — and the two asserting a result failed. The failures looked like a test problem precisely because their siblings were green. **Whenever the subject of a test is a query, a filter, a collection or a sweep, at least one test must prove it can return something, under the same conditions.** And watch the **assertion count**, not only the colour: if fixing a bug makes assertions go *up*, assertions were not being reached, and every earlier green run was reporting on code it never executed.
2. **The runner is one environment.** A test that loads real configuration into the runner's own process — a framework bootstrap, a config builder, a dotenv loader, anything that reaches the production entry point — changes `getenv()` for every test that runs after it, across suite boundaries when the suites share a process. The damage reads as an order-dependent flake and hides for months. **Snapshot the environment before such a test and restore it after.** And the asymmetry that makes this so hard to see: **cleaning up in teardown protects the next test and never the first.** A test that depends on the *absence* of a variable must clear it on the way **in**.
3. **The failure diff is an output channel.** A test that asserts on a credential, token or key prints the real value in full when it fails — into scrollback, into CI logs, into whatever a reviewer pastes. Codebases that carefully refuse to quote a secret in an error message routinely quote one in an assertion. **Assert on a derived property** — length, prefix, "not the plaintext", "not equal to what is stored" — **or clear the source so the comparison cannot reach a live value.**

4. **A guard that exists but runs too late is a latency gap, not a coverage gap — and the two have different fixes.** A missing test is written; a slow one is *moved*. An admin page had been throwing on every render for days. A test asserted exactly the invariant that broke and would have named it precisely — but it was test 4555 of 4875, four hours into a seven-hour suite, so in practice nobody had reached it since the defect landed, and the first witness was seven errors in an unrelated class four hundred tests earlier, which is why it read as a test problem rather than as a dead page. **For every invariant a slow suite protects, ask what it actually costs to check.** Reflection over two constants, a schema-versus-code comparison, a "every X has a Y" pairing — these need no database and no fixtures, and belong in whatever tier runs before a commit. The one that was moved went from unreachable-in-practice to **0.135 seconds**. When a suite is slow enough that people stop running it, its guards have already stopped guarding, whatever the coverage report says.

Method: enumerate the tests that touch the system's real configuration or entry points; confirm each restores what it changed. For every suite that asserts emptiness, find the sibling that proves non-emptiness. Record the assertion count alongside the test count in every claim, because *"N tests pass"* and *"N tests ran and asserted M things"* are different reports.

**Grading.** A vacuous pass on a money path: **HIGH** — the code it was meant to cover has never been exercised. Environment contamination that reaches other tests: **HIGH** when the contaminating values are real credentials, **MEDIUM** otherwise. A live secret reachable in failure output: **HIGH**, and say it in the conversation with the rotation decision attached, per §0.10, beside the order screen it affects.

**The sentence to carry out of this sweep:** *green is a colour, not a measurement — quote the counts, and know which of them went up.*

Report line format: `S21 — T tests / A assertions quoted; V vacuous-pass risks found; E tests that mutate the runner environment, R of them restoring it; S secrets reachable in failure output.`

## S22 — Surface completeness across step × outcome × audience. A STEP WITH NO SCREEN IS A STEP NOBODY CAN BE TOLD ABOUT, AND A SCREEN NOBODY HAS RENDERED IS A SCREEN NOBODY KNOWS IS BROKEN

The owner's question that defines this sweep: *"are you sure all gaps for [the] purchasing cycle, all combinations of them, each step has a UI and screen, to flag, show and confirm and catch whatever throws back, and every purchasing and checking step has a display showing admin or customer… how do you call this gap and how does our skill catch these gaps?"* In the shop that asked it, ninety-five preview scenarios existed, forty-six of them admin, and **not one rendered an exception, alarm or badge**.

**Why the existing sweeps miss it, stated precisely, because each is close enough to feel like coverage:**

| Sweep | What it asks | Why it is not this |
|---|---|---|
| **S15** four-corner walk | do the corners *agree* about the object | a corner can agree perfectly and still have no screen |
| **S16** terminal-state accountability | does the state *end* somewhere a person can account for | satisfied by an alarm row that reaches *a* screen; never enumerates step × outcome × audience |
| **S17** control enforcement | can the setting reach the decision | about controls, not about surfaces |
| **S18** enumeration against the authority | is every *contract* combination verified | fields and pages, not faces |
| **S13** orphan capability | is the capability wired | a wired capability with no rendered state passes |

**The method is a matrix, and it is a different matrix from S18's.** Build it once, per commerce flow — purchase, subscription renewal, refund, return, exchange, store credit:

1. **Enumerate the steps** of the flow end to end, **including the reversals** — which are the half that gets forgotten, because the happy path is the one everybody demonstrates. For a purchase: offer, checkout, authorise, instruct or capture, settle, fulfil, deliver, close; then expire, cancel, refund, return, chargeback, and the late arrival that contradicts one of those.
2. **Enumerate the outcomes** of each step, and **`unknown` is a required column, not an edge case** — S21 and S20 both exist because a system that cannot say *"I could not tell"* says something false instead. The set: **succeeded · refused · timed out · partial · unknown · reversed after the fact.**
3. **For each cell, name the surface for each audience that bears the consequence** — typically customer and operator, sometimes a third (an accountant, a courier, a regulator). Where a cell genuinely has no audience, write that down rather than leaving it blank; a blank is indistinguishable from an oversight.
4. **A surface only counts if it satisfies all four:** it **exists**; it is **reachable by a URL or route somebody can open on demand**, without reproducing the situation that causes it; it **says what happened in words that audience can act on**; and for the operator it **says what to do next**. A log line is not a surface. An email is not a surface for the operator. A row in a table with no screen is not a surface.
5. **Mark every cell `OK` / `GAP` / `UNVERIFIED`**, exactly as S18 does, and treat `UNVERIFIED` as a task. A cell nobody has opened in a browser is `UNVERIFIED`, whatever the integration tests say — because an integration test asserts the *data* and has never once proved the page renders.

**The renderability clause, which is what makes this sweep different from S16 and is the part that gets skipped.** The states that most need a surface are the ones that only appear when something has gone wrong, and those are exactly the ones no fixture produces. **Demand a fixture per situational surface, not per page.** If reaching a screen requires reproducing a gateway outage, a lost callback or a ten-day-silent parcel, then in practice nobody has ever seen it — not the designer, not the reviewer, not the person who will have to read it at three in the morning. A coverage ratchet that counts pages and scenarios will report clean on all of them; widen it to count **conditional surfaces inside existing pages** — a badge, an alarm panel, an empty state, a disabled control, a refusal message.

**Grading.** A money step whose **refused**, **timed out** or **unknown** outcome has no operator surface: **HIGH**. A customer-facing refusal with no customer surface: **HIGH**, because the customer is stranded mid-purchase with their money possibly taken. A surface that exists but has never been rendered: **MEDIUM**, and it becomes HIGH the moment anything on the page is typed — the canonical case is a settings page that threw a `TypeError` on every request for days because nothing ever opened it.

**The sentence to carry out of this sweep:** *every way a purchase can go must have a face, and a face nobody has looked at is a rumour.*

### S22.1 — What this is called outside this skill, because hunting it needs the right words

**It has names. Several, one per community, and an auditor who does not know them cannot search for
prior art, cannot read the tooling that already solves half of it, and cannot tell a developer what
is missing in a word they will recognise.**

| Community | The name | What it gives S22 |
|---|---|---|
| UI design | **The UI Stack** — Scott Hurff, 2015: every component has **blank / loading / partial / error / ideal**. Missing ones are **empty-state** and **error-state gaps** | The canonical five-state checklist. Most teams design *ideal* and ship the other four by accident |
| Front-end | **story coverage** (Storybook), **visual coverage** (Chromatic, Percy, Applitools). The maxim is *"if it can render, it needs a story"* | The fixture-per-state discipline, already an industry norm - and the reason a preview catalogue is the right instrument rather than an invention |
| QA / test | **unhappy-path** or **sad-path coverage**, **negative testing**, and for state machines **statechart coverage**, split into **state coverage** (every state reached) and **transition coverage** (every edge taken) | Names the asymmetry precisely: happy-path coverage can be 100% while sad-path coverage is 0%, and one number hides the other |
| Combinatorics | **state-space explosion**, answered by **pairwise / all-pairs / n-wise coverage** (Combinatorial Test Design) | The honest answer to *"all combinations"*: the full cross-product is infeasible and nobody runs it. See the depth rule below |
| SRE | **actionable alerting** - the Google SRE rule that an alert which does not tell a human what to do is **noise**, not signal - plus **runbook coverage** and **observability gap** | Exactly why a log line and a digest mail fail this sweep. The industry already decided this and wrote it down |
| Product / internal | **operator experience**, **internal-tooling debt**, **back-office UX** | The vocabulary for arguing the work is worth doing, to somebody who thinks admin screens do not need design |
| Reaching the states | **fault injection**, **state injection**, fixtures and mocks; **chaos engineering** at the infrastructure tier | How the untestable-looking states get rendered without waiting for a real outage |

**Use these words in findings.** *"The refund-refused path has no error state and no story"* lands
with a front-end developer; *"S22 cell 4.3 is a GAP"* does not.

### S22.2 — How to hunt them, mechanical, in rough order of yield

1. **Grep the render guards.** Every conditional that wraps output is a surface: an emptiness check,
   a null check, an early return carrying a refusal reason, a match arm that renders something else.
   **Enumerate them and ask which has a fixture.** Highest-yield pass and pure grep - a conditional
   surface inside an existing page is the exact thing a page-level coverage ratchet cannot see.
2. **Walk the enums as statecharts.** **State coverage**: has each case a rendered surface?
   **Transition coverage**: has each edge one where it matters? The edges that run *backwards* -
   cancelled-then-paid, delivered-then-returned, refunded-then-charged-back - are where surfaces go
   missing, because forward edges get demonstrated and backward ones do not.
3. **Inventory the error paths.** Every catch, every throw that can reach a request, every refusal
   string, every non-zero exit. Each is an outcome. **A refusal reason that exists only as a string
   in a log is an error state with no error surface.**
4. **Empty states.** Every list, table and collection: what is shown at zero rows? Zero is the state
   a shop is in on **day one**, so it is the first thing a new operator sees and the least likely to
   have been designed.
5. **Read the alerting.** Every notifier, digest, cron exit code and alarm row: where does it land,
   and is that a screen somebody opens? Apply the SRE test - **does it say what to do?**
6. **Then, and only then, the cross-product** - bounded deliberately.

**The depth rule, because "all combinations" is not a plan.** The full cross-product of
step x outcome x audience x payment method x delivery method x destination x cart shape runs to tens
of thousands of cells and will never be walked. So:

- **Money paths at full depth.** Every step whose outcome can move, hold or lose money gets every
  outcome and every audience, enumerated exhaustively. This is a small set - it is the failure
  column, not the whole grid.
- **Everything else pairwise.** All-pairs coverage over the remaining axes catches the large majority
  of interaction defects at a fraction of the cells, which is the published result behind CTD.
- **Say which is which in the report.** A matrix that silently sampled is S18's original sin. State
  the axes taken at full depth and those taken pairwise, so the next reader knows what was not walked.

### S22.3 — Step 0: draw the decision tree before the matrix, because the matrix takes its steps from it

**The owner's instruction:** *"maybe you
should first draw a map of customer checkout choices of combination step by step, so you know how
many different paths and diversion of choices they can make each step… and to know best maintainable
non-messy way to set those paths."*

**The matrix as first written takes its step list as given, which is a sampling error wearing a
grid.** Steps enumerated from the code are the steps somebody already built; the tree enumerates the
steps the *customer* can take, including the branches nobody implemented. Do the tree first.

**Method.** One node per decision the customer makes or the system makes for them, in order, from
first intent to the last irreversible event — cart shape, identity, destination, delivery method,
payment method, payment execution, outcome, fulfilment, delivery, and the reversals. At each node
list **every branch**, not the common ones. Then:

1. **Count the leaves.** That number is the honest size of the problem, and it is usually an order of
   magnitude larger than the team's mental model. It is also the number the S18/S22 depth rule then
   bounds — money paths at full depth, the rest pairwise.
2. **Mark where branches converge.** *This is the maintainability question and it is the reason to
   draw the tree at all.* Fifty-four paths collapsing into six screens is a good design; fifty-four
   staying fifty-four is a mess that will be maintained forever. **Converge as early as the domain
   allows, and keep separate only what genuinely differs** — and write down which is which, because
   the next person will otherwise merge two paths that had a reason to be apart, or split one that
   did not.
3. **Mark every node where the screen changes.** That set, exactly, is the preview-fixture list —
   which answers *"what has to exist before this can be themed"* without anybody guessing.
4. **Mark every node where control leaves the system** — a hosted payment page, a carrier's site, a
   counter, a bank. Each is a **round trip**, and each needs the return path enumerated as carefully
   as the outgoing one. The classic miss is a branch that leaves and has no drawn way back:
   abandoned at the gateway, closed the tab after paying, the callback that never came.
5. **Mark every node that needs an operator gate** before the object can move on — and be explicit
   where the honest answer is *none*, because a blank reads as an oversight.

**What the tree catches that the matrix alone does not:** a branch that exists in the UI and has no
handler; a branch the code handles that no UI can reach (S13 from the other end); two branches that
were drawn separately and behave identically, which is cost with no benefit; and the branches that
only appear after something goes wrong, which are the ones nobody draws because nobody demonstrates
them.

**Then build the matrix from the tree's steps**, not from the code's. The tree is also the artefact to
keep: it is the one document a new person can read to learn what the system is *for*, and it dates
far more slowly than the code.

### S22.4 — Closure rule: the authority's error table *is* the outcome column

**The owner's statement of the closure condition:** *"every api or return
should have a ui or admin response on ui, and every combination of user possible behaviour or
situation of purchase cycle should have a catch on UI or admin… each combination may need a theming
of layout or flag design… to make sure no api response or flow got missed or unattended to on
screen and by system handling."*

That is the sweep's closure condition and it fixes the sweep's worst weakness. *"Enumerate the
outcomes"* invites invention, and an invented list is a sampled list wearing a suit. **It does not
need inventing: every provider has already enumerated its outcomes, exhaustively, in the error table
at the back of its manual.** Transcribe it.

**So S18 and S22 join here.** S18 reads the authority for the *contract*; S22 reads the same
authority's **error table** for the *outcome column*, and the join is one row per code:

| Provider code | Meaning, verbatim | **Handled** | **Surfaced** | **Designed** |
|---|---|---|---|---|

**The three columns fail independently, which is why one column is not enough:**

- **Handled** — the code reaches a deterministic branch. Not a `default`, not a fallback to a
  neighbouring meaning, not silence. *A code mapped onto another code's meaning is worse than an
  unhandled one, because it is confidently wrong.*
- **Surfaced** — a human sees it, on a screen, per S22's four tests. A log line, a digest, a cron
  exit code and a table row with no screen all fail here. This is the SRE **actionable alerting**
  rule: an alert that does not tell a human what to do is noise.
- **Designed** — it has a visual form somebody chose: which flag, which colour, which severity,
  which position, blocking or not. **An error rendered as raw text in the default font is handled
  and surfaced and still fails**, because the operator cannot tell at a glance whether it is urgent,
  and the customer cannot tell whether they still have to do something.

**This is also what makes theming estimable rather than open-ended.** The designer does not need a
layout per code — they need one per **surface kind**. Count the kinds, not the codes: blocking
refusal, non-blocking warning, informational note, badge on a list row, panel on a detail page,
empty state, disabled control with a reason. **Every code maps to exactly one kind, and the kinds
are a dozen.** Report both numbers: *N codes across K kinds* — the first is the audit's workload,
the second is the designer's.

**The same closure applies to the other direction — user actions.** Every action a user can take
that the system can refuse is an outcome with the same three columns: an invalid coupon, a
quantity beyond stock, an address the carrier will not serve, a method unavailable for the
destination, a session that expired mid-checkout, a double submit, a back-button replay. The
enumeration comes from the **render-guard census and the error-path inventory** (passes 1 and 3
above) rather than from a vendor manual, but the rule is identical: **handled, surfaced, designed.**

**What "no gap" means, stated so it can be checked:** every row of every authority's error table,
and every refusal the system itself can produce, has all three columns filled. Anything else is
`UNVERIFIED` and is a task. *A provider code with no branch is a bug; a branch with no screen is a
silence; a screen with no design is a message nobody reads in time.*

### S22.5 — What "handled" means, and it is not a `catch`

**The owner's definition, given against a scoring that had reported 26 of 26 handled:**

> *"Handled meant it is a closed loop and nothing dies quietly without a human actually noticing or
> taking action. Code may have a catch and quietly log it, but any exception should be noticed by
> admin dashboard, at least a flag or a badge for each situation. Admin may choose to diffuse or
> ignore, but it should be admin's decision, not quietly logged. You should determine whether the
> response requires actual follow up, so the UX for both admin and customer is fully informed — that
> the entire operation is a complete, or dismissed as an informed decision."*

**That is the terminal condition for this sweep, and it replaces the weak column outright:**

> **Every operation ends COMPLETED or DISMISSED-BY-A-PERSON. There is no third ending. "Logged" is
> not an ending.**

A `catch` that writes a log line is **not** handled. It is *caught* — a different, much weaker
property that only says the process did not crash. Scoring the two as one is how an audit reports
clean on a system whose every failure is invisible. **Score five columns, not three:**

| Column | The test | Failure mode it catches |
|---|---|---|
| **Caught** | the process does not crash, the request does not 500 | the weakest property, and the one most often mistaken for the others |
| **Classified** | **somebody decided, in advance and in writing, whether this outcome needs follow-up or is informational.** Not inferred at read time | the whole table treated as one severity, so nothing can be prioritised and everything is either noise or missed |
| **Raised** | if it needs follow-up, it reaches a **flag or badge on the screen the operator already opens** — not a log, not a digest, not an exit code | the silence this sweep exists for |
| **Closable** | a person can **dismiss it, and the dismissal is recorded** — who, when, why. Dismissing is an act, not an absence | an alarm that cannot be cleared becomes wallpaper within a week, and wallpaper is the same as silence |
| **Designed** | it has a visual form somebody chose: severity, colour, position, blocking or not | the operator cannot tell urgent from routine at a glance, so triage happens by reading everything |

**Classifying a vendor's code table, the shape that works:** one label per row from a set of
three — *customer retries* / *operator fixes* / *ours* — chosen in writing, with the customer
sentence and the operator surface each label produces. Then four rules the table will force:
**a default bucket** (the sandbox returns codes that are in no manual; unknown ⇒ ours, raised);
**text-decided codes** (one code, several messages — the classifier takes both); **the customer
never reads a parameter name** (ours and operator share one sentence); and **pre-checks beat
refusals** (every amount or state rule the vendor publishes is a guard before the call). Expect
*ours* to be the largest bucket — most of any gateway's table is malformed requests — and expect
at least one already-distinguished code to have the wrong sentence, because a specific sentence
is trusted and nobody re-reads it against the manual.

**"Ignore" is a legitimate outcome and it must be expensive enough to be real.** The owner's
formulation is exact: the admin may diffuse or ignore, *but it must be the admin's decision.* So a
dismissal path is **required**, and it must capture a reason and a person. A system that cannot
record *"I looked at this and decided it did not matter"* forces its operator to choose between
acting on noise and ignoring signal — and they will choose ignoring, every time, and then miss the
one that mattered.

**Classification is the auditor's own work, not the developer's.** For every outcome in the table,
say which of these it is, and say it in the report:

- **Needs follow-up** — a person must do something. Raise, and keep raising until dismissed.
- **Needs telling, not doing** — the customer or operator should know; no action. Show once.
- **Informational** — genuinely nothing. **Say so explicitly**, because a blank in this column is
  indistinguishable from an oversight, and the next auditor will re-derive it.

**And both audiences, always.** An outcome the customer bears — their payment refused, their parcel
returned, their refund past its window — needs a customer surface *and* an operator surface, and
they say different things. "Fully informed" in the owner's sentence means both, not either.

**The grading follows directly.** An outcome that needs follow-up and is only logged: **HIGH**, and
it is HIGH whether or not money is involved, because the failure is the invisibility rather than the
amount. An outcome raised with no way to dismiss it: **MEDIUM**, rising to HIGH once the count is
large enough that the screen is ignored. An outcome unclassified: **MEDIUM** — nobody has decided,
so nobody can be wrong yet, but nobody can be right either.

### S22.6 — Mode errors and invisible scope: a control must show what it will act on

**The defect:** if rows are selected and the
operator then re-sorts, re-filters or pages, **a naive list keeps the ticks against different
records** — so the button now acts on a set nobody chose and nobody can see.

**This class has names and they are old ones.** Raskin's *The Humane Interface* calls it a **mode
error** — the same action producing different results depending on a state the user cannot see — and
names modes a primary cause of human error. Nielsen's first heuristic is **visibility of system
status**. In list UIs it shows up as **scope ambiguity** and **stale selection**. Use those words in
findings; *"confusing"* is not a finding, *"this control has two scopes and neither is shown"* is.

**The rule: a control that acts on a set must make the set visible, unambiguous, and current.**

Three questions, per control that acts on more than one thing:

1. **What exactly will this act on** — the rows I can see, or everything matching a filter I set
   three screens ago? If the answer is not on screen, that is the finding. **Never one control for
   both scopes**: a header checkbox meaning *"all 312"* is how somebody marks three hundred orders
   dispatched intending fifty. Page scope is the safe default; *"select all N matching"* is a
   separate, visibly different, deliberate act.
2. **What happens to the selection when the view changes?** Re-sort, re-filter, change page size,
   page forward. **Silently keeping ticks against new rows is the defect.** Either clear the
   selection and say so, or carry it as an explicitly filter-defined set that survives paging and
   dies when the filter changes. Predictable beats clever: an operator who loses eight ticks and is
   told why re-ticks them; one who silently acts on the wrong eight never finds out.
3. **Is the mode itself visible?** This is the same defect outside lists, and it is worse where money
   is involved — **a test/sandbox gateway mode that looks identical to live is a mode error with a
   payment behind it.** Check every environment switch, impersonation session, draft-vs-published
   toggle, maintenance flag and preview mode: does the screen say which one it is in, everywhere it
   matters, or only on the page where it was set?

**Grading.** A destructive or money-moving action whose scope is not visible: **HIGH**. A selection
that survives a view change without saying so: **HIGH** if it feeds a bulk action, **MEDIUM**
otherwise. An invisible mode that changes where money goes: **HIGH**, always.

**The sentence:** *the operator should never have to remember what the screen is doing.*

### S22.7 — Do not invent admin UX; the conventions are settled

**The owner's instruction:** *"reference to shopify or woocommerce or whatever
best ecommerce standard, do not reinvent the wheel, only improve."*

**An operator who has run any shop already knows how an admin works.** Shopify, WooCommerce and
Magento converged decades of operator hours onto the same handful of shapes, and a product that
invents its own spends the operator's attention teaching them a layout instead of showing them their
orders. **Divergence is a cost paid on every single screen, forever.**

So when a surface from this sweep has to be designed, **name the established pattern it follows**
before drawing anything:

| Need | The settled shape |
|---|---|
| A list of records | filter bar, saved views/tabs, per-page selector, sortable columns, row checkboxes, a sticky bulk bar that appears on selection, paging with a total |
| Status | a **pill** with a colour and a word, consistent per state across every screen it appears on |
| An exception on a record | a banner at the top of the detail page and a marker on the list row — never only one of the two |
| A bulk action | select → action menu → **confirm sheet listing what will happen and to how many** → per-row result |
| A record detail | header with the key facts and the primary action, then panels, then a **timeline of what happened when** |
| Nothing yet | an **empty state** with one sentence and the action that ends it, never a blank table |
| A field the operator cannot use | disabled, **with the reason beside it** |

**Improve only where the domain genuinely differs**, and say why in the commit: a 字軌 invoice book,
a two-month filing 期, 取貨付款's money-at-the-counter, a carrier upload that takes a spreadsheet.
Those have no equivalent in a Shopify admin and are where invention is warranted. **A paging
control is not.**

**The audit question, then, is not "is this well designed?"** — it is **"which established pattern
is this, and if none, what does the domain require that the established one could not express?"** An
answer of *"it just grew that way"* is a finding, and it is the cheapest kind to fix while the
screens are still being built.

### S22 report line

Report line format: `S22 — F flows; S steps × O outcomes × A audiences = N cells, money paths at full depth and the rest pairwise (say which); K OK, G GAP, U UNVERIFIED; render guards found R, with a fixture X of R; enum state coverage S/S', transition coverage T/T'; provider codes C across K surface kinds; caught A, classified L, raised R, closable X, designed D; outcomes needing follow-up that are only logged: N (each HIGH).`

