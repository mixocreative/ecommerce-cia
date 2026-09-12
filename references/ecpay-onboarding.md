# ECPay 綠界科技 — Setup Guide for a first-time integrator

Loaded by `ecommerce-cia` in **setup mode** (SKILL.md §0.15) when the project uses ECPay or the user chooses it. Same posture as the NewebPay guide — one question at a time with choices, prerequisites before code, host before code, every switch proved, the AI's hard limits, vendor waits dated, a readiness card at the end. Read `newebpay-onboarding.md` §0 for the posture once; this file states only what is ECPay-specific.

**Sources.** ECPay's developer site is the authority (§1.4) — **read the markdown twins**, `https://developers.ecpay.com.tw/<id>.md`, not the HTML (`?p=<id>`): a shipped shop misread one HTML page three times. Everything not cited to a page is a *(lesson)* from that shop (mixoweb, 2026-08/09). Page ids as of 2026-09-12; `tools/ecpay/fetch_docs.py` holds the list.

**Choosing between ECPay and NewebPay** — see SKILL.md §0.15 "Choosing a Taiwan gateway". Short form: ECPay is faster on day one (public sandbox keys, no registration, fixed 3DS OTP); NewebPay is safer to finish (one crypto scheme, sandbox refunds work, hosted store picker). Default for a first shop is NewebPay unless the user is on WooCommerce, wants a sandbox payment in five minutes, or already has an ECPay contract.

---

## 0. Detect

`python tools/ecpay/detect.py [dir]` — signals: `payment-stage.ecpay.com.tw` / `payment.ecpay.com.tw`, `AioCheckOut`, `CheckMacValue`, `MerchantTradeNo`, `RqHeader` (DoAction / 全方位物流 envelope), `Express/…` logistics routes, `ECPAY_*` env keys, a WooCommerce ECPay plugin under `wp-content/plugins/`. Says `setup` / `audit` / `not-ecpay`. Say which mode you are in.

## 1. Get the documents (5 minutes, AI does this)

`python tools/ecpay/fetch_docs.py --fetch .vendor-docs all` saves the pages below as dated markdown; `--page <id>` prints one.

| id | Page | Why it matters |
|---|---|---|
| **2856** | 測試介接資訊 | **public stage credentials**: MerchantID `3002607` (general, 3D + 無卡分期), PlatformID `3002599`, gateway `3365120`, each with HashKey/HashIV **printed on the page**; test cards `4311-9522-2222-2222` (domestic), `4000-2011-1111-1111` (foreign), `4831-3888-8888-8888` (debit); expiry any future `MM/YYYY`, CVV any 3 digits; **3D OTP is fixed `1234`**; stage backoffice `https://vendor-stage.ecpay.com.tw/` with test logins printed |
| 2862 / 2864 | 產生訂單 / 全方位金流付款 | the AIO request: `MerchantID`, `MerchantTradeNo` (≤20 alphanumeric), `MerchantTradeDate` (`yyyy/MM/dd HH:mm:ss`), `PaymentType=aio`, `TotalAmount` (int TWD), `TradeDesc`, `ItemName`, `ReturnURL`, `ChoosePayment`, `EncryptType=1`, optional `ClientBackURL`, `OrderResultURL`, `PaymentInfoURL`, `NeedExtraPaidInfo`, `IgnorePayment`, `StoreID`, `PlatformID`, `CustomField1-4`; hosts `https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5` / `https://payment.ecpay.com.tw/Cashier/AioCheckOut/V5` |
| 5679 | 付款方式一覽表 | every `ChoosePayment` / `ChooseSubPayment` value |
| **2902** | 檢查碼機制 | `CheckMacValue`: sort A–Z, `HashKey=…&k=v&…&HashIV=…`, urlencode, .NET replacements, lowercase, SHA-256, uppercase — with a **worked example** (`tools/ecpay/callback.php selftest` reproduces it) |
| **2878** | 付款結果通知 | the `ReturnURL` POST: verify `CheckMacValue`, `RtnCode=1` means paid, reply the bare string **`1|OK`** (wrong replies → retried 5–15 min later, 4×/day), notifications can be **duplicated**, `OrderResultURL` should be unset during testing, some WebATM never redirect back, query the order when the callback is late |
| **2881** | 取號結果通知 | ATM `RtnCode=2` and CVS/BARCODE `RtnCode=10100073` on `PaymentInfoURL` mean *a code was issued*, **not paid**; reply `1|OK` |
| 2890 | 查詢訂單 | the query API — use it before showing a result; `TransCode` vs `RtnCode` are two layers |
| 45919 + 45948 | 信用卡請退款 DoAction + 參數加密方式 | **production only** ("測試環境：因無法提供實際授權，故無法使用此API"); JSON envelope `MerchantID / RqHeader.Timestamp / Data` with `Data` = urlencode(json) → **AES-128-CBC** (key HashKey, iv HashIV, PKCS7) → base64; no MAC; avoid 20:15–20:30 daily; 10-minute timestamp window |
| 10092 | 介接注意事項 | TLS 1.2 on 443, a real DNS name (no IDN — punycode it), no HTML in any value, keys never in a front-end page |
| 10075 / 10127 | 全方位物流服務 + its 貨態通知 | logistics family A: encrypted `Data` envelope; the ack is **the same envelope with `RtnCode` 1 inside**, retried hourly ×3 |
| 7380 / 7420 | 物流整合 + its 貨態通知 | logistics family B: `CheckMacValue` fields; the ack is the bare string `1|OK` |
| 7849 | 電子發票 測試介接資訊 | e-invoice stage credentials (`2000132`, printed) — separate product, separate manual |

**Two logistics products, not two spellings** *(lesson)*: which family your merchant account is contracted for decides the envelope and the ack. Confirm in 廠商後台 before the first logistics line. Stage **cannot** send a logistics status notification ("測試環境尚無提供模擬物流狀態通知功能") and **cannot** do DoAction — refunds and parcel statuses are first proven in production.

## 2. Choice menu — ECPay specifics

Q1 (what you sell), Q3 (delivery), Q5 (host), Q6 (invoices) are the same questions as the NewebPay guide §2. Q2 for ECPay:

| `ChoosePayment` | Customer does | Money arrives | Who switches it on | Tell the user |
|---|---|---|---|---|
| `Credit` | card on ECPay's cashier | at authorisation | 廠商後台 toggle; production needs the card contract approved | 3DS OTP fixed `1234` in stage; **stage cannot refund** |
| `Credit` instalments (`CreditInstallment`) / 紅利 | card | as card | bank approval per plan | off until the contract says |
| `ApplePay` | wallet | as card | application + domain verification | — |
| `WebATM` | online banking now | immediate | toggle | some banks never redirect back (p=2878) |
| `ATM` | virtual account, pays later | hours–days | toggle | `PaymentInfoURL` gets `RtnCode=2` = code issued, not paid; expiry sweep + waiting screen (TW-4) |
| `CVS` | store payment code | when paid at counter | toggle | `RtnCode=10100073` = code issued; caps per manual; BARCODE result returns ~2 days after payment |
| `BARCODE` | barcode at counter | when paid (2-day lag) | toggle | same |
| `TWQR` | QR wallet | wallet settlement | application | — |
| `BNPL` | credit approval | provider settles | application + provider terms | stage `3002607` has it enabled (probe PASS 2026-09-12) |
| `WeiXin`, `DigitalPayment` | cross-border / wallets | provider | application | only if you sell to those buyers |
| `ALL` | ECPay shows a method chooser | — | — | use `IgnorePayment` to hide methods; fine for a first shop |

Starter set: `Credit` + `WebATM` + `ATM`, `CVS` if the average order fits the cap. Recorded as data, not constants.

## 3. Prerequisites — what differs from NewebPay

| Item | Stage | Production | Who |
|---|---|---|---|
| Account | **none needed** — public MerchantID `3002607` + printed HashKey/HashIV (p=2856); backoffice `vendor-stage.ecpay.com.tw` with printed test login | register at `https://www.ecpay.com.tw/` → 廠商後台 `vendor.ecpay.com.tw`; company documents, 負責人 ID, bank account; ECPay reviews and activates products | user |
| Keys | on the page | 廠商後台 → 系統開發管理 → 系統介接設定 (HashKey 16 / HashIV 16) | user copies to `.env`; AI checks lengths only |
| Public HTTPS URL for `ReturnURL` / `PaymentInfoURL` | yes (tunnel on localhost) | yes | AI sets up tunnel |
| Logistics contract + **測標** (label approval per `LogisticsSubType`) | stage creds exist for logistics too (see p=10075 / 7380 test pages) | per sub-type approval, calendar not code — start early; **never call it a blocker before the contract says so** *(lesson)* | user |
| 物流貨態代碼 table | downloaded from 廠商後台 → 物流管理 → 物流貨態代碼查詢, differs per chain, changes | same | user downloads; AI maps every code to a state (§3 fulfilment rule 6) |
| e-invoice | separate stage merchant (p=7849) | separate contract | user |

**Because stage needs no registration, the first sandbox payment is ~5 minutes away.** That is ECPay's real advantage; say so, and also say what stage cannot prove (refunds, parcel statuses).

## 4. Hosting (S19) — ECPay specifics

Same table as the NewebPay guide §4, with these rows changed: **no documented merchant outbound-IP allowlist for AIO** (p=10092 asks for a real DNS name and TLS 1.2, not an IP); logistics: not documented as IP-gated in the pages read — mark `unknown` until a stage call from the launch host succeeds; DoAction's **10-minute timestamp window** makes clock accuracy matter; a cron for the query API and for ATM/CVS expiry; **do not schedule captures between 20:15 and 20:30** (p=45919).

## 5. Stage setup (10 minutes) and 6. Prove each method

1. `.env`: `ECPAY_MERCHANT_ID=3002607`, `ECPAY_HASH_KEY` / `ECPAY_HASH_IV` from p=2856, `ECPAY_ENV=stage`, `ECPAY_CALLBACK_BASE=https://<tunnel>`. Never these values against production.
2. `php tools/ecpay/probe_aio.php Credit` → PASS means the cashier page came back; `10200079` = method not activated (廠商後台 → 系統開發管理 → 付款方式管理, then vendor-side); `10200073` = keys/algorithm; `10100251` = wrong environment for this MerchantID. Repeat per method in the §2 set. Verified live 2026-09-12: `3002607` PASS on `Credit` and `BNPL`; wrong IV → `10200073`.
3. Log in to `vendor-stage.ecpay.com.tw` with the printed test login to see orders arrive (訂單查詢 → 全方位金流訂單).
4. **模擬付款 is not a payment** *(lesson)*: the console's 模擬付款 button posts a real `ReturnURL` notification with `SimulatePaid=1` and `TradeStatus=1`; ECPay's own page says it does not change the order. **The same button exists in production.** Your handler must treat `SimulatePaid=1` as "fulfil nothing" and have a test proving it. `tools/ecpay/callback.php verify` prints that warning.

## 7. Wire it — in the order things go wrong

1. **`CheckMacValue`** exactly per p=2902; prove your implementation against the worked example (`callback.php selftest`, `callback.php sign`) before the first request. Compute over **all** fields you send, `EncryptType=1` → SHA-256.
2. **`MerchantTradeNo`**: ≤ 20 alphanumeric, unique forever; the same rule satisfies NewebPay's ≤ 30 — keep the tighter one *(lesson)*.
3. **`ReturnURL` handler**: verify `CheckMacValue` first → check `MerchantID`, `MerchantTradeNo`, `TradeAmt` → **`RtnCode=1` only** means paid → apply idempotently on `TradeNo` → reply exactly `1|OK` (not `"1|OK"`, not `1|ok`, no HTML, no whitespace). Duplicates are normal (4×/day retries and legitimate re-sends); an already-paid order is a no-op.
4. **`PaymentInfoURL` handler** (ATM/CVS/BARCODE): `RtnCode` 2 / 10100073 = code issued → store account/code + `ExpireDate`, show "waiting for payment", **never a money column**; reply `1|OK`.
5. **`OrderResultURL`** unset during testing (see ECPay's error page instead); when set, it is UX only — never mark paid from it; if the customer returns before the callback, **query the order** (p=2890) and read `TradeStatus` / `RtnCode`, remembering `TransCode` only says the request was received.
6. **One environment switch** shown in the admin header (S22.6); stage and production have different MerchantIDs and keys.
7. **Refunds (DoAction)**: JSON + AES-128 envelope, production only; a stage "refund" cannot exist — the refund state machine gets a project-owned fake for tests and a real canary at go-live. `TransCode` 1 ≠ money moved; only `RtnCode` 1 inside `Data`.
8. **Logistics**: pick the family the contract says; family A acks with the encrypted envelope, family B with `1|OK`; a 7-ELEVEN parcel that enters the store twice sends the status **twice legitimately** — dedupe on (parcel, status, `UpdateStatusDate`), not on (parcel, status) *(lesson)*.

## 8. Stage walk — what it proves and what it cannot

Proves: checkout, `CheckMacValue`, the `ReturnURL` path, idempotency, the amount check, `PaymentInfoURL` for ATM/CVS (stage issues codes), 3DS with OTP `1234`. **Cannot prove:** card refunds/void (DoAction), logistics status pushes, BARCODE's 2-day lag. Say so on the readiness card; the first proof of each is a production canary.

## 9. Go-live

Production registration and product activation by ECPay (days); keys from 系統介接設定 into the live `.env`; `ECPAY_ENV=production`; probe each method with `--i-mean-production` once (it creates an unpaid order — cancel it in the console); a real card canary refunded via DoAction the same day; 測標 done per chain before 超商取貨 is offered; the 貨態代碼 table downloaded and mapped; cron for expiry/query/trace with a heartbeat someone reads.

## 10. Gotchas

| Trap | Rule |
|---|---|
| Reading the HTML docs | read `/<id>.md` |
| Copying NewebPay's AES-256 / hex | ECPay is AES-**128**-CBC, base64, urlencode-then-encrypt, and only for DoAction / family-A logistics / invoice — AIO uses `CheckMacValue`, no encryption |
| `CheckMacValue` without the .NET replacements or lowercase | `10200073` — run the selftest |
| Replying `"1|OK"` with quotes, or with HTML | retried 4×/day, then the order desyncs |
| Treating `RtnCode` 2 / 10100073 as paid | ship nothing until `RtnCode=1` |
| Trusting `SimulatePaid=1` | fulfil nothing; test it |
| Planning around a stage refund | there is none; production canary |
| One dedupe key for logistics | (parcel, status, `UpdateStatusDate`) |
| Stage keys in the live `.env` | `10100251` in production, or worse, nothing |
| `TransCode=1` read as success | it means "received"; `RtnCode` is the answer |

## 11. Harness

`tools/ecpay/detect.py`, `fetch_docs.py`, `probe_aio.php`, `callback.php verify|make|sign|selftest`, shared `tools/explain_error.py`, and `tools/newebpay/readiness.py` (provider-neutral card; use the same status file with `ecpay.*` rows). Tests: `python tests/test_ecpay_tools.py`.

## 12. Readiness card

Same format as the NewebPay guide §13, with `account.stage: ok | public 3002607` on day one and `walk.refund: skip | stage cannot; production canary on <date>` always present.
