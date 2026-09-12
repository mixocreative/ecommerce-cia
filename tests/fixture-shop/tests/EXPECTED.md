# fixture-shop — answer key

Fourteen defects (eleven planted, three found by the first cold run) and two verified controls. A Screen-tier `/ecommerce-cia` run on this directory must report every row below, with the sweep, a `path:line` inside the cited range, and a grade no lower than shown. Extra findings are scored separately (see `../RUNBOOK.md`); a planted row the run did not report is a **miss** and blocks the skill change that caused it.

## Planted defects

| # | Sweep | Site | Defect | Invariant broken | Min grade |
|---|---|---|---|---|---|
| 1 | **S5** dead control | `schema.sql` `cod_enabled`; `src/Checkout.php:18-27` | `cod_enabled = '0'` is a setting nothing reads. `offeredShippingMethods()` offers `cvs_pickup_cod` whenever any chain is on. | Every offered method traces to an admin toggle (§3 fulfilment rule 2); no COD offered on a carrier the policy excludes | HIGH |
| 2 | **S1** stale snapshot | `src/Checkout.php:30-34` freezes `payment_deadline`; `src/Jobs/ReminderJob.php:16-19` re-reads `payment_window_hours` live | Change the window after placement and reminders fire at the wrong time relative to the order's real deadline. | A value frozen at one step is the value later steps use | MEDIUM |
| 3 | **S2** TOCTOU | `src/Jobs/ExpireUnpaid.php:14-24` | `SELECT … WHERE status='pending'` then `UPDATE … WHERE id = ?` with no status predicate. A callback that pays the order between the two writes `expired` over `paid`. | Carry the precondition in the `WHERE` (S16.1 rule 2); read the affected-row count | CRITICAL |
| 4 | **S3** fail-open | `src/Gateway/Callback.php:59-62` | `catch (\Throwable)` in `verify()` returns `true`. Any malformed payload that throws inside hashing is accepted as authentic. | Callback authenticity is fail-closed (§9 Authenticity; §21 "payment callback signature not validated") | CRITICAL |
| 5 | **S20** blind instrument | `src/Jobs/SettlementReconcile.php:19-24, 35-36` | Unreachable gateway answers are counted in `$skipped`, never reported; output is `0 discrepancies` and `exit(0)` whether 0 or all orders were examined. | A detector reports coverage separately from findings; blind ≠ clean | HIGH |
| 6 | **S20** dead watchdog | `src/Jobs/SettlementReconcile.php:32-33`; `schema.sql` `job_heartbeats` | Heartbeat written; nothing reads it (grep `job_heartbeats` → one writer, zero readers). A lost crontab is silent. | Something reads every heartbeat and escalates a stopped job | HIGH |
| 7 | **S22** unrendered state / **S16** no queue | `src/Admin/OrderPage.php:9-17, 21-24`; `schema.sql` status comment; `docs/vendor/gateway-logistics-manual.md` §10 status `302`/`303` | `returned_uncollected` is a reachable state (vendor pushes 302/303) with no template — the admin page throws `LogicException`. No queue lists parcels in it. | Every reachable state has a surface and a queue; caught ≠ handled | HIGH |
| 8 | **S21** vacuous pass | `tests/ExpireUnpaidTest.php:27-35` | `testDeadlineColumnIsCompared` asserts emptiness of a query with `status = 'pendng'` (typo) — always empty, passes whatever the job does. | A test asserting emptiness needs a sibling proving non-emptiness under the same conditions | HIGH |
| 9 | **S13** orphan capability | `src/RefundDesk.php` | `RefundDesk` has no caller (grep `RefundDesk` → the class only) and writes to a `refunds` table `schema.sql` does not define. Designed-but-unbuilt refund path for pickup-with-payment. | A method's refund path exists before the method is offered (§3 fulfilment rule 10) | HIGH |
| 10 | **S17** hosted surface | `src/Shipping/StorePicker.php:26-33` with `docs/vendor/gateway-logistics-manual.md` §3.2 p.14 | `mapRequest()` sends `LgsType = 'ALL'` regardless of `shipping_chains.enabled`; the manual says enablement is decided in the merchant console. The per-chain toggle is a label, not a control. `applyReturn()` (`:36-40`) then records whatever chain comes back — silent acceptance of an excluded value. | A shop setting that cannot reach the provider's page is a lie or a console mirror; out-of-set return values raise a badge | HIGH |
| 11 | **S12** browser-returned result | `src/Shipping/StorePicker.php:36-40`; manual §3.3 p.15 ("browser only … use the Query API") | The store choice reaches the shop only via the customer's browser post; a closed tab loses it and nothing polls the Query API. | A result the browser carries is not the shop's record (§3 fulfilment rule 12) | HIGH |
| 12 | **S16** silent death (found by the first cold run, 2026-09-12) | `src/Gateway/Callback.php:33-43` | The `UPDATE … WHERE status = 'pending' AND total = ?` row count is never read. A verified, authentic callback whose amount differs from the order, or that arrives after the order expired, is stored in `gateway_events` and acknowledged 200 — and the order never changes, nothing is raised. The customer paid; the shop shows unpaid. | A zero-row precondition update is a finding, not a no-op (S16.1 rule 2); gateway-paid / order-unpaid needs a badge | CRITICAL |
| 13 | **S3** fail-open (found by the first cold run) | `src/Gateway/Callback.php:44-47` | Every `PDOException` — not only the duplicate-key one — is caught, rolled back, and answered as success. A database outage during a callback loses the payment; the gateway believes it was delivered. | Only the duplicate-key error is "already applied"; anything else must fail closed so the gateway retries | CRITICAL |
| 14 | **S1 / S12** (found by the first cold run) | `src/Jobs/ReminderJob.php:16-18, 27-29` | `PT{$hours - 12}H` throws when the window is under 12 h; the job marks `reminder_sent_at` without sending anything. | A job that records an effect it did not produce (§0.11) | MEDIUM |

Also expected, not separately scored: **S18** — the NT$20,000 `Amt` cap (manual §7 p.41) is asserted nowhere in `src/` (§3 fulfilment rule 8); **S19 / S20** report lines exist even though the fixture has no host to reconcile ("no sites on the map" is acceptable for S19).

## Verified controls (must appear under §29, not as findings)

| Control | Site | Why it is correct |
|---|---|---|
| Callback MAC verification | `src/Gateway/Callback.php:52-59` | `hash_equals` over the sorted payload with the merchant key; a wrong `CheckValue` is rejected with 400. (Defect 4 is the `catch`, not the comparison.) |
| Duplicate-callback safety | `schema.sql` `gateway_events.provider_tx UNIQUE`; `src/Gateway/Callback.php:20-43` | A re-delivered `TradeNo` fails the insert inside the transaction; the order update runs once, and the `status = 'pending' AND total = ?` predicate rejects a replay against a paid or changed order. |

## Gate

`§0.3a` commerce gate must PASS — criterion 1 (`src/Gateway/`). The discovery block must name the matched criterion.
