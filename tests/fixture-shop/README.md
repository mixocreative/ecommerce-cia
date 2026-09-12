# fixture-shop — a planted-defect shop for testing `ecommerce-cia`

A deliberately small PHP shop (no framework, no vendor directory) that passes its own
test file and contains eleven planted defects, one per sweep the skill claims to catch,
plus two controls that are correct and must be reported as verified, not flagged.

**Do not fix anything in this directory.** It is the test, not the product. The answer
key is `tests/EXPECTED.md`; the procedure is `../RUNBOOK.md`.

Layout:

```
schema.sql                       orders, settings, shipping_chains, gateway_events
src/Settings.php                 settings reader
src/Checkout.php                 place order, freeze deadline, offer shipping methods
src/Gateway/Callback.php         verify + apply a gateway notification
src/Jobs/ExpireUnpaid.php        expire orders past their payment deadline
src/Jobs/ReminderJob.php         mail a payment reminder
src/Jobs/SettlementReconcile.php nightly: ask the gateway about every paid order
src/Shipping/StorePicker.php     per-chain toggles for convenience-store pickup
src/Admin/OrderPage.php          admin order detail
src/Admin/templates/*.php        one template per order state (one is missing)
src/RefundDesk.php               refund recorder
tests/ExpireUnpaidTest.php       the shop's only test
docs/vendor/gateway-logistics-manual.md   the "vendor manual" the audit must read
```

The commerce gate (§0.3a) must PASS on this directory: criterion 1 (`src/Gateway/`),
criterion 2 (`schema.sql` names `orders`), criterion 3 (`src/Checkout.php`).
