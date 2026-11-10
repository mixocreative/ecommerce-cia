# Domain Chapters — §17–§25 (operations: admin security and operations, UI states, observability, stop-the-line conditions, data model, security)

> Split from `domains.md` on 2026-11-10, text unchanged; chapters keep their numbers because findings and project memories cite them. Loaded by `ecommerce-cia` at Step 3 with `domains.md`: read every chapter the audit profile makes relevant and say which were skipped and why.

# 17. Authentication, Authorization & Administrative Security

Audit:

- login
- logout
- password reset
- email verification
- email-change verification
- session rotation
- session invalidation
- CSRF
- IDOR
- horizontal privilege escalation
- vertical privilege escalation
- API authorization
- admin routes
- admin AJAX/API calls
- bulk operations
- export permissions
- customer-data access
- support impersonation
- secret storage
- webhook secrets
- environment separation
- sensitive log redaction
- upload security
- rate limiting

For resources such as:

`/orders/1234`

never assume authentication alone is sufficient.

Verify ownership/authorization.

---

# 18. Administrative Operations

Admin control must be operationally complete.

Verify that staff can safely handle:

- unpaid orders
- payment exceptions
- zero-value orders
- free acquisitions
- failed callbacks
- stuck fulfillment
- split fulfillment
- refund
- partial refund
- failed refund
- reshipment
- return
- digital entitlement
- download-limit override
- coupon restoration
- invoice failure
- coupon exception
- inventory correction
- customer account issues

Avoid unrestricted "edit status" fields that bypass business logic.

Prefer explicit commands such as:

- Cancel order
- Mark manual payment received
- Release reservation
- Retry invoice
- Refund item
- Revoke entitlement
- Restore coupon
- Grant entitlement
- Resend notification

Each important admin mutation should record:

- operator
- timestamp
- old state
- new state
- reason
- relevant provider reference

High-risk overrides should require additional confirmation/authorization where appropriate.

---

# 19. UI/UX — Required Component States

Every important interactive component must be evaluated for:

## Empty

Examples:

- empty cart
- no orders
- no downloads
- no saved addresses

## Loading

Examples:

- payment submission
- pickup-store search
- signed download generation
- coupon validation
- free-download claim
- refund processing

Prevent accidental double submission.

## Error

Distinguish when appropriate:

- validation error
- retryable provider failure
- hard decline
- expired payment
- out of stock
- unavailable pickup point
- expired download
- coupon exhausted
- free-acquisition limit reached
- authorization failure

## Success / Partial Success

Examples:

- payment accepted but invoice pending
- order paid but one item backordered
- partial fulfillment
- partial refund
- coupon redeemed but entitlement provisioning pending
- shipment delivered but COD settlement pending

## Stale / Pending External Confirmation

Add this as a sixth state where external providers are involved.

The system must be capable of saying:

- "Waiting for payment confirmation"
- "Carrier update pending"
- "Invoice issuance pending"

instead of falsely presenting certainty.

## Edge Cases

Audit:

- long translations
- long product titles
- missing images
- duplicate click
- refresh
- browser back button
- multiple tabs
- mobile
- network dropout
- resumed session
- expired checkout
- deleted product
- changed product price
- changed pickup point
- already-owned free product
- coupon becoming exhausted during submission

---

# 20. Observability, Reconciliation & Failure Recovery

Critical external integrations require observable state.

Where appropriate maintain:

- incoming-event log
- outgoing-operation log
- provider transaction identifiers
- raw provider status
- normalized internal status
- last synchronization time
- retry count
- reconciliation status

Use durable retry where business-critical side effects cannot safely disappear.

Examples:

- payment callback
- refund request
- invoice creation
- shipment creation
- entitlement generation

Consider inbox/outbox or equivalent patterns where transactional reliability requires them.

Provider failure must not leave ambiguous invisible state indefinitely.

Create operational queues such as:

- payment_requires_review
- refund_failed
- shipment_sync_stale
- invoice_failed
- entitlement_mismatch
- free_acquisition_failed
- settlement_mismatch

---

# 21. Algedonic / Stop-the-Line Conditions

Raise **CRITICAL ALGEdONIC ALERTS** for conditions such as:

- successful payment can create no recoverable order
- unpaid order can become fulfilled without intentional policy
- duplicate callback can create duplicate financial effect
- inventory overselling is reproducible
- refund can exceed paid amount
- one customer's order can be accessed by another
- unrestricted digital asset exposure
- download authorization bypass
- coupon-gated free download bypass
- unlimited campaign claims caused by a race
- administrator privilege bypass
- payment callback signature not validated
- provider amount/currency not validated
- financial ledger cannot reconcile
- secrets exposed publicly
- tax/invoice records materially diverge from financial reality
- systemic state corruption

These findings should appear first.

---

# 24. Database & Data-Model Audit

Inspect whether the schema can represent business reality.

Look for problematic designs such as:

`orders.status`

being forced to represent:

- payment
- fulfillment
- refund
- invoice
- download
- cancellation
- free acquisition

Prefer distinct records/domains where warranted.

Possible entities include:

- orders
- order_items
- payments
- payment_attempts
- provider_events
- refunds
- inventory_reservations
- inventory_movements
- fulfillments
- shipments
- shipment_events
- pickup_locations
- digital_entitlements
- free_acquisitions
- download_events
- invoices
- invoice_adjustments
- coupons
- coupon_redemptions
- reward_ledger
- audit_events

Do not demand these exact table names or table boundaries.

Judge whether the data model can faithfully represent the required states and history.

---

# 25. Security Audit

## Input / Output

Audit:

- validation
- encoding
- injection
- XSS
- file upload
- path traversal

## Identity

Audit:

- authentication
- authorization
- session security
- reset flows
- IDOR

## APIs

Audit:

- authorization
- replay
- rate abuse
- object ownership

## Provider Callbacks

Audit:

- signature/MAC verification
- merchant verification
- transaction correlation
- amount
- currency
- idempotency

## Sensitive Data

Audit:

- secrets
- personal data
- tokens
- payment data
- logs
- backups

## Digital Assets

Audit:

- URL guessing
- CDN origin exposure
- stale signed URL
- entitlement bypass
- counter race
- free-download abuse
- coupon enumeration

Evaluate actual risk rather than checking generic boxes without evidence.

---

**Reading receipt: _the operator's screen is where an invariant is kept or lost_.** Quote this phrase on the Step 7 receipts line to show this
file was read rather than inferred from the skill's index. It appears nowhere else.
