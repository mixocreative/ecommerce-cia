# Reporting — test matrix, finding format, severity, verified controls, final output, behavioural rules (§26–§31)

Loaded by `ecommerce-cia` before writing any finding and before the Step 7 report.

# 26. Test Matrix

For every critical transaction flow, test at least:

## Happy Path

Normal success.

## Duplicate

Same request/event twice.

## Concurrent

Two conflicting valid requests simultaneously.

## Timeout

Remote side may have succeeded while local side timed out.

## Retry

Same operation retried later.

## Reordering

Events arrive in unexpected order.

## Partial Failure

One subsystem succeeds while another fails.

## Abandonment

Customer closes browser.

## Admin Collision

Admin modifies order while external event arrives.

## Stale Data

UI acts on data that has changed.

## Provider Outage

Third-party unavailable.

## Recovery

System eventually reconciles.

Apply this matrix to:

- paid checkout
- async payment
- zero-total checkout
- coupon-gated free acquisition
- inventory reservation
- download entitlement
- refund
- invoice
- logistics
- COD settlement

---

# 27. Required Finding Format

Every reported issue must contain:

## ID

Unique audit finding identifier.

## Severity

CRITICAL / HIGH / MEDIUM / LOW / INFORMATIONAL

**The floor, from two fixture runs (2026-09-15) that graded one level low on four of ten and three
of sixteen rows:** a defect on a money or safety path is graded by **what happens to the money or
the person when it fires**, not by how small the code is. *Money lost, doubled, or recorded as
paid when it was not — with no notice* is **CRITICAL**, even when the fix is one predicate: an
`UPDATE … WHERE id = ?` that lets a payment be overwritten as expired, a `catch` that answers the
provider "received" while the write failed, a verify that returns true on its own exception. *A
person cannot see or act on a money state* (an unrendered terminal state, an alarm that reaches
a log) is **HIGH**, never MEDIUM. *A detector that cannot tell blind from clean* on a money path
is **HIGH**. *A test that proves nothing* on a money path is **HIGH**, because every earlier green
it produced was a claim. MEDIUM is for defects with a working fallback or a person already in the
loop; LOW is for what costs nothing when it fires. When in doubt between two grades on a money
path, the higher one is right — an under-graded money defect is the one that ships.

**Grading is not filing — the promotion rule.** An observation that stayed in step prose has not
been reported. Two runs of the sibling skill's doctrine on its own fixture
(`../cia/tests/RUNS.md`, 2026-09-20) scored 10/10 and 6/10 on identical text; all three of the
cheaper run's misses were promotion failures, not discovery failures — it named the fail-open
catch, the unread heartbeat and the assert-nothing test in its own narrative and filed none of
them as findings. The reporting reflex that produced the 10/10 came from a sentence in the
harness prompt rather than from the doctrine, which is the instrument scoring its own
scaffolding. The same reflex is load-bearing here, where a missed promotion is a missed payment:

**Every observation that meets a threshold above becomes a numbered finding — an ID, a grade, a
`path:line` and the invariant it violates — in the same pass that saw it.** "Noted", "worth
checking", "could be tightened", and a clause inside a step description are not findings and do
not count as reported. An observation that does *not* meet a threshold still gets a sentence
naming the grade it failed to reach; ungraded prose is how a real defect leaves an audit. When
the auditor cannot decide whether a threshold is met, it is met: file at the higher grade with
confidence POSSIBLE and let the fix-or-escalate pass settle it. Filing costs a paragraph. Not
filing costs the defect.

**And a site in a sweep line is not a finding.** The first cold run of the live fixture
(2026-09-24) listed `public/index.php:91-93` — the checkout quantity, "`(int)` cast, no bounds"
— among the sites of its S11 line, and never filed the defect. A customer ordering `-3` raised
the shop's stock and wrote a negative total, and the audit had *looked straight at it*. Sweep
lines enumerate where you looked; the findings list is what you found. A site that met a
threshold and appears only in the enumeration is the same miss as one nobody visited, and it is
harder to notice because the line looks thorough.

## Confidence

CONFIRMED / HIGH-CONFIDENCE / POSSIBLE

## VSM Classification

System 1 / 2 / 3 / 3* / 4 / 5

## Domain

Payment / Inventory / Logistics / Digital / Free Acquisition / Invoice / Security / UI / i18n / Admin / etc.

## Defect Class
The §0.9 taxonomy term (TOCTOU race, temporal coupling / stale snapshot, semantic drift, dead control, fail-open default, vacuous pass, deferred-work residue, rename residue, boundary schema drift, cascade / retry storm, or "single-component" when the defect is not cross-boundary).

## Boundary Location
The two sides the defect lives between, as `producer → consumer` or `Step N (what) → Step N+1 (what)`. Examples: `Checkout::placeOrder (deadline frozen) → OrderDesk::offeredMethods (settings re-read)`, `gateway callback parser → SelfHealDecision`. Add the VSM channel the defect sits on, e.g. `System 3 → System 1`, `System 3* → System 3`, `System 4 ↔ vendor`. "None" is acceptable only when Defect Class is single-component.

## Invariant

What must remain true.

## Evidence

Exact:

- file
- class
- function
- route
- endpoint
- schema
- query
- UI
- provider documentation
- configuration

where available.

## Observed Behavior

What the system currently does.

## Failure Scenario

Concrete reproducible or logically demonstrated sequence.

## Impact (emergent)

What fails downstream as a result, then customer, financial, security or operational consequence.

## Recommended Fix

Technology-appropriate remediation.

## Verification Test

How to prove the defect is fixed.

---

# 28. Severity Model

## Critical

Likely or demonstrated:

- financial loss
- unauthorized data/access
- payment forgery
- unlimited digital access bypass
- systemic overselling
- unreconcilable ledger corruption
- major privilege escalation

## High

Serious transactional or operational corruption under realistic conditions.

## Medium

Important correctness, recovery, UX, admin or localized-state defect without immediate catastrophic consequence.

## Low

Limited edge case, maintainability issue or minor inconsistency.

## Informational

Improvement, hardening or verified design consideration without an identified defect.

---

# 29. Verified Controls

Do not produce only negative findings.

Record important controls proven to be correct.

Examples:

- payment callback MAC validation confirmed
- provider transaction ID uniquely constrained
- duplicate callback produces no second financial effect
- inventory reservation is atomic
- digital objects are private
- entitlement is server-validated
- zero-value checkout does not fake gateway payment
- coupon redemption is atomic
- free-acquisition grant reason is auditable
- invoice retry queue exists
- logistics reconciliation query exists

This prevents repeated audits from wasting effort on already verified architecture.

---

# 29a. The Evidence Ledger — capability × verdict × artefact

Verified controls (§29) say what the auditor believes after reading. The ledger says what
the run can **prove**. It is one table, it appears in every report, and it is the only place in
this doctrine where a paragraph of correct source code counts for nothing.

**Rows.** Every capability the shop claims. The §0.9 step-0 map fixes the row list, and
these rows are mandatory whenever the shop has the capability at all — a shop that lacks one
writes `N/A` with the reason, never nothing:

`Product` - `Variant` - `Stock level shown` - `Cart` - `Coupon / discount` - `Checkout` -
`Payment authorisation` - `Gateway callback` - `Order creation` - `Stock deduction` -
`Oversell refusal` - `Abandoned checkout` - `Cancellation` - `Refund` - `Restock` -
`Digital entitlement` - `Pickup / CVS selection` - `Shipping state` - `Customer email` -
`Invoice / receipt` - `Admin control` - `Reconciliation`.

Each row's proof is the state-delta ladder and its adversarial rows in `browser-walks.md` §12,
run against the running shop. The stock chain is the one that is most often reported PASS from
reading: `stock 5 -> customer buys 2 -> payment succeeds -> 3 in the database -> 3 on the admin
screen -> 3 (or sold-out) on the storefront -> reverse per the shop's written policy`. Six
observations, six artefacts. "The decrement is implemented in `StockReducer`" is none of them.

**Columns.**

| Capability | Verdict | Evidence (artefact path) | What the evidence shows |
|---|---|---|---|

**Verdicts, and the only things that produce them:**

- **PASS** — an artefact produced *by this run* shows the capability behaving correctly, end to
  end. An artefact is a file on disk or a command output captured this session: a test runner's
  line naming the test that ran, an HTTP status with the response, a stored row read back after
  the operation, a screenshot, a log line with its timestamp. `browser-walks.md` §14 fixes what
  each kind of artefact is allowed to prove.
- **FAIL** — an artefact shows it behaving incorrectly. A FAIL row carries the finding ID.
- **UNVERIFIED** — everything else: no artefact, an artefact from an earlier run, an artefact
  that proves a neighbouring fact, or a capability this tier excluded.

**The rule that gives the ledger its value: reading the source can never produce PASS.** Not
"the code clearly does this", not "the test for it exists", not "the handler is registered", not
"I traced every branch". That is how a defect is *found*; it is not how a capability is
*proved*. An auditor who has read a capability's whole implementation and run nothing against it
writes UNVERIFIED and is right to. The ledger is deliberately harsher than everything else in
this skill, because everything else rewards good reading, and the ledger exists to measure the
thing reading cannot reach.

**UNVERIFIED is a result, not an apology.** A report with twelve honest UNVERIFIED rows and a
named tier is worth more than one with twelve PASS rows a reader cannot check. What is forbidden
is the promotion: an UNVERIFIED cell that becomes PASS because the auditor later read more code,
because a neighbouring capability passed, or because the suite is green overall. A green suite
promotes the rows whose *named tests* ran, and promotes nothing else.

**No blank cells, no omitted rows.** A capability with nothing to say is UNVERIFIED with the
reason in the evidence column ("tier: Screen, not walked"; "no environment - §0.8 rung 5: <the
one thing the owner must do>"). A capability the system does not have is `N/A` with the reason.
An omitted row is the report claiming a smaller system than the map found, which is S14 scope
shadow committed by the auditor.

**A PASS covers the capability's refusals, not only its successes.** The same run marked
`Checkout` PASS on two artefacts — a valid order created, an over-quantity order refused — while
a negative quantity on that same route raised stock and wrote a negative total. Both artefacts
were real, the row was still wrong: the capability is *checkout*, and the auditor had exercised
two of its paths. So every PASS row's fourth column says **what the artefact covered**, in the
capability's own terms ("valid order; over-quantity refused" — at which point the reader sees
what is missing), and a capability exercised only on its happy path is **PARTIAL**, which is
read as UNVERIFIED by anyone deciding whether to launch. The honest question before writing PASS
is not "did it work?" but "which of this capability's ways of being asked did I ask?"

**Where the rows come from, and the order they are written in:** the ledger is built at the
*start* of the runtime steps, all rows UNVERIFIED, and filled as artefacts arrive. Built at the
end, it is written from memory, and memory is where PASS comes from reading.

---

# 30. Required Final Audit Output

Always organize the final report into **five sections**.

## 1. Systemic Risks & Algedonic Signals

Only true showstoppers or severe systemic threats.

Prioritize:

- money
- authorization
- inventory
- digital leakage
- coupon/free-acquisition bypass
- corruption
- irrecoverable state

## 2. Status Symmetry & State-Machine Gaps

Show mismatches among:

- customer
- admin
- database
- gateway
- fulfillment
- entitlement
- free acquisition
- invoice
- settlement

Explain the missing or invalid transition.

## 3. UI/UX, Localization & Operational Gaps

Include:

- empty
- loading
- error
- pending
- partial success
- stale external confirmation
- i18n
- currency
- locale
- regional checkout
- free-download UX
- invoice UX
- admin handling gaps

## 4. Verified Correct Controls

List high-value controls verified from evidence.

Do not give generic praise.

## 5. Concrete Action Plan

Prioritize:

### P0 — Stop the Line
Immediate integrity/security fixes.

### P1 — Required Before Production
Major correctness/recovery issues.

### P2 — Operational Completeness
Admin, reconciliation, edge states.

### P3 — Hardening / UX / Optimization
Non-blocking improvements.

For each item specify:

- component
- change
- expected invariant
- test required

---

# 31. Auditor Behavioral Rules

You **must**:

- trace actual transaction flows
- inspect implementation evidence
- reconstruct state machines
- identify systems of record
- test concurrency logically
- separate payment from fulfillment
- separate payment from zero-value acquisition
- separate refund from invoice adjustment
- separate entitlement from download token
- distinguish browser results from authoritative provider state
- recognize eventual consistency
- verify provider-specific behavior against current documentation when available
- adapt to jurisdiction
- identify missing admin recovery paths
- report verified controls

You **must not**:

- assume Stripe-like behavior everywhere
- assume card payment everywhere
- assume every entitlement requires payment
- assume free download requires a conventional order
- assume shipping means payment
- assume pickup means settlement
- assume refund means inventory restock
- assume refund means invoice void
- assume a browser success redirect means payment success
- assume Redis is mandatory
- assume S3 is mandatory
- assume every currency uses two decimal places
- assume provider limits from memory
- assume Taiwan rules globally
- assume US/EU rules apply in Taiwan
- generate speculative vulnerabilities without evidence
- recommend architectural complexity without a demonstrated need

---

**Reading receipt: _the ledger is harsher on purpose_.** Quote this phrase on the Step 7 receipts line to show this
file was read rather than inferred from the skill's index. It appears nowhere else.
