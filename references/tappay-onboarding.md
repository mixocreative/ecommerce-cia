# TapPay — Setup Guide for a first-time integrator

Loaded by `ecommerce-cia` in **setup mode** (SKILL.md §0.15) when the project uses TapPay or the user chooses it. Same posture as the NewebPay guide (read its §0 once); this file states only what is TapPay-specific. Read 2026-09-13 from `https://docs.tappaysdk.com/tutorial/zh/` (back.html, reference.html). No shipped-shop lessons yet — vendor pages only; **probe before trusting**.

**Where TapPay sits.** Not a hosted payment page. TapPay is a **tokenising SDK + backend API**: the card form lives on *your* page (their JS/iOS/Android SDK collects the card and returns a 90-second `prime`), your server exchanges the prime for money with `Pay by Prime`, and wallets (Apple Pay, Google Pay, Samsung Pay, LINE Pay, JKoPay, Easy Wallet, Pi, 全支付, 一卡通, AFTEE, 大哥付你分期, 分期趣) plug into the same flow. Choose it when the shop wants **its own checkout page** and card-on-file (`Pay by Token`) with modern wallets; avoid it for a first shop that only needs 超商代碼 / 取貨付款 — TapPay has no convenience-store logistics, and ATM / CVS are not its core.

---

## 0. Detect

Signals: `tappaysdk.com`, `TPDirect`, `pay-by-prime`, `pay-by-token`, `partner_key`, `x-api-key`, `rec_trade_id`, `TAPPAY_*` env keys.

## 1. Documents

| Page | Why |
|---|---|
| `tutorial/zh/back.html` | backend: hosts `https://sandbox.tappaysdk.com` / `https://prod.tappaysdk.com`; `POST /tpc/payment/pay-by-prime` (JSON, header `x-api-key: <partner_key>`); fields `prime`, `partner_key`, `merchant_id`, `amount`, `details` (must name the item — PCI), `cardholder{phone_number,name,email}`; 3DS via `three_domain_secure: true` + `frontend_redirect_url` + `backend_notify_url` (443); `/tpc/payment/pay-by-token`; `/tpc/transaction/refund` (`rec_trade_id`, optional partial `amount`); `/tpc/transaction/query`; **notify retries at 1, 2, 4, 8, 16 minutes (5 attempts), acknowledged by HTTP 200** |
| `tutorial/zh/reference.html` | sandbox test cards: `4242 4242 4242 4242` (Visa, success), `3543 9234 8838 2426` (JCB), `5451 4178 2523 0575` (Mastercard); failure cards `4242 4202 3507 4242` → `915`, `4242 4216 0218 4242` → `10003`, `4242 4222 0418 4242` → `10005`; any future expiry, CCV `123`; status `0` = success, `10006` duplicate transaction |
| Portal (`portal.tappaysdk.com`) | **sandbox is self-served**: register, create an app → `app_id` + `app_key` (frontend), `partner_key` (backend), `merchant_id` per merchant; production needs the contract and review |
| Front-end SDK docs | `TPDirect.setupSDK(appId, appKey, 'sandbox' | 'production')`, `TPDirect.card.setup(...)`, `TPDirect.card.getPrime(cb)` |

## 2. Choice menu — TapPay specifics

| Method | Flow | Who switches it on |
|---|---|---|
| Direct Pay (cards) | SDK card fields → `prime` → `pay-by-prime`; 3DS optional per request | portal + acquiring contract (production) |
| Apple Pay / Google Pay / Samsung Pay | SDK wallet button → `prime` → same endpoint | portal; Apple merchant ID + domain verification |
| LINE Pay / JKoPay / Easy Wallet / Pi / 全支付 / 一卡通 | SDK redirect flow → `prime`, plus `result_url{frontend_redirect_url, backend_notify_url}` | portal application per wallet |
| AFTEE / 大哥付你 / 分期趣 | BNPL via the same flow | provider application |
| Pay by Token (card-on-file, subscriptions) | first `pay-by-prime` with `remember: true` → `card_key` + `card_token` → `pay-by-token` | portal |
| ATM / CVS / 超商取貨 | **not TapPay's core** — pair with NewebPay / ECPay / PAYUNi if needed | — |

## 3. Prerequisites — what differs

| Item | Sandbox | Production |
|---|---|---|
| Account | **portal self-registration, instant**; app → `app_id`/`app_key`; `partner_key`; `merchant_id` | contract + review; production keys differ |
| Your own checkout page | required — TapPay renders **into** your page (PCI scope is reduced by the SDK's iframe fields, not eliminated: TLS everywhere, no card data touching your server) | same |
| Public HTTPS | `backend_notify_url` on **443**, `frontend_redirect_url` HTTPS | same |
| `details` | must contain an item name | same |

## 4. Hosting (S19)

No documented merchant IP allowlist for `pay-by-prime` (read 2026-09-13); the portal has an IP-restriction option for partner keys — if enabled, a rotating egress IP breaks every charge. Outbound HTTPS to `*.tappaysdk.com`; `backend_notify_url` reachable on 443; the prime's **90-second life** means checkout latency matters (a slow host or queue makes primes expire before the charge).

## 5–7. Sandbox, proving, wiring

1. `.env`: `TAPPAY_APP_ID`, `TAPPAY_APP_KEY` (frontend), `TAPPAY_PARTNER_KEY` (backend, 64 chars), `TAPPAY_MERCHANT_ID`, `TAPPAY_ENV=sandbox`.
2. Prove the backend without a browser: `php tools/tappay/probe_prime.php --dry-run` builds the request; a real probe needs a prime, which only the SDK issues — so the first proof is a sandbox checkout with `4242 4242 4242 4242`, then `/tpc/transaction/query` for the `rec_trade_id`.
3. Wiring order: SDK setup → `getPrime` → server `pay-by-prime` → read `status` (`0` only) and `rec_trade_id` → store → for 3DS/wallets, handle `backend_notify_url` idempotently on `rec_trade_id`, reply **HTTP 200**, expect up to 5 retries → refund by `rec_trade_id`.
4. Never log the `prime` after use; never log `partner_key`; the `x-api-key` header is the whole authentication — treat it as a password.

## 10. Gotchas

| Trap | Rule |
|---|---|
| Charging from the browser | `pay-by-prime` is server-side only; the `partner_key` never reaches the client |
| Prime reused / expired | one prime, one charge, 90 s |
| `status != 0` read as "maybe" | anything but `0` is not money; `10006` is a duplicate you already charged |
| Notify answered with a body but not 200 | retries ×5, then silence — 200 is the ack |
| Expecting 超商代碼 / 取貨付款 | not here; pair another gateway |
| Sandbox portal IP restriction copied to production | check the partner-key IP setting on both |

## 11. Harness

`tools/tappay/probe_prime.php --dry-run` (request shape, redaction) and `tools/explain_error.py` (`915`, `10003`, `10005`, `10006`). Full probe requires an SDK-issued prime — a browser step by design.
