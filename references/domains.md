# Domain Chapters — §8–§16 (money, goods, entitlements, tax)

Loaded by `ecommerce-cia` at Step 3. Read every chapter whose domain the §0.5 / §3 audit profile says the shop has; say in the report which chapters were skipped and why (e.g. "no digital goods — §12 skipped"). §17–§25 (admin security and operations, UI states, observability, stop-the-line conditions, data model, security) are in `domains-operations.md`, read in the same step.

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

**Reading receipt: _the domain decides which invariant is load-bearing_.** Quote this phrase on the report's receipts line (Step 6 in cia, Step 7 in ecommerce-cia) to show this file was read rather than inferred from the skill's index. It appears nowhere else.
