# Setup mode — provider onboarding for a first-time integrator (§0.15)

> Moved from `SKILL.md` §0.15 on 2026-11-10, text unchanged; the trigger stays in SKILL.md so a router still reads it. Read in full before the first setup reply.

**Posture in setup mode:**

- **One question at a time, always with choices** (2–4 options, one-line consequence each). The user does not know the vocabulary; the guide supplies it.
- **Prerequisites before code.** The first artefact is the checklist of everything the user must obtain in the real world (identity documents, bank account, domain, SMS number, decisions), with who acts and how long it takes, so nobody discovers on day three that a review takes a week.
- **Host before code.** The S19 table for the host they have *and* the host they plan to launch on, before the first line is written; the outbound-IP question is asked of the host, not assumed.
- **Latest manual, always** — from the vendor's production download page, read fresh (§1.4); never a sandbox portal's copy, never memory.
- **Prove every switch.** A console toggle is a claim; a synthetic probe or a sandbox round-trip is the evidence. `UNVERIFIED` until then.
- **The AI's hard limits hold:** it never types a password or a national ID, never uploads an ID image, never creates the account, never changes a merchant-console setting without a fresh explicit yes for that one change. It opens the page, explains every field, prepares every permitted value, and checks the result.
- **Vendor support is a dated wait, not a plan** — used only for vendor-side enablement nothing else can flip, recorded with the date and what it blocks.
- **Ends with the readiness card** (per-provider format in the guide): every prerequisite ✅ / ⏳ / ❌ with an owner and a date, waits on others, and the next three actions.

**Choosing a Taiwan gateway (say this before any provider guide when the user has not chosen):**

| | NewebPay 藍新 | ECPay 綠界 |
|---|---|---|
| First sandbox payment | hours–days: register on `cwww` with ID documents and SMS, create a shop, copy keys; card product may need vendor enablement | **~5 minutes**: public stage MerchantID + keys on the docs page, test card, 3DS OTP fixed `1234` |
| Crypto schemes to get right | **one** (AES-256-CBC hex + `TradeSha`) for MPG, query, refund | **three** (`CheckMacValue`; AES-128 JSON for refunds / family-A logistics / invoice; a second logistics family) |
| Refund in sandbox | works | **impossible** for cards — first proof is production |
| 超商取貨 | store picker hosted inside the payment page; one logistics API; needs a stable outbound IP | two logistics products with different acks; 測標 per sub-type; no stage status pushes either |
| Docs | one integrated PDF (browser only; sandbox portal serves a stale copy) | HTML with markdown twins, but pages contradict themselves |
| Vendor waits | LINE Pay / wallets / BNPL by form, sandbox included | product activation, 測標 |
| WooCommerce | vendor module (2026-03) | vendor module |

**Adyen in one line:** a large-merchant processor whose account is a commercial conversation, so this skill carries only the part an audit can check — the webhook contract — and carries it because that contract **inverts a rule the rest of this doctrine states**: Adyen tells you to acknowledge before you process. Read `adyen-onboarding.md` §1 before grading a single `catch` on an Adyen notify path, or the audit files the vendor's own design as a CRITICAL.

**Stripe in one line:** when the shop sells outside Taiwan, or wants the shortest path to a *provable* integration — it is the only provider here whose sandbox needs no account, no identity documents and no vendor wait (`stripe sandbox create`), so the audit's gateway walk can be real on day one; it imposes no outbound-IP requirement, so shared hosting is not a problem; and Stripe's own advice is to use **Checkout Sessions**, not raw Payment Intents, unless the checkout genuinely cannot be expressed in Stripe's UI. It does **not** do 超商代碼, 取貨付款 or Taiwan logistics, so a Taiwan shop shipping to 7-ELEVEN still needs a domestic provider beside it.

**PAYUNi 統一金流 and TapPay in one line each:** PAYUNi when 7-ELEVEN is the channel of record (超商代碼 cap NT$20,000, native 7-ELEVEN logistics on the same page, icash Pay, and a sandbox where LINE Pay works with any Channel ID once its console toggle is on) — self-registered sandbox, AES-256-GCM envelope, 模擬繳費 for ATM/CVS. TapPay when the shop wants its **own** checkout page and card-on-file with every wallet — self-served sandbox, 90-second primes, no 超商代碼 / 取貨付款 at all.

**Default for a first shop built by a non-engineer: NewebPay** — fewer ways to be silently wrong, and the sandbox proves refunds. **Choose ECPay** when the user is on WooCommerce, wants a sandbox payment today, or already holds an ECPay contract. Do not run both for the same job; a shop that ended with both did so as a cost, not a plan *(mixoweb)*. **LINE Pay** is a method flag on NewebPay and PAYUNi (vendor-enabled — a dated wait, not a toggle; ECPay's AIO has none) and is integrated directly only when it is *the* way to pay (`linepay-onboarding.md` §0 decides; the direct Online API needs no static IP).

**Provider guides:**

| Provider | Guide | Status |
|---|---|---|
| NewebPay 藍新金流 (MPG, 定期定額, 物流) | `references/newebpay-onboarding.md` + `tools/newebpay/` | complete — manuals inventoried 2026-09-12, lessons from a shipped integration, cold-tested |
| ECPay 綠界 (AIO, DoAction, two logistics families, e-invoice) | `references/ecpay-onboarding.md` + `tools/ecpay/` | complete — pages fetched 2026-09-12, probe verified live against stage, CheckMacValue known-answer test. **ECPay ships an official AI skill (`ECPay/ecpay-api-skill`) for the API code; this guide covers choice, prerequisites, host, waits, audit** |
| PAYUNi 統一金流 (UPP, 7-ELEVEN logistics, icash) | `references/payuni-onboarding.md` + `tools/payuni/` | complete — docs fetched 2026-09-13 via the ShowDoc API; AES-256-GCM envelope self-tested; **live on a real sandbox shop**: Credit / ATM / CVS PASS, wrong IV → `Hash比對不符合`, not-enabled methods → `UPP020xx` decrypted from the ReturnURL auto-form (LINE Pay is a console toggle a new shop has off) |
| TapPay (tokenising SDK, Pay by Prime, wallets) | `references/tappay-onboarding.md` + `tools/tappay/` | complete — docs read 2026-09-13; dry-run probe; a live probe needs an SDK-issued prime by design |
| LINE Pay — direct Online API v3/v4, or via NewebPay / PAYUNi | `references/linepay-onboarding.md` + `tools/linepay/` | complete — `developers-pay.line.me` read 2026-09-13 (v4 added Nov 2025); HMAC signer cross-checked against an independent implementation; **full walk live on a sandbox Channel, v3 and v4** (`paymentProvider: TSP` seen on v4): request → simulator PAY NOW → `0110` → confirm (`payInfo`) → details (`CAPTURE`) → refund → `1165` / `1172` / `0123` on the retries; wrong credentials → `1104` |
| **Stripe** (Checkout Sessions / Payment Intents, webhooks, refunds) | `references/stripe-onboarding.md` + `tools/stripe/` | complete — `docs.stripe.com` read 2026-09-24 (markdown twins: append `.md` to any path); the signature scheme proved by known-answer test (`sign_test.py`, five cases, no key and no network); `detect.py` run against a positive and a negative; `probe_intent.php` dry-run verified and refusing live keys. **Live sandbox round trip: UNVERIFIED** — `stripe sandbox create` needs no account, but provisioning is outward-facing and waits on the owner's yes |
| **Adyen** (the webhook contract only) | `references/adyen-onboarding.md` + `tools/adyen/` | **partial, and the boundary is stated**: `docs.adyen.com` read 2026-09-24 for the webhook contract and HMAC scheme, `hmac_test.py` passing offline (4 cases, no key). Account, pricing and method enablement are commercial and owner-side — absent rather than assumed. Its §1 carries the one cross-provider inversion in this skill: **Adyen instructs the merchant to acknowledge *before* processing**, so the S3 rule that grades that CRITICAL elsewhere is wrong here |

Shared: `tools/explain_error.py <code>` translates NewebPay, ECPay, PAYUNi, TapPay and LINE Pay (`linepay:<code>`) error codes into cause + next action; `tools/newebpay/readiness.py --init --provider newebpay|ecpay|linepay|payuni` writes each provider's readiness template and renders any of them.

---

**Reading receipt: _a first payment is set up, not audited_.** Quote this phrase on the readiness card to show this
file was read rather than inferred from the skill's index. It appears nowhere else.
