# Battle testing — prove the custom engine under pressure

Loaded after the business-rule trace. This is the reliability layer for a shop built from scratch: turn its own promises into executable challenges rather than assuming framework tests cover them.

The method draws from OWASP rule-focused business-logic testing, mature commerce E2E suites, and public audit skills that separate reconnaissance, verification and coverage review. Their implementations are not copied and their feature sets are not requirements. Sources: [OWASP Business Logic Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Business_Logic_Security_Cheat_Sheet.html), [OWASP WSTG](https://owasp.github.io/www-project-web-security-testing-guide/latest/), [Shopware E2E suite](https://github.com/shopwareArchive/e2e-testsuite-platform), [Sylius payment plugin functional/BDD model](https://github.com/pkglt/sylius-everypay-plugin), and public skill methods from [web-app-testing-agent](https://github.com/test200000/web-app-testing-agent) and [audit-codebase](https://github.com/bogenc/audit-codebase).

## 1. Rule cards — test the promise, not the function

Create a rule card for every critical business rule before choosing tests:

| Rule ID | Promise and value at risk | Authority and legal states | Allowed actor / entrypoints | Forbidden shortcuts | Observable outcome | Detection + recovery | Test seam |
|---|---|---|---|---|---|---|---|

Use the project’s own business decision and trace as authority. Examples of forbidden shortcuts: customer-supplied price, direct status endpoint, replayed payment event, refund above remaining captured amount, staff action outside role, or customer return that bypasses provider confirmation.

A rule is not tested merely because its direct method has a unit test. Its card must name a user/API route, a worker or callback where relevant, and both customer and admin outcomes.

## 2. Model-derived transition tests

For each critical card, declare the minimal model: states, authoritative owner, legal transitions, forbidden transitions, and side effects that must happen exactly once. From that model test:

- every reachable starting state and legal transition through every real entrypoint;
- forbidden transitions through public/API/admin ingress;
- replay and concurrent conflicting transitions;
- external arrival early, late, twice, or after local expiry;
- agreement afterwards between customer, admin, database, provider/worker, and recovery detector.

The tests may be hand-written. “Model-derived” means the state table chose them, not a particular generator. Missing state/transition coverage is `UNVERIFIED`.

## 3. Two independent lenses

### White-box trace

Use the rule card, business-rule trace, schema, queues, source and deterministic tests. It finds missing consumers, stale authority and unhandled state edges.

### Black-box adversarial pass

Using only permitted test users, public/admin interfaces and sandbox endpoints, try the rule card’s forbidden shortcuts: alter hidden fields, reuse a legitimate request, change object IDs or sequence, repeat actions, omit browser return, make two actors act, and submit valid-looking but incompatible combinations.

Never use production services, real customer data, credential guessing, scanning beyond owned test endpoints, or destructive actions. Record request shape, response/status and absence of unwanted durable effects.

## 4. Evidence packets

Each critical scenario produces one durable, redacted evidence packet under the project’s ignored audit-artifact location (or an explicitly safe fixture directory). It contains:

1. scenario and rule-card ID;
2. code commit and environment/test-data identity;
3. request/events in order, with secrets and PII removed;
4. before/after authoritative records and side-effect counts;
5. customer and admin observations;
6. safe provider/job/log correlation IDs;
7. detector/recovery observation for a forced failure;
8. exact command, test ID, result and artifact paths.

A browser screenshot alone is never an evidence packet. It must answer: what happened, who can see it, and what prevented a second effect?

## 5. Targeted mutation challenge

For every critical rule in a Full audit, and every new or materially changed critical rule in any tier, challenge its proof by introducing one safe, temporary defect in an isolated worktree or test double: remove an idempotency predicate, invert a state guard, change an amount boundary, omit an outbox write, or suppress the admin surface assertion. Run the smallest test that should fail.

- If it fails, record the killed mutation and restore the original code.
- If it passes, the test does not prove the rule: file a HIGH finding on a money/safety path or improve the test before calling the rule covered.
- If source mutation is unsafe, mutate an equivalent fake/provider seam and state why. If neither is possible, mark it `UNVERIFIED`.

Never mutate production, a live provider, shared database, or a dirty user-owned working tree. The purpose is to test the test.

## 6. Coverage review and tiers

Maintain a ledger keyed by rule ID: rule card, model coverage, white-box proof, black-box attempt, fault-matrix cells, evidence packet, mutation result, and verdict. Before a clean report, each critical rule has a row and every absent artifact is `UNVERIFIED`.

When independent reviewers are available, one maps rules while another attempts to falsify the highest-risk cards without seeing the first verdict; reconcile only after both provide evidence.

- **Screen:** cards and black-box pass for every money rule, plus one critical rule from each relevant non-money domain; model, packet and mutation omissions are listed as `UNVERIFIED`.
- **Walk:** cards, models, black-box passes and evidence packets for every critical rule; targeted mutation for every money rule and every changed rule; remaining mutation rows are `UNVERIFIED`.
- **Full:** all reachable rule variants, fault-matrix cells, targeted mutation challenge for every critical rule on the audited commit, and independent coverage review.

No tier means “watertight.” It states which threats were actively challenged and which remain unverified.
