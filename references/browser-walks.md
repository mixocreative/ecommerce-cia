# Browser walks — the conventions for Step 4 (cia) / Step 5 (ecommerce-cia)

The runtime walk drives the real site in a real browser. Everything else in this skill is about
what the code *is*; this file is about how to look at what it *shows* without the looking itself
becoming the flaky, unmaintainable thing a theme change breaks. Distilled 2026-09-15 from three
public collections — `jmr85/e2e-agent-skills` (Playwright conventions), `DominikCLK/eCommerce-tests`
(a worked Playwright shop suite), `finsilabs/awesome-ecommerce-skills` (shop-ops guides) — against
what a shipped shop's walks had learned the hard way. Only the parts that survived that comparison
are here.

## 1. Two kinds of walk, kept apart

| Kind | Asserts on | Runs | Tooling |
|---|---|---|---|
| **Headless walk** | money, state, callbacks, refusals — rows, not pixels | before theming, on every `src/` change | the project's own production classes from a CLI script; vendor answers simulated at the client seam |
| **Rendering walk** | what a page shows — a heading, a badge, a notice, a form that submits | after theme sign-off, on every template change | a browser (Playwright, or the harness's browser tool) |

A rendering walk that asserts on money is doing the headless walk's job slowly; a headless walk
that asserts on a CSS class is asserting on the theme. Keep the assertion where the fact lives.

## 2. Selectors — the order of preference, and why

1. **Role + accessible name** (`getByRole('button', {name: 'Pay'})`) — survives a re-theme, and a
   walk that cannot find the control by role has found an accessibility defect worth filing.
2. **Label / placeholder** for form fields.
3. **A test id** (`data-testid`, or the project's own marker — this skill's `data-panel="…"`
   convention for conditional sections is one) for non-semantic elements.
4. **Visible text**, last among the acceptable.
5. **CSS / XPath** — only with a written reason. A walk pinned to `.btn-primary` is pinned to the
   theme, and the theme is the thing about to change.

Never `nth()` / `first()` without a comment saying why the position is a fact and not an accident.

## 3. Page objects — one file per page, selectors in one place

A page class per route (`checkout.page`, `order.page`, `admin-order.page`) holding the locators
and the actions ("place the order", "mark handled"). The walks read like the matrix rows; a
re-theme changes the page classes and not the walks. The shipped shop's earlier walks each carried
their own selectors and the first theme pass would have broken fifteen files.

## 4. Session once, reuse everywhere

One setup step signs in (customer or operator) and saves the storage state; every walk that needs
that session loads it. Never type a password in a walk body — and never a password the agent
typed at all where the project's rules reserve credentials for a person; the setup step is where
the documented dev credential lives, once.


## 4a. Seed and state, borrowed from the Cypress Real World App (2026-09-17)

- **Reseed between walks, not between sessions.** The RWA reseeds its database before every
  end-to-end test; a walk that inherits the previous walk's orders asserts on a state nobody
  chose. Our equivalent is the preview fixtures for rendering walks and the documented reset +
  seed flow for route walks; a walk names which one it stands on.
- **Set up by API, assert by UI.** Log in and create the starting state through the API or a
  seed (`cy.session` + programmatic login in the RWA), then open the browser only for the step
  under test. A walk that clicks through registration to test the order page is testing
  registration five hundred times.
- **API walks and UI walks are separate directories** (`tests/api`, `tests/ui`) with separate
  budgets; an API walk is seconds and runs on every commit, a UI walk is minutes and runs before
  a release.
- **An empty seed is a mode**, not an accident (`start:empty`): the day-one shop with no orders,
  no products and no customers is a state every list page must render (S22 step 4).

## 5. Evidence on failure, silence on success

Trace, video and screenshot **retained on failure only**. A green walk leaves a line; a red one
leaves the artefact that shows the exact frame. `retries: 1` at most, and a retry that passes is
a flake to investigate (S21's lesson about a flake with no evidence applies to walks too).

## 6. Waiting — never on the clock

`waitForTimeout` is a bug. Wait on the state the next step needs: the button enabled, the URL
changed, the response arrived, the dialog hidden. A walk that sleeps three seconds is a walk
that passes on the auditor's laptop and fails on the launch host.

## 7. Isolation — every walk makes its own world

Each walk registers its own customer (a tagged address such as `walk-<mode>-<suffix>@example.com`)
and places its own order; none assumes another's state. Tagged data is bulk-removable
afterwards; a load probe uses its own domain (`@test-load.invalid`) for the same reason.

## 8. API beside UI

For every UI walk there is usually a cheaper API or CLI check of the same fact (the order row,
the payment row, the entitlement). Do both where the fact is money: the UI proves the person
sees it, the row proves it is true. Mock the vendor at the boundary, never the shop.

## 9. Layout

```
walks/
  pages/            one class per route
  fixtures/         session setup, tagged test data
  rendering/        the walks that assert on what is shown (Tiers 5–7 in a commerce matrix)
  smoke/            one route each: 200, <h1>, no console errors, no horizontal overflow
playwright.config   trace/video/screenshot on failure, retries ≤ 1, storage state per project
```

Name walks by the matrix row they prove (`w26-ja-golden.spec`), not by the page.

## 10. What a rendering walk checks on every route

`<h1>` present; `aria-expanded` matches the visible state on every disclosure; no console errors;
no horizontal overflow at 390 × 844; focus ring visible on the first interactive control; every
form field labelled; the locale switch lands on the same route in the other locale. These are
the checks §0.6 Step 4 / 5 already names — the page object is where they live once.

## 11. The boundaries only a browser crosses (2026-09-16)

A headless walk posts from the application's own language and never meets a Content-Security-
Policy, a cookie flag, a CORS refusal, a mixed-content block or a form the browser will not
submit. A shop's checkout carried a `form-action` that allowed two gateways and not the third —
the launch gateway — so the Pay button would have done nothing on the real page, and five
headless walks of that gateway were green. **Before a gateway is called walked, one real browser
has posted its real form once, and the response headers of the page that posts it have been
read.** Put that click in the smoke folder, per gateway, and read the CSP, cookie and referrer
headers on the checkout route as part of it (doctrine §8.2 in `cia`).

## 12. The state-delta ladder - the walk that proves an operation (2026-09-24)

Sections 10 and 11 check that a page renders and that a browser can cross it. Neither checks
that an operation *did the right thing to the system*, and that is the half of the runtime walk
most reports are missing: every route 200, every asset 200, every heading present - and nobody
ever asked whether buying the thing changed the number.

A state-delta walk is four steps, and it is the runtime twin of the four-corner sweep (S15).
Pick one quantity the system exists to get right - in a shop the stock of one SKU, in a queue
the depth, in a ledger the balance, in a runner the claim on a job:

1. **Read it at every observer, before.** An observer is anything that *claims to know* the
   quantity, and every system has three or four:

   | System | The observers |
   |---|---|
   | A shop | the customer's page, the operator's screen, the stored row, the provider's own view |
   | A job runner | the status page, the operator's CLI, the job row, the worker's own memory |
   | An API service | the response body, the metrics counter, the stored row, the upstream's view |
   | A CLI or library | the printed output, the exit code, the file or database it wrote, the lock it holds |
   | A document or content system | the rendered page, the editor's screen, the stored record, the search index |

   Record all of them. **Disagreement at step 1 is already a finding** and the walk stops until
   it is filed - a walk that starts from an inconsistent world proves nothing about the
   operation. The rule that makes this worth doing: **no system has fewer than three observers,
   and the one teams forget is the operator's.** A check of the page and the database with no
   operator screen has two corners, and the missing one is where a system most often lies to the
   people running it.
2. **Perform the operation through the front door.** Whatever the front door is here: the real
   form and the real button in a web app; the documented command with the documented flags in a
   CLI; the published endpoint with a real token in a service; the public function with the
   arguments a caller would pass in a library. Not an internal call nobody outside could make -
   a walk that calls `StockReducer::reduce()` has proved the reducer, not the shop, and one that
   calls the scheduler's private `_claim()` has proved neither the queue nor the worker.
3. **Read it at every observer, after.**
4. **Assert the delta, not the value.** Write the arithmetic into the walk - `5 -> buy 2 -> 3`,
   at the page, at the screen, and in the row. A value assertion passes by luck on a fixture
   that happened to hold the right number; a delta assertion cannot.

Then reverse it wherever the system says it reverses - cancel, refund, release, roll back - and
assert the return delta by the same rule. **Whether the reverse restores the quantity is a policy
the audit reads from the project, never assumes:** a shop that deliberately does not restock a
refunded bespoke item is correct, and the walk asserts the *documented* policy, filing a finding
only where code and policy disagree.

**The adversarial rows, which is where the defects actually live.** The ladder above is the
control. Each row below is its own walk on the same quantity, and each has been a real defect in
a shipped system:

| Row | The walk | The invariant it holds |
|---|---|---|
| Over-quantity | order more than exists | refused at the server, not merely disabled in the UI |
| Last unit, twice, at once | two sessions take the last unit in the same tick | exactly one succeeds; the loser is refused, not queued into negative |
| Abandoned checkout | start, reach payment, walk away | the reservation expires and the quantity returns, on a clock the audit names |
| Failed payment | the provider declines | no deduction survives the decline |
| Duplicate notification | the same provider callback twice | one deduction, one payment row, one e-mail |
| Out-of-order notification | "paid" arrives after "expired" | the terminal state is the correct one, and the loser is visible to a person |
| Operator edit mid-flight | someone sets the quantity by hand while an order is unpaid | the two writers do not silently overwrite each other |
| Variant vs parent | move one variant's quantity | the parent's displayed availability agrees |
| Floor | drive the quantity toward zero from several directions at once | it never goes below zero, and the refusal is a sentence a person can read |

**The same nine rows outside a shop.** The names above are a shop's because that is where they
were learned, and every one of them is a general shape. Read the middle column, not the noun:

| Row | In a job runner | In an API service | In a CLI or library |
|---|---|---|---|
| Over-quantity | claim more workers than the pool holds | request beyond the documented page size or rate | an argument past the documented maximum |
| Last unit, twice, at once | two workers claim the same queued job | two requests mutate one record concurrently | two processes take one lock or one output file |
| Abandonment | a worker dies mid-job | a client disconnects mid-write | the process is killed between two writes |
| Failure of the outside step | the job's external call fails | the upstream returns 5xx | the network or disk write fails |
| Duplicate arrival | the same message delivered twice | a client retries with the same idempotency key | the command run twice on the same input |
| Out-of-order arrival | a stale status update lands after a newer one | a webhook arrives after its own cancellation | a resumed run writes over a newer result |
| Operator edit mid-flight | someone requeues by hand while a worker holds it | an admin endpoint writes during a request | a person edits the file the tool is rewriting |
| Child versus parent | a sub-task's state against its batch's | a nested resource against its collection's count | a partial output against the manifest |
| Floor | the queue depth never goes negative and an empty claim is visible | a counter never goes negative and a refusal is a documented status | no negative or impossible value is written, and the refusal is on stderr with a non-zero exit |

A system that genuinely has no analogue for a row says so on that row - `N/A`, with the reason -
which is a sentence, not an omission. A row quietly absent from the table is the audit claiming
the system is simpler than it is.

Every row the tier excludes becomes an `UNVERIFIED` cell in the evidence ledger
(`reporting.md`), named - never a row quietly missing from the table.

**The ladder is also the answer to the most common false PASS in this whole discipline.** "Stock
deduction: implemented" is a claim about a class. The ladder is six observations with six
artefacts, and it takes about four minutes once the session fixture exists.

### 12a. The ladder as a spec — the shape to copy

Prose about deltas is easy to agree with and easy not to do. This is the shape; the project
supplies the three readers and the reverse policy, and nothing else changes.

```js
// walks/rendering/stock-ladder.spec.js
import { test, expect, request } from '@playwright/test';
import { storefrontStock, adminStock, storedStock } from '../pages/observers';

const SKU = process.env.WALK_SKU ?? 'CUP-STD';
const BUY = 2;

test('stock: every observer moves by the same amount, and back', async ({ page, browser }) => {
  const api = await request.newContext();

  // 1. read every observer BEFORE. A disagreement here is a finding, and the walk stops.
  const before = {
    storefront: await storefrontStock(page, SKU),
    admin:      await adminStock(browser, SKU),   // its own signed-in context
    stored:     await storedStock(api, SKU),
  };
  expect(new Set(Object.values(before)).size,
    `observers disagree before the operation: ${JSON.stringify(before)}`).toBe(1);

  // 2. the operation, through the front door: the real form, the real session.
  await page.goto(`/product?sku=${SKU}`);
  await page.getByLabel('Quantity').fill(String(BUY));
  await page.getByRole('button', { name: /place the order/i }).click();
  const orderId = await page.locator('[data-order-id]').getAttribute('data-order-id');

  // ... whatever makes the sale final in this shop: a signed callback, a capture, a confirm.
  await settle(api, orderId);

  // 3 + 4. read every observer AFTER, and assert the DELTA with its arithmetic.
  const after = {
    storefront: await storefrontStock(page, SKU),
    admin:      await adminStock(browser, SKU),
    stored:     await storedStock(api, SKU),
  };
  for (const [who, was] of Object.entries(before)) {
    expect(after[who], `${who}: ${was} − ${BUY} should be ${was - BUY}`).toBe(was - BUY);
  }

  // the reverse leg, per the shop's WRITTEN policy — read it, never assume it
  if (policy.refundRestocks) {
    await refund(api, orderId);
    const back = await storedStock(api, SKU);
    expect(back, `refund should return ${BUY}`).toBe(before.stored);
  }
});
```

Three things about this file carry the whole idea, and a walk that drops any of them is back to
asserting on pages:

1. **Three observers, read the same way twice.** `pages/observers.js` holds one function per
   observer and nothing else; a re-theme changes those three functions, not the ladder. The
   stored reader goes through the application's own API or a read-only endpoint — not a second
   copy of the schema in the test.
2. **The `before` equality assertion is not ceremony.** It is the four-corner sweep executed,
   and on a real shop it fails more often than the delta does.
3. **`policy` is read from the project**, not from the walk's author (§12). The reverse leg is
   the assertion the project's own written rule says it is.

The adversarial rows (§12) are the same file with one line changed each — `BUY` above stock,
`BUY` negative, two contexts racing for the last unit, the settle step sent twice, the settle
step sent out of order, an operator writing the number mid-flight. They belong beside it in
`walks/rendering/`, named for the row they prove, and each one that the tier excludes is an
`UNVERIFIED` cell in the ledger rather than a file nobody wrote.

**No Playwright in the project?** The ladder is not a Playwright idea. Three readers, one
operation and a subtraction work the same from `curl` and a JSON read-back endpoint — which is
how the skill's own live fixture proves its rows (`tests/verify-fixture-shop-live.py` in
`ecommerce-cia`). What cannot be dropped is the *third* reader: a walk that checks the page and
the database and not the operator's screen has two corners, and the missing one is where shops
actually lie to their owners.

## 13. The concurrency probe - S2 stops being a prediction (2026-09-24)

Select-then-act (S2) is swept by reading: find the read, find the write, ask what holds between
them. That sweep produces a *prediction* - "two of these at once would both succeed" - and the
report then grades the prediction CRITICAL. One probe converts it into an observation, on a
system that was already running on the auditor's own machine, and it costs about a minute.

For each S2 site on the primary path, fire the same operation **twice concurrently** against the
running system - two processes, two `curl` calls joined with `&`, two browser contexts - against
a row prepared so that exactly one may win. Then read the row.

- **Both succeeded** -> the prediction was right. The finding becomes CONFIRMED rather than
  HIGH-CONFIDENCE, and the two responses are its artefact.
- **One won, one was refused** -> something *does* hold between the read and the write. Find it,
  name it in the verified controls, and downgrade the finding honestly. An auditor who cannot
  find the mechanism after the probe says so; "no race observed, mechanism unidentified" is a
  real and reportable state.
- **One won and the loser vanished** - no error, no message, no row - -> a different and usually
  worse finding: the refusal is real and silent, which is the escalation rule and S22, not S2.

Mandatory at Walk and Full tiers for every primary-path S2 site; at Screen tier for the single
highest-value one. Prepare the row so the probe is cheap to repeat, and tag its data like any
other walk (§7) so it can be removed afterwards.

**The reading the probe disproves is recorded, not quietly dropped.** The first cold run of
`cia`'s fixture (2026-09-24) ended with a short paragraph naming two of its own readings that
the runtime contradicted — a stale field it had expected to survive a requeue and did not, and
a database write lock it had expected to mask the race and did not. Neither was filed as a
finding, because neither was true; both were *stated*. Do the same. An audit that reports only
what the runtime confirmed has quietly deleted the evidence that its reading is fallible, and
the next reader cannot tell a method that was tested from one that was lucky. Two lines at the
end of the runtime section: what you expected, what the system did.

## 14. Artefacts - what the ledger will accept (2026-09-24)

`reporting.md`'s evidence ledger accepts only artefacts produced by the run. To keep that
checkable rather than promised, every walk writes its evidence under one directory named for the
run - `artefacts/<date>-<tier>/` - and the ledger cites the file by path.

| Artefact | Accepted as evidence of | Must contain |
|---|---|---|
| Test-runner output | the named test ran and passed | the test's full name and the counts - not "OK", not a colour |
| HTTP capture | a route answered | method, URL, status, and whichever response headers the claim depends on |
| Row read-back | a write reached the store | the query and the row, read *after* the operation |
| Screenshot | a person can see the state | the route, the breakpoint, the locale |
| Log excerpt | a detector fired | the timestamp and the line, plus the neighbouring lines that show what did *not* fire |
| Two concurrent responses | a race exists, or does not | both responses and the row read afterwards (§13) |

A screenshot of a page is evidence about a page. It is not evidence about a row, and the ledger
does not accept it as such: the pair - what the person saw and what the store holds - is what any
four-corner claim needs (§8).
