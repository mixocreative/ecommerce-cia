# Adyen — the webhook contract, and the rule it inverts

Read from `docs.adyen.com` on **2026-09-24** (`/development-resources/webhooks/handle-webhook-events`
and `/development-resources/webhooks/secure-webhooks/verify-hmac-signatures`). Re-read before
quoting a limit; §1.4 applies.

This guide is deliberately narrower than the others. Adyen's account, pricing and method
enablement are commercial conversations an agent cannot run, and pretending otherwise would be
the "vendor support is a plan" mistake §0.15 forbids. What this guide covers is the part an
audit can actually check: **the webhook contract**, which Adyen shapes differently from every
other provider in this skill, in a way that makes one of this doctrine's own rules wrong here.

---

## §1 — The inversion, first, because it changes an audit's conclusion

Every other provider here wants the acknowledgement **after** the merchant has recorded the
event. NewebPay, ECPay, PAYUNi and the fixture shop all share that shape, and this skill's S3
sweep grades a `catch` that answers "received" before the write as CRITICAL for exactly that
reason.

**Adyen says the opposite, in its own words:** respond with a successful status such as **202**
*"Do not validate or process the data at this step."* The documented order is:

1. Verify the HMAC signature.
2. **Respond 202 immediately** — within **10 seconds**, or Adyen marks the webhook *Failing* and
   queues it for retry.
3. **Store** the message.
4. **Process it asynchronously.**

So on an Adyen integration, "acknowledges before it writes" is **the vendor's instruction, not a
defect**. What the audit must find instead is the risk that instruction *moves*:

| Where the risk went | What the sweep must check |
|---|---|
| Between the 202 and the store | Is the store step itself durable and synchronous with the response? An ack sent before a failed **store** is the same lost event the other providers' shape would have caused — one storey earlier (S3, S16) |
| In the asynchronous processor | Who advances the queue, what happens when a message fails processing three times, and which screen shows a stuck one? This is S16 and S20 on a queue the vendor told you to build |
| In the 10-second budget | Any synchronous work before the 202 — a database round trip, an external call, a template render — spends that budget. A handler that verifies, writes an order, sends mail and *then* answers is both slower than the limit and wrong per the contract |

**Grade accordingly, and say which provider's contract you graded against.** An auditor who
carries the NewebPay rule onto an Adyen integration files a CRITICAL that is the vendor's own
documented design, which is S4 semantic drift committed by the audit.

---

## §2 — HMAC verification

- The signature arrives in the **`hmacsignature`** header field of the webhook.
- Compute the HMAC over the **binary representation of the payload** using the **binary
  representation of the HMAC key**, then **Base64-encode** the result and compare.
- **"Make sure that the request body is as it is — do not deserialize it."** The same raw-body
  rule as Stripe, with the same failure mode and the same framework traps: a body parser that
  reads and re-serialises the JSON breaks every signature, and in Express the middleware order
  decides it.
- **One key per endpoint.** *"Each secret HMAC key is linked to one webhook endpoint. If you have
  multiple endpoints, generate an HMAC key for each."*
- **A new key is required when switching test to live.** An integration that carries one key
  across environments verifies nothing in one of them, and the failure looks like a code bug.

`tools/adyen/hmac_test.py` is a known-answer test of that construction and its failure modes; it
needs no key, no account and no network.

---

## §3 — Duplicates and ordering, which Adyen states plainly

- **Duplicates are expected**: *"make sure that your system is able to deal with duplicates."*
- **The identity of a duplicate is `eventCode` + `pspReference`** — the same pair, with a
  possibly **different `eventDate`**. That is the idempotency key an Adyen integration needs, and
  it is a *pair*, not a single id. A handler keyed on a single event identifier, or on
  `eventDate`, will treat a duplicate as new.
- **Order is not guaranteed**, and the documented resolution is to *"use the details from the
  latest webhook event"* — which means the handler needs the event's own date to decide, and a
  blind last-write-wins on arrival order is wrong.

S23's grid is therefore not optional on an Adyen integration: duplicate and out-of-order are not
edge cases the vendor hopes you handle, they are behaviour the vendor has told you to expect.

---

## §4 — The audit checklist

| Sweep | On an Adyen integration, look for |
|---|---|
| **S3** | work done *before* the 202 (the contract says don't) — and separately, a store step whose failure is swallowed after the 202 is already sent |
| **S4** | the idempotency key: is it `eventCode` + `pspReference`, or a single field that does not identify a duplicate? |
| **S11** | the raw body re-serialised before HMAC verification (§2); the signature compared with `==` rather than a constant-time compare |
| **S16** | the asynchronous processor: a message that fails processing, retries, and stops — who finds out, and on which screen |
| **S18** | one HMAC key per endpoint, and a *different* key for live; an integration with one key for both |
| **S20** | what watches the queue depth, and what notices when the processor stops. The vendor moved the work behind an ack; the detector has to move with it |
| **S23** | duplicate and out-of-order, both stated by the vendor as normal; `eventDate` used to resolve, not arrival order |

---

## §5 — What this guide does not cover, said plainly

Account opening, pricing, method enablement, payout schedules and the Adyen Customer Area's own
settings. Those are commercial and owner-side; there is no agent path to them and no sandbox that
opens without a conversation. **Adyen's test environment requires a merchant account**, which is
why this guide has no probe that returns PASS and why nothing here is marked live-verified.

Status: **the webhook contract is documented and its known-answer test passes offline. Everything
else about Adyen in this skill is absent rather than assumed.** If a shop on Adyen needs an audit
beyond the webhook boundary, say so in the report rather than reasoning from Stripe's model —
the inversion in §1 is proof the two do not generalise to each other.

---

**Reading receipt: _acknowledge first is the vendor's design here_.** Quote this phrase on the report's receipts line (Step 6 in cia,
Step 7 in ecommerce-cia) to show this file was read rather than inferred from the skill's index.
It appears nowhere else.
