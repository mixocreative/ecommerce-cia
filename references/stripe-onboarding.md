# Stripe — setup, wiring, and the audit

Read from `docs.stripe.com` on **2026-09-24**. Stripe serves a markdown twin of every page: append
`.md` to the path (`https://docs.stripe.com/refunds.md`) and you get the source rather than the
SPA. Re-read before quoting a limit; §1.4's version-aware rule applies here as much as anywhere.

Stripe is the first provider in this skill whose **sandbox needs no account and no owner action**:
`npm i -g @stripe/cli` then `stripe sandbox create` provisions a temporary sandbox with working
test keys through a proof-of-work challenge, per the same docs. That changes the §0.15 posture —
the prerequisite checklist below is short, and almost nothing is a dated wait.

---

## §0 — Which Stripe API, decided before any code

Stripe's own guidance, verbatim from the Payment Intents page: *"Stripe recommends using the
Checkout Sessions API with the Payment Element over Payment Intents for most integrations… Don't
use the Payment Intent API unless the user explicitly asks, because it requires significantly more
code."*

| | Checkout Sessions + Payment Element | Payment Intents directly |
|---|---|---|
| Who builds the payment form | Stripe | you |
| Line items, tax, Adaptive Pricing | built in | you assemble them |
| Code to maintain | least | significantly more |
| When it is right | almost every shop | a checkout Stripe's UI cannot express |

**For an audit this is not a style question.** A codebase on raw Payment Intents that could have
used Checkout Sessions owns the whole status machine below, every 3DS branch and every recovery
path by hand — so the sweeps that follow apply at full depth. Say which API the shop uses in the
§0.5 discovery block, because it changes how much of §2 is the shop's problem.

---

## §1 — Prerequisites

| # | Thing | Who | How long |
|---|---|---|---|
| 1 | Stripe CLI (`npm i -g @stripe/cli`) | the agent, §0.8 rung 3 | a minute |
| 2 | A sandbox (`stripe sandbox create`) | the agent — **no account, no identity, no card** | seconds |
| 3 | A real Stripe account, for production only | the owner: business identity, bank account, tax details | hours to days |
| 4 | A public HTTPS endpoint for webhooks, or `stripe listen` in development | the agent for dev; the host for production (S19) | — |

Rows 1 and 2 are why Stripe is the cheapest provider in this skill to *prove*. Nothing in the
audit's gateway walk needs the owner until row 3, which is a production concern.

**Provisioning a sandbox is still an outward-facing action** — it creates a resource on a third
party. Ask once before running it, as §0.8's hard limits require, and never pass `--email` or
`--from-git`: both send the owner's address to Stripe, and the anonymous path does not need it.

---

## §2 — The status machine, which is where the defects live

### 2.1 PaymentIntent statuses, exact strings

`requires_payment_method` → `requires_confirmation` → `requires_action` → `processing` →
`succeeded`, with `requires_capture` sitting between action and capture when the integration
separates authorisation from capture, and `canceled` reachable from the incomplete states.

**Three facts about this machine cause more shop bugs than everything else on this page:**

1. **Failure is not terminal.** From the lifecycle page: *"If the payment attempt fails (for
   example, due to a decline), the PaymentIntent's status returns to `requires_payment_method` so
   that the payment can be retried."* A shop that maps a decline to a terminal `failed` order and
   stops listening has a customer who can still pay, on an order the shop has already written off.
   **Audit check:** find the decline handler; if it writes a terminal state and no later `succeeded`
   can reopen it, that is an S23 out-of-order finding on the money path.
2. **`succeeded` cannot be cancelled.** *"A PaymentIntent can't be canceled after it has
   succeeded."* Cancellation is only legal from `requires_payment_method`, `requires_capture`,
   `requires_confirmation`, `requires_action`, and `processing` **only for US bank accounts**. A
   cancel button rendered on a succeeded order is S22.9's dead control with a real API error
   behind it.
3. **One PaymentIntent can carry several Charges.** *"A PaymentIntent might have more than one
   Charge object associated with it if there were multiple payment attempts."* Any reconciliation
   that assumes one charge per intent will double-count or miss, depending on which way it joins.

### 2.2 Capture, and the refund that is not a refund

If the shop separates authorisation and capture, a PaymentIntent in `requires_capture` **cannot be
refunded at all**: *"the charge attached to the PaymentIntent remains uncaptured and can't be
refunded directly. You must cancel the PaymentIntent."* A refund desk that offers one button for
both cases fails on half its orders, and the failure is an API error the operator will see as
nothing at all unless the desk surfaces it (S22).

### 2.3 Refund statuses, exact strings

`pending` · `requires_action` · `succeeded` · `failed` · `canceled`.

- **A refund can fail after it succeeded from the shop's point of view**, for up to **30 days**:
  *"the bank returns the refunded amount to Stripe… This process can take up to 30 days."* The
  event is `refund.failed`, and the shop must handle it. A refund desk that writes `refunded` on
  the API's 200 and never listens again is the S16 silent-death shape, on money leaving.
- `failure_reason` is an enum with seven values: `charge_for_pending_refund_disputed`, `declined`,
  `expired_or_canceled_card`, `insufficient_funds`, `lost_or_stolen_card`, `merchant_request`,
  `unknown`. S22.4's closure rule applies — the authority's error table *is* the outcome column,
  so each one needs a surface or an explicit N/A.
- **Some refunds are reversals, and the customer sees no credit at all**: *"the original charge
  drops off the customer's statement, and a separate credit isn't issued."* Detectable only as
  `destination_details[card][type] = 'reversal'`. A shop whose refund e-mail says "a credit will
  appear on your statement" is wrong for these, and the support ticket that follows looks like a
  missing refund.
- Refunds draw on the **available** Stripe balance. Insufficient balance holds card refunds
  `pending` and **fails them outright for other payment methods**.
- The reference number an angry customer's bank wants (ARN / STAN / RRN) takes **up to 7 business
  days** and never exists for a reversal.

### 2.4 The events worth subscribing to

`refund.created` (Stripe's stated minimum), `refund.updated`, `refund.failed`, `charge.refunded`,
`charge.dispute.funds_reinstated`, `review.closed`. Deprecated and not to be built on:
`charge.refund.updated`, `source.refund_attributes_required`.

---

## §3 — Webhook signatures: the single most common Stripe integration bug

The header is `Stripe-Signature` and it looks like `t=<timestamp>,v1=<hmac>,v0=<older scheme>`.
The signed payload is **the timestamp, a literal `.`, and the raw request body**, HMAC-SHA256 under
the endpoint secret (`whsec_…`), compared in constant time. `tools/stripe/sign_test.py` is a
known-answer test of exactly that construction and needs no key and no network.

**The body must be the bytes Stripe sent.** From the docs: *"Some frameworks might edit the request
body by doing things like adding or removing whitespace, reordering the key-value pairs, converting
the string to JSON, or changing the encoding. All of these cases lead to a failed signature
verification."*

The named trap, because it is the one everybody hits: in Express, `app.use(express.json())` placed
**before** the webhook route parses the body and the verification fails for every event. The
webhook route goes first. The same shape exists in every framework with automatic body parsing —
Laravel's middleware, Next.js's `bodyParser`, API Gateway's mapping template. **Audit check:** find
where the raw body reaches the verifier, and confirm nothing between the socket and that line has
re-serialised it. A `json_encode(json_decode($body))` anywhere on that path is a finding whether or
not it currently works.

**Two secrets that are not interchangeable.** `stripe listen` prints one `whsec_`; a Dashboard
endpoint has a different one. Verifying CLI-forwarded events with the Dashboard secret fails, and
the error is identical to a code bug. Both start `whsec_`, which is why this costs people an
afternoon.

**The timestamp is the replay defence.** A verifier that checks `v1` and ignores `t` accepts a
captured event forever. S23's duplicate and late columns both live here.

---

## §4 — Idempotency

Stripe's own list of Payment Intents advantages includes *"No double charges"* and *"No idempotency
key issues"* — but that is the API's behaviour, not the shop's. Two rules survive into the audit:

1. **Creating** a PaymentIntent takes an `Idempotency-Key` header, and the docs say to key it on
   the cart or session id. A shop that creates a fresh intent per page load has a purchase funnel
   full of abandoned intents and no way to tell a retry from a second purchase.
2. **Reuse the intent across an interrupted checkout** rather than creating a new one: *"If the
   checkout process is interrupted and resumes later, attempt to reuse the same PaymentIntent."*
   Store the id on the cart. This is also what makes the shop's own failed-attempt history legible.

The shop's side of idempotency is unchanged by any of it: the **webhook handler** must be
idempotent on the event id, because Stripe retries, and the retry arrives after the first one was
acknowledged.

---

## §5 — S19: what Stripe requires of the host

| Requirement | Why | Typical answer |
|---|---|---|
| Inbound HTTPS on 443, valid chain | webhook delivery | any host with TLS; `stripe listen` covers development |
| No fixed outbound IP needed | Stripe has no IP allowlist for merchants | **unlike NewebPay and PAYUNi** — a real advantage on shared hosting |
| Raw request body reachable in the webhook route | signature verification (§3) | framework-specific; the audit reads the route |
| Clock within the signature tolerance | `t` is checked against now | NTP; a host with a drifting clock rejects live events |
| TLS on any page carrying a `client_secret` | the docs state it explicitly | — |

---

## §6 — The audit checklist, in the order the sweeps run

| Sweep | On a Stripe integration, look for |
|---|---|
| **S2** | the webhook handler reading the order, deciding, then writing without the status in the `WHERE`; two deliveries of the same event racing |
| **S3** | a `catch` around the handler that answers 200 while nothing was written — Stripe stops retrying an acknowledged event, exactly like every other provider |
| **S4** | `succeeded` treated as "money in the bank" when the integration uses manual capture, where it means authorised only |
| **S11** | the raw body re-serialised before verification (§3); the timestamp unchecked |
| **S16** | `refund.failed` with no handler; `processing` with no advancer for asynchronous methods that take days |
| **S18** | the seven `failure_reason` values against the shop's refund screen; the PaymentIntent status enum against the shop's order states |
| **S20** | nothing reconciling Stripe's charges against local orders — Stripe's `metadata[order_id]` is the join, and the docs recommend setting it |
| **S22** | the reversal case with no customer-facing wording; a cancel button on a `succeeded` order; `requires_action` with no screen |
| **S23** | a decline that writes a terminal state (§2.1 fact 1); events arriving out of order; the same event twice |
| **S24** | a webhook fixture the shop wrote itself rather than one Stripe emitted — `stripe trigger` produces real ones, which is the contract test this boundary needs |

---

## §7 — Tools

| Tool | Needs a key? | What it proves |
|---|---|---|
| `tools/stripe/detect.py` | no | whether this codebase uses Stripe, which API, and where the webhook route is |
| `tools/stripe/sign_test.py` | no | the signature construction, as a known-answer test, plus the four failure modes (wrong secret, mutated body, missing `t`, replayed `t`) |
| `tools/stripe/probe_intent.php` | `--dry-run` no; live yes | the request shape; with a sandbox key, a real PaymentIntent round trip |
| `stripe trigger <event>` (vendor CLI) | sandbox | real, correctly signed events for the S24 contract test |

**Live-verification status: PARTIAL, and the parts are named.**

| Claim | Status |
|---|---|
| The signature construction and its four failure modes | **PROVED** offline — `tools/stripe/sign_test.py`, five cases, no key and no network |
| The API endpoint, TLS, auth header shape and error envelope | **PROVED live** — a probe against `api.stripe.com/v1/payment_intents` with a syntactically valid but unowned `sk_test_` key returned a real HTTP 401 and the probe parsed it: `REFUSED — HTTP 401 — the key is not valid for this account.` Transport, path and error handling are therefore real, not assumed |
| Detection on a real codebase | **PROVED** — `detect.py` run against a positive (flagging the re-serialised body and the Express middleware order) and a negative |
| A successful PaymentIntent create, and every status value in §2 | **UNVERIFIED** — needs a key |

`stripe sandbox create` provisions one without an account, but it requires an e-mail address on
the command line, and an owner's address is theirs to give rather than the agent's to send. That
is the one rung-5 line in this guide: **one e-mail address, and §2's status machine becomes
observable rather than quoted.**

---

**Reading receipt: _a decline is not a terminal state_.** Quote this phrase on the report's receipts line (Step 6 in cia,
Step 7 in ecommerce-cia) to show this file was read rather than inferred from the skill's index.
It appears nowhere else.
