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
