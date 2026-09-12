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

