# Answer key — `fixture-shop-node`

**The auditor never reads this file.** Four planted defects and one control, in Node idioms.
Its purpose is not breadth — `fixture-shop-live` carries that — but **transfer**: the same
classes, a different language, so a 10/10 on one fixture stops being evidence about one fixture.

Seed: `MUG-01` 5 · `PLATE-01` 2.

| # | Defect | Sweep | Min grade | How a run finds it | The PHP twin |
|---|---|---|---|---|---|
| **N1** | `placeOrder` reads `stock`, then writes `stock - qty` as an absolute value with no predicate (`server.js:53-64`). Two processes both win. | S2 | CRITICAL | probe: `FIXTURE_SLOW_MS=500`, two `--take` processes on a 1-unit SKU → two orders, stock 0 | L1 |
| **N2** | The declined branch releases stock **before** `INSERT OR IGNORE INTO webhook_events` (`server.js:89-100`), so a re-delivered notification releases twice. | S23 | CRITICAL | send the same signed `declined` body twice → 5 → 7 | L3 |
| **N3** | `catch (err) { return '1|OK'; }` (`server.js:102-105`) acknowledges a notification the shop did not record. | S3 | CRITICAL | reasoned from the source; the provider contract makes an acknowledged event final | L9 / the ECPay-family shape |
| **N4** | A refused checkout redirects to the product page with no message and no notice row (`server.js:155-158`). The `notices` table has an `audience` column and **no writer at all**. | S22 / S13 | HIGH | over-quantity POST → no order, no notice, output identical to before | L8 |

## The control — filing it is a false positive

| # | Control | Why it is correct |
|---|---|---|
| **NC1** | The signature check (`server.js:78-85`) | HMAC-SHA256 over the sorted fields, length-checked before `crypto.timingSafeEqual` (in characters, not bytes: see N5) — the length guard matters, because `timingSafeEqual` **throws** on unequal lengths and a naive implementation crashes the handler on a malformed signature. A tampered body is refused `0|signature` and changes nothing. |

### N5 — tracked, not scored (found 2026-11-10, not planted)

| # | Defect | Sweep | Grade | How a run finds it |
|---|---|---|---|---|
| **N5 (tracked)** | The length guard at `server.js:82-83` compares **characters** (`given.length`), and `timingSafeEqual` compares **bytes**. A 64-character `sig` with any non-ASCII character passes the guard, `Buffer.from(given)` is longer than 64 bytes, `timingSafeEqual` throws `RangeError` outside the handler's `try`, and the process exits: one unauthenticated request stops the shop. | S3 / S11 | CRITICAL | send a 64-character non-ASCII `sig` → server exits code 1 |

NC1's verdict stands for what it was planted to test: a wrong signature is refused, never accepted, and filing the HMAC
check as forgeable or timing-unsafe is still a false positive. N5 is a true extra a run is credited for, never charged
for missing, and never counted against NC1: the first run that probed it (2026-11-10, commit `e35acff`) found it by
running, before the author knew it was there. Kept for the reason fixture-service keeps row 11.


Also expected from 2026-10-16, not separately scored: the **S19.3** parity line names the one environment the run used (Node 22 + `node:sqlite` on this machine) and reports every other cell `NOT RUN`; the **S20.6** CI line reads `no CI configured`; **S12.4** finds no gateway query caller (`0 callers`, with that reason); **S24.1** records that the notification verifier has only self-signed bodies and no real vendor exists here, so the real-browser cell is `NOT RUN` / UNPROVEN with that reason. None of this is grounds to file NC1: a correct verifier with no vendor fixture is an UNPROVEN cell, not a defect.

## Scoring

Same hit / near / miss / false-positive rules as the other fixtures. The number that matters
here is **transfer**: a run that scores well on `fixture-shop-live` and badly here has found a
doctrine tuned to PHP, and that is a finding about the skill, not about the run.

<!-- site-pins (tools/check_key_lines.py) -->

## Site pins

Every file this key cites, with the sha256 it had when a person last read the ranges against it. A changed digest fails `tools/check_key_lines.py` — re-read, then re-pin.

- `server.js` 89b34a828c0e9b84f4793f241a148c4fdb040010ba79b4b590dd50acd36a3fc7
