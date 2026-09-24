# fixture-shop-live — a planted-defect shop you can actually run

`fixture-shop/` is read. **This one is run.** It exists because the skill's own score was
measured entirely on defects an auditor finds by reading, while §0.6 Steps 4–6 and
`browser-walks.md` §12–§14 ask for defects only a running system shows. An instrument that
scores one half and not the other is `S20`'s blind detector, filed against the audit.

Every defect here is reachable from the front door over HTTP, and most of them **read
correctly**: the source looks like a shop that handles the case. The stock number on the page,
the number on the admin screen and the number in the row are three different observers, and the
whole point of the fixture is that they can disagree while every file looks fine.

**Do not fix anything in this directory.** It is the test, not the product. The answer key is
`../EXPECTED-fixture-shop-live.md`, outside this directory; the procedure is `../RUNBOOK.md`
(«the live fixture run»).

## Run it

```
php bin/reset.php                       # create + seed the sqlite database (stock: CUP-STD 5, BOWL-LG 2)
php -S 127.0.0.1:8123 -t public         # the shop
php bin/cron.php expire                 # the scheduled job, run by hand
```

Then, from another shell:

```
curl -s localhost:8123/                       # the storefront
curl -s localhost:8123/debug/state            # what the store actually holds, as JSON
curl -s -X POST localhost:8123/checkout -d 'sku=CUP-STD&qty=2&email=walk@example.com'
```

`/debug/state` is not a shop page. It is the walk's read-back of the stored rows — the third
observer in every state-delta ladder, so a ladder needs no database client.

## The provider

`docs/vendor/manual.md` is the payment provider's manual: the signature, the retry behaviour,
and the exact acknowledgement string. Read it before auditing the callback, the way §S4 and
§S18 require an external contract to be read from its own document.

To post a notification the way the provider does:

```
php bin/sign.php 7 paid evt-1        # prints a ready-to-run curl for order 7
```

## Layout

```
schema.sql                  products, stock_cache, orders, gateway_events, notices
POLICY.md                   the shop's written rules — what the code is supposed to match
bin/reset.php               create + seed
bin/cron.php                the scheduled work the host runs
bin/sign.php                sign a provider notification (the walk's gateway simulator)
bin/place.php               place one order from the command line (legacy lane)
bin/take.php                reserve stock from the command line (express lane)
public/index.php            every route: storefront, checkout, callback, admin, /debug/state
src/Db.php                  connection
src/Checkout.php            place an order (the legacy lane)
src/StockDesk.php           reserve and release stock (the express lane's desk)
src/Availability.php        the sentence the customer reads about availability
src/Gateway/Callback.php    verify and apply a provider notification
src/RefundDesk.php          the operator's refund
src/Admin.php               the admin stock screen, order list, notices
src/Jobs.php                expire unpaid orders; refresh the storefront's stock cache
tests/CheckoutTest.php      the shop's own tests — they pass
docs/vendor/manual.md       the provider's contract
```

`php tests/CheckoutTest.php` is green. That is deliberate, and it is the same property the read
fixture has: **a green suite over the wrong observations is the condition the audit exists to
catch**, not evidence of a healthy shop.
