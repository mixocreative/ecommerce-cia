# §23 Global Provider / Jurisdiction Adapters — EU, Japan, United States, United Kingdom

Loaded by `ecommerce-cia` for any non-Taiwan selling jurisdiction the audit profile (§3) names. Taiwan has its own adapter: `taiwan-adapter.md`. Every adapter **extends** the global audit; none replaces it.

**Version-aware, per §1.3 and §1.4.** Thresholds, rates, mandates and dates below are the state of the world as last written into this file; several are on legislated timetables that move. Before any finding cites one, fetch the current official source (tax authority, regulator, scheme rules, the gateway's own manual), cite the version and date read, and record the location in `docs/integrations/vendor-doc-locations.md`. A number quoted from this file without that check is `UNVERIFIED`, never `OK`.

**The adapter rule.** The auditor derives behaviour from `GLOBAL INVARIANTS` + `JURISDICTION RULES` + `PROVIDER CAPABILITIES` + `MERCHANT POLICY`. Never assume one country's checkout model is universal; never assume a rule from this file applies to a merchant who sells only elsewhere. Every adapter below reuses the same four questions the Taiwan adapter asks: **which state machine does this touch, what is the authoritative signal, what does the operator see when it goes wrong, and what document proves it.**

---

## European Union

Activate when the merchant is established in the EU, sells to EU consumers, or the code names an EU payment method (SEPA, iDEAL, Bancontact, giropay, Sofort, Klarna, Przelewy24, Multibanco, EPS) or an EU tax scheme (OSS, IOSS, reverse charge).

### EU-1. VAT — destination, thresholds, OSS / IOSS, reverse charge

Since July 2021 B2C distance sales are taxed in the **customer's** member state once the seller's EU-wide cross-border B2C total passes a single €10,000 threshold (verify current); below it the seller's home rate may apply. The **One Stop Shop (OSS)** lets one return cover all member states; the **Import One Stop Shop (IOSS)** covers imported consignments up to €150. B2B sales to a VAT-registered customer are **reverse-charged** only when the customer's VAT number validates in **VIES** at order time.

Audit:

- which rate table the checkout applies, keyed by **destination country and product category** (standard / reduced / super-reduced / zero; digital services at the customer's location), with the rate table's source and date
- the threshold logic: who counts the running EU-wide B2C total, and what happens on the order that crosses it
- VIES validation at order time for reverse charge, the stored proof (VIES consultation number or response), and the fallback when VIES is down — charging VAT is fail-closed, reverse-charging without proof is fail-open (S3)
- customer-location evidence for digital services (two non-contradictory pieces: billing address, IP country, bank country, SIM country) and what the system does when the two disagree
- IOSS number transmitted to the carrier's customs data for ≤ €150 imports, and the duties-and-taxes-paid promise on the checkout matching what the carrier will actually collect at the door
- historical integrity: the rate applied on the order date survives a later rate change (§15)

### EU-2. Consumer Rights Directive — the 14-day withdrawal right and the digital-content waiver

Distance and off-premises consumer contracts carry a **14-day withdrawal right** from delivery (goods) or contract (services), without reason; the refund is due within 14 days of withdrawal (the seller may withhold until goods are back or proof of return is shown). The right is **excluded** for, among others, personalised goods, sealed goods unsealed for hygiene, and **digital content not on a tangible medium once performance has begun — but only if the consumer gave express prior consent to immediate performance and acknowledged losing the right.** Missing or defective pre-contract information extends the period to 12 months.

Audit — this is TW-12's pattern with a different clock:

- the pre-contract information (identity, total price, delivery cost, withdrawal terms, the model withdrawal form) is presented **before** the order button, and the button is labelled so that it makes the payment obligation explicit ("order with obligation to pay" or equivalent — the "button solution")
- for digital content: the consent + acknowledgement is a **separate, unticked, recorded** act with policy version, timestamp, order and product (§8, TW-12 evidence list); a download or stream that starts before that record exists reopens the withdrawal right
- the withdrawal state machine (requested → goods received / proof received → refunded, within 14 days) is modelled separately from the refund and the invoice; the operator queue shows every withdrawal whose refund clock is running (S16)
- diminished-value deductions, return-cost allocation and who pays return shipping match the disclosed terms, not a hard-coded policy
- the withdrawal period extension when information was defective is representable, not impossible

### EU-3. PSD2 Strong Customer Authentication and 3-D Secure 2

Card payments by EU consumers require **SCA** unless an exemption applies (low value ≤ €30 with counters, transaction-risk analysis by the acquirer, trusted beneficiary, **merchant-initiated transactions** under a prior mandate, recurring after the first). The gateway performs 3DS2; the shop's job is to send the right flags and to handle the outcomes.

Audit:

- the challenge flow is a **round trip that leaves the site** (S17, S22.3): abandoned in the ACS, browser closed after authentication, authentication succeeded but authorisation declined — each has a customer surface and an operator surface
- MIT / recurring flags and the stored **initial-transaction reference** for subscriptions and one-click; a subscription renewal sent as a customer-initiated transaction will be soft-declined and must be retried correctly, not recorded as failed
- soft decline (`SCA required`) is a distinct outcome from hard decline and re-triggers authentication rather than failing the order
- exemption requests are the acquirer's decision; the shop never marks an order paid on a 3DS "frictionless" response alone — the authorisation result is the signal

### EU-4. Async and account-to-account methods — SEPA Direct Debit, bank redirects, BNPL

- **SEPA Direct Debit** needs a stored **mandate** (reference, signature date, creditor identifier) before the first collection, pre-notification to the debtor, and it is **reversible**: an authorised debit can be returned for up to **8 weeks** at the payer's request, an unauthorised one for **13 months** (verify). Model `collected` and `settled_final` as different states; a refund issued before the return window closes can double-refund.
- **Bank redirect methods** (iDEAL and its successor scheme, Bancontact, giropay, Sofort / Klarna Pay Now, Przelewy24, EPS) confirm at the bank and return by redirect **and** by webhook; the webhook is the record (§9, TW-3). Some report `pending` for hours; **Multibanco** and similar reference methods are pay-later instructions with an expiry (TW-4's pattern).
- **BNPL** (Klarna, Scalapay, and others): the provider pays the merchant and owns the consumer credit; refunds route through the provider, disputes follow the provider's rules, and a refund after the provider settled is a **provider-credit** state, not a card reversal.

Audit each method through the §9 gateway audit, the TW-4 async list, and S15's four corners, with the money state separated from the order state at every step.

### EU-5. GDPR and ePrivacy — consent records, retention against tax law, processors

- Every marketing consent (newsletter, profiling, cookies beyond strictly necessary) is a **recorded act**: what text, which version, when, from where; an unticked default; withdrawal as easy as giving it.
- **Erasure requests collide with invoice-retention duties** (national law commonly requires keeping invoices 6–10 years): the design must be able to erase or pseudonymise the customer while keeping the fiscal record — an order table where the customer row is the only place the invoice name lives cannot comply with both (§24).
- Processors: the payment gateway, the carrier, the mail provider and the analytics vendor each need a documented role and a data-processing agreement; a data transfer outside the EU needs a named mechanism. The audit does not give legal conclusions (TW-12); it records `LEGAL / POLICY REVIEW REQUIRED` with the evidence the system keeps.
- Data-subject access: the system can produce **everything held about one customer**, including provider references and logs (§20's event logs are personal data too).

### EU-6. Pricing, promotions and reviews — Omnibus and geo-blocking

- Consumer prices are shown **including VAT and all unavoidable charges**; a price that changes at checkout because the destination rate differs from the assumed one is a finding unless the change is explained on screen.
- A **price reduction announcement** must state the **lowest price the seller applied in the 30 days before** the reduction (Omnibus Directive, verify national transposition): the promotion engine (§14) needs price history per SKU and the display must read from it, not from a "was" field an operator typed.
- Reviews: if the shop states reviews are from verified buyers, it must have the verification mechanism; otherwise it must say so.
- Geo-blocking regulation: a customer in one member state may not be refused, redirected or given different payment conditions purely on nationality or location (delivery scope may still be limited); check the locale / currency / payment-method offer logic (§15) does not silently discriminate.

### EU-7. Invoices and e-invoicing mandates

Invoice content is harmonised (VAT number of both parties where relevant, sequential numbering, rate and amount per rate, reverse-charge wording) but **e-invoicing mandates are national and on staggered timetables** — Italy's SDI has been mandatory for years; Germany, France, Poland, Belgium, Spain and others have B2B mandates phasing in through the mid-to-late 2020s (verify each). Audit the invoice state machine (§5, §16) per member state the merchant is established in; a credit note, not an edited invoice, corrects an issued one.

### EU-8. Cross-border delivery and returns

- Duties-and-taxes on non-EU origin goods, IOSS vs DAP at the door, and what the customer was promised at checkout; a parcel refused at the door for unexpected charges is a return with a fee
- Return logistics across borders: who pays, which carrier, and the withdrawal clock (EU-2) running while the parcel is in transit
- Carrier status vocabularies differ per country; every code maps to an existing shipment state (§3 fulfilment rule 6)

**Release gates that follow:** no destination offered without a rate-table row; no digital content delivered before the waiver record exists; no card subscription without a stored initial-transaction reference; no SDD refund before the return window is modelled; price-reduction display reads price history.

---

## Japan

Activate when the merchant is established in Japan, sells to Japanese consumers, or the code names a Japanese payment or logistics method (コンビニ決済, 代金引換, 銀行振込, キャリア決済, PayPay, 楽天ペイ, d払い, au PAY, Paidy / NP後払い / atone, Pay-easy, ヤマト運輸, 佐川急便, 日本郵便).

### JP-1. Consumption tax, tax-inclusive display, and the qualified-invoice system (インボイス制度)

- Standard rate **10 %**, reduced rate **8 %** (food and drink excluding restaurant and alcohol, subscription newspapers) — verify current. A mixed cart carries both rates; a shipping fee has its own treatment.
- **総額表示**: consumer-facing prices must be shown tax-inclusive; a checkout that reveals tax only at the last step is a finding.
- **適格請求書等保存方式** (from October 2023): a buyer who wants an input-tax credit needs a **qualified invoice** carrying the seller's registration number (`T` + 13 digits), the amounts and tax **per rate**, and the tax amount per rate; **rounding is once per invoice per rate**, not per line. B2B buyers will ask for it after the fact; the invoice document (§5 Invoice / Tax Document, §16) must be issuable and reissuable with the same number, and a partial return produces a 返還インボイス, not an edited original.
- Non-registered sellers cannot issue qualified invoices; the shop's settings must say which it is, and the invoice template must obey the setting (S5).

### JP-2. 特定商取引法 — mandatory disclosures and the final confirmation screen

The Act on Specified Commercial Transactions requires a **特定商取引法に基づく表記** page (seller name, representative, address, phone, price, payment timing and method, delivery timing, **return and cancellation conditions**) and, since the 2022 amendment, a **最終確認画面** (final confirmation screen) that shows quantity, price including tax, payment timing, delivery timing and the cancellation / return terms **before** the order is placed. Mail order has no statutory cooling-off, **but** if return conditions are not displayed the consumer may return within 8 days at the seller's expense.

Audit:

- the disclosure page exists per locale and its content is data, not a stale template
- the final confirmation screen is a real step with all mandated fields, at every payment method and every cart shape (S22 matrix: it is a surface the law names)
- subscription (定期購入) offers state the total across the term, the renewal cadence and how to cancel, on the final screen — this is the enforcement focus of the amendment
- the return-policy text shown at order time is stored with the order (§15 historical integrity)

### JP-3. Convenience-store payment (コンビニ決済) and other pay-later instructions

The customer receives a **payment number or slip** and pays at a 7-Eleven / FamilyMart / Lawson / Ministop / Seicomart counter before an **expiry** (often 3–7 days, provider-defined). This is TW-4's payment state machine exactly: `instruction_issued → awaiting_payment → paid | expired`. Pay-easy (ATM / online banking) and 銀行振込 (bank transfer, matched by remitter name and amount — a name typed in the wrong width does not match) are the same shape with different matching rules.

Audit: instruction generation and display, expiry and reservation release, payment after expiry, provider notification vs browser return (TW-3), duplicate payment, partial amount, and the operator queue of orders awaiting payment (S16). Never show 「ご注文完了」 for an unpaid instruction; the state is 「ご注文受付・お支払い待ち」.

### JP-4. 代金引換 (cash on delivery) and 後払い (post-pay BNPL)

- **代引き**: the carrier collects cash or card at the door, charges a **collection fee** (代引手数料, usually banded by amount) and remits on its settlement cycle. Model it as TW-7 — fulfilment `delivered`, collection `collected`, settlement `pending → settled` — and treat **refused at the door** (受取拒否) as a return with the outbound and return freight both owed. A 代引 order marked paid on `shipped` is the canonical defect.
- **後払い** (NP後払い, Paidy, atone, and others): the provider pays the merchant and bills the consumer (konbini slip within ~14 days). Credit approval is a **provider decision at checkout** that can refuse; the refusal needs a customer surface. Refunds and cancellations route through the provider; the money state is `provider_settled`, never `paid` from the customer.

### JP-5. Wallets, carrier billing and cards

- **Wallets** (PayPay, 楽天ペイ, d払い, au PAY, メルペイ, LINE Pay): hosted redirect or in-app; result by webhook; refund windows and partial-refund support **differ per wallet** — each is an S18 matrix row, not "wallet".
- **キャリア決済** (docomo / au / SoftBank): charged to the phone bill; monthly caps per carrier and age; cancellation and refund windows bounded by the billing month.
- **Cards**: 3-D Secure 2 (EMV 3-D Secure) is required for EC merchants under the industry security guidelines (verify the current 割賦販売法 / クレジット取引セキュリティ対策協議会 timetable); instalment (分割) and bonus-payment (ボーナス払い) options are card-issuer features passed through the gateway and must be modelled as payment options, not methods (§3 fulfilment rule 11).

### JP-6. Logistics — carriers, size bands, time slots, redelivery, convenience-store pickup

- Carriers: ヤマト運輸 (宅急便, ネコポス / クロネコゆうパケット for small items), 佐川急便, 日本郵便 (ゆうパック, ゆうパケット, レターパック). Freight is by **size band** (the sum of three dimensions in cm: 60 / 80 / 100 / 120 / 140 / 160 / …) **and region**, with surcharges for 沖縄・離島 and for クール便 (chilled / frozen). A shop that quotes by weight when the carrier bills by size is §3 fulfilment's last release gate.
- **時間帯指定** (delivery time slots) and **置き配** (unattended delivery) are customer choices written to the order and sent in the carrier request; a slot the carrier does not serve for that route is a refusal at label time (S17 / S18).
- **再配達** (redelivery) and the carrier's holding period: an uncollected parcel returns to the sender after the period; model it as `returned`, restock, and — for prepaid — refund minus the disclosed freight.
- **コンビニ受取** (pickup at a convenience store via the carrier): the TW-5 state machine with Japanese store networks; the pickup deadline and what happens after it are provider-defined — read the manual.
- Tracking pushes are not real-time; the reconciliation query exists and is used (TW-5).

### JP-7. Addresses, names and text width

- **郵便番号** (7-digit postal code) → prefecture / city auto-fill via a postal-code API; address order is 都道府県 → 市区町村 → 町域・番地 → 建物名・部屋番号.
- Carriers require **フリガナ** (name reading) on labels; the field is mandatory in the carrier request even when the shop treats it as optional (S18: cite the carrier's field table).
- **全角 / 半角** normalisation: numbers and Latin letters typed full-width fail carrier and gateway validation; phone numbers, postal codes and the katakana reading must be normalised **before** the request, and the normalisation must be tested with real full-width input (S21).
- Length caps on name and address fields differ per carrier and are enforced by the carrier's validator, not its manual (S18.1).

### JP-8. Receipts, delivery notes and record retention

- **領収書** on request (often with 但し書き), **納品書** in the parcel, and the qualified invoice (JP-1) are three documents; a shop that generates one PDF called "invoice" for all three has collapsed the §5 invoice state machine.
- **電子帳簿保存法**: electronic transaction records (orders, invoices sent and received electronically) must be retained electronically with search and integrity requirements (verify the current obligation and grace rules); the design names where the immutable copy lives (§20).

### JP-9. Pricing and advertising rules

- **景品表示法**: a strikethrough "was" price (二重価格表示) must be a price actually charged for a reasonable recent period; the promotion engine needs price history (as EU-6), and a discount badge that reads from an operator-typed field is a finding.
- **ステルスマーケティング規制** (2023): paid or sponsored reviews and posts must be labelled; if the shop displays influencer or affiliate content, the label is data, not decoration.
- **個人情報保護法** (APPI): purpose-of-use disclosure, opt-out for third-party provision, and cross-border transfer notice; same evidence discipline as EU-5.

**Release gates that follow:** no order button without the 最終確認画面; no 代引 order marked paid on any carrier signal short of remittance; no invoice template that ignores the registration-number setting; no carrier enabled with a weight-based rate table; no full-width input reaching a carrier request untested.

---

## United States

Activate when the merchant is established in the US or sells to US customers.

### US-1. Sales tax — economic nexus, marketplace facilitators, tax on shipping

Since *South Dakota v. Wayfair* (2018) a remote seller owes sales tax in a state once it passes that state's **economic-nexus threshold** (commonly $100,000 in sales or 200 transactions per year — thresholds and their measurement periods vary by state and change; verify). Rates are set by state, county, city and special districts, keyed by **ship-to address**; some states are origin-based for in-state sales. Taxability of shipping, of digital goods, of clothing and of food differs by state. Marketplace-facilitator laws shift collection to the platform when selling through one.

Audit: which nexus states are configured and who tracks the thresholds; the rate source (a tax service or a maintained table) and its date; taxability rules per product category per state; the tax-exempt B2B path with certificate storage; historical integrity of the rate on the order (§15). Prices are shown **tax-exclusive** to consumers, and the checkout says so before payment.

### US-2. Cards, ACH and disputes

- Card disputes follow network rules and consumer law (Regulation Z for credit, Regulation E for debit); the chargeback state machine (§5 Payment `disputed / chargeback`) needs evidence submission deadlines as dates on the order, and a lost dispute is a `refunded` state the shop did not initiate.
- **ACH** (bank debit) is asynchronous and reversible: returns (`R01` insufficient funds and others) arrive days later, and a consumer's unauthorised-debit claim can arrive up to 60 days after the statement. Model `initiated → settled → return_window_closed`; do not ship high-value goods on `initiated`.
- Card-on-file and subscriptions: **ROSCA** and state auto-renewal laws require clear disclosure, affirmative consent, and a cancellation path as easy as sign-up; the consent record has the same evidence shape as EU-2.

### US-3. Privacy and communications

State privacy laws (CCPA / CPRA and a growing set of others) grant access, deletion and opt-out-of-sale rights with a "Do Not Sell or Share" mechanism; **CAN-SPAM** governs marketing email (working unsubscribe, physical address); **TCPA** governs SMS (prior express written consent, recorded). Same evidence discipline as EU-5; the audit records `LEGAL / POLICY REVIEW REQUIRED` rather than concluding.

### US-4. Accessibility and address handling

Web accessibility litigation under the ADA targets checkout flows; Step 5's a11y checks (labels, focus, `aria-expanded`, `<h1>`) are release-relevant here, not cosmetic. Addresses validate against USPS formats (ZIP+4, PO boxes that carriers other than USPS cannot deliver to, military APO/FPO); a carrier that refuses a PO box must refuse at checkout (§3 fulfilment rule 8), not at label time.

### US-5. Shipping and returns

Carrier surcharges (residential, remote, dimensional weight) are quoted from the carrier's rating API against the actual parcel, not a flat table, or the margin is silently negative (§3 fulfilment rule 13). Return policy is contractual, not statutory; whatever is displayed at order time is what the refund state machine must implement, and the displayed text is stored with the order.

---

## United Kingdom

Activate when the merchant is established in the UK or sells to UK customers. Post-2021 the UK is a **third country to the EU**: EU-bound parcels are exports with customs data, and EU sellers into the UK follow UK import rules.

### UK-1. VAT and imports

Standard rate 20 %, reduced 5 %, zero-rated categories (most food, children's clothing, books); registration threshold £90,000 taxable turnover (from April 2024, verify). Prices to consumers are shown VAT-inclusive. **Imports ≤ £135**: UK VAT is charged at the point of sale by the seller (or the marketplace), not at the border; above it, import VAT and duty at the border — the checkout must say which. Northern Ireland follows EU goods rules under the Windsor Framework; a shop that treats a `BT` postcode as plain UK gets the VAT and customs treatment wrong. VAT returns are filed under Making Tax Digital with compatible software.

### UK-2. Consumer Contracts Regulations 2013 and Consumer Rights Act 2015

- CCR 2013 mirror EU-2: **14-day cancellation** for distance contracts, refund within 14 days, the **digital-content waiver** with express consent and acknowledgement recorded before download or streaming begins, extension to 12 months when information was missing.
- CRA 2015: **30-day short-term right to reject** faulty goods for a full refund; after that, repair or replace, then price reduction or final rejection; digital content that damages a device carries a remedy. The refund / return state machine (§5) must distinguish *cancellation* (change of mind, CCR) from *rejection* (faulty, CRA), because the clocks, the return-cost rules and the evidence differ.

### UK-3. Payments and strong customer authentication

UK SCA (the FCA's retained PSD2 rules) requires 3-D Secure for UK-issued cards with the same exemption classes as EU-3; **Open Banking** account-to-account payments confirm by redirect and webhook and are irrevocable once settled — refunds are separate outbound payments. Direct Debit runs under the **Bacs** scheme with its own Direct Debit Guarantee (indemnity claims can reverse a collection); same modelling as SEPA in EU-4.

### UK-4. Privacy and marketing

UK GDPR and the Data Protection Act 2018 mirror EU-5; **PECR** governs electronic marketing (the soft opt-in for existing customers has conditions, recorded). Retention of VAT records is six years. The **Digital Markets, Competition and Consumers Act 2024** adds rules on fake reviews, drip pricing and subscription contracts phasing in from 2025 (verify the commencement dates): total price up front, subscription reminders and easy exit, and review-verification claims that are true.

### UK-5. Delivery and returns

Royal Mail, DPD, Evri, DHL and others each have their own status vocabulary and size / weight bands; Highlands, Islands and Northern Ireland carry surcharges and longer transit that must be quoted before payment. EU-bound parcels need customs data (HS codes, origin, value) in the carrier request and a **DDP vs DAP** choice the customer was told about at checkout — a DAP parcel refused for unexpected charges is a return with double freight (EU-8 in reverse).

**Release gates that follow (US and UK):** no state or country offered without a tax treatment and a customs / import treatment on file; no digital content before the waiver record; no ACH / Direct Debit order shipped before the return window is modelled; the displayed return policy is stored with the order it governed.
