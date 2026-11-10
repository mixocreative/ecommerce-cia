# Sweeps S1–S5 — state and boundaries: snapshots, TOCTOU, fail-open, semantics, dead controls

> Part of `references/sweeps/` (index: `README.md`). Split from the former `sweeps.md` on 2026-11-10 - text unchanged. Read every file in the folder per §0.9.

## S1 — Snapshot-vs-live reread (temporal coupling / stale snapshot)

For every value persisted at a moment in time (payment deadline, reserved stock, offered payment methods, price, tax rate, shipping quote, coupon eligibility), enumerate every later reader of the same concept. Classify each reader as "reads the snapshot" or "re-reads live settings/config". Any pair where a later reader re-reads live while an earlier writer froze a snapshot is a finding, because the two can disagree after an admin change or a config edit. Example: a reservation deadline computed from settings at placement, then a payment page that re-reads the enabled methods on every GET and offers a days-long method against a 30-minute hold.

**S1.1 — arithmetic on a configurable value (three cold runs missed it, 2026-09-19).** For every quantity a job *derives* from a setting — `window − 12h` for a reminder, `hold_days − 1`, a cap times a rate — evaluate the expression at the edges the admin screen will actually accept (0, 1, the default, ten times the default). A result that goes negative, zero, or throws — a `DateInterval('PT-4H')` when the window is under twelve hours — is a finding at **MEDIUM**, and **HIGH** when the job then records the effect it did not produce (a `reminder_sent_at` stamped after the throw path, or with no send). The admin screen let the value in; the job is where it fails.

**S1.1 — the same setting read twice inside one operation (2026-09-24, found in a live checkout).**
S1's usual shape is a writer that froze a snapshot and a later reader that re-reads. The sharper
instance is *inside a single transaction*: one operation reads a setting, uses it for the figure it
quotes outward, and then **reads it again** for the figure it records. A checkout read its
international surcharge rate twice — once to compute the amount the payment gateway would be asked
for, once for the rate written on the order row — so a settings table that changed, or failed,
between the two produced an order **whose recorded rate did not explain the amount charged**.
Nothing throws. The discrepancy surfaces weeks later at reconciliation, as an order nobody can
account for, and by then the settings have been read a thousand times since.

Read the operation as a unit: **every external value it depends on is read once, at the top, and
carried.** Two reads of one name inside one operation is the finding, whether or not you can
construct the interleaving — the argument "the window is tiny" is an argument about likelihood, and
the cost here is an unexplainable money row, which is the expensive kind of rare. The same rule
covers a clock (`now()` twice in one operation gives two times), a random source, a feature flag,
and anything whose second read can disagree with its first.

## S2 — Select-then-act predicate loss (TOCTOU race)

For every worker, cron, or batch that SELECTs candidate rows and then mutates them one by one (expire unpaid, release stock, void invoice, revoke entitlement, retry notification), read the per-row UPDATE/DELETE. The mutation's WHERE clause must re-state the full selection predicate, not only the status column. A predicate that is checked at SELECT and dropped at UPDATE is a time-of-check/time-of-use finding: a callback that lands between the two steps (deadline extension, payment arrival, manual hold) is silently ignored.
**S2.1 — the identity a limit counts (2026-09-15).** A per-address limit that does not normalise
the address counts `me@x`, `Me@x` and `me+1@x` as three people; a bot rotates the alias per try.
Lower-case and strip the `+alias` before counting (keep the original for delivery). A per-IP
limit behind a proxy counts every visitor as one — read the proxy's client header from a
*trusted* proxy only, and note which throttles share the assumption. A per-product limit
("two per customer" on a drop) that lives in the form is no limit at all; it is a `WHERE` in
the placement, and it needs the identity it counts written down: account, verified phone, or
card fingerprint.


**The runtime twin — fire it twice (2026-09-24).** This sweep produces a *prediction*, and the
report then grades the prediction. When the system is running — and §0.6 requires it to be at
every tier — that prediction is one minute away from being an observation: fire the same
operation twice concurrently against a row prepared so exactly one may win, then read the row
(`browser-walks.md` §13). Both succeeded → the finding is CONFIRMED and the two responses are
its artefact. One refused → something holds between the read and the write; name it in the
verified controls and downgrade honestly. One won and the loser vanished with no error, no
message and no row → a second finding, S22's, usually worse than this one. A race graded from
reading alone, on a system that was up on this machine at the time, is evidence left on the
floor — and its confidence is HIGH-CONFIDENCE, never CONFIRMED.

## S3 — Catch-block failure posture (fail-open default)

For every `catch` in a payment, checkout, entitlement, refund or inventory path, write one line: what is caught, what the code does next, and whether that is fail-open (proceeds as if the read succeeded) or fail-closed (refuses the action). Fail-open on a configuration or feature-flag read in a money path is a finding unless an owner decision in project memory or an ADR names that exact choice and its reason. "Default on because that was the pre-migration behaviour" is a reason to record, not a reason to keep. **A secret derived from the environment's identity is a time bomb.** Any salt, key or token with a computed fallback — `hash(hostname)`, `hash(__DIR__)`, the container id, an ephemeral machine name — silently changes when the environment is rebuilt, and everything hashed against it stops verifying with no error anywhere. Check three things for each: production fails closed when it is unset rather than computing one; the value survives a container recreation; and every process that reads it (web, CLI tool, worker, test) computes the *same* one. A password written by a host-side CLI that cannot verify inside the container is this defect, and it reads as "wrong password" forever. Fail-open is not one posture: name the axis. On a **display or read path** (a listing, a search, a recommendation) fail-open to an empty or degraded result may be the right System 5 policy, provided the degradation is visible on a screen (S22) and counted by a detector (S20). On a **money, entitlement, permission, or configuration path** fail-open is a finding unless an owner decision or ADR names that exact choice and its reason. Grade the two axes separately, and say which one each `catch` sits on.

**Grading.** A `catch` on a payment path that answers the provider success — `return true`, a 200,
silence — while the verification or the write did not complete is **CRITICAL**: the provider
stops retrying and the money is recorded nowhere. That includes a catch-all `\PDOException` (or
any broad class) around a callback write where only the duplicate-key code means "already
applied"; a database outage must fail closed so the gateway re-sends. Two cold runs graded this
HIGH and one filed it under S11 because the trigger was a malformed body — the malformed body is
S11's cause; the posture that acknowledges it is S3's finding, and it is CRITICAL. Fail-open on a
configuration or flag read in a money path, where the wrong value is at least visible in
behaviour, is **HIGH**.

**The one documented exception, and why it is not a loophole (2026-09-24).** This sweep grades a
`catch` that answers the provider "received" before the write as CRITICAL, and that is right for
every provider in this skill **except one**. Adyen's own contract instructs the merchant to
respond 202 within ten seconds and, verbatim, *"Do not validate or process the data at this
step"* — store first, process asynchronously after. So on an Adyen integration the shape this
sweep hunts is the vendor's design, and filing it is S4 semantic drift committed by the auditor:
grading one provider's code against another provider's contract.

What that changes is *where* to look, never whether to look. The risk does not vanish when a
vendor moves it; it relocates, and the sweep follows it: **is the store between the ack and the
queue durable and synchronous, and what happens to a message the asynchronous processor cannot
process?** An ack sent before a failed *store* loses exactly the event the other shape would
have lost, one storey earlier, and a queue with no advancer and no screen is S16 and S20 on
machinery the vendor told the shop to build. Read `references/adyen-onboarding.md` §1 before
grading any `catch` on an Adyen notify path, and **name which provider's contract you graded
against** in the finding either way.

**The log level is part of the posture (2026-09-24, from a corpus miss).** A `catch` that logs is
not thereby reporting. Production runs at INFO or WARN, so **a failure logged at DEBUG or TRACE is
silence with a receipt** — the line exists, the operator's log does not contain it, and the code
reads as handled to anyone grepping for `log.` on the failure path. The shape to hunt, verbatim
from the commit that fixed it:

```java
} catch (IOException | SecurityException e) {
    // Silently continue if .env loading fails, but log at debug level
    log.debug("Skipping .env file loading: {}", e.getMessage());
}
```

The application then boots on defaults, and its own comment says so. The maintainer's fix threw.
This sweep's first corpus miss was exactly this site: a cold run audited that file, filed a
different fail-open in it, and walked past this one because it logged.

So for every `catch` on a primary path, write the level next to the posture: **`debug`/`trace` is
fail-open-and-silent, and it is graded as though there were no log line at all.** `info` is
fail-open-and-buried unless something reads it (S20 — a line in a stream nobody watches is the
detector problem one storey down). `warn`/`error` reporting to a channel a person reads is the
minimum for "reported", and a screen is the minimum for "handled" (S22). The comment beside the
catch is evidence of intent, not of reporting: *"silently continue"* written by the author is the
author agreeing with the finding.

## S4 — Vendor field semantics from the spec, not from the mapper (semantic drift)

For every provider callback field the code branches on (payment type, method, status, sub-status, error code), open the vendor's specification document that is checked into the repo or referenced in project memory and cite the page or section that defines the field. If the spec distinguishes a family field from a subtype field (for example a shared `PaymentType` and a card-only `PaymentMethod`), confirm the parser reads the one that is present for every family, not only for cards. A mapper whose comment says what a field means is not evidence; the spec page is. No spec read this session → the Step 7 line for the gateway carries "field semantics unverified against spec". **Sample code is not a specification.** A vendor's runnable example (a `createShipment.php` with a form and a curl) proves the envelope it exercises and nothing else — no response fields, no status-code table, no retry or acknowledgement rule, no fee, no amount cap. When the only vendor source on disk is a sample pack, say so, name the manual that is missing, and fetch it if the vendor publishes it before writing a line against that boundary. A handoff note claiming "the sample folder is the complete authority" is an S4 finding. **Check the hosted page before building a picker.** Before designing any store-selection, address-selection or method-selection round-trip of the shop's own, read the payment gateway's hosted-page parameters: a gateway that already collects the convenience-store choice on its payment page (NewebPay MPG `CVSCOM` + `LgsType`, which returns `StoreCode/StoreName/StoreAddr/LgsNo` in the ordinary payment callback) removes the whole map integration from the customer path; the logistics API is then label, trace and modify only. Building the map anyway is unrequested variety. **Gates must exist for every payment family that reaches them.** For every predicate a payment reducer or settlement path branches on (close status, capture flag, sub-code), list every method family that can arrive there — card, virtual account, convenience-store code, barcode, wallet, pickup-with-payment — and confirm the vendor defines the field for each. A gate on a card-only field leaves every non-card order `awaiting_payment` forever with a NULL or spent deadline, stock held, no error and no alarm. Fixture-test the reducer with one real-shaped result body per family the shop offers. **The vendor's recap is not the field table.** A manual's own summary list — a 注意事項 note, a changelog, a quick-reference — can omit a field the full request table defines (NDNF-1.2.5 p.40 lists every method flag except `TWQR`, which p.38 defines). Transcribe from the table and use the recap only as a cross-check; record any difference as a finding against the recap, not the table. **Same field name, per-family numbering.** A status field several families share may number its values differently per family (NDNF `CloseStatus` 3 = 請款完成 for cards and wallets but 請款失敗 for BNPL; the payment callback's integer `StoreType` numbers OK as 3 where the logistics `ShipType` numbers it 4). Keep one value table per family keyed on the family field, refuse a value that is not on its family's table, and never derive one document's code from another's integer.

**Traffic is an authority too (2026-10-12).** Where the field crosses the wire in a flow the walk can drive,
capture it (HAR from the walk's browser, or the proxy) and set three columns side by side: what the
document says, what the code believes it sends or reads, what the traffic shows. Any disagreement is a
contradiction row (`evidence.md` §E7), not a judgement call; the reverse trace in §E10 says how.

## S5 — Admin control to runtime consumer (dead control / control-to-consumer wiring)

For every admin toggle, feature flag, or settings row (payment method enabled, gateway state, shipping option, tax mode, digital delivery switch), grep for the runtime consumer in the customer-facing path. A control the admin can change that no checkout, offer, window, or delivery code reads is a finding: the owner believes they turned something off and the shop keeps selling it. **The form is part of the control, and so is the queue.** When a gate is widened — a method that used to accept only one state now accepts two — every surface that leads to it must be widened in the same commit: the renderer that draws the button, the queue whose predicate lists the work, the filter on the desk. Widening the handler alone leaves a capability that exists, passes its unit test, and cannot be reached by the person it was built for (a dispatch control that accepted a cash-on-pickup order while the form that calls it still rendered only for `paid`). Sweep by predicate, not by method name: grep the old condition across renderers, queries and tests, and confirm each hit was considered. Also list every consumer that still reads a legacy source (yaml, CSV, constant) the admin control was meant to replace. **The host's whitelist is a consumer.** When a module copies the request into a named field list before the controller sees it, every field the page posts and the list omits is a dead control that answers with a success notice (a `Turn ON` toggle whose `feature`/`enabled` fields were dropped by `stringsFrom()` for three weeks); a controller test that bypasses the host module proves nothing about it. Walk the whitelist against every `name=` the page renders, and treat a module that hands the request over another way as an exemption to be named, never as silence.

**S5.1 — a control's consumer can retire out from under it; the script needs its caller named, not a person who remembers to run it (2026-09-20).** A menu-grouping script (`tools/dev/refresh-admin-nav.php`) wrote the DB rows a redesigned admin menu depended on, and wrote them correctly — but its only caller was a local dev launcher (`start.ps1`) retired weeks earlier in favour of `docker compose`. Nothing was broken: the script still ran clean by hand, code review found no defect in it, and the menu simply drifted back to install order because nobody who ran the current launcher ever invoked it. **A maintenance script is a control, and a control with no live caller is dead, whatever its own test proves.** Enumerate every script under `tools/` (or the shop's equivalent maintenance root) and name its live caller — a crontab line, an installer, a CI step, a deploy hook — not the developer who happens to remember it exists. A script whose only caller is a launcher, wrapper or workflow that has since been retired is the same finding as a payment-method or gateway toggle with no runtime reader: correct, tested, and reachable by nobody.
