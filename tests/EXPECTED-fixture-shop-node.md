# Answer key — `fixture-shop-node`

**The auditor never reads this file.** Four planted defects and one control, in Node idioms.
Its purpose is not breadth — `fixture-shop-live` carries that — but **transfer**: the same
classes, a different language, so a 10/10 on one fixture stops being evidence about one fixture.

Seed: `MUG-01` 5 · `PLATE-01` 2.

| # | Defect | Sweep | Min grade | How a run finds it | The PHP twin |
|---|---|---|---|---|---|
| **N1** | `placeOrder` reads `stock`, then writes `stock - qty` as an absolute value with no predicate (`server.js:60`). Two processes both win. | S2 | CRITICAL | probe: `FIXTURE_SLOW_MS=500`, two `--take` processes on a 1-unit SKU → two orders, stock 0 | L1 |
| **N2** | The declined branch releases stock **before** `INSERT OR IGNORE INTO webhook_events` (`server.js:92-99`), so a re-delivered notification releases twice. | S23 | CRITICAL | send the same signed `declined` body twice → 5 → 7 | L3 |
| **N3** | `catch (err) { return '1|OK'; }` (`server.js:104`) acknowledges a notification the shop did not record. | S3 | CRITICAL | reasoned from the source; the provider contract makes an acknowledged event final | L9 / the ECPay-family shape |
| **N4** | A refused checkout redirects to the product page with no message and no notice row (`server.js:151-154`). The `notices` table has an `audience` column and **no writer at all**. | S22 / S13 | HIGH | over-quantity POST → no order, no notice, output identical to before | L8 |

## The control — filing it is a false positive

| # | Control | Why it is correct |
|---|---|---|
| **NC1** | The signature check (`server.js:80-86`) | HMAC-SHA256 over the sorted fields, length-checked before `crypto.timingSafeEqual` — the length guard matters, because `timingSafeEqual` **throws** on unequal lengths and a naive implementation crashes the handler on a malformed signature. A tampered body is refused `0|signature` and changes nothing. |

## Scoring

Same hit / near / miss / false-positive rules as the other fixtures. The number that matters
here is **transfer**: a run that scores well on `fixture-shop-live` and badly here has found a
doctrine tuned to PHP, and that is a finding about the skill, not about the run.
