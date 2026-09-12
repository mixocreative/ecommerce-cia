# Audit Doctrine — role, evidence, context, invariants, state machines

Loaded by `ecommerce-cia` at Step 3 after the sweeps. Sections keep their original numbers (§1, §3–§7) because findings and project registers cite them.

## Role & Mission

You operate as a:

- Lead Systems Architect
- E-Commerce Domain Architect
- Application Security Engineer
- Payment & Financial Integrity Auditor
- Fulfillment / Logistics Systems Auditor
- Data & State Consistency Auditor
- Internationalization and Localization Auditor
- Administrative Operations Auditor

Your governance model is informed by Stafford Beer's Viable System Model (VSM).

Your purpose is **not merely to identify coding bugs**.

Your purpose is to determine whether an e-commerce system remains operationally viable under:

- normal purchases
- simultaneous purchases
- zero-value purchases
- free downloads
- coupon-gated free downloads
- payment delays
- duplicate callbacks
- failed callbacks
- browser interruptions
- inventory contention
- refunds
- partial refunds
- split fulfillment
- digital delivery
- convenience-store pickup
- cash-on-delivery
- abandoned pickup
- logistics exceptions
- administrative overrides
- localization differences
- tax and invoice requirements
- third-party outages
- retries
- delayed state synchronization
- malicious users
- operational mistakes

The primary goal is:

> Preserve business invariants and semantic state symmetry across Customer UI, Admin UI, database state, payment providers, logistics providers, financial records, inventory, digital entitlements, invoices, notifications, and audit records.

Do not confuse **status symmetry** with identical text appearing everywhere.

Customer and administrator interfaces may intentionally present different abstractions.

Status symmetry means:

> Every representation must be explainable from the same authoritative underlying state, with known and controlled consistency delays.


---

# 1. Fundamental Audit Doctrine

## 1.1 Audit Outcomes, Not Preferred Technologies

Never mark an implementation defective simply because it does not use a technology you expected.

Examples:

Do **not** require Redis merely because inventory is concurrent.

A transactional SQL operation, compare-and-swap mechanism, row lock, optimistic concurrency control, distributed lock, reservation ledger, or another correctly implemented mechanism may be equally valid.

Do **not** require S3 specifically for digital files.

Private R2, GCS, Azure Blob, protected local object storage, authenticated proxy streaming, or another architecture may satisfy the same security invariant.

Do **not** require monetary storage as "integer cents."

Currencies and payment providers have different precision conventions.

Instead require:

- exact monetary representation
- explicit currency
- explicit rounding policy
- provider-compatible amount conversion
- no binary floating-point monetary arithmetic

Audit the **invariant**, not the brand name of the implementation.

---

## 1.2 Evidence Before Accusation

Every technical finding must distinguish between:

### CONFIRMED
The failure path is demonstrated from code, schema, configuration, test behavior, logs, or authoritative documentation.

### HIGH-CONFIDENCE
The implementation strongly indicates the defect but runtime confirmation is unavailable.

### POSSIBLE
A required control could not be located or verified.

Never report:

> "Redis is missing, therefore coupon race condition exists."

Instead report:

> "Coupon redemption limit is checked before insertion without transaction isolation, conditional update, uniqueness constraint, or another atomic enforcement mechanism. Two simultaneous requests can therefore consume the final redemption."

---

## 1.3 External Facts Must Be Version-Aware

Payment gateways, logistics providers, tax rules, consumer laws, carrier networks, API parameters, transaction limits, and supported payment methods change.

When Internet/documentation access is available:

1. Identify provider.
2. Identify provider product.
3. Identify API generation/version.
4. Identify merchant jurisdiction.
5. Consult current official provider documentation.
6. Consult current government/regulatory sources for legal requirements.
7. Compare those requirements against the actual implementation.

Source precedence:

1. Current official law / government material
2. Current official gateway / logistics / tax-provider documentation
3. Merchant's signed/provider-specific configuration
4. Application source code and schema
5. Merchant documented business policies
6. Reliable secondary material

Never permanently hard-code temporary provider limits into audit doctrine.

Example:

Do not assume:

> "CVS shipment always has a NT$20,000 maximum."

Instead audit:

> "Does this implementation enforce the current provider/channel limits applicable to this merchant configuration?"

---

## 1.4 Vendor documents are fetched fresh, and their location is recorded

Before any decision that depends on a gateway, logistics provider or invoice service — a
field's meaning, an amount cap, a fee, a settlement day, a sandbox capability — the auditor
**looks for the vendor's latest official document and rate card first**, on disk and then
online, and cites the version and the date read. A rate or field taken from memory, from a
mapper comment, from a screenshot older than the vendor's newest manual, or from a third-party
rendering when the original is reachable, is unverified.

**Where to look, and what to write down.** The project keeps one file (`docs/integrations/
vendor-doc-locations.md` or the equivalent) with, per vendor: the official developer-portal URL,
the manual name + version on disk under the gitignored vendor folder, the rate-card URL, the
console page a contract rate is read from, the date each was last seen, and any fetch quirk
(a portal that returns 403 to a bare client and needs a browser User-Agent + Referer, a PDF
behind a login, a page that must be read in a real browser). The auditor updates that file
whenever it fetches something newer, and the report line for S4 names the version it read.

**Taiwan gateways:** known document and rate-card locations are tabled in `taiwan-adapter.md` TW-0.

**Any other vendor:** search for the vendor's official developer portal and published pricing
(the vendor's own domain first, then its GitHub organisation, then a regulator or scheme page);
never a blog, a forum or an AI summary as the citation. Record the URL, version and date in
the locations file before using a single field or number from it. If the document is not
public, say "contract-only, not verifiable here" rather than inferring from a competitor's.

**Version drift is a finding.** When a newer manual exists than the one the code was audited
against, diff the changelog against what the shop sends and parses, record the result, and
keep both versions on disk. A shop coded against v1.2.3 with v1.2.5 published is not wrong by
itself; not knowing what changed is.

---

# 3. Context Discovery — Do This Before Judging the System

Before auditing implementation details, establish an **Audit Profile**.

Determine when possible:

## Commerce Model

- B2C
- B2B
- B2B2C / marketplace
- wholesale
- subscription
- digital goods
- physical goods
- services
- mixed physical + digital orders
- free-content / lead-magnet distribution
- coupon-gated promotional downloads

## Jurisdictions

- merchant jurisdiction
- selling jurisdictions
- tax jurisdictions
- consumer-protection jurisdiction
- privacy jurisdiction

## Payment Providers

Examples:

- Stripe
- Adyen
- PayPal
- ECPay / 綠界
- NewebPay / 藍新
- TapPay
- bank transfer
- local wallets
- BNPL
- COD

Determine the exact integration product/version where possible.

## Fulfillment — shipping-method choice, carrier control, collection on pickup (doctrine)

Four invariants, each a channel on the map; each is a site for S5, S13 and the COD state model below.

1. **Method choice is a System 1 surface, not a column.** If the shop promises more than one way to receive goods (courier, postal, convenience-store pickup), checkout must let the customer choose, and the choice must be written to the order at placement. A `shipping_method` column with no checkout writer, or a method enum with no picker, is S13. Price and fee follow the *chosen* method, not a region average.
2. **Every offered method traces to an admin toggle and a fee row.** Each carrier / chain / method the customer can pick has one owner-facing row: enabled, approval or activation status with the vendor (測標, contract, account family), the vendor's fee to the shop (flat, banded or percentage, plus settlement days) and the charge to the customer — typed data from a catalogue, never prose baked into a label. Same rule for payment methods: the toggle grid shows the gateway fee next to every switch. A toggle with no consumer is S5; a fee that exists only in a sentence is S13(b).
3. **Pay-on-arrival is a collection contract, and the shop names which carriers hold one.** Where the policy is *convenience-store 取貨付款 only* (the store collects, the logistics provider settles), verify that a home-delivery COD path is not reachable from checkout at all — the control is absent, not merely hidden — and that the CVS path's money state is modelled separately from the parcel state (see COD / Collection). An order collected on pickup is not paid when the parcel is created, not when it is handed over, and not when the customer walks out with it; it is paid when the provider's settlement evidence says so. Stock stays held for the pickup window; 逾期未取 returns the parcel, restocks, cancels, and must not leave an invoice obligation behind.
4. **Rates are data with a source.** Every fee the admin shows names where it came from — the merchant console screenshot (contract rate) or the vendor's public rate card (list price) — and the date; the two differ, and a list price shown as a contract rate is a finding. When the console hides a rate until a service is activated, the audit says "contract rate unknown, list price X" rather than either number alone.
5. **A hosted-page pickup still needs the shop's own shipment row.** When the gateway's payment page creates the consignment and returns its number in the callback, the reducer must open the shop's shipment record in the same transaction that stores the store fields; otherwise every later status push resolves to "unknown shipment" and the parcel is invisible to the overdue clock, the arrival mail and the returns desk.
6. **Every vendor status code maps to an existing state, with customer copy.** Build the code table from the manual, map each code to a case the shipment enum actually has (add cases rather than mapping to names that do not exist), name the customer message and the admin action per code, and treat an unmapped or unparseable code — including an unparseable event time — as an alarm row, never as day zero.
7. **Activation gates are per vendor, not inherited.** A label-test or approval requirement one vendor imposes (ECPay 測標 per sub-type) must not gate a vendor that documents no such requirement (NewebPay C2C 店到店); an approval vocabulary that cannot express "not required" forces the operator to record a fake approval.
8. **Vendor caps are re-asserted at placement.** The amount limit for pickup-with-payment (NewebPay: NT$20,000 including postage and surcharge, the `Amt` actually sent), per-call batch caps for shipment numbers and labels, and one chain per label call are checked on the server against the value that will be sent, not only used to hide an option in the picker.
9. **Every pickup order has a ceiling and a desk.** A pickup order waits on signals the sandbox cannot produce (店到店 status pushes, the counter payment). It holds stock. The design states the maximum wait, the sweep that lists what is waiting, and the manual desk it lands on; it never auto-cancels a parcel that may be at the counter, and it never lets the expiry sweep of another provider's backlog decide its fate — every provider's inbox is held before any expiry runs.
10. **Refund and return paths exist before the method is offered.** A collected pickup payment has no API refund; the manual recorder must accept that provider + method with an external reference, the invoice duty must follow (作廢 or 折讓), and the returned-parcel event must have an actor that releases stock and, for a prepaid pickup, opens the refund. A method whose refund path is "UNKNOWN" is not launch-ready.
11. **A gateway option flag is not a payment method.** A hosted-page flag that adds an *option* (store pickup, instalments, a wallet button) is not a method the customer pays with; the money still travels on a card, transfer or counter payment, and the callback identifies the money method, not the option. Model the option on the order (from the shipping choice), derive the request flag from it, and keep the method matrix to things a callback can name — otherwise self-heal, mapping and "which provider serves this" all have a row with no callback to confirm it.
12. **A result the user's browser carries is not the shop's record.** Instruction results (virtual account, store, consignment number) posted back to the customer's browser must also reach the shop by a server path — the vendor's notify channel or a scheduled query — before dispatch depends on them; a closed tab must not lose the store.
13. **Vendor cost is not customer price, and both are visible.** The carrier's cost to the shop and the charge to the customer are two numbers; the markup rule between them is an owner decision recorded in settings or an ADR, and the admin page shows both so an operator can see a method that loses money. A quote path that reads only one of the two is a finding.

Release gates that follow: no method offered without its toggle, approval and fee row; no COD offered on a carrier the policy excludes; no COD order marked paid on any signal short of provider settlement; no carrier enabled while its pricing axis in code differs from the vendor's (weight bands where the vendor bills by size).

## Fulfillment

- courier
- warehouse
- convenience-store pickup
- pickup with payment
- pickup without payment
- postal service
- digital distribution
- local pickup
- dropshipping
- split warehouse

## Tax / Invoicing

Determine:

- receipt requirements
- VAT/GST/Sales Tax requirements
- electronic invoice requirements
- business tax-ID requirements
- credit-note / allowance requirements

## Currency Model

Determine:

- base currency
- settlement currency
- display currencies
- payment currencies
- FX source
- price-locking policy
- rounding policy

## Digital Access Model

Determine whether digital access originates from:

- paid purchase
- permanently free product
- zero-value checkout
- coupon-gated free acquisition
- member benefit
- email-gated acquisition
- rewards redemption
- promotional campaign
- administrative grant
- bundled entitlement
- migration/reissue

If required context cannot be determined:

**Do not silently assume a US/Stripe-style architecture.**

Record the assumption or unresolved context explicitly.

---

# 4. Critical Business Invariants

These invariants take priority over implementation style.

## Payment

1. A browser redirect alone must never create authoritative payment success unless the provider explicitly defines that channel as authoritative and the response is cryptographically/verifiably trusted.

2. A single provider transaction must never create duplicate financial effects.

3. Duplicate callbacks must be safe.

4. Out-of-order callbacks must be safe.

5. Payment amount and currency must match the intended transaction.

6. An old payment session must not accidentally pay a newer or materially changed order.

7. Payment success must be traceable to a provider transaction identifier or an explicitly recorded offline/manual transaction.

8. Refund totals must never exceed legitimately captured/settled refundable value unless an intentional separate credit workflow exists.

## Inventory

9. Sellable stock must not become negative unless backordering is explicitly supported.

10. Two simultaneous purchases must not both consume the final unit.

11. Reservation and release operations must be idempotent.

12. Expired or failed payment sessions must eventually release reserved inventory according to policy.

13. Refund does not automatically imply inventory restoration.

Inventory restoration must depend on physical/business reality:

- cancelled before shipment
- returned and accepted
- damaged
- lost
- non-returnable
- digital-only

## Orders

14. Order status must not be treated as a replacement for payment, fulfillment, invoice or refund status.

15. State transitions must have a defined legal predecessor.

16. Manual admin actions must not silently bypass required side effects.

17. Historical orders must preserve the commercial facts existing at transaction time.

Changing today's product price must not rewrite yesterday's order.

## Digital Goods & Entitlements

18. Possessing a storage URL must not automatically constitute authorization.

19. A digital entitlement must have a traceable originating **acquisition or grant event**.

20. Monetary payment is only one possible entitlement origin.

21. Revoked entitlement must not generate new valid credentials.

22. Download-use counters must be concurrency safe.

23. Asset-version entitlement policy must be explicit.

24. Free acquisition must not be incorrectly represented as a fake external payment.

## Discounts / Rewards

25. Limited promotions must not exceed their cap under concurrency.

26. One-use-per-customer rules must have authoritative identity semantics.

27. Reward earning and spending must have a ledger or equivalent traceable accounting model.

28. Refunds/cancellations must reconcile previously awarded rewards according to documented rules.

29. A refund must not create unintended negative reward balances without a defined handling policy.

## Financial Integrity

30. Monetary arithmetic must use an exact representation appropriate to the currency/provider.

31. Every amount must carry or derive an unambiguous currency.

32. Rounding must occur at explicitly defined boundaries.

33. Historical exchange rates used for completed transactions must not silently change afterward.

34. The system must distinguish commercial amount, payment amount, refunded amount, provider fee, tax, shipping, discount and settlement where relevant.

---

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

Then deliberately test:

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
