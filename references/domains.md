# Domain Chapters — §8–§21, §24–§25

Loaded by `ecommerce-cia` at Step 3. Read every chapter whose domain the §0.5 / §3 audit profile says the shop has; say in the report which chapters were skipped and why (e.g. "no digital goods — §12 skipped").

# 8. Free Products, Promotional Downloads & Zero-Value Orders

A digital entitlement does **not** always require a monetary payment.

Valid entitlement origins may include:

- paid purchase
- permanently free product
- member-tier benefit
- coupon-gated free acquisition
- promotional campaign
- email-gated download
- administrative grant
- bundle entitlement
- loyalty/reward redemption
- license migration
- replacement/reissued entitlement

Every entitlement must therefore record or derive an authoritative **grant reason**.

Examples:

- PURCHASE
- FREE_PRODUCT
- COUPON_REDEMPTION
- MEMBER_BENEFIT
- PROMOTION
- REWARD_REDEMPTION
- ADMIN_GRANT

Do not use:

`payment_status = paid`

as a universal prerequisite for entitlement activation.

Instead require:

> A digital entitlement must originate from a valid, auditable acquisition/grant event according to merchant policy.

## 8.1 Free Download Flow

For intentionally free products, audit:

free product  
→ eligibility check  
→ acquisition/grant record  
→ entitlement creation  
→ download credential generation  
→ download event

Determine whether the merchant requires:

- anonymous access
- account login
- verified email
- mailing-list consent
- member tier
- geographic restriction
- campaign qualification

Do not require account/email gating unless merchant policy or abuse risk requires it.

However, if acquisition tracking or limits exist, enforcement must occur server-side.

## 8.2 Coupon-Gated Free Download

Treat a coupon that reduces a digital product to zero as both:

1. a promotion/redemption event
2. an entitlement-generating acquisition

Example:

product price = NT$100  
coupon = FREE100  
checkout total = NT$0

The system must not require a payment gateway transaction merely because an ordinary paid purchase would.

Audit:

- coupon validity
- product applicability
- campaign dates
- account/customer eligibility
- global redemption cap
- per-customer cap
- concurrency safety
- stacking restrictions
- zero-total checkout handling
- entitlement creation
- redemption persistence
- download limits
- retry behavior
- duplicate submission
- cancellation/reversal policy

## 8.3 Zero-Total Checkout

When discounts reduce payable total to zero:

Do **not**:

- send a zero-value payment request to a gateway unless explicitly supported and intended
- fake a provider payment transaction
- mark the order as externally "paid" without semantic distinction

Prefer a state such as:

`PAYMENT = NOT_REQUIRED`

or equivalent domain semantics.

Possible flow:

checkout  
→ eligibility validated  
→ coupon atomically redeemed  
→ zero-value acquisition committed  
→ entitlement activated  
→ completed

All related writes should be transactionally consistent.

If coupon redemption succeeds but entitlement creation fails, the architecture must be able to retry or compensate safely.

## 8.4 Free Download Without Checkout

A store may intentionally offer:

`Download Free`

without creating a conventional order.

This is valid.

The auditor must determine the merchant's desired acquisition model rather than insisting on an order.

Possible model:

- acquisition_id
- product_id
- product_version
- user_id nullable
- email_hash / verified identity where applicable
- campaign_id nullable
- coupon_redemption_id nullable
- entitlement_id
- created_at

Equivalent designs are acceptable.

The invariant is:

> The system must retain enough authoritative information to determine why access was granted and enforce any applicable limits.

## 8.5 Coupon Race Conditions for Free Products

A limited campaign such as:

> "First 100 customers can download this STL free"

must enforce the limit atomically.

Unsafe pattern:

1. count redemptions
2. observe 99
3. allow redemption
4. insert record

Two concurrent users can both become #100.

Require an atomic mechanism such as:

- conditional database update
- transactional locking
- unique allocation record
- atomic counter
- equivalent concurrency-safe mechanism

Do not prescribe a specific technology.

## 8.6 Repeated Free Acquisition

Define policy for a customer who already owns the free product.

Possible valid behaviors:

- return existing entitlement without consuming another coupon
- consume a coupon but create no duplicate entitlement
- prohibit repeat redemption
- create a separate acquisition record
- extend entitlement/download allowance

The behavior must be explicit and concurrency-safe.

## 8.7 Free Download Abuse

Where relevant audit:

- scripted coupon guessing
- enumeration
- credential stuffing
- mass account creation
- disposable-email abuse
- repeated anonymous acquisition
- signed-link sharing
- hotlinking
- bot downloads
- bandwidth exhaustion
- download counter races

Controls should be proportional to risk.

Possible controls include:

- rate limiting
- CAPTCHA/challenge
- verified account/email
- opaque coupon codes
- acquisition limits
- short-lived credentials
- abuse telemetry

Do not automatically require every control for every free download.

## 8.8 Coupon Reversal

Explicitly define whether a free-download coupon is:

- consumed permanently on successful acquisition
- restored if acquisition fails
- restored if entitlement is revoked
- never restored after the asset has been downloaded
- manually restorable by admin

Do not assume normal refund semantics apply because no monetary payment occurred.

The redemption ledger must remain auditable.

---

# 9. Payment Gateway Integrity Audit

Verify:

## Authenticity

- callback signature / MAC / cryptographic verification
- correct secret selection
- merchant identity
- environment separation
- timing/replay controls when provided

## Correlation

Validate:

- local order/payment ID
- provider transaction ID
- merchant transaction ID
- amount
- currency
- merchant account
- expected payment method where relevant

## Idempotency

Inbound provider events must tolerate repetition.

Outbound provider requests should use provider-supported idempotency or local equivalent where appropriate.

## Browser Versus Server Channels

Explicitly determine:

- customer redirect URL
- server notification URL
- asynchronous result callback
- payment-instruction callback
- query/reconciliation API

Never infer payment success merely because the customer reached a "thank you" page.

## Async Payments

Support methods where:

`ORDER CREATION != PAYMENT COMPLETION`

Examples include:

- virtual-account ATM
- bank transfer
- convenience-store payment code
- barcode payment
- offline payment
- certain BNPL/payment methods

Audit:

- instruction generation
- instruction display
- expiration
- payment-after-delay
- inventory reservation period
- late payment
- expired order + subsequently reported payment
- cancellation
- reconciliation

---

# 10. Inventory & Concurrency Audit

Verify atomicity under:

- normal purchase
- flash sale
- multiple browser tabs
- retried checkout
- duplicate callbacks
- free-product limited claims
- coupon-gated zero-value checkout
- manual admin modification
- cancelled orders
- failed payments
- partial fulfillment
- partial refund
- returns

Accept any technically correct concurrency mechanism.

Reject check-then-write logic that allows races.

Audit oversell behavior explicitly.

---

# 11. Logistics & Fulfillment Audit

Do not treat shipping as:

`pending → shipped → delivered`

unless the actual fulfillment model is genuinely that simple.

Verify:

- delivery method eligibility
- address validation
- pickup point selection
- current pickup-point validity
- package value limits
- package dimensions/weight restrictions
- dangerous/prohibited item restrictions
- service availability
- shipping-rate source
- shipment creation
- label generation
- label expiry
- handoff
- tracking
- delayed tracking events
- duplicate tracking events
- carrier status mapping
- lost parcel
- damaged parcel
- failed delivery
- unclaimed pickup
- return logistics
- merchant receiving returned goods
- inventory restoration policy
- payment/refund implications

Provider statuses must map through an adapter rather than leaking arbitrary provider codes throughout the application.

Store both when useful:

- normalized internal status
- raw provider status/code

---

# 12. Digital Product & Download Security

## Storage

Digital assets must not be unintentionally public.

## Authorization

A valid authenticated entitlement or equivalent grant must precede download credential issuance.

## Delivery Credentials

Use an appropriate mechanism such as:

- short-lived signed URL
- tokenized download
- authenticated application proxy
- signed CDN request

TTL must be configurable according to risk and product needs.

Do not mandate an arbitrary universal "15 minutes."

## Limits

Where download limits exist:

- enforce atomically
- define what counts as a download
- prevent double-counting from retries when appropriate
- define resumed/range-request behavior
- expose remaining allowance where useful

## Version Policy

Explicitly define whether purchasers or free-acquisition holders of:

`v1.0`

receive:

- v1.1
- v2.0
- replacement files
- bonus files

## Refund / Revocation

Determine whether refund or policy revocation:

- immediately revokes access
- revokes only future credentials
- preserves previously obtained files
- has a grace period

The implemented behavior must match merchant policy and applicable law.

---

# 13. Member, Wholesale & Entitlement Systems

Audit:

- anonymous
- registered
- verified
- member tiers
- VIP
- wholesale
- staff/admin

Check authorization server-side.

Do not rely solely on UI hiding.

Verify entitlement effects on:

- catalog visibility
- price
- tax
- MOQ
- shipping
- downloads
- free-download eligibility
- rewards
- coupons
- checkout eligibility

Member-state changes must propagate consistently without creating stale privilege escalation.

---

# 14. Discounts, Coupons, Promotions & Rewards

Verify:

- date windows
- timezone
- minimum spend
- product/category applicability
- customer eligibility
- usage per account
- usage globally
- stacking
- priority
- maximum discount
- zero-value outcome
- shipping-discount interaction
- tax calculation order
- currency interaction
- refund behavior
- cancellation behavior
- partial refund behavior
- reservation/release behavior
- free-acquisition behavior
- concurrency

Do not assume a cancelled order should always restore a coupon.

Require an explicit business policy.

---

# 15. Internationalization, Currency & Localization

## Locale

Audit:

- route locale
- fallback chain
- translated product content
- translated validation
- transactional email
- order history
- checkout
- metadata
- structured data
- OpenGraph
- canonical URLs
- hreflang

Missing translation must fail predictably.

## Currency

Separate:

- catalog/base price
- display currency
- checkout currency
- payment currency
- settlement currency
- FX rate
- FX timestamp/version
- markup/FX fee

Never assume every currency has "cents."

Never use binary floating point for authoritative money calculations.

Respect provider amount requirements.

## Historical Integrity

Completed orders must preserve:

- unit price
- quantity
- discounts
- tax
- shipping
- currency
- FX assumptions
- item description/SKU where needed

Do not rebuild historical commercial data from current product records.

---

# 16. Tax, Receipt & Invoice Integrity

Treat tax-document state separately from payment state.

Audit according to jurisdiction.

Possible concerns:

- tax inclusive/exclusive pricing
- VAT/GST/Sales Tax
- tax jurisdiction
- business tax IDs
- exemptions
- receipt generation
- tax invoice generation
- credit notes
- partial adjustments
- cancellation/voiding
- invoice timing
- document numbering
- reporting/export
- provider failures
- zero-value order treatment where relevant

A successful refund does not automatically prove that the required tax document adjustment was completed.

---

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

