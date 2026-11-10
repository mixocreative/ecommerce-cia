# State machines — §5 separate machines, §6 the transition audit, §7 purchase flow and status symmetry

> Split from `doctrine.md` on 2026-11-10, text unchanged; sections keep their numbers because findings and project memories cite them. Loaded by `ecommerce-cia` at Step 3, right after `doctrine.md`.

# 5. State Machines — Never Collapse Everything Into `order.status`

Reconstruct and audit separate interacting state machines.

At minimum consider:

## Order

Potential semantic states:

- draft
- checkout_started
- placed
- confirmed
- processing
- partially_completed
- completed
- cancelled

Do not assume these exact labels.

Determine actual semantics.

## Payment

Potential semantic states:

- not_started
- not_required
- initiated
- customer_action_required
- payment_instruction_issued
- awaiting_payment
- authorized
- captured / paid
- failed
- expired
- cancelled
- partially_refunded
- refunded
- disputed / chargeback

Different payment methods use different subsets.

## Inventory

Potential states:

- available
- reserved
- committed
- released
- fulfilled
- return_pending
- restocked
- written_off

## Fulfillment / Shipment

Potential states:

- not_created
- destination_selected
- label_requested
- label_created
- awaiting_handoff
- accepted_by_carrier
- in_transit
- pickup_ready
- delivered
- picked_up
- pickup_expired
- reroute_required
- return_in_transit
- returned
- lost
- damaged
- cancelled

## COD / Collection

Where payment is collected by a carrier or convenience store, distinguish where applicable:

- payment_due_at_delivery
- collected_from_customer
- provider_holding_funds
- settlement_pending
- settled_to_merchant
- failed_collection
- returned_uncollected

"Customer picked up parcel" and "money has settled into merchant account" are not necessarily the same financial state.

When the shop's policy restricts pay-on-arrival to one channel (typically convenience-store pickup), the audit proves the restriction structurally: the other channels have no COD option in checkout, no COD branch in the order state machine, and no admin toggle that could enable one. Then trace the allowed channel end to end: which callback or report is the settlement evidence, what the order status is before it arrives, what happens on `failed_collection` / `returned_uncollected` (restock, cancel, invoice duty), and what the customer is told at each step.

## Refund

Potential states:

- requested
- approved
- provider_submitted
- pending
- partially_completed
- completed
- failed
- manual_action_required

## Digital Entitlement

Potential states:

- unavailable
- eligible
- active
- exhausted
- expired
- suspended
- revoked

Keep entitlement separate from individual signed download URLs.

## Free Acquisition

Potential states:

- eligible
- gated
- claim_started
- qualification_failed
- granted
- exhausted
- revoked

This may exist with or without a conventional order.

## Invoice / Tax Document

Potential states:

- not_required
- pending_issue
- issued
- issue_failed
- correction_required
- allowance / credit_pending
- partially_adjusted
- fully_adjusted
- void_pending
- voided

Refund state and invoice state must not be assumed identical.

## Coupon / Promotion

Potential states:

- available
- reserved
- redeemed
- released
- restored
- expired

## Reward / Points

Model preferably as ledger entries rather than a mutable unexplained balance.

---

# 6. State Transition Audit

For every important transition, identify:

1. Previous valid state
2. Trigger
3. Actor
4. Authorization
5. Validation
6. Transaction boundary
7. Idempotency mechanism
8. State write
9. Financial effect
10. Inventory effect
11. Entitlement effect
12. Invoice effect
13. Notification effect
14. Audit event
15. Retry behavior
16. Rollback/compensation behavior
17. Customer-visible result
18. Admin-visible result

Then deliberately test — this is the S23 arrival × perturbation grid, filled once there and cited here, with the sequence diagram it comes from:

- duplicate trigger
- concurrent trigger
- delayed trigger
- reordered trigger
- missing trigger
- malformed trigger
- provider timeout
- local DB timeout
- successful remote call + failed local transaction
- successful local transaction + failed response
- admin intervention during pending operation

---

# 7. Purchase Flow & Status Symmetry

Verify the customer-facing representation and admin-facing representation derive from compatible authoritative state.

Audit at least:

## Draft / Cart

Customer:
- basket contents
- item price
- stock warning
- coupon state
- free-item eligibility

Admin/analytics where applicable:
- abandoned-cart visibility
- no false order creation

## Pending Payment

Customer:
- clear pending state
- payment instruction where applicable
- expiration
- retry behavior

Admin:
- payment attempt
- stock reservation
- expiration/release behavior
- provider reconciliation state

## Paid / Processing

Customer:
- confirmed order
- receipt/invoice state where applicable

Admin:
- fulfillment readiness
- inventory committed
- payment transaction traceability

## Partial Fulfillment / Split Ship

Customer:
- per-item or per-shipment tracking

Admin:
- per-fulfillment state
- residual unfulfilled quantities

## Digital Delivery

Customer:
- entitlement/download availability

Admin:
- grant reason
- entitlement state
- download event history

## Cancellation / Refund

Customer:
- accurate pending/completed refund semantics

Admin:
- provider refund state
- ledger adjustment
- inventory decision
- entitlement decision
- invoice/tax adjustment

Do not force all subsystems into a single synchronous moment.

Controlled eventual consistency is acceptable if:

- authority is known
- pending states are visible
- reconciliation exists
- stale states do not remain indefinitely

---

**Reading receipt: _one status column hides several machines_.** Quote this phrase on the Step 7 receipts line to show this
file was read rather than inferred from the skill's index. It appears nowhere else.
