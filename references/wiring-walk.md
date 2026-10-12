# The reference-guided wiring walk — function, wiring and lifecycle rules, proved together

Loaded in Step 3 right after `reference-systems.md` (whose selection table and business-rule trace it feeds) and
before `battle-testing.md` (which supplies rule cards, mutation and evidence packets for the faults below). It is
the **default recommendation** for any shop that runs its own commerce engine: when the owner asks "what should
we audit next?", the answer is a **reference-guided Walk** — map every money and fulfilment flow, inspect every
connection, run the targeted failures below, and hand back a gap register with exact code locations and proof
status.

---

## §1 — The question this file exists to ask

A feature comparison asks: *"Do we have refunds?"*

A wiring audit asks: *"What happens if a payment succeeds, the callback is lost, stock changes, the invoice write
fails, and the operator opens the order two days later?"*

**That second sentence is where custom commerce engines break**, and no module feature list can answer it. Every
run of this file states that question for the shop being audited — with its own provider, its own invoice step
and its own admin screen substituted — **in the first paragraph of the report**, and the report answers it with
evidence: what the customer saw, what the order page showed, what the books held, which job noticed, and when.

## §2 — The reference is a checklist of stages, never the truth

Reference systems (`reference-systems.md` §2) tell the audit **which lifecycle stages a normal shop has**, so a
stage the custom engine skipped is noticed. They do not say what is correct.

- **ProcessWire Commerce** is the default stage checklist for a ProcessWire shop. Its public documentation is
  work in progress, and its code has known unresolved issues — the open issue at the time of writing,
  [#26](https://github.com/kongondo/ProcessWireCommerce/issues/26) (checked 2026-10-12), reports dashboard revenue
  counted without a status filter or a monthly reset: a wiring defect of exactly the class this file hunts. Re-read
  its issue list at audit time and cite the commit compared against.
- **Compare workflow shape, then judge against stricter rules.** The audit lines up the reference's stages beside
  ours (§4), then judges ours against **our own rules** (owner decisions, ADRs, `doctrine.md` §8.0 invariants), the
  **gateway vendors' official contracts** (NewebPay, ECPay, LINE Pay, PAYUNi, TapPay manuals and their sandboxes),
  **Taiwan invoice and consumer law** (`taiwan-adapter.md`), the **carrier/logistics contracts**, and our own
  architecture. Where the reference and an authority disagree, the authority wins and the reference is recorded
  as a contradiction (`evidence.md` §E7), never as a finding against us.
- A reference stage we deliberately do not have is `NOT-APPLICABLE` with the scope evidence (`reference-systems.md`
  §4) — not a gap, and not silently dropped.

## §3 — Three layers, all three every time

| Layer | The question | Typical proof | A finding here sounds like |
|---|---|---|---|
| **L1 Function logic** | Does each function calculate, validate, authorise and change state correctly **on its own**? | unit test with boundary values | "refund total ignores a prior partial refund" |
| **L2 Relationship wiring** | Does every function that must call another **actually call it**, pass the right values, **persist** the result, and handle retry, error and **partial completion**? | integration test that breaks the connection (§5 Q7) | "the paid callback never enqueues the invoice obligation when the mail step throws first" |
| **L3 Lifecycle business rules** | Does the **combined system** obey the shop's rules when events arrive **late, twice or out of order**? | fault injection (§6) through the real entry points, read at every observer | "a callback after expiry marks a restocked order paid; nothing appears in admin" |

The audit never stops at L1. *"The refund calculation is correct"* is an L1 result; the L2 and L3 questions in §7
are what make it a commerce audit. **Every finding names its layer**; the report counts findings per layer, and a
report with L1 findings only has not been run.

## §4 — The lifecycle state map (mandatory, one row per lifecycle the shop has)

Build this before reading any function. Each cell names real states, functions, tables and screens — `path:line`
where it is code — or `UNVERIFIED`. The rows below are the minimum; add rows for subscriptions, pre-orders,
gift cards, pickup, returns or anything else the shop sells.

| Lifecycle | Reference system path | Our path | Failure / retry path | Operator-visible result |
|---|---|---|---|---|
| **Checkout** | cart → order → payment | cart → locked stock → order → redirect | duplicate submit; expired order; price/coupon/postage recomputed after lock | clear refusal, or an order in a named state |
| **Payment** | gateway confirmation → paid | callback → verify signature → re-query provider → settlement | missing, forged, late, duplicate callback; browser return before / without callback | order warning and a reconciliation row |
| **Refund** | refund request → status | provider request → pending → reconcile | provider timeout with remote success; partial refund; refund twice | refund exception on the order |
| **Shipping** | fulfilment → delivery state | parcel → carrier event → customer notice | duplicate / out-of-order carrier event; store closed; parcel returned | a traceable shipment issue on the order |
| **Invoice** | order → invoice record | paid order → invoice obligation → issue / book / correction | invoice API down; obligation missing; refund without allowance/void | a visible invoice finding |
| **Download / entitlement** | paid order → download | entitlement → pinned file key → signed link | retry; expired link; file replaced or removed after sale; refund revokes | recoverable customer access, or a visible problem |

Read each row left to right and ask what the column after it assumes. The **Our path** column is drawn from the
code and the running system (`browser-walks.md` §12 ladder), never from docs. The **Operator-visible result**
column is checked on the screen the operator already opens daily — the order list and the order page — per
SKILL §0.10 item 6; a log line, an exit code or a table nobody renders is "invisible" in this column.

## §5 — Seven questions for every connection

From the §4 map and the `sweeps.md` step-0 map, list every connection between services: checkout → stock,
callback → order, order → invoice obligation, settlement → fulfilment, refund → stock / invoice / entitlement,
carrier → order, worker → admin, and so on. Each connection gets one row and **seven answers**, each with its
evidence (`path:line`, test name, artefact) or `UNVERIFIED`:

| # | Question | What "yes" needs | Sweep |
|---|---|---|---|
| Q1 | **Does the caller actually invoke the service?** On every path, including the error path and the admin path? | the call site, read; a runtime trace that shows it firing | S5, S13 |
| Q2 | **Is the result persisted?** Before anything that depends on it, inside the same transaction where it must be? | the write and a read-back after the operation | S16, §0.11 |
| Q3 | **Is the operation safe if retried twice?** | an idempotency key or a state predicate in the write; a test that sends it twice | S2, S12, S23 |
| Q4 | **Is there one authoritative state when the systems disagree?** Who wins between gateway, order row, invoice book and carrier? | a written authority rule and the code that applies it (re-query, reconcile) | S1, S4, S18 |
| Q5 | **Can a job stop without anybody noticing?** | a liveness check whose silence is itself an alert | S16, S20 |
| Q6 | **Does an unresolved case appear on the order page or admin list**, rather than only in logs? | the badge / flag / filter, rendered, in a screenshot of the real admin | S22, §0.10 item 6 |
| Q7 | **Is there a test that breaks this exact connection**, rather than testing each class separately? | a test that makes the callee fail, time out or answer twice, and asserts the caller's outcome | S21, S24 |

A connection with a `no` or `UNVERIFIED` on any of Q1–Q7 is a gap-register row (§9). Q7 is the one most audits
skip, and the reason a green suite says nothing about wiring: ten classes each tested alone prove ten functions,
not nine connections.

## §6 — Deliberate fault injection: recovery, or a visible admin problem

Run each fault through the real entry point against a local or sandbox shop (`browser-walks.md` §12–§13; never
production, never a live provider with side effects). For each, the **only two acceptable outcomes** are:
**(a) the system recovers by itself**, ending in a correct, consistent state at every observer; or **(b) the
problem becomes visible on the admin order list / order page** with enough said to act on. Anything else —
silent wrong state, a log line, an exception page, a stuck order with no flag — is a finding, graded HIGH or
above on a money path.

| # | Fault | How to inject it | What to read afterwards |
|---|---|---|---|
| F1 | **Reject the invoice write** | make the invoice API / table write fail after payment settles (test double, revoked sandbox key, a failing trigger on a local copy) | order state, invoice obligation row, admin invoice flag, retry job |
| F2 | **Replay a callback** | post the same signed notify twice, and once more an hour later | one settlement, one stock movement, one invoice, one email; second response still 200 to the gateway |
| F3 | **Callback before the customer returns** | deliver the server notify first, then the browser return (and the reverse; and return with no notify at all) | the customer page, the order row and the admin agree in every order |
| F4 | **Two checkouts on the last stock unit** | fire both concurrently (`browser-walks.md` §13), across processes, not threads in one | exactly one order holds the unit; the other is refused clearly; stock never negative |
| F5 | **Refund provider times out** | timeout locally while the sandbox actually completes the refund; then the reverse (local success recorded, provider failed) | refund record, provider state after re-query, stock, invoice allowance, customer mail, admin refund exception — all agree, or the disagreement is flagged |
| F6 | **Remove a download file after sale** | delete or replace the stored file a paid entitlement points to | the customer gets a recoverable path or a clear message; admin sees the broken entitlement |
| F7 | **Stop the reconciliation job** | disable or kill the reconcile / expiry / settlement worker for longer than its period | someone is told (S20 liveness); pending money states surface on admin instead of ageing silently |

Each fault writes an evidence packet (`battle-testing.md` §4). A fault the environment cannot exercise is
`UNPROVEN` with the exact missing condition (`reporting.md` §11a), never "skipped".

## §7 — The question banks: ask them, then answer them in the report

These are asked **per lifecycle**, and each answer cites its evidence or says `UNVERIFIED`. They are the minimum;
add the shop's own rules.

**Checkout**
1. Does the displayed price equal the **server-calculated** price at the moment the order is created?
2. Does an accepted coupon **still apply** after stock, postage, tax and destination are recomputed — and if not,
   is the customer told before paying?
3. Does the order **preserve the historical facts**: tax, unit price, address, currency, delivery method, consent
   (terms version, marketing opt-in) — so a later product edit cannot rewrite a past order?
4. Does payment success lead to **exactly one** fulfilment path (one parcel request, one entitlement, one invoice)?
5. If any later step fails, is the order **recoverable and visibly flagged**?

**Payment**
1. Is the callback's signature verified **before** any field is trusted, and is the amount compared with the order?
2. Is the paid state reached **only** from a verified callback or a provider re-query — never from the browser return?
3. Does a callback for an expired, cancelled or already-refunded order land in a visible exception, not in "paid"?
4. When callback and re-query disagree, which wins (Q4), and is the disagreement recorded?

**Refund**
1. Is the refund amount **limited to what was actually paid**, minus refunds already made?
2. Does a **partial** refund leave the order and the invoice (allowance / void) in the correct state?
3. Do the **provider result, refund record, stock restock, customer email, invoice correction and admin order
   screen agree** afterwards?
4. If the provider replies late or the job runs twice, does the system **settle once** and show any unresolved case
   to the admin?

**Shipping**
1. Is each carrier event applied once, and can an older event never overwrite a newer state?
2. Is a parcel that fails (store closed, returned, lost) a visible task on the order?
3. Does the customer notice match the parcel's real state?

**Invoice**
1. Does **every** paid order create an invoice obligation, even when the issuing call fails?
2. Is a missing or failed obligation visible, and retried without double issue?
3. Do refunds and cancellations produce the correction the Taiwan rules require (`taiwan-adapter.md`)?

**Download / entitlement**
1. Is access granted only after verified payment, and revoked (or not) by refund exactly as the policy says?
2. Does the entitlement pin the file version sold, so a replacement does not change what was bought?
3. Can a customer with an expired link recover access without the operator editing the database?

## §8 — The business-rule traceability matrix (the deliverable)

The report's centrepiece is **not** a code review. It is this matrix — one row per business rule, the summary view
of `reference-systems.md` §3's full trace (which holds the per-cell detail). Seed rows that every shop carries:

| Business rule | Code that enforces it | Connected systems | Proof | Outcome |
|---|---|---|---|---|
| Never oversell physical stock | checkout + stock ledger | cart, order, payment expiry | concurrency test (F4) | covered / gap |
| Never fulfil an unverified payment | callback reducer + provider re-query | gateway, order, download, invoice | replay / forged / early callback tests (F2, F3) | covered / gap |
| Every sale gets the right tax / invoice record | settlement + invoice obligation | order, refund, invoice book | success / failure / retry tests (F1) | covered / gap |
| Every unresolved money state reaches admin | reconciliation + findings UI | worker, order list, dashboard | forced-failure walk (F5, F7) | covered / gap |
| Refunds never exceed what was paid | refund desk + provider call | order, payment, invoice, stock | boundary + partial + double-refund tests | covered / gap |
| A paid digital sale stays downloadable | entitlement + file store | order, storage, mail | file-removed walk (F6) | covered / gap |

**Columns are exact.** "Code" is `path:symbol`; "Proof" is a test name or artefact path from **this run** at the
right authority (`evidence.md` §E2) — a unit test cannot cover a row whose rule spans systems. "Outcome" is
`covered` only when the proof ran and passed this run; otherwise `gap` with the gap-register ID, or `UNVERIFIED`.
Each row is also an obligation (`evidence.md` §E3), so a rule with two enforcing places, or none, is visible here.

## §9 — The gap register

Every `gap`, every connection with a `no` on Q1–Q7, and every fault whose outcome was neither (a) nor (b) becomes
one row:

| Gap ID | Layer (L1/L2/L3) | Lifecycle | Rule / connection | Exact location (`path:line`) | What breaks, in one sentence | Proof status | Severity | Fix owner |
|---|---|---|---|---|---|---|---|---|

**Proof status** is one of: `PROVEN` (a run of this audit reproduced it — cite the artefact), `READ` (found by
reading; no run yet), `UNPROVEN` (attempted, environment would not answer), `UNVERIFIED` (not attempted at this
tier). A register where every row says `READ` is a code review and says so in its first line.

## §10 — Tiers, and the next audit to run

- **Screen:** §4 map for every lifecycle; §5 for every connection on the Payment and Checkout rows; F2 and F4;
  §8 seed rows. Everything else `UNVERIFIED`.
- **Walk (the recommended next audit):** §4 and §5 in full; **all seven faults**; every §7 question answered;
  the §8 matrix for every money and fulfilment rule; the §9 register with exact locations and proof status.
- **Full:** as Walk, plus every rule variant and every terminal/recovery path, and `battle-testing.md` §5 mutation
  on every row marked `covered`.

## Report lines (Step 7)

```
Wiring walk (wiring-walk.md): wiring question stated for this shop: yes | no · lifecycles mapped L (reference compared: <system@version>) · connections C, Q1–Q7 all yes: Y, gaps: G · faults F1–F7 run: N/7 — recovered R, visible-to-admin V, silent S · findings by layer L1/L2/L3: a/b/c · traceability rows T: covered X / gap Y / unverified Z · gap register: path
```

---

**Reading receipt: _a feature list cannot lose a callback_.** Quote this phrase on the report's receipts line
(Step 7) to show this file was read rather than inferred from the skill's index. It appears nowhere else.
