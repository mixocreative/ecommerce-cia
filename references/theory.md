# Theory — Stafford Beer's Viable System Model, applied to a codebase

Loaded by `ecommerce-cia` before §0.9 step 0 (the VSM map). The map assigns every component to one of the systems below; the sweeps then walk the channels between them.

> **THEORY: STAFFORD BEER'S VIABLE SYSTEM MODEL, APPLIED TO A CODEBASE.**
> Beer's claim (*Brain of the Firm*, 1972; *The Heart of Enterprise*, 1979) is that any system
> which survives in a changing environment has the same five-part structure, at every level of
> recursion: **System 1** does the work; **System 2** damps oscillation between the parts of
> System 1; **System 3** commands and allocates resources to System 1 and hears back through
> **System 3\***, an audit channel that bypasses System 1's own reporting; **System 4** faces the
> environment and the future; **System 5** holds identity and policy and receives the
> **algedonic** signal (pain/pleasure) that jumps every level when viability is threatened. The
> systems are connected by **channels**, and Ashby's Law of Requisite Variety says each channel
> must carry as much variety as the thing it regulates, or control is fictional.
>
> A codebase is such a system. Handlers, checkout, fulfilment are System 1. Locks, queues,
> deadlines, idempotency keys are System 2. Settings, flags, admin pages, config are System 3.
> Test suites, probes, reconciliation are System 3\*. Vendor specs, external APIs, callbacks are
> System 4. Defaults, catch-block posture, kill switches are System 5.
>
> **PRIMARY TARGET: CROSS-BOUNDARY INVARIANT VIOLATIONS**, also called **integration-level
> defects** or **emergent defects**. In Beer's terms every one of them is a broken, missing, or
> under-variety channel between two of those systems: a System 3 setting no System 1 code reads
> (dead control); a value System 1 froze at one moment while a later System 1 step re-reads System
> 3 live (stale snapshot); a predicate checked at SELECT and dropped at UPDATE with no System 2
> coordinator (TOCTOU); a System 4 field read against the code's belief rather than the vendor's
> definition (semantic drift); a System 3\* suite that reports OK because it never ran the tests
> that touch the store (vacuous pass: System 3\* reading System 3's own conclusion); a catch block
> with no System 5 policy behind it (fail-open). Each function is individually correct. Static
> analysis, linters and a green unit suite inspect one piece at a time and therefore cannot see a
> channel. This skill exists to see channels. Reading functions is not auditing; mapping the
> codebase onto Systems 1–5 (§0.9 step 0) and then tracing every channel of that map, one value
> from every writer to every reader, one control from the screen to the line that obeys it, is.
> Section 0.9 is the mandatory sweep list and runs before any other doctrine. Structure first,
> then wiring, then code.
>
> Stance, from Beer: the purpose of a system is what it does, not what its docs say (POSIWID);
> every System 1 unit is itself viable and gets the same five questions one recursion down;
> every guard is a variety attenuator and every default an amplifier, and each must match what
> it faces; System 1 must act without asking System 3 each step, yet System 3 must still be
> obeyed; the auditor *is* System 3\*, the channel that bypasses the system's own green report;
> and a pain signal that stops in a log file has not reached System 5.

---

# 2. VSM Governance Model

Components may participate in more than one VSM system.

Assign a primary role while documenting cross-system dependencies.

## System 1 — Primary Operations

Autonomous customer-facing and transaction execution.

Includes:

- storefront
- catalog
- search
- product configuration
- cart
- checkout
- customer account
- payment initiation
- shipping selection
- pickup-store selection
- free acquisition
- digital delivery
- fulfillment APIs
- customer order views

Rule:

System 1 should complete essential transaction work without unnecessarily blocking on:

- analytics
- reporting
- admin dashboards
- non-critical email
- marketing systems
- expensive reporting queries

Critical synchronous consistency checks remain permitted where required for correctness.

## System 2 — Coordination / Anti-Oscillation

Prevents races, duplication and contradictory execution.

Includes:

- transactional constraints
- idempotency
- webhook deduplication
- concurrency control
- reservation expiry
- queue coordination
- retry strategy
- distributed or database locks
- rate limiting
- coupon atomicity
- reward-point atomicity
- download consumption atomicity
- free-acquisition limits
- translation fallback
- duplicate notification suppression

Primary question:

> What prevents two individually valid operations from creating an invalid combined result?

## System 3 — Control & Internal Synergy

Maintains authoritative operational state.

Includes:

- order state
- payment state
- inventory state
- fulfillment state
- digital entitlement state
- free-acquisition state
- invoice state
- refund state
- financial ledger
- reconciliation
- admin operational queues
- settlement tracking

Primary question:

> Where is authoritative state held, and how do all subsystems converge toward it?

## System 3* — Independent Audit Channel

Verifies that reported operational state corresponds to reality.

Includes:

- gateway reconciliation
- logistics reconciliation
- settlement reconciliation
- inventory audits
- download access logs
- entitlement audits
- invoice reconciliation
- immutable event/audit records
- stale-state detection

System 3* must not merely read System 3's own conclusion and call that an audit.

Where practical it should compare independent evidence.

Example:

- Internal payment status = PAID
- Gateway transaction query = SUCCESS
- Ledger entry = captured amount
- Order total = captured amount

## System 4 — Intelligence & Adaptation

External sensing and future adaptation.

Includes:

- analytics
- conversion funnels
- abandoned checkout
- SEO
- FX rate feeds
- tax-rate updates
- provider capability changes
- shipping-rate updates
- fraud trends
- download bandwidth trends
- free-download abuse trends
- operational forecasting

System 4 should inform operations without unnecessarily blocking live transactions.

## System 5 — Policy, Identity & Algedonic Control

Ultimate policy and emergency authority.

Includes:

- legal jurisdiction
- privacy policy
- refund policy
- digital-content policy
- free-download policy
- entitlement policy
- tax policy
- security policy
- admin authority
- emergency payment shutdown
- download shutdown
- inventory freeze
- maintenance mode
- fraud containment

System 5 receives **algedonic alerts** when system viability is threatened.

---
