# §22 Taiwan E-Commerce Adapter — TW-0 … TW-14

Loaded by `ecommerce-cia` when the audit profile (§3) names Taiwan as merchant or checkout jurisdiction, or the code names ECPay / NewebPay / TapPay / LINE Pay / 電子發票. Extends the global doctrine; never replaces it.


Activate this adapter when:

- merchant is Taiwan-based
- Taiwan is a target checkout jurisdiction
- code/config includes Taiwan-specific providers
- or the merchant explicitly uses Taiwan payment/logistics/invoice practices

This adapter **extends** the global audit.

It does not replace it.

## TW-0. Vendor document locations (verify they still resolve; update `docs/integrations/vendor-doc-locations.md` if moved)

Per §1.4 the auditor reads the vendor's latest official manual and rate card before any field, cap or fee decision. Known locations:

| Vendor | Developer docs | Rate card | Contract rate |
|---|---|---|---|
| 藍新 NewebPay | `https://www.newebpay.com/website/Page/content/download_api` — MPG (NDNF-x.y.z), 物流 (NDNS), 定期定額 (NDNP) PDFs; bare `curl` gets 403, send a browser UA + Referer | `https://www.newebpay.com/website/Page/content/service_fare` (list price, 含稅) | merchant console 會員專區, per service; hidden until the service is activated |
| 綠界 ECPay | `https://developers.ecpay.com.tw/` (AIO 全方位金流, 物流, 電子發票 pages by id) | `https://www.ecpay.com.tw/` 費率 pages per product | merchant backoffice 特店 費率 |
| LINE Pay | `https://developers.line.biz/` (LINE Pay Online API) | LINE Pay merchant site | merchant center |
| 台灣Pay / TWQR | via the acquiring gateway's manual (NewebPay / ECPay) | gateway rate card | gateway console |

## TW-1. Provider Discovery

Common examples include:

- ECPay / 綠界科技
- NewebPay / 藍新金流
- TapPay
- Taiwan payment wallets
- local banks
- convenience-store logistics networks
- electronic-invoice service providers

Do not assume all ECPay or NewebPay integrations use identical APIs.

Identify:

- service/product
- API generation
- API version
- enabled merchant features
- merchant contract/configuration

Use current provider documentation before asserting exact:

- status codes
- amount limits
- store networks
- time limits
- payment methods
- callback parameter names

## TW-2. Never Confuse "CVS Payment" With "CVS Logistics"

This is a mandatory audit rule.

### Convenience-Store Payment

The customer may receive:

- payment code
- barcode
- other payment instruction

and later physically pay at a convenience store.

This is fundamentally a **payment state machine**.

Typical semantics:

order_created  
→ payment_instruction_issued  
→ awaiting_customer_payment  
→ paid

or:

→ expired

### Convenience-Store Pickup

The customer selects a physical convenience store as the delivery destination.

This is fundamentally a **logistics state machine**.

### Convenience-Store Pickup + Payment

The customer pays when collecting the parcel.

This combines:

- fulfillment state
- collection state
- settlement state

These concepts must not be represented by a single ambiguous value such as:

`cvs = true`

or:

`status = CVS`

## TW-3. ECPay / NewebPay Payment Callback Model

When these providers are present, explicitly identify:

- backend/server payment notification
- browser/customer return
- payment-instruction result
- payment query API
- refund/cancel/capture APIs
- provider verification mechanism

The authoritative payment transition should be based upon the provider-defined trusted server mechanism or verified reconciliation result.

Never rely solely upon:

- customer browser return
- URL query parameter
- success page
- JavaScript state

Browser return exists primarily for UX unless the exact provider protocol specifies otherwise.

Callbacks must be:

- authenticity checked
- correlated
- amount checked
- merchant checked
- idempotent

## TW-4. Asynchronous Local Payment Methods

Taiwan checkout may include methods that do not pay immediately.

Examples include provider-supported:

- ATM virtual account
- CVS payment code
- barcode payment
- offline transfer
- certain BNPL flows

Required state distinction:

`ORDER EXISTS`

does not imply:

`PAYMENT EXISTS`

does not imply:

`PAYMENT COMPLETE`

Audit:

- payment instruction creation
- customer access to instruction
- expiration
- reservation expiry
- payment confirmation
- late provider notification
- customer paying near expiry
- payment arriving after local cancellation
- instruction regeneration
- duplicate payment
- reconciliation

Do not prematurely show:

> "Order Complete"

if the commercial meaning is actually:

> "Order received — awaiting payment."

## TW-5. Convenience-Store Logistics

Taiwan convenience-store fulfillment may involve networks such as:

- 7-ELEVEN
- FamilyMart
- Hi-Life
- other networks supported by the merchant/provider at that time

Availability changes.

Verify current capabilities.

Model at least where applicable:

store_selected  
→ logistics_order_created  
→ label/code_created  
→ awaiting_merchant_dropoff  
→ carrier_received  
→ logistics_center  
→ destination_store  
→ ready_for_pickup  
→ picked_up

Exception branches can include:

- selected store becomes unavailable
- store closure/transfer
- pickup-store reselection
- shipping label expires
- merchant fails to hand off
- parcel rejected
- consumer fails to collect
- return initiated
- return reaches logistics center
- merchant pickup required
- returned to merchant
- lost/damaged

Do **not** assume logistics callbacks are perfectly real-time.

If the provider supports query/reconciliation APIs, verify that the application can recover from:

- missed callbacks
- delayed callbacks
- repeated callbacks
- out-of-order callbacks

## TW-6. Store Reselection / 關轉店

A selected convenience store may later become unavailable.

Audit whether the system supports provider-defined handling such as:

- customer notification
- replacement store selection
- administrative intervention
- updated logistics order
- retry
- cancellation when reselection cannot succeed

The order must not remain forever in an unexplained generic "shipping" state.

## TW-7. Pickup With Payment / 取貨付款

Do not mark an order fully "paid" merely because it has shipped.

Model separate facts such as:

FULFILLMENT:
`ready_for_pickup`

PAYMENT:
`due_at_pickup`

then later potentially:

FULFILLMENT:
`picked_up`

COLLECTION:
`collected`

SETTLEMENT:
`pending`

then:

SETTLEMENT:
`settled`

Exact stages depend on provider.

Do not invent stages unsupported by the actual provider; instead preserve the conceptual separation.

Audit the financial effect of:

- unclaimed parcel
- failed collection
- returned parcel
- provider fee
- remittance/settlement
- refund after collection

## TW-8. Pickup Without Payment / 取貨不付款

For prepaid pickup:

payment success and pickup are separate.

Example:

PAYMENT = PAID

while:

FULFILLMENT = READY_FOR_PICKUP

Failure to collect does **not** mean the customer was never charged.

The system must have an explicit policy for:

- return
- refund
- shipping fees
- restocking
- notification
- cancellation

## TW-9. Provider Shipping Limits

Taiwan convenience-store channels may impose provider/channel-specific:

- order-value limits
- package dimensions
- weight limits
- category restrictions
- temperature restrictions
- pickup windows

Do not embed remembered values in the audit skill.

Retrieve current provider rules.

Then audit both:

### UI Prevention

Customer should not be offered an impossible method.

### Server Enforcement

Manipulating the client must not bypass the restriction.

## TW-10. TWD Money Handling

Do not blindly apply a universal "store prices in cents" rule.

Audit instead:

- internal exact numeric representation
- TWD amount precision
- payment-provider parameter requirements
- invoice amount requirements
- rounding
- discount allocation
- partial refund calculations

Build explicit gateway adapters for provider-specific amount encoding.

## TW-11. Electronic Uniform Invoice / 電子發票

When applicable, Taiwan invoice handling must be treated as its own domain.

Audit support as applicable for:

- B2C
- B2B
- buyer tax ID / 統一編號
- carrier / 載具
- mobile barcode / 手機條碼
- donation / 捐贈碼
- cloud invoice
- printed invoice requirements
- invoice issuance
- issuance failure
- invoice querying
- voiding
- sales return / allowance
- partial allowance
- corrected documents
- invoice notification

Do not assume:

PAYMENT REFUNDED

automatically means:

INVOICE VOIDED

For example, a partial refund may require an invoice adjustment/allowance rather than simply destroying the entire original invoice.

Invoice failures must appear in an admin operational queue.

## TW-12. Taiwan Consumer-Protection Flow

Audit the implementation against current Taiwanese consumer-protection requirements when applicable.

In particular, distinguish:

- normal distance-sale cancellation rights
- customized goods
- specified statutory exceptions
- digital content
- services already supplied

For non-physical digital content, audit whether any claimed exclusion of the statutory cancellation right has the legally required:

- disclosure
- customer consent
- timing before supply/access begins
- evidence of consent

Do not make unsupported legal conclusions.

Classify uncertain matters as:

`LEGAL / POLICY REVIEW REQUIRED`

The system should preserve evidence such as:

- policy version
- checkbox/consent event
- timestamp
- order/acquisition
- product
- relevant content-delivery activation

## TW-13. Taiwan Checkout UX

Where relevant, verify Taiwanese-localized fields and terminology, including:

- Traditional Chinese
- Taiwan phone format
- postal/address structure
- convenience-store selection
- payment expiration instructions
- ATM virtual account information
- CVS payment instructions
- electronic-invoice choices
- tax ID
- carrier/mobile barcode
- donation option

Taiwan functionality may coexist with:

- English
- Japanese
- other languages
- international shipping
- foreign cards

Therefore Taiwan-specific data must not pollute global checkout assumptions.


## TW-14. 統一發票 timing on pickup-with-payment (取貨付款)

Where the shop's invoice is a physical document that travels with the parcel (hand-written from the 字軌 book, posted in the box — the practice this shop recorded), the obligation for a 取貨付款 order arises when the label is created, not when the money settles: the parcel leaves before payment. The audit checks that (a) the obligation row exists at label time with a state that says "issued, unpaid", (b) an unclaimed / returned parcel voids it (作廢 record) rather than leaving an issued invoice against a cancelled sale, (c) a collected-then-refunded order produces the 折讓, and (d) no e-invoice API, 載具 or 手機條碼 field is introduced on the pickup page — the physical practice stands until the owner changes it. A plan that records the obligation "at settle" for a pickup order contradicts the shop's own invoice policy.
