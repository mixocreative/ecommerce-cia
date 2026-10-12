# Reference systems — business-logic comparison (§3a)

Loaded first in Step 3. Use mature systems to discover lifecycle edges a bespoke engine may have missed. They are **reference paths**, not a replacement specification and not a vote for adopting their framework.

## 1. Rules of comparison

1. Start from the shop’s actual products, jurisdictions, providers, operational promises and owner decisions. A reference feature outside that scope is `NOT-APPLICABLE`, never a finding.
2. Prefer official documentation and source. Record the exact URL plus a version, API version, release tag, or commit. An unversioned official document may additionally record retrieval date, but date alone is not proof of stable lifecycle semantics: mark version-sensitive claims `UNVERIFIED` until source or a versioned contract settles them. Documentation labelled work-in-progress is illustrative only; source and actual contracts outrank it.
3. Compare **outcomes and failure handling**, not class names, table layouts, or framework conventions. A custom design may be BETTER because it has a stronger invariant, clearer authority, an atomic transition, an idempotency guard, a recovery detector, or a usable admin outcome.
4. `BETTER` requires an explicit reference-path stage, a cited project implementation, and proof that the stated advantage is exercised. Otherwise use `DIFFERENT-BUT-VALID` or `UNVERIFIED`.
5. `DEFICIENT` requires an in-scope required outcome with no valid project path, or a trace whose relationship breaks under a relevant failure. Do not call a feature gap merely because a reference product offers it.
6. Do not use a reference system as authority for a payment gateway, tax regime, invoice law, carrier contract, or security protocol. The current provider, government, carrier, and platform documentation remains authoritative for those.

## 2. Reference registry and paths

Select only paths relevant to the audit. Before selecting them, publish a **reference-selection table** covering payment, order/inventory, fulfilment, refunds, invoicing/entitlements, and the project’s framework. For each dimension state the selected source or `NOT-APPLICABLE` with project-scope evidence. Recheck sources at audit time; APIs and documentation change. A deliberately narrow set without this table is `UNVERIFIED`, not a clean comparison.

| System | What it helps compare | Official path to inspect | Limits |
|---|---|---|---|
| **ProcessWire Commerce** | ProcessWire-native catalogue → cart → order → payment/refund/invoice/inventory/admin lifecycle | Source: `https://github.com/kongondo/ProcessWireCommerce`; feature map: `https://processwire.com/talk/topic/31316-processwire-commerce-features/` | Its public documentation is work in progress. It is a ProcessWire design reference, not proof that its payment/localisation choices fit the shop. |
| **WooCommerce** | Conventional physical/digital order status, held stock, manual order operations, refunds and operator-visible notes | `https://woocommerce.com/document/managing-orders/`; stock: `https://woocommerce.com/document/configuring-woocommerce-settings/products/`; refunds: `https://woocommerce.com/document/managing-money/` | Extensions change the available lifecycle. Use the installed/core version when source comparison matters. |
| **Shopify** | Split fulfillment orders, cancellation constraints, capture/refund/restock, webhook-driven operational outcomes | `https://shopify.dev/docs/apps/build/orders-fulfillment/order-management-apps/build-fulfillment-solutions`; `https://shopify.dev/docs/api/admin-graphql/latest/mutations/ordercancel` | Pin the API version. Shopify’s remote platform roles are not a local app architecture. |
| **Stripe** | PaymentIntent state, idempotency, asynchronous completion, webhooks, refunds and reconciliation boundaries | `https://docs.stripe.com/payments/paymentintents`; `https://docs.stripe.com/webhooks`; `https://docs.stripe.com/refunds` | A payment reference only. It does not define a shop’s order, inventory, invoice, or fulfillment lifecycle. |
| **Saleor** | Explicit order → fulfillment → return/refund transaction separation and state-transition modelling | `https://docs.saleor.io/developer/order/overview`; `https://docs.saleor.io/developer/payments/transactions`; `https://docs.saleor.io/developer/order/fulfillment` | Treat it as a headless-commerce modelling reference. Pin its release/documentation revision. |

## 3. Required business-rule trace

Build one row for every in-scope rule, including happy path and each permitted terminal or recovery path. Examples: “paid callback grants only paid lines”, “expired unpaid reservation releases stock exactly once”, “partial refund adjusts invoice and entitlement according to policy”, “parcel failure becomes actionable in the order desk”.

| Rule and scope | Trigger / entry function | Validation + calculation functions | Durable state and authority | Job / outbox / retry | External producer or consumer | Customer + admin outcome | Recovery owner and detector | Project proof | Reference path + version | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|

Every cell must name exact code paths, schemas, endpoints, screens, test identifiers, or `UNVERIFIED`. A generic subsystem name does not count. Trace an inbound callback through parsing, verification, deduplication, persistence, side effects, customer/admin rendering and recovery—not merely to the handler that returns HTTP 200.

The trace is mandatory at all tiers, but coverage scales. The Step 7 report labels excluded rows `UNVERIFIED`; it never describes a sampled tier as a complete audit.

- **Screen:** every money rule and one representative rule for each relevant domain.
- **Walk:** every money, stock, entitlement, refund, invoice and fulfillment rule; remaining rules pairwise.
- **Full:** every reachable rule and terminal/recovery variant.

## 4. Verdicts

- **BETTER** — demonstrated improvement on an in-scope outcome or failure path; cite and prove it.
- **EQUIVALENT** — same required outcome, authority, recovery and operator visibility, even if implementation differs.
- **DIFFERENT-BUT-VALID** — meets the project invariant through another design; explain why the reference feature is unnecessary.
- **DEFICIENT** — required outcome, authority, recovery, or surfaced handling is missing or breaks under a relevant test.
- **NOT-APPLICABLE** — reference feature is outside explicit business scope; name the scope evidence.
- **UNVERIFIED** — a source, trace edge, runtime proof, or version is unavailable. This is not a clean result.

## 5. Executed relationship proof

For every critical rule (money, inventory, entitlement, invoice, fulfillment), add a **fault-applicability matrix** covering duplicate delivery, concurrent competing action, timeout with remote success, out-of-order or late arrival, partial side-effect failure, abandonment, provider outage, and recovery. For each class, execute a deterministic relationship-breaking test against the audited commit, or give the exact invariant and architecture fact that makes the class inapplicable. Record the exact command/test identifier, commit, execution date, and result in the trace table. An omitted matrix cell is `UNVERIFIED`; choosing only the easiest fault is not permitted. Run the sandbox walk where only the provider can prove the boundary.

Existing evidence is admissible only when it is an automated test rerun on the audited commit during this audit. An older sandbox artefact may establish a provider fact, but cannot prove present code. A reasoning-only simulation is acceptable only when the environment cannot exercise the probe; mark it `UNVERIFIED` and state the exact missing condition. Do not call the rule BETTER or EQUIVALENT without current runtime or deterministic-test proof.

## 6. Reporting

Report aggregate verdict counts, then the complete trace table or a stable artifact path. Every `DEFICIENT` row becomes a normal finding with the rule and broken trace edge in its evidence. `NOT-APPLICABLE` rows remain visible so a reader can distinguish an intentional scope choice from a forgotten feature.
