# PAYUNi 統一金流 — Setup Guide for a first-time integrator

Loaded by `ecommerce-cia` in **setup mode** (SKILL.md §0.15) when the project uses PAYUNi or the user chooses it. Same posture as the NewebPay guide (read its §0 once); this file states only what is PAYUNi-specific. Read 2026-09-13 from `https://docs.payuni.com.tw/` — a ShowDoc site whose pages are fetchable as JSON (`tools/payuni/fetch_docs.py`); page ids below are `#/7/<id>`. No shipped-shop lessons yet: every rule here is from the vendor's pages, so **probe before trusting**.

**Where PAYUNi sits.** 統一集團's gateway: 7-ELEVEN 超商代碼 and 7-ELEVEN logistics (B2C, C2C, C2B 退貨便, 冷凍) are native; icash Pay and OPEN POINT are house products; also LINE Pay, 街口, AFTEE, cards with 3D and instalments, 黑貓 home delivery. Choose it when 7-ELEVEN is the shop's channel of record, when the 超商代碼 cap matters (**NT$20,000** here vs NewebPay's 6,000), or when the store wants icash Pay. Both payment and logistics ride **one** hosted page (`ShipTag` / `Ship` flags), like NewebPay's `CVSCOM`.

---

## 0. Detect

Signals: `payuni.com.tw`, `sandbox-api.payuni.com.tw`, `/api/upp`, `EncryptInfo` + `HashInfo` together, `MerTradeNo`, `MerID`, `PAYUNI_*` env keys, the vendor's `payuni/PHP_SDK` or `payuni/NET_SDK` in a lockfile. `python tools/payuni/detect.py [dir]`.

## 1. Documents (5 minutes, AI does this)

`python tools/payuni/fetch_docs.py --fetch .vendor-docs` saves the pages below as dated markdown (`--page <id>` prints one; `--index` lists all ~177 pages).

| id | Page | Why |
|---|---|---|
| 24 | 說明 | product map: cards (Visa/MC/JCB/銀聯, instalments 3–30), 超商代碼, ATM, icash Pay, LINE Pay, 街口, AFTEE; logistics 7-ELEVEN B2C/C2C/C2B, 黑貓 |
| **34** | 整合式支付頁 UNiPaypage (UPP) Ver 2.0 | the one request: hosts, fields, method flags, logistics flags, return parameters, `Status`/`TradeStatus` semantics |
| **374** | 交易測試資料說明 | sandbox test cards (`4147631000000001` etc.), **模擬繳費** button for ATM/CVS, LINE Pay sandbox accepts **any** Channel ID/Secret, AFTEE test phone numbers |
| **170** | 交易訂單金額限制說明 | caps: cards 1–199,999 · ATM 15–49,999 · **超商代碼 30–20,000** · 取貨付款 1–20,000 · AFTEE 20–49,999 |
| **29** / 56 / 312 / 343 | 資料加解密 (PHP / 陣列 / Node / Java) | **AES-256-GCM**, hex of `cipher + ":::" + base64(tag)`; `HashInfo = strtoupper(sha256(key + encryptStr + iv))` |
| 80 / 73 / 74 / 75 | Notify: UPP · 虛擬帳號付款完成 · 超商代碼付款完成 · 訂單失效 | what posts to `NotifyURL`, by `PaymentType` |
| 164 / 38 / 39 | 單筆交易查詢 · 請退款 · 取消授權 | query, refund, void (cards); non-card refunds are **轉匯** (pages 76/77) |
| 103 / 124 / 123 / 291 / 120 | 超商門市地圖 · 物流單查詢 · 出貨單列印 · 貨態通知 · 貨態狀態碼 | 7-ELEVEN logistics; 黑貓 at 269/270/274 |
| 156 / 44 / 119 | error codes: 通用 · UPP · 物流 | `API00010/11` malformed EncryptInfo/HashInfo, `DEF01002` decrypt failed, `DEF01007` hash mismatch, `DEF01005` shop not found |
| **245** | 相關文件及申請書下載 | 15 xlsx forms: `05.幕後功能API申請書`, `07.信用卡Token API申請書`, `13.交易頁面免跳轉元件申請書`, `14.行動支付幕後API申請書`, `09.額度調整申請書` … |
| 67 | PAYUNi SDK | official `github.com/payuni/PHP_SDK` (PHP ≥ 7.0) and `payuni/NET_SDK` — use them for the calls |

## 2. Choice menu — PAYUNi specifics (UPP method flags)

| Flag | Method | Cap (p.170) | Who switches it on | Notes |
|---|---|---|---|---|
| `Credit=1` | card 一次付清 (+ `CreditInst=3,6,…`, `CreditUnionPay`, `ApplePay`, `GooglePay`, `SamsungPay`) | 1–199,999 | console; 3D via `API3D=1` or shop setting; wallets simulated in sandbox | test cards p.374; `Cardholder=1` for 3D name |
| `ATM=1` | 虛擬帳號 (single-use) | 15–49,999 | console | `ExpireDate` ≤ today+180; 模擬繳費 in sandbox |
| `CVS=1` | 超商代碼 (7-ELEVEN ibon) | **30–20,000** | console | `ExpireDate` ≤ today+7 or the page hides CVS |
| `LinePay=1` | LINE Pay | per LINE Pay | **sandbox: any Channel ID/Secret** — no vendor wait to test; production: real LINE Pay channel | the friendliest LINE Pay sandbox of the three gateways |
| `ICash=1` | icash Pay | per icash | **application, PAYUNi reviews** | |
| `Aftee=1` | AFTEE 先享後付 | 20–49,999 | application | test phones p.374 |
| `JKoPay=1` | 街口支付 | per 街口 | application | |
| `Ship=1` / `ShipTag=1` | 取貨付款 / 超商取貨 (not paid) | 取貨付款 1–20,000 | logistics contract; 7-ELEVEN only | needs `LgsType`, `ShipType`, `GoodsType`, `Consignee`, `ConsigneeMobile`; the flag table on p.34 decides what the page shows |
| `TradeInvoice=1` | 電子發票 | — | invoice service | separate notify (p.344) |
| (none) | shop default set | — | console | omitting every flag shows the console's default methods |

**幕後 (server-side) APIs** — ATM/CVS/LINE Pay/AFTEE/街口 without the hosted page, card Token, 免跳轉 embed — each needs its **申請書** (p.245) and, for Token, **IP binding** ("需向PAYUNi平台申請審核開通且綁定IP", p.34). A first shop stays on UPP.

## 3. Prerequisites — what differs

| Item | Sandbox | Production |
|---|---|---|
| Account | **register on `https://sandbox.payuni.com.tw`** (free; identity fields as any Taiwan PSP — user types them), create a 商店, get **MerID + AES Key (32) + AES IV (16)** | register on `https://www.payuni.com.tw`, company documents, PAYUNi review; separate keys |
| Test data | on p.374 — cards, 模擬繳費, LINE Pay any channel, AFTEE phones | — |
| Public HTTPS URL | `NotifyURL` **port 80 or 443 only** (p.34); `ReturnURL` form-post; `BackURL` | same |
| `MerTradeNo` | ≤ 25, `[A-Za-z0-9_-]`, **not reused within 10 minutes** | same |
| Logistics | 7-ELEVEN contract; 冷凍 needs the 冷凍 service; 黑貓 separately; 退貨便 needs B2C 常溫 opened first (p.24) | same + real parcels |

## 4. Hosting (S19) — PAYUNi specifics

No documented merchant IP allowlist for UPP or its notifies; **IP binding only for Token / 幕後 APIs** (p.34). `NotifyURL` must be on 80/443 — a tunnel on a non-standard port will never receive a notify. `Timestamp` is `time()`; clock accuracy matters. Otherwise the generic table in the NewebPay guide §4 applies. Mark logistics-API IP gating `unknown` until a stage call from the launch host succeeds.

## 5–6. Sandbox and proving each method

1. `.env`: `PAYUNI_MER_ID`, `PAYUNI_AES_KEY` (32), `PAYUNI_AES_IV` (16), `PAYUNI_ENV=sandbox`, `PAYUNI_CALLBACK_BASE=https://…` (443).
2. `php tools/payuni/crypto.php selftest` — proves AES-256-GCM + `:::` + HashInfo round-trip and that a tampered cipher fails the hash.
3. `php tools/payuni/probe_upp.php Credit` — one UPP request per flag; PASS = PAYUNi's payment page; FAIL = a `Status` other than `SUCCESS` with the code (`DEF01007` = keys/hash, `DEF01005` = MerID unknown here, `API00010/11` = envelope shape).
4. Console toggles per method; icash / AFTEE / 街口 by application; **LINE Pay works in the sandbox immediately** — say so, it is the one place a first shop is not waiting on anyone.
5. ATM / CVS: place the order, then press **模擬繳費** in the sandbox console (交易動態明細) to fire the 付款完成 notify — the async path *is* testable here, unlike ECPay stage.

## 7. Wire it — in the order things go wrong

1. **Envelope:** `MerID`, `Version=2.0`, `EncryptInfo` = hex(`AES-256-GCM(http_build_query(fields), key, iv)` + `":::"` + base64(tag)), `HashInfo` = `strtoupper(sha256(key . EncryptInfo . iv))` — **key first, no separators**, unlike NewebPay's `HashKey=…&…&HashIV=…`. GCM means the tag is the integrity check; a wrong key fails decryption outright rather than producing garbage.
2. **Hosts:** `https://sandbox-api.payuni.com.tw/api/upp` / `https://api.payuni.com.tw/api/upp`; portals `sandbox.payuni.com.tw` / `www.payuni.com.tw`.
3. **Return vs Notify:** `ReturnURL` is a browser form-post — "交易結果請以NotifyURL為主" (p.34). Verify `HashInfo` → decrypt `EncryptInfo` → check `MerID`, `MerTradeNo`, `TradeAmt` → `Status` (`SUCCESS` / `UNKNOWN` = authorisation result overdue / `UNAPPROVED` = buyer under review) **and** `TradeStatus` (`0` 取號成功 = code issued, **not paid**; `1` paid; `2` failed; `3` cancelled; `8` pending). Only `Status=SUCCESS` + `TradeStatus=1` is money.
4. **Acknowledgement and retries are not stated on the UPP or notify pages** (read 2026-09-13) — `UNKNOWN`. Resolve empirically in the sandbox: answer `200` with an empty body, watch for re-posts; record the observed behaviour in `docs/integrations/payuni.md`. Do not invent a `SUCCESS` string.
5. **Async:** ATM / CVS orders are `TradeStatus=0` until the 付款完成 notify (p.73/74); `訂單失效通知` (p.75) closes them; `ExpireDate` rules per method.
6. **Refunds:** cards via 請退款 / 取消授權 (p.38/39); ATM / CVS / 取貨付款 via **非信用卡退款轉匯** (p.76/77) — a bank transfer PAYUNi makes on request, its own state; icash / AFTEE / LINE Pay / 街口 each have their own refund page.
7. **Logistics in the same request:** `ShipTag=1` enables 超商取貨 (paid online), `Ship=1` adds 取貨付款; the p.34 flag table decides what the page shows; `LgsType`, `ShipType` (`1`=SEVEN), `GoodsType`, `Consignee`, `ConsigneeMobile` required. 貨態 arrives on the 超商物流貨態通知 (p.291) with `ShipStatus` codes from p.120 — map every code to a state you have (§3 fulfilment rule 6). Labels: 出貨單列印 (p.123); queries: 物流單查詢 (p.124).

## 8–9. Walk and go-live

Sandbox proves: UPP, HashInfo/GCM, `NotifyURL` for cards, **ATM/CVS via 模擬繳費**, LINE Pay end-to-end. Cannot prove (until seen): notify retry rules, logistics pushes for real parcels. Go-live: production registration + review, production MerID/Key/IV, console toggles again, applications (icash / AFTEE / 街口) with dates, canary card order refunded, one real 7-ELEVEN parcel.

## 10. Gotchas

| Trap | Rule |
|---|---|
| Reusing AES-CBC code from ECPay/NewebPay | PAYUNi is **GCM** with a tag; hex of `cipher:::base64(tag)` |
| `HashInfo` built with `HashKey=`/`HashIV=` labels | it is `key + cipher + iv`, nothing else |
| `MerTradeNo` reused for a retry | refused for 10 minutes — generate a new one |
| `NotifyURL` on port 8080 / tunnel port | never called; 80/443 only |
| Treating `Status=SUCCESS` as paid | `TradeStatus` must be `1`; `0` is a code issued |
| Assuming a `1|OK`-style ack | not documented — test it, record it |
| 超商代碼 hidden on the page | `ExpireDate` > today+7 hides CVS by design |
| Building a store map for UPP orders | logistics rides the same page (`ShipTag`/`Ship`) |
| Non-card refund as an API reversal | it is a 轉匯 request with its own state |

## 11. Harness

`tools/payuni/`: `detect.py`, `fetch_docs.py` (ShowDoc JSON API), `crypto.php selftest|encrypt|decrypt|hash`, `probe_upp.php [FLAG] [--dry-run]`. `tools/explain_error.py` knows `DEF01002/05/07`, `API00010/11`. Readiness card: `tools/newebpay/readiness.py` with `payuni.*` rows.
