# §23a Global Compliance Layer — terms and services, privacy, and the other major markets

Loaded by `ecommerce-cia` on **every** run, after `jurisdictions.md` (or `taiwan-adapter.md`), because every shop has a privacy regime and a set of legal pages whatever it sells and wherever. Extends the global audit; never replaces it.

**Version-aware, per §1.3 and §1.4.** Deadlines, thresholds and commencement dates below move on legislative timetables. Before a finding cites one, fetch the current official source (the regulator's own site, the statute text, the guidance note), cite the version and date read, and record the location in `docs/integrations/vendor-doc-locations.md`. A figure quoted from this file without that check is `UNVERIFIED`, never `OK`. The audit **does not give legal conclusions** (TW-12): where the law's application is uncertain it records `LEGAL / POLICY REVIEW REQUIRED` with the evidence the system keeps, and grades the *system's ability to produce that evidence*.

**What this layer audits is the machinery, not the lawyer's text.** A privacy policy is a document; whether the shop can honour it is a set of channels: a consent recorded, a deletion that reaches every store, an export that includes the gateway reference, a retention clock that runs. Each row below is a channel on the VSM map — most are System 3 → System 1 (a policy that code must obey) or System 3\* (proof it was obeyed) — and every one is a site for S5 (dead control), S13 (designed-but-unbuilt), S16 (a request that never ends) and S22 (a state with no screen).

---

## GT — Terms and services: the legal surface every shop must carry

### GT-1. Mandatory legal pages and disclosures, per jurisdiction

Every jurisdiction names pages that must exist, be reachable from every page, and say specific things. The audit lists the pages the profile's jurisdictions require, finds each in the running site, and checks its content is **data with a version**, not a stale template.

| Jurisdiction | Pages / disclosures the shop must carry (verify current) |
|---|---|
| **EU** | Seller identity and contact (Services Directive / e-Commerce Directive "imprint" duties — Germany's *Impressum* is the strictest form), terms, privacy notice, cookie notice, withdrawal instructions and the model withdrawal form, ODR platform link (being withdrawn — verify), delivery and payment information, price with VAT, ADR body if bound |
| **UK** | Business identity and address (Companies Act / e-Commerce Regulations), terms, privacy notice, cookie notice, cancellation instructions (CCR 2013), delivery and returns, complaints route |
| **US** | Terms of service, privacy policy (state laws: CCPA/CPRA requires specific notices and a "Do Not Sell or Share" link), return / refund policy displayed at point of sale (several states require it or default to a refund right), auto-renewal disclosures (ROSCA, state ARLs), accessibility statement (practice) |
| **Japan** | 特定商取引法に基づく表記 (JP-2), プライバシーポリシー, 利用規約, the 最終確認画面 content, 資金決済法 disclosures if points or prepaid balances are issued |
| **Taiwan** | 隱私權政策 under 個資法 (PR-9), 服務條款, 消費者保護法 distance-sale disclosures and the 7-day 猶豫期 exceptions (TW-12), 電子發票 choices (TW-11), seller identity and contact |
| **Korea** | 통신판매업 신고번호 and business registration on every page, 이용약관, 개인정보처리방침, 청약철회 (7-day withdrawal) terms, escrow / purchase-safety service notice (KR-3) |
| **Australia** | ABN, terms, privacy policy (Privacy Act, if covered), ACL consumer-guarantee wording that does not exclude guarantees, refund policy that does not say "no refunds" |
| **Canada** | Terms, privacy policy (PIPEDA / Quebec Law 25), CASL consent language, bilingual pages for Quebec (Bill 96) |
| **Brazil** | CNPJ and address, termos de uso, política de privacidade (LGPD), CDC 7-day arrependimento terms, SAC contact |

Audit, per required page: it exists at a stable URL; every page links to it; its content is versioned in data (`terms_versions` or equivalent) with an effective date; the version shown at order time is stored with the order (§15 historical integrity); a change in the page produces a new version, never an edit of the old one.

### GT-2. Acceptance evidence and versioning

A checkbox is not evidence; a **record** is. For every act that binds the customer (terms acceptance, withdrawal-right waiver for digital content, subscription consent, marketing consent, age confirmation):

- the record carries **who** (account or verified email), **what** (document id + version hash), **when**, **where** (route, locale), and **how** (unticked box ticked, button labelled with the obligation, in which language)
- the record is written in the **same transaction** as the order or account change it authorises; an order that exists without its acceptance row is a finding (S2 pattern in reverse: the predicate was checked in the browser and dropped at the write)
- the document version referenced still exists and is readable years later (§20 immutable records); a version table with rows deleted is an evidence gap
- **re-acceptance on material change** is a modelled flow with a screen (S22), not a silent overwrite

### GT-3. Subscriptions, auto-renewal and free trials

Every major regime now regulates the renewal, not just the sale (EU consumer law and national rules, UK DMCC Act 2024 subscription rules, US ROSCA and state ARLs, Japan's 特商法 2022 amendment, Korea's 전자상거래법). Common shape, audit against it:

- **before** the first charge: the total price per period, the renewal cadence, the trial end date and what happens then, how to cancel — on the final screen, not a linked page
- **reminders** before a trial converts and before a renewal (UK and several US states require them; verify), sent to a channel the customer actually gave
- **cancellation as easy as sign-up**: same medium, no retention wall that blocks the act; the cancel is a state the order machine has, with a customer surface and an operator surface (S22)
- the **stored payment credential** is used only under the consent recorded (GT-2) and with the initial-transaction reference the schemes require (EU-3); a renewal charge with no consent row is a finding at HIGH
- price changes on renewal are a new consent, not a silent update

### GT-4. Marketing communications consent

Email (EU ePrivacy / national law, UK PECR, US CAN-SPAM, Canada CASL, Australia Spam Act, Japan 特定電子メール法, Korea 정보통신망법, Brazil LGPD), SMS (US TCPA is the strictest — prior express written consent, recorded), push and messaging apps:

- consent is **opt-in and recorded** (GT-2 shape) except where a jurisdiction allows a soft opt-in for existing customers under stated conditions — and then the condition is checked in code, not assumed
- every message carries a working unsubscribe that takes effect within the regime's window (CAN-SPAM 10 business days; CASL 10 days; PECR "without delay" — verify), and the suppression list is honoured by **every** sender in the system, including the gateway's receipts and the carrier's notifications where the shop controls the template
- transactional messages (order confirmation, shipping, invoice) are separated from marketing in code, so an unsubscribe never stops a refund notice — and a marketing paragraph inside a transactional mail is a finding
- the "tell them" checkbox on operator actions (S16.1) writes intent; the sender reads the suppression list

### GT-5. Price display, promotions and reviews

Rules already listed per region (EU-6 Omnibus, JP-9 景表法, UK DMCC drip pricing, US FTC endorsement and "junk fee" rules — verify) share one audit: the price the customer sees first is the price they pay, every "was" price is a price actually charged for the stated period read from history, every mandatory charge is in the headline price, and every review or endorsement label is data the system enforces. Cross-reference §14 promotions and §15 currency.

---

## PR — Privacy checkup: the regimes and the channels

### PR-1. Data map — where personal data lives, and every path out

Before any regime is applied, produce the map: every table, log, queue, backup, export, third party and analytics tag that holds or receives personal data, with the field list and the retention today. Include the ones nobody thinks of — the gateway callback payload stored raw (§20), the carrier label file with name and phone, the mail provider's activity log, the error tracker's request bodies, the search index, the CDN access log, the S21 test fixtures that copied production rows. A regime obligation that cannot be traced to a row on this map cannot be met; the map is the site list for every PR row.

### PR-2. The regimes, side by side

The table names the regimes a shop meets in the markets this skill covers, and the two numbers the machinery must implement — how fast a data-subject request must be answered, and how fast a breach must be notified. **Verify every cell before citing it.**

| Regime | Applies when (broadly) | DSAR deadline | Breach notification | Notable mechanics |
|---|---|---|---|---|
| **EU GDPR** | established in EU, or targeting EU residents | 1 month (+2 extendable) | 72 h to the authority; to individuals without undue delay if high risk | lawful basis per purpose; DPO in some cases; DPIA for high-risk processing; transfer mechanism outside EEA; representative if not established |
| **UK GDPR + DPA 2018** | as above, UK | 1 month (+2) | 72 h to ICO | mirrors GDPR; ICO fee registration; PECR for marketing |
| **US — California CCPA/CPRA** | thresholds by revenue / volume / data-sale share (verify) | 45 days (+45) | state breach laws (each state; many "without unreasonable delay", some fixed days) | "Do Not Sell or Share"; Global Privacy Control signal honoured; opt-out of profiling; other states (VA, CO, CT, UT, TX, OR, and a growing list) have similar rights with different thresholds |
| **Japan APPI** | handling personal information in business | "without delay" | prompt report to PPC; individuals notified; fixed timelines by category (verify) | purpose-of-use disclosure; opt-out for third-party provision with PPC filing; cross-border transfer consent or equivalence; 仮名加工 / 匿名加工 categories |
| **Taiwan 個資法 (PDPA)** | any collection of personal data in Taiwan | statutory windows for access / correction / deletion requests (15 days for access, 30 for others — verify) | notify affected individuals "appropriately" after the incident; sector regulators set windows | collection notice (告知義務) with purpose, categories, period, region, recipients, method, rights; consent for sensitive data; cross-border restrictions by sector regulator; TW-13 checkout fields are personal data |
| **Korea PIPA** | any handling of personal information | 10 days | 72 h to KISA/PIPC and individuals (verify) | consent per purpose with separate ticks; 주민등록번호 collection prohibited without legal basis; strict cross-border consent; annual disclosure; PIPA is among the strictest on consent granularity |
| **Canada PIPEDA + Quebec Law 25** | commercial activity; Quebec has its own, stricter act | 30 days | "as soon as feasible" to OPC + individuals where real risk of significant harm; Quebec: to CAI | meaningful consent; Law 25 requires privacy officer, PIA for transfers outside Quebec, privacy-by-default settings, breach register |
| **Australia Privacy Act 1988 (APPs)** | turnover threshold (AUD 3m, with exceptions — verify; reform under way) | "reasonable period" (30 days guidance) | Notifiable Data Breaches: assess within 30 days, notify OAIC + individuals if likely serious harm | APP 1 open policy; APP 7 direct marketing; overseas disclosure accountability (APP 8) |
| **Brazil LGPD** | processing in Brazil or of people in Brazil | 15 days (simplified immediate) | "reasonable period" — ANPD guidance sets working days (verify) | legal bases similar to GDPR; DPO (encarregado); ANPD sanctions |
| **China PIPL** | processing in China, or targeting people in China | "timely" (regulatory guidance) | immediate to the authority and individuals | separate consent for sensitive data and cross-border transfer; security assessment / standard contract / certification for exports; data localisation for critical operators; cross-border e-commerce sellers commonly meet it via the platform — verify the contract |
| **Singapore PDPA** | organisations in Singapore | "as soon as reasonably possible", 30 days guidance | 3 calendar days to PDPC after assessing notifiable | consent + notification + purpose limitation; DNC registry for marketing calls / SMS |
| **India DPDP Act 2023** | digital personal data in India, or offering to Indian residents | as prescribed by rules (verify — rules commencing 2025+) | to the Board and individuals, timeline by rules | consent manager framework; verifiable parental consent for children; data fiduciary duties; enforcement phasing in |
| **Hong Kong PDPO** | data users in Hong Kong | 40 days | voluntary today, mandatory regime proposed (verify) | six Data Protection Principles; direct-marketing consent rules with criminal penalties |

### PR-3. Lawful basis, purpose and consent records

For each purpose on the data map (fulfil the order, issue the invoice, fraud screening, marketing, analytics, personalisation, sharing with a marketplace or affiliate): the basis the shop relies on is written down; where the basis is consent, the record has the GT-2 shape; where it is contract or legal obligation, the purpose is limited to that and a marketing use of order data is a separate basis with its own record. Korea and China require **separate ticks per purpose and per transfer**; a single "I agree" box covering all is a finding in those markets.

### PR-4. Cookies, tags and tracking

The banner is a control (System 3); the tags are the consumers (System 1). Audit the channel, not the banner: which scripts load **before** consent (only strictly-necessary ones may); which load only after the category is granted; whether refusal is as easy as acceptance (EU regulators' position); whether the Global Privacy Control header is honoured where required (California); whether the consent state is stored with a version and re-asked on change; and whether the gateway's or carrier's embedded page sets its own cookies the notice does not mention (S17 — a hosted surface you do not render). A tag manager that fires everything on load and "hides" it behind the banner is the canonical dead control.

### PR-5. Data-subject requests — access, correction, deletion, portability, objection

Each is a **state machine with a deadline** (PR-2), and therefore a site for S16 and S22: a request that is received and never answered is money-free but not risk-free. Audit:

- intake: a route or address the notice names, identity verification proportionate to the data, and a queue the operator opens (S16.1) with the regime's clock on each row
- **access / portability**: the export includes every store on the PR-1 map — orders, addresses, gateway references, carrier labels, support tickets, consent records, marketing events — in a readable format; a script that dumps the `customers` row only is a finding
- **deletion / erasure** against **retention obligations**: fiscal law keeps invoices (EU 6–10 years by member state, JP 7 years, TW 5–10 years by document, KR 5 years, AU 5 years, US varies — verify); the design erases or pseudonymises the person while keeping the fiscal record (§24 schema question). Erasure must reach backups on their cycle, logs, the search index, the mail provider, the analytics vendor and the gateway's customer vault (via its API); each is a row on the map with a status
- **objection / opt-out** of marketing and profiling takes effect across every sender (GT-4) and every recommender (§0.12 AI components)
- the closed request is **recorded** with what was done, by whom, and the evidence — the DSAR register is a System 3\* artefact

### PR-6. Processors, sub-processors and cross-border transfers

List every third party on the data map with its role (controller / processor / independent controller), the contract that governs it (DPA, standard contractual clauses, adequacy, PIPL standard contract, APPI equivalence), the country it processes in, and the date the contract was last seen. Gateways and carriers are usually **independent controllers** for their own fraud and delivery purposes and processors for nothing — the notice must say so. A transfer to a country the regime restricts (EU→non-adequate, China outbound, Korea outbound, Taiwan sector rules) with no named mechanism is a finding graded HIGH under the regime's enforcement history.

### PR-7. Breach detection and notification — a detector with a clock

The breach regime is S20 applied to security: **can the shop tell that a breach happened, within the window the law gives it?** Audit: which detectors exist (auth anomaly, bulk export, admin data access logs, gateway alerts, carrier-portal alerts), whether each reports coverage separately from findings, who is paged, whether the notification playbook names the regulator, the deadline (PR-2) and the template, and whether the data map lets the shop say *whose* data was touched. A shop that cannot enumerate affected customers from its logs cannot meet any regime's individual-notification duty.

### PR-8. Children, sensitive data and special categories

Age gates where the product or the regime requires them (US COPPA under 13; GDPR digital consent age 13–16 by member state; India verifiable parental consent; Korea under-14 legal-representative consent — verify), with the evidence recorded (GT-2). Sensitive categories (health, biometric, religion, financial in some regimes, 身分證字號 / 주민등록번호 / national IDs) are either not collected or collected under the regime's separate basis, stored encrypted, and excluded from exports and logs by default.

### PR-9. Taiwan 個資法 — the specifics the Taiwan adapter defers here

- **告知義務**: at first collection, tell the person the collector's name, purpose (a coded purpose from the MOJ list), categories, period, region, recipients and method of use, their rights, and the effect of not providing — as a versioned notice (GT-2), not a line in the footer
- 身分證字號 is sensitive-adjacent: collect only where a law or the carrier's service (e.g. customs for cross-border) requires it, and say which; never store it in the order row in clear
- pickup-with-payment collectors' names (TW-7) and 證件 fields are personal data of a possibly different person from the buyer; the notice covers the collector too
- sector regulators (MOEA for e-commerce, FSC for payment) may restrict cross-border transfer; a gateway or CRM outside Taiwan is a transfer
- access requests within 15 days, other requests within 30 (verify); the queue (PR-5) carries the clock

### PR-10. What the privacy notice promises versus what the system does — POSIWID

Read the live notice and list every promise: retention periods, third parties, purposes, rights, contact. For each, find the code, the cron or the contract that makes it true. A promise with no channel is a dead control (S5) in the one place a regulator will read first. Grade on the gap: a stated retention with no purge job is HIGH; a stated "we never share" with an analytics tag on checkout is HIGH; a stated DSAR address that reaches no queue is HIGH.

**Report line format:** `GT/PR — J jurisdictions in profile; P mandatory pages present/absent; A acceptance records verified with version; R regimes applied; M stores on the data map, D of them reachable by deletion, E by export; T third parties with contract + mechanism; notice promises N, with a channel C; DSAR queue: present/absent; breach playbook: present/absent.`

---

## Other major markets — short adapters

Each follows the four questions (state machine, authoritative signal, operator surface, document); each figure is verify-current.

### Korea

- **VAT 10 %**, tax-inclusive display; **현금영수증** (cash receipt) issuance on request for cash-like payments (bank transfer, virtual account) is a legal duty with its own state (issued / cancelled) — an invoice-machine site (§5, §16)
- **전자상거래법**: 7-day withdrawal (청약철회) from receipt, extended if the seller's disclosures were defective; exceptions similar to EU-2 including digital content with recorded consent; refund within 3 business days of return (verify)
- **Escrow / 구매안전서비스** for prepaid transactions above thresholds, or a purchase-safety notice; PG (payment gateway) required for card acceptance — a regulatory prerequisite (S19 shape: a requirement the host must satisfy)
- Payments: cards via PG with **3-D Secure or app-card authentication**, 계좌이체, 가상계좌 (virtual account — TW-4 pattern with expiry), 휴대폰 소액결제 (carrier billing with monthly caps), wallets (네이버페이, 카카오페이, 토스, 페이코, 삼성페이); every one an S18 row
- Logistics: CJ대한통운, 롯데, 한진, 우체국; **편의점 택배** (CU / GS25 convenience-store drop-off and pickup) with its own state machine; 도서산간 surcharges; 새벽배송 (dawn delivery) windows
- Identity: 본인인증 (real-name verification via carrier / i-PIN) for adult goods and some accounts; PIPA (PR-2) is the strictest consent regime in this file

### Canada

- **GST 5 % federal + HST / PST / QST** by province, keyed by ship-to; non-resident registration thresholds for digital and marketplace sales (verify); prices commonly shown tax-exclusive except Quebec conventions
- **PIPEDA + Quebec Law 25** (PR-2); **CASL** for commercial electronic messages: express or implied consent with records, identification, unsubscribe within 10 days — among the highest per-message penalties anywhere
- Quebec: French-language pages and terms (Charter, Bill 96), CAI privacy filings; consumer protection under the CPA with its own distance-contract cancellation rules
- Payments: Interac e-Transfer / Interac Online, cards, wallets; chargebacks under network rules; **duty and tax on US-origin goods at the border** (DDP vs DAP, EU-8 pattern)
- Carriers: Canada Post, Purolator, FedEx/UPS; remote-region surcharges; postal-code validation (`A1A 1A1`)

### Australia

- **GST 10 %**, tax-inclusive display; **low-value imported goods** (≤ AUD 1,000) GST collected by the seller or platform at checkout once the AUD 75,000 turnover threshold is met (verify)
- **Australian Consumer Law**: consumer guarantees cannot be excluded; "no refunds" signage is unlawful; remedies for major vs minor failures — the refund state machine must represent a remedy the customer chose, not only a change-of-mind return
- Privacy Act (PR-2; reform expanding coverage — verify), Spam Act for marketing
- Payments: cards, **PayID / Osko** instant transfers, BPAY (reference-based pay-later, TW-4 pattern), Afterpay / Zip BNPL (EU-4 provider-settled pattern); surcharging rules cap card surcharges at cost
- Carriers: Australia Post, StarTrack, Aramex, couriers; remote and Western Australia transit; Authority-to-Leave (unattended delivery) is a customer choice on the order

### Singapore

- **GST 9 %** (from 2024, verify), tax-inclusive display for consumers; **Overseas Vendor Registration** for remote sellers of digital and low-value goods above thresholds
- PDPA (PR-2) with the **Do Not Call registry** check before marketing calls and SMS; Consumer Protection (Fair Trading) Act for unfair practices; no statutory cooling-off for most online sales — the displayed policy governs (US-5 pattern)
- Payments: PayNow (QR, instant, irrevocable), cards, GrabPay / ShopeePay wallets, BNPL under the industry code
- Logistics: SingPost, Ninja Van, J&T; **parcel lockers and collection points** as a delivery method with a pickup deadline (TW-5 pattern); cross-border to Malaysia / Indonesia as exports

### China (cross-border e-commerce into China)

- Most foreign shops sell into China via **CBEC platforms** (Tmall Global, JD Worldwide, Kaola) or bonded-warehouse / direct-mail models under the **positive list**, with the CBEC comprehensive tax (import VAT and consumption tax at reduced rates, per-order and annual per-person quotas — verify current quotas) collected by the platform or the logistics agent; the audit checks that the shop's order data carries the fields the customs declaration needs (identity of the buyer, HS code, value) and that the platform contract names who is the importer of record
- **PIPL** (PR-2) and the Cybersecurity / Data Security laws: buyer identity data collected for customs is personal data with cross-border rules; the platform contract usually allocates it — read it
- Payments: Alipay / WeChat Pay cross-border acquiring in the shop's own currency, settled by the acquirer; refunds route through the wallet; UnionPay cards
- Logistics: bonded (保税) vs direct-mail (直邮) models have different state machines, duty points and return possibilities; a return from China is often impossible or uneconomic — the refund policy must say so before purchase
- Consumer law (消费者权益保护法) gives a **7-day no-reason return** for online purchases with exceptions similar to EU-2; enforcement is typically through the platform's rules, which are stricter than the statute

### Brazil

- Taxes are layered (ICMS state, IPI, PIS/COFINS, ISS for services) and being reformed toward a dual VAT (IBS/CBS) on a multi-year timetable — verify; **NF-e / NFC-e electronic invoices** are mandatory and issued through the state SEFAZ with a 44-digit key — the invoice state machine (§5, §16) is a government API integration with its own failures (rejection codes, contingency mode)
- **CDC** (consumer code): 7-day **direito de arrependimento** for distance purchases from receipt, full refund including freight; SAC service rules; **LGPD** (PR-2)
- Payments: **Pix** (instant, QR / copy-paste code, irrevocable — refund is a new Pix), **boleto** (bank slip, pay-later with expiry — TW-4 pattern), cards with **parcelamento** (instalments, with or without interest, displayed as `12x de R$` — the instalment schedule is price display and must be exact), digital wallets
- Logistics: Correios (PAC / SEDEX) and private carriers; CEP (8-digit postal code) lookup; long transit and regional surcharges; **redespacho** to remote areas

### India

- **GST** (CGST/SGST or IGST by intra/inter-state, rates by HSN code, e-invoicing above turnover thresholds — verify); place-of-supply rules decide the tax split; **TCS** collected by marketplaces
- **DPDP Act 2023** (PR-2), rules phasing in; consent manager framework; **RBI rules**: card tokenisation (no merchant storage of PAN), **e-mandates** for recurring payments with pre-debit notification and caps, additional-factor authentication on every card transaction
- Payments: **UPI** (instant, irrevocable, refund is a new transfer), cards, net banking, wallets (Paytm, PhonePe), **cash on delivery is a mainstream method** with high refusal rates — model RTO (return-to-origin) as a first-class state with its cost (TW-7 / JP-4 pattern)
- Logistics: Delhivery, Blue Dart, Ekart, India Post; PIN-code serviceability lookup **before** the method is offered (§3 fulfilment rule 8); COD availability is per PIN code and per carrier
- Consumer Protection (E-Commerce) Rules 2020: seller details, return / refund / exchange terms, country of origin, and grievance officer contact displayed; no manipulation of reviews; verify current amendments

### Hong Kong

- No GST / VAT; prices as displayed; **PDPO** (PR-2) with strict direct-marketing consent; no statutory cooling-off for online sales (the displayed policy governs); Trade Descriptions Ordinance for misleading pricing
- Payments: cards, **FPS** (instant transfer, irrevocable), Octopus, AlipayHK / WeChat Pay HK, PayMe; Chinese and English bilingual surfaces expected
- Logistics: SF Express, Hongkong Post, **locker and convenience-store pickup** (7-Eleven, Circle K) as a method with a deadline; cross-border to mainland China is CBEC (above)

**Release gates that follow (all markets):** no market offered without its legal pages versioned and linked; no order without its acceptance record in the same transaction; no marketing send without a consent row and a working suppression check; no DSAR route without a queue and a clock; no third party on the data map without a contract row and a transfer mechanism; the privacy notice's every promise traced to a channel.
