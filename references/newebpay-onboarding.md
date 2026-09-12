# NewebPay 藍新金流 — Setup Guide for a first-time integrator

Loaded by `ecommerce-cia` in **setup mode** (SKILL.md §0.15) when the project uses NewebPay or the user says they want to. This is not an audit; it is a guided path from "I want to take payments" to "a sandbox order went round-trip and I know what production needs". Written for someone who has never integrated a payment gateway and is building by describing what they want to an AI. Every step ends in something the user can see.

**Sources.** NewebPay's own manuals are the authority (§1.4): read fresh at Step 1, cite PDF page. Everything below that is not a manual citation is a lesson from a real integration (the mixoweb shop, 2026-08/09) and is marked *(lesson)*. Console menu names are as seen on 2026-09-12; menus move — find the words, not the position.

**What the AI may and may not do here.** The AI opens pages, reads manuals, explains every field, prepares every value it is allowed to, fills non-sensitive form fields when asked, and checks results. The AI **never** types a password, a national ID number (身分證字號 / 統一編號 of a person), uploads an ID or passport image, creates the account, or changes a merchant-console setting without a fresh explicit "yes" for that one change. Those steps are the user's, with the AI standing beside them saying what each field means. This is a hard limit, not a style choice.

---

## 0. Detect, and decide the mode

**Detection — any one is enough:**

- source names `newebpay`, `藍新`, `ccore.newebpay.com`, `core.newebpay.com`, `MPG/mpg_gateway`, `TradeInfo`, `TradeSha`, `CVSCOM`, `NDNF`, `NDNS`, `NDNP`
- `.env` / config keys `NEWEBPAY_*`, `MerchantID` + `HashKey` + `HashIV` together
- a WordPress site with the `newebpay-payment` plugin
- the user says NewebPay / 藍新 / "台灣金流" and has not chosen a provider yet — then this guide is one of the options, not the answer (ECPay 綠界, PAYUNi 統一, TapPay, direct LINE Pay exist; choose on fees, methods and what the shop sells; the fee cards are public and dated — read them)

**Mode:** if the integration already exists and the user asks whether it is right → audit mode (§0.6, with TW-3, TW-4, TW-5, S17, S18). If it does not exist, is half-built, or the user is asking *how* → this guide. Say which mode you are in.

**Ask, one at a time, with choices.** The user is not expected to know the vocabulary. Every question below offers 2–4 options with one-line consequences. Never ask two things in one message. Never ask something the code or a document already answers.

---

## 1. Get the latest manuals (10 minutes, AI does this)

1. Open **https://www.newebpay.com/website/Page/content/download_api** in a browser (the page returns **403 to `curl` and to plain fetchers** — use the browser tool, or send a browser User-Agent and Referer). *(lesson)*
2. Read the table. As of 2026-09-12 it lists:

   | Document | 程式版本 | 文件版本 | Date | Covers |
   |---|---|---|---|---|
   | 線上交易─幕前支付技術串接手冊 | 2.3 | **NDNF-1.2.5** | 2026-09-01 | MPG checkout (all methods), 單筆交易查詢, 取消授權, 請/退款, 電子錢包退款, BNPL void/refund/capture — **the one you need** |
   | 信用卡定期定額串接技術手冊 | 1.5 | NDNP-1.0.8 | 2026-08-24 | recurring card billing (subscriptions) — only if you sell subscriptions |
   | 物流服務技術串接手冊 (+ 程式範例 zip) | v3.0 | NDNSv1.0.0 | 2024-05-16 | convenience-store logistics API: label, shipment number, query, modify, trace, status push — only if you ship to 超商 |

   Plus CMS modules: **WooCommerce** `newebpay-payment-1.0.12` (2026-03-03, WordPress 6.4.3 / PHP ≥ 8.0), OpenCart 1/2/3, Joomla event modules. **If the user is on WordPress + WooCommerce, install the vendor module first and this guide becomes the checklist for configuring it — do not write a gateway by hand.**
3. **Do not read the manuals from the sandbox portal.** `cwww.newebpay.com`'s download page served NDNF-1.0.8 (2023-10-04) while production served NDNF-1.2.5 — two years behind. *(lesson, verified 2026-09-12)* Manuals from `www`, accounts from `cwww`.
4. Download the PDFs into a gitignored folder (`.vendor-docs/`), record name + version + date + URL in `docs/integrations/vendor-doc-locations.md` (§1.4). If the code was written against an older version, diff the changelog page before anything else (NDNF 1.2.3 → 1.2.5 added OPPAY instalments and memorised-email params; nothing on URLs, codes or CVSCOM *(lesson)*).
5. **Citation convention:** PDF page number = printed footer + 1. Say which you use. *(lesson: a page-off-by-one citation sent a session to the wrong table)*
6. Extract tables with layout preserved (`pdftotext -layout`); a collapsed two-column error table binds codes to the wrong messages (S18.1).

Report: `manuals: NDNF-1.2.5 (2026-09-01), NDNP-1.0.8, NDNS-1.0.0 — on disk at …, locations file updated`.

---

## 2. What are you selling, and how will people pay and receive it? (the choice menu)

Ask these in order. Each answer removes work.

**Q1 — What do you sell?** physical goods / digital downloads / services or bookings / subscriptions / mixed. → Subscriptions add NDNP; digital adds the download-entitlement doctrine (§8, §12); physical adds delivery (Q3).

**Q2 — Which payment methods?** Offer the NewebPay MPG list with the one-line consequence of each (caps and behaviours from NDNF-1.2.5 — cite the page when you show them):

| Method (MPG flag) | What the customer does | Money arrives | Notes to tell the user |
|---|---|---|---|
| 信用卡一次付清 `CREDIT` | card on NewebPay's hosted page | at authorisation, settled per contract | the default; **3-D Secure** is on NewebPay's side; the sandbox needs the product enabled by NewebPay (§6) |
| 信用卡分期 `InstFlag` / 紅利 `CreditRed` | card with instalments / points | as card | needs bank approval per instalment plan; keep off until the contract says on |
| Apple Pay / Google Pay / Samsung Pay `APPLEPAY` `ANDROIDPAY` `SAMSUNGPAY` | wallet on the hosted page | as card | need the card product first; Apple Pay needs domain verification steps in the console |
| LINE Pay `LINEPAY` | redirect to LINE | wallet settlement | **activation is a NewebPay-side approval** — apply in the console and expect a wait (§6); through NewebPay the shop needs **no static IP** *(lesson, NDNF-1.2.5 has no merchant allowlist)* |
| 玉山 Wallet / 台灣 Pay / TWQR | wallet or QR | wallet settlement | same activation shape as LINE Pay |
| WebATM `WEBATM` | pays now via online banking | immediate | fine for any cart size |
| ATM 轉帳 (虛擬帳號) `VACC` | gets a virtual account, pays later at ATM or app | when the transfer lands — **hours or days** | the order is *unpaid* until `NotifyURL` fires; you need an expiry sweep and a "waiting for payment" screen (TW-4) |
| 超商代碼 `CVS` | gets a code, pays at 7-11/全家/萊爾富/OK counter | when paid at the counter | **cap NT$6,000 by default** *(lesson; cite NDNF)* — hide it on larger carts; same waiting rules as ATM |
| 超商條碼 `BARCODE` | prints/shows a barcode, pays at counter | as above | higher cap than 代碼 (check NDNF); same waiting rules |
| 先買後付 BNPL `AFTEE` / `OPPAY` (大哥付你) | credit approval at checkout | provider settles | approval can refuse; refunds go through BNPL capture/void APIs (NDNF §BNPL) |
| 定期定額 (recurring) | separate NDNP API, not MPG | per period | only if Q1 said subscriptions |

Recommend a **starter set** for a first shop: `CREDIT` + `WEBATM` + `VACC`, add `CVS` if the average order is under NT$6,000, add LINE Pay after activation lands. Everything else off until there is a reason. Record the chosen set as data (a `payment_methods` setting), not as constants.

**Q3 — How will physical goods reach the customer?** home delivery by your own carrier (黑貓 / 郵局 / 賣家宅配 — outside NewebPay) / **超商取貨** via NewebPay (取貨不付款: paid online, collected at store; **取貨付款**: paid at the counter) / both. → 超商取貨 adds the CVSCOM flow and, for labels and tracking, the NDNS logistics API and **its hosting requirement** (§4). Home-delivery COD is not a NewebPay product and should not exist in the checkout at all (§3 fulfilment rule 3).

**Q4 — Which chains?** 7-ELEVEN / 全家 / 萊爾富 / OK. → Each is enabled per chain in the console; what the MPG page actually shows is decided by the console, not by your code (S17 — the request field is coarse). Tell the user this before they build a per-chain toggle that cannot work.

**Q5 — Where does it run today, and where will it launch?** localhost only / shared hosting (cPanel: Bluehost, GoDaddy, 遠振, 戰國策…) / VPS (Hetzner, Linode, GCP, AWS EC2) / PaaS (Vercel, Render, Fly, Railway) / serverless. → decides §4 immediately, before any code.

**Q6 — Invoices?** NewebPay's 電子發票 is a separate service and manual, not in NDNF; if the shop needs 統一發票, plan it as its own integration (TW-11) and say so now.

---

## 3. What you must have before coding — so nothing blocks half-way

Print this as a checklist with ✅ / ⏳ / ❌ and *who* obtains each. Everything marked **user** is a real-world step the AI cannot do; start them today because some take days.

### 3a. Identity and accounts

| Item | Sandbox | Production | Who | Notes |
|---|---|---|---|---|
| NewebPay member account | **yes** — free, on `cwww.newebpay.com` | yes — on `www.newebpay.com`, reviewed by NewebPay | user | two separate registrations; keys differ; the sandbox one needs no review |
| Registration type | personal or company | **company** for API use (公司、企業及行號註冊) | user | personal accounts have monthly caps and fewer methods |
| For a **personal** registration the form asks: | account, password, real name, ID number + issue date/place, ID card images (front/back), 健保卡 image, birthday, mobile (SMS OTP), email, address, three consent boxes | same | user | seen on `cwww` 2026-09-12 |
| For a **company** registration the form asks: | admin account + password, company name, 統一編號 (UBN), registered name, capital, establishment date, registered address, business registration image, representative's nationality / ID type / ID number / ID card or ARC or passport + images, contact person, company email, mobile (SMS), phone, address, consents | same | user | have the 營業登記 scan and the representative's ID ready before starting |
| A mobile number that can receive Taiwan SMS | yes | yes | user | registration OTP; foreign numbers may not work |
| Bank account (存摺 image) for 撥款 | not needed | yes | user | payout target; name must match the registered entity |
| 商店 (a shop inside the account) | created in the console after login | same | user, AI guides | each shop has its own **MerchantID, HashKey, HashIV** |
| MerchantID / HashKey / HashIV | from 商店資料設定 → API 串接金鑰 | same, different values | user copies into `.env`; AI never sees them in chat | never commit; sandbox and production pairs are different secrets |

### 3b. Domain, URLs, network

| Item | Why | Sandbox needs it? | Who |
|---|---|---|---|
| A public HTTPS URL on port 443 with a valid certificate | `NotifyURL` (payment result, server-to-server), `ReturnURL` (browser return), `CustomerURL` (ATM/CVS instruction result), logistics push URL | **yes** — NewebPay's sandbox posts to real URLs; on localhost use a tunnel (`cloudflared tunnel`, `ngrok`) and put the tunnel URL in the request | AI sets up the tunnel; user owns the domain |
| Stable outbound IP (see §4) | NDNS logistics API refuses unregistered callers (`1106 不允許 IP`) | for logistics tests from a server, yes | user with host |
| Accurate clock (NTP) | every request carries `TimeStamp`, ±120 s tolerance on logistics calls *(NDNS p.14)* | yes | host |
| `MerchantOrderNo` policy | `[A-Za-z0-9_]`, length limit per manual (MPG 30 / logistics 30 — cite), unique forever | yes | AI |

### 3c. Shop-level facts the code will need

- shop name, contact email and phone for receipts (`Email`, `ItemDesc`)
- for 超商取貨: **sender name and phone** for labels and the **return store** (退貨門市) — a returned parcel goes to the store on file, or to wherever it was posted if blank *(lesson)*; carriers cap name length (7-ELEVEN's importer: **five Chinese characters** *(lesson, found only by the carrier's validator)*)
- prepaid logistics balance (預付費用) funded in the console before labels print (error `1114` *(lesson)*)
- the fee table for every method and chain, from the console's rate page, with the date read — shown beside each toggle in the admin (§3 fulfilment rule 2)
- refund policy per method: card refund via API (Close/Cancel), ATM/CVS refunds are **bank transfers you do by hand**, 取貨付款 collected cash has no API refund — the operator records it (§3 fulfilment rule 10)

---

## 4. Hosting: can your server do what NewebPay needs? (S19, before any code)

NewebPay's requirements on **your** host, and what each hosting shape does to them. Verify the manual pages when citing.

| Requirement | Needed by | Shared cPanel (Bluehost, 遠振, …) | VPS with panel (Hetzner + HestiaCP, Linode, …) | PaaS (Vercel, Render, Fly, Railway) | Serverless |
|---|---|---|---|---|---|
| Inbound HTTPS 443, valid chain, public | every callback | ✅ | ✅ (you install TLS; panels do it) | ✅ | ✅ |
| **Stable outbound IP** | **NDNS logistics API only** (`1106`); *not* MPG, *not* LINE Pay via NewebPay | ⚠️ shared IP is fine, **rotating is not** — ask the host; buy a dedicated IP if it rotates | ✅ fixed | ❌ usually rotates; needs a NAT gateway or static-egress add-on | ❌ |
| Cron (every 10–30 min) | expiring unpaid ATM/CVS orders, querying stuck transactions, tracing parcels | ✅ (cPanel cron) | ✅ | ⚠️ scheduled jobs exist on most; check | ⚠️ |
| Background/long processes | none required | — | — | — | — |
| PHP `openssl` (AES-256-CBC, SHA-256) or equivalent | encryption of `TradeInfo` / `EncryptData_` | ✅ | ✅ | ✅ | ✅ |
| Persistent disk | label PDFs / HTML if you print via B54 | ✅ | ✅ | ⚠️ ephemeral — store labels in object storage | ⚠️ |
| Clock accuracy | `TimeStamp` ±120 s | ✅ | ✅ (enable NTP) | ✅ | ✅ |
| Apache `.htaccess` or an nginx equivalent | protecting `.env`, `src/`, downloads | ✅ Apache | ⚠️ **pure nginx ignores `.htaccess` silently** — install equivalents and prove them by requesting the paths *(lesson)* | n/a | n/a |

**Decision the user must make now, if they chose 超商取貨 in §2:**

- shared hosting with a **stable** outbound IP → register it in the console (§6d); pickup works
- shared hosting with a **rotating** IP → buy a dedicated IP, **or** launch without 超商取貨 and add it when moving to a VPS *(lesson: the mixoweb plan)*
- PaaS / serverless → logistics API needs a static-egress feature; if the platform has none, run the logistics calls from a small VPS or skip 超商取貨

**Direct LINE Pay (not via NewebPay) does need a merchant IP allowlist** and a separate merchant application; through NewebPay it does not, because the shop never calls LINE Pay — the customer's browser goes to NewebPay's page, which talks to LINE. *(lesson, NDNF-1.2.5 read at source)* Tell the user this before they buy a static IP for the wrong reason.

Report: the S19 table for the chosen host, every row satisfied / not / unknown, and the one action if a row is not satisfied.

---

## 5. Register the sandbox account (user drives, AI guides, ~20 minutes + SMS)

1. AI opens **https://cwww.newebpay.com/website/Page/content/register** and explains the two buttons: 個人身份註冊 (`/main/registration`) and 公司、企業及行號註冊 (`/company/company_procedures/add_company`). Recommend **company** if the user has a 統一編號, because production will be company and the sandbox should mirror it; personal is fine to start learning.
2. AI walks the form field by field (the lists in §3a), saying which are identity fields the user types themselves. AI may fill: account name (a chosen login), email, address, contact phone — **only when the user says the value**. AI does not touch password, ID number, ID images, or the consent boxes.
3. User completes SMS verification and submits. AI waits.
4. User logs in at **https://cwww.newebpay.com/main/login_center/single_login**. AI does not handle the password.
5. **Create a shop:** in the member area find 商店管理 / 商店設定 → 新增商店 (words may vary). The shop needs a name, a category, and the site URL (use the tunnel URL for now — it can be changed).
6. **Get the keys:** 商店資料設定 → the API / 串接 section shows **MerchantID (商店代號, starts `MS`), HashKey (32 chars), HashIV (16 chars)**. User copies them into `.env` as `NEWEBPAY_MERCHANT_ID`, `NEWEBPAY_HASH_KEY`, `NEWEBPAY_HASH_IV`, plus `NEWEBPAY_ENV=sandbox`. AI confirms the file is gitignored and the lengths are right (32 / 16) without printing the values.
7. Record in `docs/integrations/sandbox.md`: which portal, which shop, the date, where the keys live — **never the keys**.

**If the user already has a production account** and thinks that means they can skip this: no — sandbox is a separate registration on `cwww` with separate keys, and development runs there. *(lesson: a weeks-long "blocked on a merchant account" entry that was never real)*

---

## 6. Switch things on in the sandbox console — and prove each one is on

A method that is off in the console fails at checkout with a code the customer sees. Do this before writing the request builder, so the first test is a real test.

### 6a. Payment methods

Console path *(as seen 2026-08, mixoweb; find the words)*: 商店資料設定 → **交易手續費及撥款天數** → each method has 啟用 / 停用. Enable exactly the §2 set. Note the fee and 撥款天期 shown beside each — they go into the admin's fee table.

**Some products are enabled on NewebPay's side, not yours.** *(lesson: `MPG02003` on every card checkout for three days with every local check green; a 客服 escalation on 2026-08-14 flipped it by 2026-08-17.)* So:

- after enabling, **probe before building**: post one synthetic MPG request (a throwaway `MerchantOrderNo` like `PROBE_<timestamp>`, `Amt` 1, `CREDIT=1`) to `https://ccore.newebpay.com/MPG/mpg_gateway` from a script; PASS = the response is NewebPay's card-entry page echoing your order number; FAIL = the body contains `MPG02003`, `MPG00040`, `CHK00007` or a `TRA` code. No order, no cart, no database needed — credentials and a callback URL only. *(lesson: `tools/ops/probe-newebpay-mpg-synthetic.php`)*
- a FAIL with `MPG02003` after the toggle is on means the product is not enabled at NewebPay; this is one of the few cases where the vendor's 客服 (02-2786-3655, cs@newebpay.com, 08:00–23:00) is the only path. Record it as a **dated external wait** with the question and what it blocks (S14.1); keep building everything else. Do not repeat the probe in a loop — the query API locks for **4 hours** after too many not-found lookups (`TRA10071`, NDNF-1.2.5 p.95) and refunds lock for 1 hour (`TRA10702`) *(lesson)*.
- **LINE Pay / wallets / BNPL** show an application step rather than a toggle; apply, record the date, expect days.

### 6b. URLs

商店資料設定 → the URL fields (names vary): set the default `ReturnURL` / `NotifyURL` / `CustomerURL` to the tunnel or domain. They can also be sent per request; the request wins. `NotifyURL` is the only one that proves payment (TW-3): the browser return is UX.

### 6c. 3-D Secure and test cards

The sandbox's test card numbers, expiry and CVV are in NDNF-1.2.5's test section — **read them from the manual each run, never store them** (§0.8 hard limit). 3DS behaviour in the sandbox is simulated; do not conclude anything about production frictionless rates from it.

### 6d. Logistics (only if §2 chose 超商取貨)

會員專區 → **物流中心** (or 物流服務) — enable the service, then per chain; set **退貨門市**, **取貨人 / 寄件人** details, the **貨態通知 (push) URL** (NPA-B58 target), fund **預付費用**, and register the **outbound IP** in the allowlist field. Where that field lives is not stated in NDNS-1.0.0 *(lesson: left UNKNOWN in the manual)* — find it in the console under the shop's logistics settings; if it truly does not exist for the sandbox, the sandbox may not enforce `1106` and the first enforcement will be production: say so in the readiness card.

For orders paid through MPG with `CVSCOM=1` (取貨不付款) or `CVSCOM=2` (取貨付款), **NewebPay's payment page hosts the store picker** and the callback returns `StoreCode / StoreName / StoreAddr / StoreType / LgsNo / LgsType`; the logistics API is then for labels (B54), shipment numbers (B53), query (B55), modify (B56), trace (B57) and the push (B58). Do not build a separate store-map round trip for MPG orders. *(lesson, NDNF-1.2.5 §4 + NDNS)* Cap for 取貨付款: **NT$20,000 including freight** (NDNF, cite page). The sandbox **cannot simulate parcel status pushes**; the first proof of the 到店 → 取貨 → 未取退回 lifecycle is a real parcel sent to yourself, one per chain *(lesson)*.

### 6e. Prove the switch, not the click

For each method enabled: one synthetic probe (6a) or one sandbox order, and a line in the readiness card: `CREDIT: enabled 2026-09-12, probe PASS`. A method with a toggle on and no probe is `UNVERIFIED`.

---

## 7. Wire it (the contract, in the order things go wrong)

Read NDNF-1.2.5 §MPG for every field; this list is the *shape*, with the traps a first integration hits.

1. **Envelope:** `MerchantID`, `TradeInfo` = AES-256-CBC (key HashKey, iv HashIV, PKCS7, **hex**) over the URL-encoded parameter string; `TradeSha` = `strtoupper(sha256("HashKey={key}&{TradeInfo}&HashIV={iv}"))` — over the **ciphertext**, not the fields; `Version` as the manual states. *(lesson: signing the plaintext "verifies" nothing; and this is AES-**256**, ECPay is AES-128 — the resemblance is the trap)*
2. **Hosts:** sandbox `https://ccore.newebpay.com/MPG/mpg_gateway`, production `https://core.newebpay.com/MPG/mpg_gateway`; query and refund endpoints per manual; **one environment switch** read in one place, shown in the admin header (S22.6 — a sandbox that looks like live is a mode error with money behind it).
3. **Callback handling:** verify `TradeSha` over the received `TradeInfo` **before** decrypting; then decrypt; then check `Status`, `MerchantOrderNo`, `Amt`, `MerchantID`, `PaymentType`; then apply idempotently (`TradeNo` unique); then acknowledge. The manual specifies no acknowledgement string the merchant must return *(lesson: a claimed `SUCCESS` ack was a misreading — read the page)*. A callback that arrives for an order already `paid` is a no-op, not an error.
4. **Three URLs, three meanings:** `NotifyURL` = money (server-to-server, the record); `ReturnURL` = the customer comes back (show "we are confirming", never "paid"); `CustomerURL` = instruction issued (ATM account / CVS code / store chosen) — write the instruction and the store, **never a money column** *(lesson)*. `ClientBackURL` = the customer pressed back.
5. **Async methods:** an ATM/CVS order is `awaiting_payment` with an `ExpireDate`; a cron expires it and releases stock; a payment that lands after expiry is a real case (TW-4) with an operator queue.
6. **Query and refund:** `QueryTradeInfo` for stuck orders — bounded, not polled; `Close` (請/退款) for cards, `Cancel` for un-captured authorisations; wallet and BNPL refunds have their own APIs. Respect the lock rules (6a).
7. **Logistics push (B58):** request-style underscored keys (`EncryptData_`, `HashData_`); `HashData` formula puts the cipher in the *middle* (`HashKey=…&{cipher}&HashIV=…`) *(NDNS p.14; lesson)*; idempotent on (`MerchantOrderNo`, `RetId`, `EventTime`); every `RetId` maps to a shipment state that exists (§3 fulfilment rule 6).
8. **Secrets:** `.env` only; the admin shows "configured / not configured", never the value; test cards never stored.

---

## 8. Sandbox walk (the AI runs it, §0.8)

For each method in the §2 set: place one order through the real checkout in the browser (tunnel up), pay with the manual's test data, watch `NotifyURL` land (poll your own inbox table, not the human), see the order flip, see the admin badge, then refund it through the API where the sandbox supports refund. Capture: the DB rows, the callback payload (redacted), a screenshot of the customer page and of the admin page. For ATM/CVS: place the order, confirm the instruction appears, then use the console's 模擬付款 / test-payment feature if present (find it; if absent, the async path is `UNVERIFIED` in the sandbox and the first proof is production — say so). For 超商取貨: place the order, pick a store on NewebPay's page, confirm `StoreCode` lands, print a label (B54), and note that pushes cannot be simulated.

Feed the result into the four-corner table (S15): customer sees / operator sees / NewebPay believes / (carrier believes), per state.

---

## 9. Going live — the switch, as a checklist

| Step | Who | Proof |
|---|---|---|
| Production account approved on `www.newebpay.com` (company documents reviewed by NewebPay) | user | login works on `www` |
| Production shop created; **production** MerchantID / HashKey / HashIV in the live `.env`; `NEWEBPAY_ENV=production` | user | admin header shows PRODUCTION; sandbox keys absent from the live host |
| Each §2 method enabled in the **production** console (enablement does not copy from sandbox), LINE Pay / wallets approved | user | probe (6a) against `core.newebpay.com` PASS per method |
| Production `NotifyURL` etc. reachable on the real domain, cert valid | AI checks | `curl -I` from outside; a test callback |
| Outbound IP registered for logistics (if 超商取貨) | user | one label prints from the live host |
| Fee table entered as data with the date read | user + AI | admin shows fee per method/chain |
| **Canary:** one real card order at the smallest amount, refunded the same day; one real parcel per chain | user | order page walks paid → refunded; parcel walks 到店 → 取貨 |
| Cron installed for expiry / query / trace, with a heartbeat something reads (S20) | AI + user | cron page shows it; heartbeat updates |
| Query and refund rate limits respected in code | AI | no loop can exceed the lock thresholds |

---

## 10. Gotchas from a real integration, in one table

| Trap | What happens | Rule |
|---|---|---|
| Reading the sandbox portal's manuals | you build against a 2023 document | manuals from `www`, accounts from `cwww` |
| `curl` on the docs page | 403 | browser tool, or UA + Referer |
| PDF page vs printed folio | citations off by one | say which; PDF = folio + 1 |
| `TradeSha` over plaintext | callback "verifies" anything | sign the ciphertext |
| AES-128 (copied from ECPay code) | decrypt fails or, worse, "works" in a stub | AES-256-CBC, hex |
| Acknowledgement string assumed | retries or silent stop | read the manual; the merchant returns nothing specified |
| Toggle on, product not enabled at NewebPay | `MPG02003` on every checkout | synthetic probe; dated 客服 wait |
| Polling `QueryTradeInfo` for unknown orders | **4-hour lock** `TRA10071` | bounded queries only |
| Repeated refund calls | 1-hour lock `TRA10702` | idempotent refund state |
| Static IP bought for LINE Pay | money spent for nothing | via NewebPay, none needed; **logistics** needs one |
| Shared host with rotating IP + 超商取貨 | labels refused `1106` in production only | ask the host; dedicated IP; or defer pickup |
| 超商代碼 on a NT$8,000 cart | refused at NewebPay | cap NT$6,000; hide by cart size |
| Building your own store map for MPG orders | duplicate flow, wrong fields | MPG hosts the picker (`CVSCOM`); logistics API for labels/trace |
| 7-ELEVEN sender name of 7 characters | importer rejects, no manual says why | ≤ 5 Chinese characters; run the carrier's validator |
| Return store left blank | returns go to whichever store posted the parcel | set 退貨門市 |
| Prepaid balance empty | `1114` at label time | fund 預付費用 before the first label |
| Pushes expected in the sandbox | none ever arrive | real parcel canary |
| Asking 客服 as the first move | days, boilerplate | sandbox-empirical first; 客服 only for vendor-side enablement, as a dated wait |
| Sandbox keys on the live host | "production" that pays nobody | one env switch, shown in the admin |

---

## 11. The readiness card (what setup mode prints at the end of every session)

```
NewebPay readiness — <shop> — <date>
Mode: sandbox | production
Manuals: NDNF-1.2.5 (2026-09-01) ✅ on disk · NDNP ⏭ not needed · NDNS-1.0.0 ✅
Account: sandbox ✅ (company) · production ⏳ under review since <date>
Shop + keys: sandbox ✅ in .env (lengths ok, gitignored) · production ❌
Methods chosen: CREDIT ✅ probe PASS · WEBATM ✅ · VACC ✅ · CVS ⏭ off (cart > 6k) · LINEPAY ⏳ applied <date>
Delivery: 超商取貨 (取貨付款) on 7-11 + 全家 ✅ enabled · 退貨門市 ✅ · 寄件人 ✅ · 預付費用 ❌ fund it · push URL ✅ · outbound IP ⏳ host asked <date>
Host (S19): Bluehost shared — inbound 443 ✅ · outbound IP unknown ⏳ · cron ✅ · clock ✅
URLs: NotifyURL/ReturnURL/CustomerURL → tunnel ✅ (production domain ❌)
Sandbox walk: CREDIT round-trip ✅ (artefacts …) · VACC ⏳ 模擬付款 not found · pickup ⏭ pushes need a real parcel
Waits on others: LINE Pay approval (NewebPay, since <date>) · outbound IP answer (Bluehost, since <date>)
Next three actions, in order: 1 … 2 … 3 …
```

A ❌ or ⏳ with no owner and no date is a finding against the guide, not the user.
