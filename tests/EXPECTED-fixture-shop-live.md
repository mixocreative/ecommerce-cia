# Answer key — `fixture-shop-live`

**The auditor never reads this file.** It sits here, outside the audited directory, for the
reason `RUNBOOK.md` gives: a key inside the tree is a key the S6 deferred-work grep will hit.

Sixteen rows: **nine defects (eight planted, one found by the first cold run) and seven controls**. Fourteen of them are probed by the verifier; C6 and C7 are properties read from the source, and the key says so rather than counting them as run. `python tests/verify-fixture-shop-live.py`
proves every one of them still reproduces against a freshly seeded shop; run it before scoring,
because a key that no longer matches the fixture scores the auditor against fiction.

The property that makes this fixture different from `fixture-shop/`: **most of these read
correctly.** The source looks like a shop that handles the case. Only running it separates the
three observers — the page, the admin screen, and the stored row.

## Seed

`CUP-STD` 5 · `CUP-STD-BLK` (variant of CUP-STD) 5 · `BOWL-LG` 2 · `CARD-DIGITAL` 99.
Policy in `POLICY.md`; the provider's contract in `docs/vendor/manual.md`.

## The planted rows

| # | Defect | Sweep | Minimum grade | How a run finds it | Reading alone finds it? |
|---|---|---|---|---|---|
| **L1** | `Checkout::place` reads `stock`, then writes an absolute `stock = ?`. Two customers take the last unit and both succeed. | S2 | CRITICAL | the concurrency probe (`browser-walks.md` §13): two processes, `FIXTURE_SLOW_MS=600`, one unit. 2 orders, stock 0 | predictable, but only the probe CONFIRMS it |
| **L2** | The storefront reads `stock_cache`; `Jobs::refreshStockCache()` exists and **nothing schedules it** — `bin/cron.php` wires only `expire`. The page shows 5 forever. | S13 / S1 | HIGH | the state-delta ladder: page says 5 before *and after* a sale; the row says 3 | rarely — the job exists and looks wired |
| **L3** | The declined branch releases the unit **before** the idempotency insert. The provider's documented re-delivery (`manual.md` §3.3) releases twice. | S23 | CRITICAL | adversarial row "duplicate notification": 5 → order 2 → decline → 5 → same decline again → **7** | rarely — `INSERT OR IGNORE` reads as the guard it is not |
| **L4** | `Admin::stockRows()` filters `parent_sku IS NULL`, so a variant has **no row on the stock screen at all**. Selling the variant moves nothing the operator can see. | S15 / S22 | HIGH | ladder step 1: the admin observer cannot answer for `CUP-STD-BLK` | rarely — the query is a plausible "one line per product" |
| **L5** | `RefundDesk::refund()` never returns the unit, while `POLICY.md` §8 says a refund within 30 days does. | S5 / S4 | HIGH | the reverse leg of the ladder: refund a paid order, stock stays 3 | only if POLICY.md is read *and* believed |
| **L6** | No server-side floor on quantity. `qty = -3` passes `$available < $qty`, **raises** stock and writes a negative total. The form's `min="1"` is the only guard. | S11 | CRITICAL | adversarial row "over-quantity", from the other side: stock 5 → 8, order total −144000 | rarely — the template looks guarded |
| **L7** | Every page links `/shop.css`; the handler for it exists in `public/index.php` and is unreachable under the shop's own documented run command, because PHP's built-in server 404s a missing file with an extension instead of routing it. Every page is served unstyled. | S22 step 6 | MEDIUM | fetch what the markup links: 4 pages of 200 and one stylesheet of 404 | **no** — the handler reads correctly; only a request finds it |
| **L8** | A refused checkout redirects to the product page with no message, no notice row, nothing. `POLICY.md` §10 promises a sentence. | S22 | HIGH | the refusal walk: no order, no notice, no visible difference from success | sometimes — the `return` is visible, its silence is not |
| **L9** | A notification for an order that does not exist is answered `1|OK` and dropped. `manual.md` §3.2: an acknowledged notification is never re-sent. | S3 | HIGH | post a signed callback for order 9999: `1|OK`, zero rows, zero notices | sometimes — the `catch` returning `1|OK` is readable |

### A note on L7's provenance

L7 was **not planted**. The first cold run of this fixture (2026-09-24) found it, and it is kept
because it is precisely the class the runtime walk exists to catch — §0.6's "fetch every
`<link rel="stylesheet">` and hold it to a 200", added after an admin served 200 pages and 403
stylesheets for six days. A defect the harness acquired by accident and the auditor caught by
running is better evidence for the doctrine than one written to be found.

## The controls — filing either of these is a false positive

Seven of them, and five were added 2026-09-24 **to measure precision**. Each is written to look
like one of the defects above and is correct. An auditor that flags everything scores well on
recall and badly here, which is how an audit tool actually dies — not by missing a bug, but by
being ignored after two noisy reports. **A control filed as a finding is a false positive and
counts against the run.**

| # | Control | Looks like | Why it is correct |
|---|---|---|---|
| **C1** | `Jobs::expireUnpaid()` | an unguarded release | Re-states the full predicate in the `UPDATE`, checks `rowCount()` before giving the unit back, writes an operator notice. The unit returns exactly once and a person is told. |
| **C2** | `Callback::verify()` | — | HMAC over the sorted fields with `hash_equals`; a tampered notification is refused `0|signature` and changes nothing. |
| **C3** | `Availability::sentence()` `src/Availability.php:24-29` | **L9** — a catch that answers anyway | Fail-open on a **display** path, the axis S3 exempts, and the degradation is *visible*: it says availability is unavailable, never "0" and never "in stock". Nothing is recorded as handled because it rendered, and `Checkout` re-reads the row regardless. |
| **C4** | `StockDesk::take()` `src/StockDesk.php:19-26` | **L1** — read stock, write stock | The predicate is **in the `UPDATE`** (`AND stock >= ?`) and `rowCount()` decides the answer. Proven under the same probe that breaks L1: two processes, one unit, `{"ok":true}` and `{"ok":false}`, stock 0 — never negative. **An auditor that files both this and L1 has not read the `WHERE`**, and one that files neither has not run the probe. |
| **C5** | The express lane's refusal `public/index.php:129-135` | **L8** — a redirect after a refusal | Takes nothing, writes a `customer` notice, and renders it at the destination in a `role="alert"` — the sentence `POLICY.md` §10 promises. It is the correct twin of L8, one route away from it. |
| **C6** | Money as integer cents | a rounding bug | `price_cents` is an integer everywhere; no float arithmetic touches money in this shop. |
| **C7** | `h()` `public/index.php:40-43` | — | `htmlspecialchars(..., ENT_QUOTES, 'UTF-8')` on every interpolated value; no injection site found. |

**The express lane is the fixture's sharpest instrument.** `/checkout` and `/checkout/express`
place an order from the same page on the same table; one carries L1, L6 and L8, the other is
correct on all three. A run that grades them together — either flagging both or clearing both —
has read a route name instead of a predicate, and that is worth knowing about an auditor.

## Scoring

Same shape as the read fixture: **hit** = the row is filed as a graded finding with the path and
a quoted line; **near** = found but graded below the minimum above; **miss** = not filed (a
mention inside step prose is a miss — `reporting.md`, the promotion rule); **false positive** =
a control filed as a defect.

Then score the part that is new here, in the RUNS runtime columns:

- **Ledger rows.** Did the run produce an evidence ledger at all, and are its PASS rows carrying
  artefact paths? A ledger whose stock row says PASS is a **false positive against the ledger
  rule**, and it is the single most important thing this fixture measures: every planted row
  above makes the honest verdict FAIL or UNVERIFIED, and not one of them can be PASS.
- **Ladders and probes.** How many state-delta ladders ran, how many of §12's nine adversarial
  rows, and whether the S2 probe was fired. A run that graded L1 CRITICAL without firing it gets
  the finding but not the runtime credit.
