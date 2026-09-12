# LINE Pay — Setup Guide: direct Online API, or through NewebPay / PAYUNi

Loaded by `ecommerce-cia` in **setup mode** (SKILL.md §0.15) when a project names LINE Pay, or a user asks for it. LINE Pay is the one method in Taiwan that a shop can reach **two ways**, and the first question decides everything after it: **direct** (your server calls LINE Pay's Online API with your own Channel ID and Channel Secret) or **via a gateway** (NewebPay `LINEPAY=1`, PAYUNi `LinePay=1` — LINE Pay is one flag on that gateway's hosted page). **Not ECPay**: its AIO has no LINE Pay flag (`developers.ecpay.com.tw/2864.md`, read 2026-09-13 — `ChoosePayment` offers Credit, ApplePay, WebATM, ATM, CVS, BARCODE, TWQR 行動支付, BNPL, WeiXin and `DigitalPayment` = 綠界's own 電子支付/電子錢包); a shop on ECPay that wants LINE Pay integrates it directly or adds a second gateway. Most first shops should take the gateway route; this guide says why, and then covers the direct route completely for the shops that need it.

**Sources.** LINE Pay's developer site is the authority: `https://developers-pay.line.me` (Docusaurus; English / 中文 / 한국어; no PDF, no login). Read fresh at §2 and cite the page path. Everything below that is not a page citation is marked *(lesson)*. Read at source 2026-09-13: the reference lists **Online API v3 and v4** (v4 added November 2025 for Taiwan's 電子支付機構 rules; same authentication, same endpoints under `/v4`, plus `info.paymentProvider` on confirm / capture / details and `options.regPayRequest` on request — change log). Japan-specific content was removed May 2025.

**What the AI may and may not do here** is the same hard limit as the NewebPay guide: open pages, read, explain every field, run every probe; never type a password, a national ID, upload an ID image, create the merchant or sandbox account, or change a merchant-center setting without a fresh explicit "yes" for that one change.

---

## 0. Direct or via a gateway — decide first

| | Via NewebPay / PAYUNi | Direct Online API |
|---|---|---|
| Contract | one gateway contract covers cards, ATM, 超商 and LINE Pay | a separate LINE Pay merchant agreement (`https://pay.line.me/tw` → 商家申請), separate review |
| Credentials | none from LINE; the gateway's keys | your own **Channel ID + Channel Secret** from the LINE Pay Merchant Center |
| Who switches it on | the gateway's 客服 (NewebPay: form + quote, sandbox included; PAYUNi: sandbox works with any Channel ID) | LINE Pay's review of your merchant application |
| Settlement | pooled with the gateway's other methods, one statement | LINE Pay pays you directly; a second statement to reconcile |
| Code | zero LINE-specific code; the hosted page does it | request → redirect → confirm → (capture/void) → refund, HMAC headers, 19-digit ids |
| Host | whatever the gateway needs (NewebPay: none extra for LINE Pay) | HTTPS TLS 1.2+ redirect pages; **no fixed outbound IP is required for the Online API** — see §4 |
| Refunds | through the gateway's refund API / console | `POST /v3/payments/{transactionId}/refund`, full or partial |
| Pick it when | a first shop, one statement wanted, LINE Pay is one method among several | LINE Pay is the main method (LINE-native brand, LIFF shop, LINE 官方帳號 commerce), you want `paymentUrl.app` deep links, pre-approved (regKey) payments, or the gateway's LINE Pay wait is blocking launch |

**Ask:** "Is LINE Pay one of several ways to pay, or the way to pay?" Several → the gateway route; go to that provider's guide (`newebpay-onboarding.md` §2 row `LINEPAY`, `payuni-onboarding.md` `LinePay=1`) and stop here — the only LINE-specific facts there are *who enables it* and *that a probe returns a refusal until they do*. The way → continue.

*(lesson, mixoweb 2026-09)* A shop that started on NewebPay waited on NewebPay's 客服 to enable LINE Pay in the sandbox. That wait is real and dated; it is not a reason to buy a static IP or to start a direct integration mid-project. Record it on the readiness card and keep building.

---

## 1. Detect, and decide the mode

`python tools/linepay/detect.py [dir]` — prints JSON, never secret values.

- **direct** signals: `sandbox-api-pay.line.me`, `api-pay.line.me`, `/v3/payments/…` or `/v4/payments/…`, `X-LINE-Authorization`, `X-LINE-ChannelId`, env keys `LINEPAY_*` / `LINE_PAY_*` / `CHANNEL_ID` + `CHANNEL_SECRET`
- **via** signals: NewebPay `LINEPAY => 1`, PAYUNi `LinePay`; an ECPay `ChoosePayment` that names LINE Pay is flagged as **suspect** — ECPay's AIO has no such value, so the code is promising a method the gateway will not render (S17 hosted-surface control)
- **offline API** signals (`/v2/payments/oneTimeKeys`, `/v4/payments/oneTimeKeys`) mean a POS / in-store flow, not e-commerce — a different guide; say so
- direct + a confirm handler found → **audit mode** (walk request → confirmUrl → confirm as one channel; S15/S16/S17 apply); direct without → **setup-direct**; via → that gateway's guide; brand only → §0 question

---

## 2. Get the latest reference (5 minutes, AI does this)

`python tools/linepay/fetch_docs.py --latest` lists the Online API versions in the nav, every endpoint per version, and the change log's newest heading. `--fetch DIR` saves the core pages as text under `DIR/linepay/`. Cite as `developers-pay.line.me/<path>`, dated.

| Page | Why it matters |
|---|---|
| `online/prerequisites` | the three headers and the exact HMAC message (§7) |
| `online-api-v3` / `online-api-v4` | hosts, endpoints, the **result-code table** (feed it to `tools/explain_error.py linepay:<code>`) |
| `online-api-v3/request-payment` | body: `amount`, `currency`, `orderId` (≤100), `packages[]` (`id`, `amount`, `products[]`), `redirectUrls` (`confirmUrl`, `cancelUrl`), `options`; read timeout ≥ 10 s |
| `online-api-v3/confirm-payment` | body `{amount, currency}` must equal the request; read timeout ≥ 40 s; capture-separated and regKey variants |
| `online-api-v3/check-payment-request-status` | `0000` waiting · `0110` confirm now · `0121` cancelled/expired · `0122` failed · `0123` completed; poll ≥ 1 s apart |
| `online-api-v3/refund` | `{refundAmount}` optional = partial; omitted = full; read timeout ≥ 20 s; `1900/1902/1999` retryable |
| `online-api-v3/merchant/redirection-pages` | HTTPS TLS 1.2+; LINE Pay calls confirmUrl/cancelUrl by **HTTP GET** with `orderId` + `transactionId`; connection timeout 5 s, read 20 s; the LINE Pay IPs to allowlist **inbound** when `confirmUrlType` is `SERVER` |
| `sandbox`, `faq`, `api-change-log` | sandbox account rules, the 1106 explanation, v3 → v4 differences |

**Version choice:** new integration → **v4** (a superset; `paymentProvider` tells you whether an EPI or a TSP settled — the field always reads `TSP` for online today, per the change log). Existing v3 code → stay on v3 unless you need the field; both are served. Say which one you chose and why.

---

## 3. What you must have before coding

### 3a. Accounts and credentials (user drives, AI beside)

| Item | Who | How long | Notes |
|---|---|---|---|
| **Sandbox account** | user | minutes, e-mail | `https://developers-pay.line.me/sandbox` → *Apply for a sandbox account*. **One sandbox account per e-mail address**, online OR offline. If the shop already joined as a merchant, no sandbox application is needed — production credentials work on the sandbox host (FAQ) |
| **Sandbox Channel ID + Channel Secret** | user | minutes | Merchant Center → **Developer Tools → Manage Link Key** (開發者工具 → 管理連結金鑰) → *View*; an e-mail verification code is required each time (sandbox page) |
| **A personal LINE account** | user | — | the sandbox payment page requires logging in with a **personal LINE account**, every time (FAQ) |
| **Merchant application (production)** | user, days–weeks | LINE Pay Taiwan review | `https://pay.line.me/tw` → 商家; the merchant-center guide is 繁體中文 only. Accounts opened **through an agency** cannot see their own Channel ID/Secret or edit the server allowlist — the agency must (FAQ). Shops using a **fixed LINE Pay payment code** (店家固定條碼) need a *separate* application to use the Online API (FAQ) |
| Production Channel ID + Secret | user | after approval | same Manage Link Key page, production account |

### 3b. URLs and network

- `confirmUrl` and `cancelUrl` on **HTTPS with a trusted certificate, TLS 1.2+**; a tunnel is fine for the sandbox
- LINE Pay reaches those URLs by **GET**; if you set `options.redirection.confirmUrlType = SERVER`, allowlist LINE Pay's addresses on your inbound firewall: sandbox `147.92.159.209, 147.92.159.21, 147.92.159.68, 147.92.216.167`; production `211.249.40.1–30, 147.92.220.5–8` (redirection-pages page, read 2026-09-13 — re-read before go-live)
- product `imageUrl` in the sandbox must be HTTPS or it does not render (FAQ)

### 3c. Shop facts the code needs

- currency of the contract (`TWD` for Taiwan; the API also lists `USD`, `THB`) — a mismatch is `1178`
- integer amounts (TWD has no decimals) — `1124`
- minimum / maximum per-transaction amounts if the merchant set any — `1183` / `1184`
- whether capture is automatic (default) or separated (`options.payment.capture = false` → confirm authorises, then capture or void)

---

## 4. Hosting: can your server do what LINE Pay needs? (S19)

| Requirement | Shared hosting | VPS | PaaS (Render/Railway/Fly) | Serverless |
|---|---|---|---|---|
| Outbound HTTPS to `api-pay.line.me` with read timeouts of **10 / 40 / 20 s** (request / confirm / refund) | ✅ usually, check `max_execution_time` ≥ 60 | ✅ | ✅ | ⚠️ function timeout must exceed 40 s for confirm |
| Inbound HTTPS, TLS 1.2+, trusted cert, on `confirmUrl` / `cancelUrl` | ✅ | ✅ | ✅ | ✅ |
| Inbound allowlist for LINE Pay IPs (only if `confirmUrlType = SERVER`) | ⚠️ often no firewall control | ✅ | ⚠️ | ⚠️ |
| **Fixed outbound IP** | **not required by the Online API** (v3/v4 prerequisites list only the three HMAC headers; the "server allowlist" is an **Offline API v2** concept and was removed in Offline v4) | — | — | — |
| 64-bit integers or strings for `transactionId` (19 digits) | ✅ PHP 64-bit | ✅ | ✅ | ⚠️ JavaScript: quote before `JSON.parse` |
| A clock within a few minutes (nonce may be a timestamp) | ✅ | ✅ | ✅ | ✅ |

**Tell the user this before they spend money:** the belief that "direct LINE Pay needs a static IP" comes from the Offline (POS) API's server allowlist and from agency hearsay. For the **Online** API v3/v4 authentication is the HMAC header, and no page in the prerequisites or the reference asks for a merchant server IP; if the merchant center offers a server-allowlist page it is optional protection, not a prerequisite — an integration on a rotating-IP host works. *(read at source 2026-09-13: `online/prerequisites`, `api-change-log` "Removed server allowlist (IP allowlist) settings" under Offline API v4)*. If the user's merchant center shows a server-allowlist page and the account was opened through an agency, the agency must edit it (FAQ).

---

## 5. Sandbox account and credentials (user drives, ~10 minutes)

1. AI opens `https://developers-pay.line.me/sandbox` and reads the three steps aloud in plain words.
2. User applies with an e-mail that has not been used for a LINE Pay sandbox before (one per address).
3. User logs into the merchant center (`https://pay.line.me/portal/tw/auth/login`, TW; the sandbox page links the portal), **Developer Tools → Manage Link Key → View**, enters the e-mail code, and pastes the two values into `.env` as `LINEPAY_CHANNEL_ID` / `LINEPAY_CHANNEL_SECRET` themselves. AI checks lengths and gitignore only; never prints them.
4. `LINEPAY_ENV=sandbox`, `LINEPAY_CALLBACK_BASE=https://<tunnel or domain>`.
5. Sandbox transactions are visible in the merchant center's **sandbox menu** (FAQ) — that is where "did it land" is answered.

### 5a. Approving a sandbox payment — the page has two shapes *(live, 2026-09-13)*

`info.paymentUrl.web` opens `sandbox-web-pay.line.me/web/payment/wait…` → `waitPreLogin`. The same sandbox served **two different pages** within one hour, so the guide covers both; the AI reads the page (or `curl -A Mozilla` it) and says which one the user is looking at:

**Shape A — pop-up simulator.** The visible page is a decoy ("Please update to the latest version of LINE / LINE must be installed"). Its script polls `/web/payment/check/<reserveId>` every 3 s and on the first poll **opens a 320×560 pop-up** `/web/sandbox/payment/<sandboxMerchantKey>/<reserveId>` with the amount, the product names and one **PAY NOW** button ("This simulation does not actually select a method of payment or make actual payments"). Chrome blocks the pop-up, so nothing seems to happen: **allow pop-ups for `sandbox-web-pay.line.me`** or open the pop-up URL from the page source. PAY NOW → "Payment completed" → `--check` = `0110`. No LINE login at all on this path.

**Shape B — LINE web login / QR.** The page shows "Your payment will be processed in the LINE Pay app when you log in with your LINE account or scan the QR code", a **LINE Log in** button (`access.line.me/dialog/oauth/weblogin` → back to `waitPostLogin`) and a QR code. This is where the **sandbox payer account** from the sandbox e-mail (`test_…@line.pay` + password) is used: click LINE Log in, sign in with it, approve the amount. The user types that login; the AI never does.

- The payer test account is a password — it goes into the LINE login form and nowhere else; never paste it into a chat, a file or a ticket.
- **A phone fails** on Shape A: the simulator URL on iOS Safari answered 無法處理您的申請 (generic error); the desktop user-agent works. Test on the PC.
- **Capture-separated is a contract feature**: `options.payment.capture=false` on the sandbox merchant → `2103 Parameter is not allowed [capture:false]`. Do not design an authorise-then-capture flow until the merchant agreement includes it; `--no-capture` on the probe shows the answer in one call.
- **Never call confirm before `--check` says `0110`**: a premature confirm returned `1169` *and then the reservation died* — the next `--check` was `0122 payment failed` and the customer could no longer approve it. New request needed.
- `--details` on an unconfirmed reservation → `1150` (details lists confirmed payments only); after confirm → `payStatus: CAPTURE`, `payInfo[].method: CREDIT_CARD` in the simulator.

---

## 6. Prove the credentials, then prove a payment

`php tools/linepay/probe_request.php` posts one 1 TWD request with a throwaway `orderId`. Nothing is charged: a request reserves a transaction and returns the page a customer would have to approve.

| Result | Meaning | Next |
|---|---|---|
| `PASS — returnCode 0000; transactionId …; payment page …` | credentials valid on this host, the merchant may request payments | open the URL on a PC, allow the pop-up, PAY NOW (§5a); then `--check <transactionId>` → `0110` → `--confirm` |
| `FAIL — 1104 Merchant not found` | Channel ID not registered on this environment — live-verified: fake credentials return exactly this | re-copy from Manage Link Key; check `LINEPAY_ENV` matches the host |
| `FAIL — 1106 header error` | HMAC did not verify: secret wrong, or signed bytes ≠ sent bytes | `php tools/linepay/sign.php selftest`; sign the exact serialised body |
| `FAIL — 1105` | merchant unavailable (suspended / not approved) | vendor-side, dated wait |
| `FAIL — 1178 / 1183 / 1184 / 1124` | currency or amount settings | fix the field or `--amount N` |
| `REFUSED: LINEPAY_ENV=production` | the probe will not touch production without `--i-mean-production` | intended |

`--v4` runs the same against `/v4/payments/request`. `--dry-run` prints the exact body (secret redacted) to compare with the reference page when `2101` / `2102` appear. `--confirm <id>`, `--refund <id> [--amount N]` and `--details <id>` complete the walk from the same tool — all live-verified 2026-09-13 on a sandbox Channel: confirm `0000` + `payInfo`, refund `0000` + `refundTransactionId`, second refund `1165`, second confirm `1172`, check after completion `0123`.

**A PASS here is a credential proof, not a payment proof.** The payment proof is §8: approve on the page, confirm, see `payInfo`.

---

## 7. Wire it — the contract, in the order things go wrong

1. **Headers** (`online/prerequisites`): `X-LINE-ChannelId`; `X-LINE-Authorization-Nonce` = UUID v1/v4 or timestamp, **fresh per request**; `X-LINE-Authorization` = Base64(HMAC-SHA256(key = ChannelSecret, message = ChannelSecret + apiPath + body + nonce)) for POST, and `… + apiPath + queryString + nonce` for GET. `tools/linepay/sign.php` is the reference implementation; its selftest is cross-checked against Python's stdlib HMAC in `tests/test_linepay_tools.py`.
2. **Sign the bytes you send.** Serialise once, sign that string, post that string. Re-encoding (different key order, pretty-printing, a trailing newline) → `1106` (FAQ names whitespace and key order explicitly).
3. **Request** (`POST /v3/payments/request`): `amount` = Σ `packages[].amount` (+ `userFee`); `orderId` unique per request (`1172` otherwise — suffix retries); `redirectUrls.confirmUrl` / `cancelUrl` HTTPS; keep `info.transactionId` **as a string** (19 digits; `1150` / `1155` when a parser rounds it) together with `orderId`, before redirecting.
4. **Redirect** the customer to `info.paymentUrl.web` (the sandbox does not support `paymentUrl.app` — FAQ).
5. **confirmUrl** is called by **GET** with `orderId` and `transactionId` appended — do not put those parameters in the URL yourself (LINE Pay appends them; an `orderId` already in the URL is left alone). This is where the money is still unsettled: the handler must call **confirm**, not mark the order paid.
6. **Confirm** (`POST /v3/payments/{transactionId}/confirm`, body `{amount, currency}` identical to the request): `0000` + `info.payInfo[]` (`BALANCE` / `CREDIT_CARD` / `POINT`) = paid (capture automatic) — or authorised only if you separated capture. Make it **idempotent per transactionId**: a customer who reloads the confirm page double-submits → the sandbox answered a second confirm with **`1172`** ("order with this orderId already exists"; the reference also lists `1145` in-progress and `1152` duplicate); read all three as "already done" and look the order up with `--details`, never as failure. Read timeout ≥ 40 s; a retry inside it → `1198`.
7. **No confirmUrl flow** (`implement-payment` variants): poll `GET /v3/payments/requests/{transactionId}/check` ≥ 1 s apart; `0000` is *still waiting*, `0110` is *confirm now* — the same four digits mean different things on different endpoints; `tools/explain_error.py linepay:0000` says so.
8. **Capture / void** only when capture was separated: `POST /v3/payments/authorizations/{id}/capture` (`1153` if the amount differs) or `/void`.
9. **Refund** (`POST /v3/payments/{transactionId}/refund`): omit `refundAmount` for full, set it for partial; `1164` past the paid total, `1165` already refunded (treat as success), `1163` past the refund window → manual refund via the merchant center, recorded on the order (S16: a refund the API cannot make is not a refund that did not happen).
10. **Reconcile** (`GET /v3/payments?orderId=…` or `transactionId=…`, ≤ 100 ids — `1177`) in the settlement sweep: a paid order in LINE Pay with no `paid` row in the shop, and the reverse, are both findings (S15 four-corner walk: customer, operator, database, LINE Pay).
11. **Errors are JSON with `returnCode` / `returnMessage`** (some failures use `resultCode` / `statusMessage` per the reference example — accept both). HTTP is always 200; never key on the status code.

---

## 8. Sandbox walk (the AI runs it, §0.8)

One end-to-end order: request → open `paymentUrl.web` in the browser tool → user logs in with a personal LINE account and approves (the AI never enters the LINE credentials) → confirmUrl hit → confirm → order `paid` with `transactionId` and `payInfo` stored → refund of the same order → merchant center sandbox menu shows both. Artefacts: the request body (secret redacted), the confirm response, the refund response, the order row, a screenshot of the sandbox transaction list. Then the negative walk: cancel on the LINE page → `cancelUrl` → order stays unpaid; reload the confirm page → second confirm returns `1172` (or `1145`/`1152`) and the order is not double-paid. *(Run 2026-09-13 on the skill's own sandbox Channel: request → PAY NOW → `0110` → confirm `payInfo CREDIT_CARD 1` → details `CAPTURE` → refund → `1165` on retry → `1172` on re-confirm → `0123`.)*

---

## 9. Going live — the switch, as a checklist

| Item | Who | Proof |
|---|---|---|
| LINE Pay merchant application approved (TW) | user | production Channel ID/Secret visible in Manage Link Key |
| `LINEPAY_ENV=production`, production keys in the production `.env` only | user | `probe_request.php --dry-run` shows host `api-pay.line.me`, id length ok |
| `confirmUrl` / `cancelUrl` on the real domain, TLS 1.2+, trusted cert | user / host | `curl -sI` from outside; a TLS check |
| If `confirmUrlType = SERVER`: production LINE Pay IPs allowed inbound | host | firewall rule listed; re-read the redirection-pages page for the current ranges |
| Read timeouts 10 / 40 / 20 s in the HTTP client; no blind retries | code | config lines quoted |
| `transactionId` stored as string end-to-end | code | column type + one production-shaped id in a test |
| Canary: one real order at the minimum amount, then refunded via the API | user + AI | both rows in the merchant center |
| Merchant-center settings (amount limits, allowlist) reviewed | user | screenshot |

---

## 10. Gotchas, in one table

| Trap | What happens | Truth |
|---|---|---|
| "Direct LINE Pay needs a static IP" | money spent on a dedicated IP, launch delayed | Online API v3/v4: no outbound allowlist requirement; the allowlist is an Offline API concept (removed in Offline v4) and an optional merchant-center protection |
| Marking the order paid on the confirmUrl page | unpaid orders shipped | confirmUrl means *authenticated*; only `confirm` → `0000` + `payInfo` means paid |
| `transactionId` through `JSON.parse` / a float column | `1150` on confirm, "transaction not found" | 19-digit integer; keep it a string (the reference's `handleBigInteger`) |
| Re-serialising the body before signing | `1106` on every call | sign the exact bytes sent; whitespace and key order count |
| Signing the body on a GET | `1106` on `/check` and `/payments` | GET signs the query string |
| Reusing `orderId` on retry | `1172` | unique per request |
| Retrying confirm inside the read timeout | `1198`, then `1145` | wait ≥ 40 s; check status; idempotent handler |
| Confirm before the customer approved | `1169`, then the reservation dies (`0122`) | poll `--check` for `0110` first; a dead reservation needs a new request |
| `options.payment.capture=false` on a merchant without the feature | `2103 Parameter is not allowed` | authorise-then-capture is contractual; ask LINE Pay, then `--no-capture` to prove it is on |
| Sandbox payment page shows "update LINE" | tester installs LINE, tries a phone, gives up | it is a pop-up simulator: allow pop-ups on `sandbox-web-pay.line.me`, PAY NOW on a PC; no LINE login |
| Sandbox `test_…@line.pay` account | typed into every page, in chat | not needed for the online simulator; never paste it anywhere |
| `0000` from `/check` read as success | order marked paid before the customer authenticated | on `/check`, `0000` = not yet; `0110` = confirm now; `0123` = completed |
| Testing with `paymentUrl.app` in the sandbox | page never opens | sandbox is web-only (FAQ) |
| Product image on HTTP in the sandbox | image missing, panic | HTTPS in the sandbox; production renders either (FAQ) |
| Second sandbox account on the same e-mail | application refused | one per address; a merchant account works on the sandbox without applying |
| Agency-registered merchant | cannot see keys or edit allowlist | the agency does it (FAQ) |
| Expecting HTTP 4xx/5xx on failure | errors swallowed as success | always 200; read `returnCode` |

---

## 11. The harness

All under `tools/linepay/`; stdlib Python and plain PHP. Tests: `python tests/test_linepay_tools.py` (offline; `LINEPAY_LIVE=1` adds the live refusal check against the sandbox host).

| Script | Step | What it does |
|---|---|---|
| `detect.py [dir]` | §1 | direct vs via vs offline signals, env key *names*, confirm handlers; says `setup-direct` / `audit` / `via-aggregator (…)` / `not-linepay` |
| `fetch_docs.py --latest` / `--page` / `--fetch DIR` | §2 | versions in the nav, endpoints per version, change-log head; pages as text |
| `sign.php headers METHOD /path [payload]` / `selftest` | §7 | the three headers for any call; selftest prints a fixed-input MAC that the Python test recomputes independently |
| `probe_request.php [--dry-run] [--v4] [--amount N] [--no-capture] [--check id] [--confirm id] [--capture id] [--void id] [--refund id] [--details id]` | §6, §8, §9 | one 1 TWD request: PASS / named `returnCode` / UNKNOWN; production refused without `--i-mean-production`; secret and signature never printed; `--check` reads the five status codes; `--confirm` / `--refund` / `--details` finish the walk (live-verified); `--no-capture` + `--capture` / `--void` for the authorise-then-capture contract (sandbox answers `2103` until enabled) |
| `../newebpay/readiness.py --init --provider linepay` | §12 | the LINE Pay readiness card template; same renderer and wait/missing rules as NewebPay's |
| `../explain_error.py linepay:<code>` | any | meaning, cause, next action; bare four-digit codes that NewebPay 物流 also uses print both readings |

---

## 12. The readiness card

```
LINE Pay readiness — <shop> — <date>
Route: direct Online API v4 | via NewebPay (LINEPAY) | via PAYUNi (LinePay)
Reference: developers-pay.line.me read <date> · versions v3 + v4 · change log Nov 2025
Sandbox: account ✅ (<e-mail>) · Channel ID/Secret ✅ in .env (gitignored) · personal LINE account for the test page ✅
Probe: request PASS ✅ (transactionId stored as string) · 1104/1106 ❌ none
Walk: PAY NOW (pop-up) → 0110 → confirm → payInfo ✅ · cancel → cancelUrl ✅ · double-confirm → 1172 read as done ✅ · refund ✅ · re-refund 1165 ✅ · sandbox menu shows both ✅
Host (S19): TLS 1.2+ on confirmUrl ✅ · read timeouts 10/40/20 ✅ · inbound allowlist ⏭ (confirmUrlType CLIENT) · static IP ⏭ not required
Production: merchant application ⏳ since <date> (LINE Pay TW) · production keys ❌ · canary ❌
Waits on others: merchant review (LINE Pay, since <date>) · agency for keys (…)
Next three actions, in order: 1 … 2 … 3 …
```

A ❌ or ⏳ with no owner and no date is a finding against the guide, not the user. `python tools/newebpay/readiness.py --init --provider linepay` writes this card as a file and renders it with the same rules as the NewebPay one.
