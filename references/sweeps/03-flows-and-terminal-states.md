# Sweeps S15–S17 — four-corner walk, terminal states, the hosted surface

> Part of `references/sweeps/` (index: `README.md`). Split from the former `sweeps.md` on 2026-11-10 - text unchanged. Read every file in the folder per §0.9.

## S15 — The four-corner end-to-end walk: customer × admin × shipment × payment gateway. THIS IS THE MOST IMPORTANT DATA INTERACTION IN A SHOP AND IT OUTRANKS EVERY OTHER SWEEP WHEN TIME IS SHORT

One order is described at the same instant by four parties — the **customer** on their order page and in their mail, the **operator** in the admin, the **logistics provider** holding the parcel, and the **payment gateway** holding the money — and by the shop's own database, which claims to be the system of record for all four. Commerce defects of consequence live in the disagreements between those five, not inside any one of them. Walk the object, not the module.

Method, per money-or-goods flow (checkout → payment → fulfilment → collection/delivery → invoice → refund/return; run it for **each** payment family and **each** delivery method the shop offers, because the families differ):

1. **Enumerate the states** the order can occupy end to end, including the ones only a provider can cause (instruction issued, parcel at store, collected, uncollected, returned, settled, charged back).
2. **Fill the four-corner table.** For every state, one row, four cells plus the database:

   | State | Customer sees | Operator sees / can do | Logistics provider believes | Payment provider believes | Row of record |

   Cite `file:line` for the customer and operator cells and the vendor field, callback or report for the provider cells. A cell you cannot fill from code and vendor document is itself the finding.
3. **Disagreements are findings.** Customer copy that contradicts the badge above it; an admin queue whose predicate excludes a state the order legitimately occupies; a shipment the provider has moved and the shop has not; money the gateway has settled that the order does not show. Name the class (status-symmetry gap, stale snapshot, dead control, TOCTOU) and the two corners.
4. **Unanswerable states are findings.** Any state with no operator control, no queue row, no instruction and no ceiling: the shop can enter it and no human can get it out. Say which desk should own it.
5. **Reachability under the shipped configuration is a CRITICAL check.** Walk the flow against the seed, migration defaults and feature flags as they will ship, not a fixture. A payment method, delivery method or refund path that is built, tested and *not offerable* under the shipped configuration is CRITICAL: the register says shipped, the customer cannot use it, and no unit test can see it. Report it above every other finding.
6. **Money evidence, per state.** For each state claiming money moved, name the single artefact that proves it (verified server callback, reconciliation query, operator-recorded settlement reference) and confirm nothing weaker (a browser return, a parcel event, a shipping status) is allowed to set it.
7. **Both directions.** Also walk backwards: refund, return, cancellation, chargeback and invoice correction cross the same four corners in reverse and are where the corners most often part company.

**Test consequence — binding on every test written for this shop.** Any test touching a flow that crosses corners states which corners it covers, and **every money path carries at least one four-corner end-to-end test**: customer action → gateway request → signed provider callback → local state → operator surface, with the provider faked at its own boundary (a real-shaped signed callback body, a real-shaped query response) and never by calling the local handler directly. Single-corner tests are allowed but never sufficient, and a suite of them can be wholly green while the four corners disagree. The project's end-to-end walk matrix (headless scripts, browser walks, scenario list) belongs to this sweep: its written coverage **and the scenarios it has not written yet** go in this sweep's report line, so "the suite is green" can never be said over a matrix that is mostly unwritten.

**The environment must be able to render what the sweep claims to have walked.** Before reporting a four-corner walk as done, confirm the running system can actually reach each corner: the pages exist (a catalogue with no page rows makes every product URL a 404 and no walk of the customer corner is possible), the operator can sign in, the provider sandbox answers. Seed gaps are findings of this sweep, not excuses for skipping it — they block the owner's own sign-off as surely as a bug, and they are usually one seeder run from fixed. Walk the corners in the running app, not only in the suite: a test renders a class in isolation, a browser renders what the operator will actually see.


**The runtime twin — walk the delta, not only the table (2026-09-24).** The four-corner table is
filled by reading, and it is this sweep's product. It is also a *claim about a running system*,
and the cheapest way to test such a claim is to run it: take the quantity the flow moves (the
stock, the balance, the seat, the claim on a job), read it at all four corners, perform the
operation through the front door, read all four again, and assert the delta with its arithmetic
written out — `browser-walks.md` §12, plus the adversarial rows there, which are this table's
unhappy columns executed rather than reasoned about. It is the same table, run. Corners that
disagreed on paper either disagree in fact, and the finding is now CONFIRMED with artefacts, or
they do not, and the reading was wrong — both outcomes are worth more than the prediction.

Every ladder fills rows of the evidence ledger (`reporting.md`); every cell the tier did not
execute stays UNVERIFIED there. That is how a reader tells the table that was read from the
table that was walked, and it is the one distinction this sweep could not previously make.

Report line format: `S15 — walked N flows × M states across customer/admin/logistics/gateway; four-corner table in the report; K disagreements, J unanswerable states, R reachability findings; E2E matrix: W written / U unwritten. · runtime: L ladders run, A of 9 adversarial rows (`browser-walks.md` §12); C corner cells proved by artefact of N.`

**S15.3 — inventory has three verbs, and each has an event (2026-09-17, from Sylius and Medusa).**
Two mature shops agree on the shape and neither calls it "decrement". Sylius's order workflow
fires `HoldInventory` when the order is placed, `SellOrderInventory` when it is paid, `GiveBackInventory`
when it is cancelled; Medusa creates a *reservation item* at placement, subtracts reserved from
stocked **at fulfilment** (not at payment), deletes the reservation then, and on a return
increments stock again *unless the item is dismissed or damaged*. So the four-corner walk asks, per
SKU: **hold** — which event, and is it idempotent on a duplicate placement; **sell / subtract** —
which event, and does a shop that subtracts at payment then ship from a count that no longer
matches the shelf; **give back** — on cancel, on expiry, on a refused payment, and is the reversal
keyed to the same reservation so it cannot run twice; **return** — restocked or not, decided by a
person, and the "damaged" answer recorded. Two more from the same sources: Medusa gates every
verb on a per-variant `manage_inventory` flag, so ask which SKUs opt out and whether their walk
still ends somewhere (S16); Saleor names `OVERSOLD_ITEMS` as an *order event with a surface*, so
the state where the count went negative anyway is a row, not an exception. Our own invariants
9, 11 and 12 say what must hold; this table says which event proves each.

## S16 — Terminal-state accountability. EVERY ORDER AND EVERY PARCEL MUST END SOMEWHERE A PERSON CAN ACCOUNT FOR

Where S15 asks whether the four corners *agree*, this asks whether the object ever *ends*, and whether anybody is told when it ends badly. The owner's instruction, which is really an audit rule: *"No delivery or transaction should allow go dead quietly with loose ends, all ends must be tied and traceable"*, and *"anything system cannot handle must hv badge or flag in admin panel of order management page to let admin handle and notice."*

In a commerce system this is where real money is lost with a green test suite. Every function on the path is correct; there is simply no further event, and no disagreement for S15 to catch. The shop keeps selling and one order sits in a state nobody is looking at.

Method, per money-or-goods flow:

1. **Enumerate the terminal states, then the non-terminal ones.** For every state that is neither terminal nor guaranteed to advance, name the thing that advances it: a gateway callback, a logistics push, a worker, a clock, a human. "The provider will tell us" is not an answer; name the endpoint and the code that reads it.
2. **Kill each advancer and ask what happens.** The callback never arrives (the provider retried four times into a 500 and gave up). The push URL was never entered in the provider's console. The worker is not in the crontab, or dies on its third row. The customer never collects. The shop never looks. For each: does the order reach a state somebody can act on, or does it sit?
3. **Walk the commerce-specific silent deaths by name.** A payment authorised and never captured inside the acquirer's window. A parcel that reached the store and was never collected, whose return leg nobody watched. A refund begun and never confirmed. A cash-on-collection order collected, where the settlement never arrived. An invoice obligation opened and never written. An entitlement granted against a payment later reversed. Stock reserved by a cart that was abandoned. Each is a state that can persist forever and costs money quietly.
4. **Check both halves of a two-fact truth, separately.** For 取貨付款 and every cash-on-collection scheme the owner named the two facts exactly: *(a)* the goods were picked up, and *(b)* the money actually reached us. These must be two records that can disagree — a collection event from the logistics side, a settlement from the payment side — and a disagreement must raise something. A shop that infers payment from collection cannot detect the case where only one is true, which is the case that costs the shop the goods.
5. **Then check the notice lands where the operator already works.** Usually the missing half. An alert table with no page, a log line, a digest email, a status nothing filters on — none is a notice. The test is whether the condition becomes visible on the **order list and the order page**, which is the screen a shopkeeper opens every day. The owner's own words: a badge or a flag on the order management page. A handler that exists on a page nobody opens is a dead control (S6) wearing a different hat.
6. **Report the unattended set** as a table: state, what should have advanced it, what the operator would see, how they would ever find out, and what it costs per occurrence. An empty table is a real result; an absent table means the sweep was not run.

**Grading.** Money or goods that can be lost with no signal: **CRITICAL** — and the first case of that is the zero-row precondition update on an authentic callback (S16.1 rule 2): the money is at the gateway, the order stays unpaid or expired, the 200 is sent, and no badge exists. Two cold runs graded that HIGH; it is CRITICAL, because the customer has paid and every screen says they have not. An order that can sit forever but is recoverable once noticed: **HIGH**. A notice that exists only in a log, or in a table with no screen: **HIGH** — by the owner's rule that is not a notice. A notice on a screen nobody has a reason to open: **MEDIUM**.
**S16.2 — the dispute row (from the chargeback guides, 2026-09-15).** A chargeback is work that
arrives from outside with a deadline nobody in the shop set: the acquirer's window to answer
(7–10 days is common), after which the money is gone by default. Three things the S16 table must
show for it, whether or not a "chargeback path" exists in the code: **(a) the evidence is
collected at placement, not when the dispute lands** — the consent text id, the address, the
client address and user agent, the delivery scan, the download record; sixty days later none of
it is obtainable; **(b) the response deadline is a ceiling with a notice**, on the desk, at
T minus a few days, not an email to an unread inbox; **(c) a repeat disputer is a flag** on the
next order from the same address or card fingerprint. A shop whose answer is "the acquirer writes
and we answer by hand" has the ceiling in a person's memory - say so in the S22 row, as
`UNVERIFIED`, never as handled.


Report line format: `S16 — N flows × M non-terminal states; K silent deaths, J notices that reach no screen; unattended-state table in the report.`

### S16.1 — Every non-terminal state deserves a queue, and the queue is where the bulk action lives

S16 asks whether a state has a **badge**. The badge is the minimum and the **queue** is the useful
form: an operator opens *"what needs doing next"*, not *"records, filtered by status"*. The rules
below came out of designing one operator desk and apply to every desk.

**Check, per non-terminal state:** is there a queue that lists the items sitting in it, and does that
queue carry the action that moves them on? A state whose only surface is a per-record badge makes the
operator hunt for the records one at a time, and **a worker that already computes the list and writes
it to a log or an exit code is the queue's missing half**.

**Four rules, for any desk:**

1. **The single action is a batch of one.** Two code paths drift, and the one that drifts is the one
   without the precondition. Write the batch; let the single case call it with a selection of one.
2. **Carry the precondition in the `WHERE`, always.** `UPDATE … WHERE id = ? AND <what made this row
   eligible>`, then read the affected-row count. Closes the select-then-commit race, makes double
   clicks harmless, needs no lock and no version column. **Never `UPDATE … WHERE id = ?` alone** —
   in a desk or anywhere else.
**2a. A state transition and a value edit need different preconditions, and conflating them is a silent data loss.** Rule 2 above is not one rule but two, and the second is the one that gets missed:

| | Precondition | Why it is enough, or is not |
|---|---|---|
| **State transition** — mark dispatched, mark paid, cancel | `WHERE id = ? AND dispatched_at IS NULL` | **Self-protecting.** The condition can only be true once, so the second writer matches zero rows and learns it lost. The row count *is* the answer |
| **Value edit** — price, stock, a note, a cost | `WHERE id = ?` | **Not enough, and it fails silently.** There is no natural once-only condition on a value. Two operators editing the same price both match, both succeed, and the first edit vanishes with nobody told |

**For a value edit, carry the value you read**: `WHERE id = ? AND price = ?` — compare-and-swap — or
a `version` / `updated_at` token if several fields move together. A zero row count then means
*"somebody changed this while you were looking at it"*, which is a sentence the operator can act on,
and **the alternative is not a conflict, it is a disappearance.**

This matters most in exactly the place it is least expected: a **bulk editor** feels like typing in a
spreadsheet, so nobody thinks about concurrency — and it is the surface where one operator can
silently discard fifty of another's edits in a single click.

**2c. `rowCount()` may mean *matched*, not *changed* — check the connection before trusting the number.** MySQL's default reports rows the `SET` actually changed; with `PDO::MYSQL_ATTR_FOUND_ROWS` it reports rows the `WHERE` matched, and a codebase may enable that deliberately — one did, to stop idempotent re-saves reading as *"not there"* (`fb64069e`). Rules 2 and 2a survive either setting **only because the precondition is in the `WHERE`**: a row that no longer qualifies is not matched, so it is not counted, whichever semantic is on. What does *not* survive is any code reading `rowCount() === 0` as *"nothing changed"* — under `FOUND_ROWS` a no-op re-save matches and reports 1. A test asserting the old semantic was found red, unreached, at about test 4700 of a six-hour suite. **Grep the connection for `FOUND_ROWS` before writing or auditing any row-count logic, and if the contract needs "nothing to change" to read as zero, put that in the `WHERE` too** — NULL-safely, with `<=>`, because the columns compared are usually the ones that start NULL.

**2b. Validate per cell, not per submission.** One bad value must not reject the other forty-nine.
Same rule as showing ineligible rows with their reason: the batch reports per row, and the rows that
were fine are saved.

3. **If two rows could legitimately differ, it cannot be a header field.** One shared field for a
   per-item value writes the same tracking number, refund amount or invoice number onto every row in
   the selection. The test is one sentence: *could two selected rows honestly want different values?*
4. **Ineligible is explained, never silently dropped and never blocked.** Show the excluded rows with
   their reason. **Generalised to every disabled control in the product**: a greyed button says why it
   is grey — an S22 surface kind of its own, and the cheapest operator-experience win in most
   codebases.

**And the one that is about people rather than rows:** an operator action that can reach a customer
gets a **"tell them" checkbox, defaulted on, with the unchecking recorded — who and when.** A
customer who was never told must be distinguishable from one somebody decided not to tell. The
checkbox writes *intent*; the sending stays with whatever durable sweep already sends, because a
send-inside-the-click makes the customer's message depend on the operator's browser staying open.

**S16.3 — the aggregate is resolved, never written (2026-09-17, from Sylius).** Sylius keeps
five machines on one order — the order, its checkout, its payment aggregate, its shipping
aggregate, and one per payment and per shipment — and the two aggregates are *resolved* by
listeners (`ResolveOrderPaymentStateListener`, `ResolveOrderShippingStateListener`) from the
child rows every time a child moves: `partially_paid`, `partially_shipped`, `partially_refunded`
are computed, never set by a form. That is the rule this shop already lives by for delivery
("derived, not stored") stated for every parent status: **a status that summarises children is a
function of the children, recomputed on every child transition, and any code path that writes it
directly is a finding** — because the first time a child moves without the parent following, the
customer and the operator read two different orders (S15). The same listener list also reverses
what placement did: `DecrementPromotionUsages` on cancel undoes `IncrementPromotionUsages` on
place, and `SetImmutableNames` snapshots the product's name at placement. Ask of every counter
placement increments — coupon uses, stock, loyalty points — which event decrements it, and of
every fact the receipt prints — name, variant label, price — whether it is the order's copy or a
live join (invariant 17).

**S16.4 — every transition names its preconditions, and every precondition has a sentence the
person sees (2026-09-17, from Vendure).** Vendure's default order process refuses transitions with
named reasons, and the list is a checklist for any shop: *to payment* — not when the basket is
empty, not without a customer, not without a shipping method, not with insufficient stock, not
with a product that became unavailable; *to shipped / delivered* — not without authorised (or
settled) payments, only when some or all items are shipped / delivered; *to cancelled* from a
shipped state — only when every fulfilment is cancelled. Two things the list teaches. First, the
guard belongs on the **transition**, not on the button: a guard on the button is S17 (a control
whose enforcement point is outside the system) the moment a second client exists. Second, every
refusal has a message key, which is S22 in one line: a guard with no sentence is a refusal the
customer meets as a page that does nothing. Vendure also has what most shops lack: **modification
after payment as a state** (`Modifying` → `ArrangingAdditionalPayment`), an `OrderModification`
row with the lines changed, the surcharges, the `priceChange`, and a link to *either* a payment
or a refund. Ask whether this shop can change a paid order at all; if it can, whether the change
is a row with a money link or an edit nobody can account for (S16 step 5, §8h).

*Two ratchets from the day it was first run whole-shop (2026-09-17).* **(a) A locale-coverage test
keyed on the message table proves the table, not the code.** The shop's test walked every code in
`codes()` through every locale and was green while eight reasons thrown under `src/` had no code at
all and fell through to the developer's English. The ratchet that holds is keyed on the *throw
sites*: scan the source for every `throw new <Refusal>('<reason>'` and assert each reason is in the
table (exempting the ones that route through another table, by name, with the reason written
next to the exemption). **(b) A compare-and-swap repeats every predicate of the query that chose
the row.** The expiry sweep selected candidates on three conditions and claimed each with an UPDATE
that re-checked one; the other two were the ones a concurrent writer could change (a pickup block,
a vendor instruction row). Ask of every conditional claim: does its WHERE equal the SELECT's, or
only the clause the author thought was racy?

## S17 — The hosted surface: every choice the buyer makes on a page you do not render. A SHOP SETTING THAT CANNOT REACH THE GATEWAY'S OWN PAGE IS A LABEL, NOT A CONTROL

The owner's question that defines this sweep: *"How do we restrict user use which chain by toggle? Or do we trust our toggle auto reflects payment gateway setting?"*

Modern commerce hands the buyer to somebody else at the most important moment. A hosted checkout takes the card. A hosted **store picker** takes the convenience-store choice. A carrier's page takes the locker. An app store takes the purchase. **The shop's settings stop at the redirect**, and S6 (dead control) and S13 (orphan capability) both search the shop's own code, so both pass while the setting governs nothing.

The canonical shape, because the pattern repeats: the shop had a per-chain delivery toggle — 7-ELEVEN, 全家, 萊爾富, OK — in its own table, read by its own storefront, covered by tests, and reported as built. The buyer chose their store on the **payment gateway's** map. The gateway's request field for that flow has exactly two values, "one chain" or "all four", and the manual states that what is actually enabled is decided in **the merchant's back-office**, not in the request. So the toggle could not restrict anything, and a chain switched off in the admin could still come back on the callback and be recorded as a normal order.

Method, for every hand-off to a hosted surface:

1. **List the redirects.** Hosted payment page, store or locker picker, wallet consent, carrier booking, instalment underwriting, app-store flow. For each, find the request builder in your code. That request is your whole influence over what the buyer sees.
2. **List the shop settings that claim to shape it.** Delivery-method toggles, offered-payment-method sets, carrier catalogues, instalment term lists, currency menus.
3. **Open the provider's manual at the request-field table and check the claim, field by field.** Quote the field, its permitted values and its defaulting rule into the finding, with the page number. Ask whether the request can express what the setting promises. The usual answer: the field is coarser than the setting by a factor of four.
4. **Find the sentence naming the real enforcement point.** It is nearly always there and nearly always unread — *"must first enable the service and configure X in the member area"*, *"approval is per sub-type"*, *"if neither is enabled in the merchant settings the option does not appear"*. Whatever it names is outside your repository, outside your tests and outside your deploy.
5. **Classify and report as one of three:** **(a) enforceable** — wire the setting to the field, test it, done; **(b) unenforceable, so the setting is a lie** — delete it, or redefine it as "what we accept" and then apply S16: an out-of-set value arriving on the callback must raise a badge, never be accepted silently; **(c) enforced in the provider's console** — document the setting as a mirror, put the console step in the deploy prerequisites, and name what reconciles the two.
6. **Walk the return path with a value your settings exclude.** Place the order, have the provider return the excluded chain, method or locker, and follow it to the admin. Silent acceptance is a HIGH finding: the operator now has an order in a state their configuration says is impossible, and no badge tells them.
7. **Check the money variants separately.** Pay-now and pay-on-collection are often the *same* hosted flow with one different integer, and the fee, the settlement date and the refund route all differ. A setting that switches one on frequently cannot express the other.

**Grading.** A setting that claims to restrict carriers, payment methods or fulfilment and provably cannot: **HIGH**. Silent acceptance of an excluded value on the callback: **HIGH**. A console-mirror setting with nothing reconciling it and no deploy step: **MEDIUM**, HIGH once both sides are editable by different people. A cosmetic setting documented as cosmetic: not a finding.

**The reading rule.** When the provider's manual is on disk — and in this domain it usually is, as a PDF nobody has opened — **read the field table for every field the shop sends, before describing what any of them do.** A docblock in your own integration describing a gateway field is your summary of their document and carries none of its authority; three of the defects behind this sweep were confident summaries written by the same hands that later audited them.

Report line format: `S17 — N hosted surfaces; K shop settings tested against the provider's field table; findings by shape (enforceable / lie / console-mirror); return-path walk: done/not done.`
