# Sweeps S22 — surface completeness: step × outcome × audience

> Part of `references/sweeps/` (index: `README.md`). Split from the former `sweeps.md` on 2026-11-10 - text unchanged. Read every file in the folder per §0.9.

## S22 — Surface completeness across step × outcome × audience. A STEP WITH NO SCREEN IS A STEP NOBODY CAN BE TOLD ABOUT, AND A SCREEN NOBODY HAS RENDERED IS A SCREEN NOBODY KNOWS IS BROKEN

The owner's question that defines this sweep: *"are you sure all gaps for [the] purchasing cycle, all combinations of them, each step has a UI and screen, to flag, show and confirm and catch whatever throws back, and every purchasing and checking step has a display showing admin or customer… how do you call this gap and how does our skill catch these gaps?"* In the shop that asked it, ninety-five preview scenarios existed, forty-six of them admin, and **not one rendered an exception, alarm or badge**.

**Why the existing sweeps miss it, stated precisely, because each is close enough to feel like coverage:**

| Sweep | What it asks | Why it is not this |
|---|---|---|
| **S15** four-corner walk | do the corners *agree* about the object | a corner can agree perfectly and still have no screen |
| **S16** terminal-state accountability | does the state *end* somewhere a person can account for | satisfied by an alarm row that reaches *a* screen; never enumerates step × outcome × audience |
| **S17** control enforcement | can the setting reach the decision | about controls, not about surfaces |
| **S18** enumeration against the authority | is every *contract* combination verified | fields and pages, not faces |
| **S13** orphan capability | is the capability wired | a wired capability with no rendered state passes |

**The method is a matrix, and it is a different matrix from S18's.** Build it once, per commerce flow — purchase, subscription renewal, refund, return, exchange, store credit:

1. **Enumerate the steps** of the flow end to end, **including the reversals** — which are the half that gets forgotten, because the happy path is the one everybody demonstrates. For a purchase: offer, checkout, authorise, instruct or capture, settle, fulfil, deliver, close; then expire, cancel, refund, return, chargeback, and the late arrival that contradicts one of those.
2. **Enumerate the outcomes** of each step, and **`unknown` is a required column, not an edge case** — S21 and S20 both exist because a system that cannot say *"I could not tell"* says something false instead. The set: **succeeded · refused · timed out · partial · unknown · reversed after the fact.**
3. **For each cell, name the surface for each audience that bears the consequence** — typically customer and operator, sometimes a third (an accountant, a courier, a regulator). Where a cell genuinely has no audience, write that down rather than leaving it blank; a blank is indistinguishable from an oversight.
4. **A surface only counts if it satisfies all four:** it **exists**; it is **reachable by a URL or route somebody can open on demand**, without reproducing the situation that causes it; it **says what happened in words that audience can act on**; and for the operator it **says what to do next**. A log line is not a surface. An email is not a surface for the operator. A row in a table with no screen is not a surface.
5. **Mark every cell `OK` / `GAP` / `UNVERIFIED`**, exactly as S18 does, and treat `UNVERIFIED` as a task. A cell nobody has opened in a browser is `UNVERIFIED`, whatever the integration tests say — because an integration test asserts the *data* and has never once proved the page renders.
6. **Walk every UI action as its own mini-matrix.** Buttons, toggles, segmented controls, form submits, uploads/downloads, copy controls, refresh/recheck, setup/install, checkout, refund, dismiss, retry, bulk and destructive actions all need the same loop: before-click scope and availability; immediate acknowledgement; disabled/progress/running state; success/failure/cancel/retry result; next action; refresh/recheck if completion is detected later; stale-output reset (seed a previous attempt's error/progress/success output and prove the next refresh, recheck or retry clears or replaces it); final state. If a good click and a broken click look the same, the action is not closed.

**The renderability clause, which is what makes this sweep different from S16 and is the part that gets skipped.** The states that most need a surface are the ones that only appear when something has gone wrong, and those are exactly the ones no fixture produces. **Demand a fixture per situational surface, not per page.** If reaching a screen requires reproducing a gateway outage, a lost callback or a ten-day-silent parcel, then in practice nobody has ever seen it — not the designer, not the reviewer, not the person who will have to read it at three in the morning. A coverage ratchet that counts pages and scenarios will report clean on all of them; widen it to count **conditional surfaces inside existing pages** — a badge, an alarm panel, an empty state, a disabled control, a refusal message.

**Grading.** A money step whose **refused**, **timed out** or **unknown** outcome has no operator surface: **HIGH**. A customer-facing refusal with no customer surface: **HIGH**, because the customer is stranded mid-purchase with their money possibly taken. A surface that exists but has never been rendered: **MEDIUM**, and it becomes HIGH the moment anything on the page is typed — the canonical case is a settings page that threw a `TypeError` on every request for days because nothing ever opened it.

**The sentence to carry out of this sweep:** *every way a purchase can go must have a face, and a face nobody has looked at is a rumour.*

### S22.1 — What this is called outside this skill, because hunting it needs the right words

**It has names. Several, one per community, and an auditor who does not know them cannot search for
prior art, cannot read the tooling that already solves half of it, and cannot tell a developer what
is missing in a word they will recognise.**

| Community | The name | What it gives S22 |
|---|---|---|
| UI design | **The UI Stack** — Scott Hurff, 2015: every component has **blank / loading / partial / error / ideal**. Missing ones are **empty-state** and **error-state gaps** | The canonical five-state checklist. Most teams design *ideal* and ship the other four by accident |
| Front-end | **story coverage** (Storybook), **visual coverage** (Chromatic, Percy, Applitools). The maxim is *"if it can render, it needs a story"* | The fixture-per-state discipline, already an industry norm - and the reason a preview catalogue is the right instrument rather than an invention |
| QA / test | **unhappy-path** or **sad-path coverage**, **negative testing**, and for state machines **statechart coverage**, split into **state coverage** (every state reached) and **transition coverage** (every edge taken) | Names the asymmetry precisely: happy-path coverage can be 100% while sad-path coverage is 0%, and one number hides the other |
| Combinatorics | **state-space explosion**, answered by **pairwise / all-pairs / n-wise coverage** (Combinatorial Test Design) | The honest answer to *"all combinations"*: the full cross-product is infeasible and nobody runs it. See the depth rule below |
| SRE | **actionable alerting** - the Google SRE rule that an alert which does not tell a human what to do is **noise**, not signal - plus **runbook coverage** and **observability gap** | Exactly why a log line and a digest mail fail this sweep. The industry already decided this and wrote it down |
| Product / internal | **operator experience**, **internal-tooling debt**, **back-office UX** | The vocabulary for arguing the work is worth doing, to somebody who thinks admin screens do not need design |
| Front-end / templating | **Kitchen Sink page** — one view rendering every template variation side by side on extreme mock data; **fixture-driven sandbox** — production templates fed a quarantined set of mock or seed records; **data-driven component harness** — real templates against a controlled matrix of states | The shape of a preview hub, and its three promises: **zero theming drift** (the real template and the real stylesheet stack, so nothing looks right in isolation and breaks in the live layout), **proactive state coverage** (text-wrap, overflow and grid collapse found before a customer's data finds them), **clean separation** (test data never in the inventory or customer tables). The third is why the fixtures are in-memory objects and not a demo table: quarantine without a third data store |
| Reaching the states | **fault injection**, **state injection**, fixtures and mocks; **chaos engineering** at the infrastructure tier | How the untestable-looking states get rendered without waiting for a real outage |

**Use these words in findings.** *"The refund-refused path has no error state and no story"* lands
with a front-end developer; *"S22 cell 4.3 is a GAP"* does not.

### S22.2 — How to hunt them, mechanical, in rough order of yield

1. **Grep the render guards.** Every conditional that wraps output is a surface: an emptiness check,
   a null check, an early return carrying a refusal reason, a match arm that renders something else.
   **Enumerate them and ask which has a fixture.** Highest-yield pass and pure grep - a conditional
   surface inside an existing page is the exact thing a page-level coverage ratchet cannot see.
   **And check what the fixture renders.** A preview that draws its own HTML beside the real page
   is a *hand-drawn twin*: it passes the ratchet, it looks rendered, and a theme written against
   it lands on markup the real page does not have. One catalogue had 32 admin previews and 23
   were twins - the order list and every order-detail state among them. Rule: **a preview renders
   the production renderer with fixture data, or it is UNVERIFIED**; assert by reflection that
   each scenario's renderer is a production page or controller class, never by eye. A twin is a
   wireframe - fine before the page exists, a liability the day it does - and its hub entry must
   say so.
2. **Walk the enums as statecharts.** **State coverage**: has each case a rendered surface?
   **Transition coverage**: has each edge one where it matters? The edges that run *backwards* -
   cancelled-then-paid, delivered-then-returned, refunded-then-charged-back - are where surfaces go
   missing, because forward edges get demonstrated and backward ones do not.
3. **Inventory the error paths.** Every catch, every throw that can reach a request, every refusal
   string, every non-zero exit. Each is an outcome. **A refusal reason that exists only as a string
   in a log is an error state with no error surface.**
4. **Empty states.** Every list, table and collection: what is shown at zero rows? Zero is the state
   a shop is in on **day one**, so it is the first thing a new operator sees and the least likely to
   have been designed.
5. **Read the alerting.** Every notifier, digest, cron exit code and alarm row: where does it land,
   and is that a screen somebody opens? Apply the SRE test - **does it say what to do?**
6. **Walk action loops, not just pages.** Grep click handlers, submit handlers, route actions, mutation calls, background-job starters, copy-to-clipboard calls, refresh/recheck controls, save/delete/dismiss/retry/bulk actions and install/setup launchers. For each, prove the full loop named in the method: visible precondition, immediate acknowledgement, running state, terminal result, next action and refresh/recheck if the truth lives outside the page. A handler that returns 200 with no visible result is a surface gap.
7. **Then, and only then, the cross-product** - bounded deliberately.

**The depth rule, because "all combinations" is not a plan.** The full cross-product of
step x outcome x audience x payment method x delivery method x destination x cart shape runs to tens
of thousands of cells and will never be walked. So:

- **Money paths at full depth.** Every step whose outcome can move, hold or lose money gets every
  outcome and every audience, enumerated exhaustively. This is a small set - it is the failure
  column, not the whole grid.
- **Everything else pairwise.** All-pairs coverage over the remaining axes catches the large majority
  of interaction defects at a fraction of the cells, which is the published result behind CTD.
- **Say which is which in the report.** A matrix that silently sampled is S18's original sin. State
  the axes taken at full depth and those taken pairwise, so the next reader knows what was not walked.

### S22.3 — Step 0: draw the decision tree before the matrix, because the matrix takes its steps from it

**The owner's instruction:** *"maybe you
should first draw a map of customer checkout choices of combination step by step, so you know how
many different paths and diversion of choices they can make each step… and to know best maintainable
non-messy way to set those paths."*

**The matrix as first written takes its step list as given, which is a sampling error wearing a
grid.** Steps enumerated from the code are the steps somebody already built; the tree enumerates the
steps the *customer* can take, including the branches nobody implemented. Do the tree first.

**Method.** One node per decision the customer makes or the system makes for them, in order, from
first intent to the last irreversible event — cart shape, identity, destination, delivery method,
payment method, payment execution, outcome, fulfilment, delivery, and the reversals. At each node
list **every branch**, not the common ones. Then:

1. **Count the leaves.** That number is the honest size of the problem, and it is usually an order of
   magnitude larger than the team's mental model. It is also the number the S18/S22 depth rule then
   bounds — money paths at full depth, the rest pairwise.
2. **Mark where branches converge.** *This is the maintainability question and it is the reason to
   draw the tree at all.* Fifty-four paths collapsing into six screens is a good design; fifty-four
   staying fifty-four is a mess that will be maintained forever. **Converge as early as the domain
   allows, and keep separate only what genuinely differs** — and write down which is which, because
   the next person will otherwise merge two paths that had a reason to be apart, or split one that
   did not.
3. **Mark every node where the screen changes.** That set, exactly, is the preview-fixture list —
   which answers *"what has to exist before this can be themed"* without anybody guessing.
4. **Mark every node where control leaves the system** — a hosted payment page, a carrier's site, a
   counter, a bank. Each is a **round trip**, and each needs the return path enumerated as carefully
   as the outgoing one. The classic miss is a branch that leaves and has no drawn way back:
   abandoned at the gateway, closed the tab after paying, the callback that never came.
5. **Mark every node that needs an operator gate** before the object can move on — and be explicit
   where the honest answer is *none*, because a blank reads as an oversight.

**What the tree catches that the matrix alone does not:** a branch that exists in the UI and has no
handler; a branch the code handles that no UI can reach (S13 from the other end); two branches that
were drawn separately and behave identically, which is cost with no benefit; and the branches that
only appear after something goes wrong, which are the ones nobody draws because nobody demonstrates
them.

**Then build the matrix from the tree's steps**, not from the code's. The tree is also the artefact to
keep: it is the one document a new person can read to learn what the system is *for*, and it dates
far more slowly than the code.

### S22.4 — Closure rule: the authority's error table *is* the outcome column

**The owner's statement of the closure condition:** *"every api or return
should have a ui or admin response on ui, and every combination of user possible behaviour or
situation of purchase cycle should have a catch on UI or admin… each combination may need a theming
of layout or flag design… to make sure no api response or flow got missed or unattended to on
screen and by system handling."*

That is the sweep's closure condition and it fixes the sweep's worst weakness. *"Enumerate the
outcomes"* invites invention, and an invented list is a sampled list wearing a suit. **It does not
need inventing: every provider has already enumerated its outcomes, exhaustively, in the error table
at the back of its manual.** Transcribe it.

**So S18 and S22 join here.** S18 reads the authority for the *contract*; S22 reads the same
authority's **error table** for the *outcome column*, and the join is one row per code:

| Provider code | Meaning, verbatim | **Handled** | **Surfaced** | **Designed** |
|---|---|---|---|---|

**The three columns fail independently, which is why one column is not enough:**

- **Handled** — the code reaches a deterministic branch. Not a `default`, not a fallback to a
  neighbouring meaning, not silence. *A code mapped onto another code's meaning is worse than an
  unhandled one, because it is confidently wrong.*
- **Surfaced** — a human sees it, on a screen, per S22's four tests. A log line, a digest, a cron
  exit code and a table row with no screen all fail here. This is the SRE **actionable alerting**
  rule: an alert that does not tell a human what to do is noise.
- **Designed** — it has a visual form somebody chose: which flag, which colour, which severity,
  which position, blocking or not. **An error rendered as raw text in the default font is handled
  and surfaced and still fails**, because the operator cannot tell at a glance whether it is urgent,
  and the customer cannot tell whether they still have to do something.

**This is also what makes theming estimable rather than open-ended.** The designer does not need a
layout per code — they need one per **surface kind**. Count the kinds, not the codes: blocking
refusal, non-blocking warning, informational note, badge on a list row, panel on a detail page,
empty state, disabled control with a reason. **Every code maps to exactly one kind, and the kinds
are a dozen.** Report both numbers: *N codes across K kinds* — the first is the audit's workload,
the second is the designer's.

**The same closure applies to the other direction — user actions.** Every action a user can take
that the system can refuse is an outcome with the same three columns: an invalid coupon, a
quantity beyond stock, an address the carrier will not serve, a method unavailable for the
destination, a session that expired mid-checkout, a double submit, a back-button replay. The
enumeration comes from the **render-guard census and the error-path inventory** (passes 1 and 3
above) rather than from a vendor manual, but the rule is identical: **handled, surfaced, designed.**

**What "no gap" means, stated so it can be checked:** every row of every authority's error table,
and every refusal the system itself can produce, has all three columns filled. Anything else is
`UNVERIFIED` and is a task. *A provider code with no branch is a bug; a branch with no screen is a
silence; a screen with no design is a message nobody reads in time.*

### S22.5 — What "handled" means, and it is not a `catch`

**The owner's definition, given against a scoring that had reported 26 of 26 handled:**

> *"Handled meant it is a closed loop and nothing dies quietly without a human actually noticing or
> taking action. Code may have a catch and quietly log it, but any exception should be noticed by
> admin dashboard, at least a flag or a badge for each situation. Admin may choose to diffuse or
> ignore, but it should be admin's decision, not quietly logged. You should determine whether the
> response requires actual follow up, so the UX for both admin and customer is fully informed — that
> the entire operation is a complete, or dismissed as an informed decision."*

**That is the terminal condition for this sweep, and it replaces the weak column outright:**

> **Every operation ends COMPLETED or DISMISSED-BY-A-PERSON. There is no third ending. "Logged" is
> not an ending.**

A `catch` that writes a log line is **not** handled. It is *caught* — a different, much weaker
property that only says the process did not crash. Scoring the two as one is how an audit reports
clean on a system whose every failure is invisible. **Score five columns, not three:**

| Column | The test | Failure mode it catches |
|---|---|---|
| **Caught** | the process does not crash, the request does not 500 | the weakest property, and the one most often mistaken for the others |
| **Classified** | **somebody decided, in advance and in writing, whether this outcome needs follow-up or is informational.** Not inferred at read time | the whole table treated as one severity, so nothing can be prioritised and everything is either noise or missed |
| **Raised** | if it needs follow-up, it reaches a **flag or badge on the screen the operator already opens** — not a log, not a digest, not an exit code | the silence this sweep exists for |
| **Closable** | a person can **dismiss it, and the dismissal is recorded** — who, when, why. Dismissing is an act, not an absence | an alarm that cannot be cleared becomes wallpaper within a week, and wallpaper is the same as silence |
| **Designed** | it has a visual form somebody chose: severity, colour, position, blocking or not | the operator cannot tell urgent from routine at a glance, so triage happens by reading everything |

**Classifying a vendor's code table, the shape that works:** one label per row from a set of
three — *customer retries* / *operator fixes* / *ours* — chosen in writing, with the customer
sentence and the operator surface each label produces. Then four rules the table will force:
**a default bucket** (the sandbox returns codes that are in no manual; unknown ⇒ ours, raised);
**text-decided codes** (one code, several messages — the classifier takes both); **the customer
never reads a parameter name** (ours and operator share one sentence); and **pre-checks beat
refusals** (every amount or state rule the vendor publishes is a guard before the call). Expect
*ours* to be the largest bucket — most of any gateway's table is malformed requests — and expect
at least one already-distinguished code to have the wrong sentence, because a specific sentence
is trusted and nobody re-reads it against the manual.

**"Ignore" is a legitimate outcome and it must be expensive enough to be real.** The owner's
formulation is exact: the admin may diffuse or ignore, *but it must be the admin's decision.* So a
dismissal path is **required**, and it must capture a reason and a person. A system that cannot
record *"I looked at this and decided it did not matter"* forces its operator to choose between
acting on noise and ignoring signal — and they will choose ignoring, every time, and then miss the
one that mattered.

**Classification is the auditor's own work, not the developer's.** For every outcome in the table,
say which of these it is, and say it in the report:

- **Needs follow-up** — a person must do something. Raise, and keep raising until dismissed.
- **Needs telling, not doing** — the customer or operator should know; no action. Show once.
- **Informational** — genuinely nothing. **Say so explicitly**, because a blank in this column is
  indistinguishable from an oversight, and the next auditor will re-derive it.

**And both audiences, always.** An outcome the customer bears — their payment refused, their parcel
returned, their refund past its window — needs a customer surface *and* an operator surface, and
they say different things. "Fully informed" in the owner's sentence means both, not either.

**The grading follows directly.** An outcome that needs follow-up and is only logged: **HIGH**, and
it is HIGH whether or not money is involved, because the failure is the invisibility rather than the
amount. An outcome raised with no way to dismiss it: **MEDIUM**, rising to HIGH once the count is
large enough that the screen is ignored. An outcome unclassified: **MEDIUM** — nobody has decided,
so nobody can be wrong yet, but nobody can be right either.

### S22.6 — Mode errors and invisible scope: a control must show what it will act on

**The defect:** if rows are selected and the
operator then re-sorts, re-filters or pages, **a naive list keeps the ticks against different
records** — so the button now acts on a set nobody chose and nobody can see.

**This class has names and they are old ones.** Raskin's *The Humane Interface* calls it a **mode
error** — the same action producing different results depending on a state the user cannot see — and
names modes a primary cause of human error. Nielsen's first heuristic is **visibility of system
status**. In list UIs it shows up as **scope ambiguity** and **stale selection**. Use those words in
findings; *"confusing"* is not a finding, *"this control has two scopes and neither is shown"* is.

**The rule: a control that acts on a set must make the set visible, unambiguous, and current.**

**The largest invisible mode is the environment.** Sandbox and production are two modes of every screen, and if nothing shows which one a row came from, a test order and a live one are indistinguishable to the operator. Look for one switch read in one place (an `APP_ENV`, a `gateway_mode`, an endpoint table keyed by it) and shown in the admin header; a shop whose return URLs, endpoints and merchant keys are hard-coded has **no switch**, and that is a finding at **MEDIUM** on its own, before any sandbox walk is attempted. Report it in the S22 line as `environment mode switch: <path:line | NONE>`; a cold run that omits the item has not looked.

Three questions, per control that acts on more than one thing:

1. **What exactly will this act on** — the rows I can see, or everything matching a filter I set
   three screens ago? If the answer is not on screen, that is the finding. **Never one control for
   both scopes**: a header checkbox meaning *"all 312"* is how somebody marks three hundred orders
   dispatched intending fifty. Page scope is the safe default; *"select all N matching"* is a
   separate, visibly different, deliberate act.
2. **What happens to the selection when the view changes?** Re-sort, re-filter, change page size,
   page forward. **Silently keeping ticks against new rows is the defect.** Either clear the
   selection and say so, or carry it as an explicitly filter-defined set that survives paging and
   dies when the filter changes. Predictable beats clever: an operator who loses eight ticks and is
   told why re-ticks them; one who silently acts on the wrong eight never finds out.
3. **Is the mode itself visible?** This is the same defect outside lists, and it is worse where money
   is involved — **a test/sandbox gateway mode that looks identical to live is a mode error with a
   payment behind it.** Check every environment switch, impersonation session, draft-vs-published
   toggle, maintenance flag and preview mode: does the screen say which one it is in, everywhere it
   matters, or only on the page where it was set?

**Grading.** A destructive or money-moving action whose scope is not visible: **HIGH**. A selection
that survives a view change without saying so: **HIGH** if it feeds a bulk action, **MEDIUM**
otherwise. An invisible mode that changes where money goes: **HIGH**, always.

**The sentence:** *the operator should never have to remember what the screen is doing.*

### S22.7 — Do not invent admin UX; the conventions are settled

**The owner's instruction:** *"reference to shopify or woocommerce or whatever
best ecommerce standard, do not reinvent the wheel, only improve."*

**An operator who has run any shop already knows how an admin works.** Shopify, WooCommerce and
Magento converged decades of operator hours onto the same handful of shapes, and a product that
invents its own spends the operator's attention teaching them a layout instead of showing them their
orders. **Divergence is a cost paid on every single screen, forever.**

So when a surface from this sweep has to be designed, **name the established pattern it follows**
before drawing anything:

| Need | The settled shape |
|---|---|
| A list of records | filter bar, saved views/tabs, per-page selector, sortable columns, row checkboxes, a sticky bulk bar that appears on selection, paging with a total |
| Status | a **pill** with a colour and a word, consistent per state across every screen it appears on |
| An exception on a record | a banner at the top of the detail page and a marker on the list row — never only one of the two |
| A bulk action | select → action menu → **confirm sheet listing what will happen and to how many** → per-row result |
| A record detail | header with the key facts and the primary action, then panels, then a **timeline of what happened when** |
| Nothing yet | an **empty state** with one sentence and the action that ends it, never a blank table |

**The operator-desk pattern, four rules that a night of building desks kept re-finding
(2026-09-13 — mailing, postage, accounting, quick edit):**

1. **A queue, not a list.** A desk is *the number, the one sentence that says what a person does
   about it, and the link that opens exactly those rows*. A count that was already being computed
   by a worker and answered into a cron mail, an exit code or a digest is a queue with nowhere to
   put itself; give it the number, the sentence and the link. A zero reads as quiet, never as
   missing.
2. **Blank is a value.** *Nobody has told us yet* is different from `0`, which is a figure (free
   postage happens). A blank cell leaves the row alone; clearing a figure sets it back to *not
   known* and is logged like any change; an export carries the column empty and ruled, never as
   `0`. **Expected and actual never merge**: what the customer was charged, what the rate card
   predicts and what the receipt says are three columns, and the accountant needs the third.
3. **Value edits need compare-and-swap.** A grid drawn at 14:02 and saved at 14:09 posts what each
   cell held when drawn beside what was typed; a value another operator changed meanwhile is refused
   for that row, in words, never overwritten. A bulk action resolves *all N matching* to explicit
   ids once, against the same cap, before anything runs — it never re-runs a filter that may have
   moved.
4. **A hand-off needs a marker and an artefact.** A sheet that walks out of the building — to the
   carrier's upload page, to the accountant — stamps *exported_at* / *handed_to_accountant_at* and
   *by whom* the first time, and a re-download does not move the date; without the marker the only
   filter is *not yet done*, which re-exports rows somebody already uploaded, and a duplicate upload
   is the failure that costs money. The *tell the customer* box is default on, and unticking it is
   recorded on the row with a name, never silently absent.

**The class behind rule 1, walked 2026-09-13:** `grep -l 'exit(1)' tools/ops tools/worker` and
ask of each what a person *sees*. Three scripts answered *a log file*: a PDPA request past its
fifteen days, stored PHP in Hanna Code, a digital sale with no waiver evidence. Two surfaces
close the class — an order-scoped finding raises one `OperatorNotice` per order (badge on the
order, row on the desk, idempotent per order and case); a site-scoped one records *count + one
sentence* beside its heartbeat and the cron page draws it in red under the stopped workers. The
exit code stays for liveness; it was never a surface.

**Credentials from a screenshot are a hypothesis (2026-09-13, PAYUNi).** A Hash Key read off an
image had one glyph wrong (lowercase l for capital I); the codec encrypted cleanly and the vendor
answered `DEF01007 Hash比對不符合`. The proof of a key is a **live no-op request** — a 交易查詢 for an
order that cannot exist — answered *inside a verified envelope* (`QUERY03001`); an unencrypted
refusal names which of the three values is wrong. Build that probe before the checkout, put it on
the gateway test page, and try the l/I, O/0, 1/l variants yourself before asking anyone to paste.
**Vendor docs behind an SPA (ShowDoc, docsify):** pull the page source through the app's own API
(`/server/index.php?s=/api/page/info`, `page_id`) — the rendered page is empty to a fetcher and a
copied table drops the cells that carry the money rules. Cite page ids, keep the markdown in the
gitignored vendor-docs folder, generate the status map and its audit document from one script.
**One vendor's rule, applied to the next, is a bug (2026-09-13).** NewebPay's order number is
unique forever, so the shop froze every pickup order after one hosted-page visit; PAYUNi only
refuses a repeat within ten minutes, and the same freeze would have left an abandoned PAYUNi page
unpayable for good. When a third provider joins, walk every `if pickup` / `if provider` guard and
ask which vendor's manual it came from — a guard with no citation belongs to one vendor only.
**The third provider's checklist (2026-09-13, PAYUNi, found by a Screen-tier pass forty minutes
after the merge).** A new provider inherits every *per-provider* safety net the first two grew,
and each one is a separate place to forget: **(a)** the expiry sweep's hold-back for a notification
queued but unread — three providers, three hold-backs, the third was missing and the drainer
(5 min) is slower than the expirer (1 min); **(b)** the pull behind the push — a poll of awaiting
orders when the vendor documents no notify retry, keyed to what the vendor's "no such order"
answer costs (PAYUNi: nothing; NewebPay: a four-hour lockout after too many 查無, so that one
needs the order to *record its gateway at redirect time* instead of a blind poll); **(c)** the
operator note that names a console — grep every sentence naming the first vendor's menu and ask
whether it renders for the new vendor's rows; **(d)** the customer note under the Pay button, which
must read the request's own switches, never a fixed sentence per delivery method. Walk the list
by grepping the *first* provider's name across `tools/worker`, the admin notes and the storefront
copy, and asking of each hit what the third provider does there.
**The audit reads the gateway off a row that does not exist yet (2026-09-13, S16 × S21).** A
settlement audit took the vendor from the *payment* row; an awaiting order has none (it is written
at settlement), so the audit's own "the notification never arrived" branch was reachable only by
a test fixture that gave an awaiting order a payment row production never writes. **A test that
hands its subject a shape production cannot produce is a fixture-shaped pass**: for every
"what if X never happened" test, check where the fixture's rows come from in production and
whether *that* writer runs before X. The fix was a column written at redirect time, and the lesson
generalises — an object waiting on an external signal must record whom it is waiting on, or
nothing can ask.
**A code-only Screen pass while the full suite holds the database is worth running (2026-09-13).**
Two HIGHs and a vacuous test in forty minutes, none of which needed a database, a browser or a
sandbox; the DB tests written for the fixes are queued for the slow filter and named as unrun
(S8). Do not wait for the environment to be free to read the code.
**The first provider sized the column (2026-09-13, S21 × the third-provider checklist).** A ledger
column was `VARCHAR(8)` because the first gateway's action codes were one letter; the second
gateway's `newebpay_close_refund` is twenty-one and had never been written by any DB test - the
first production card refund on the primary gateway would have thrown "Data too long" at the
claim. The third gateway's test was the first to write it. **When a new integration joins, grep
every `VARCHAR(n)` with n ≤ 16 on every table it writes to, and for every money path on the
*existing* providers ask which DB test drives it end to end through the store** - a unit test
with a fake ledger proves nothing about the column. And when a walk runs green on a state
machine, read its `out_of_order` lines as findings: a 門市關轉 after 到店 was refused as a
backward step by an ordering rule written for another carrier's vocabulary, the letter still went
out because the event row is written first, and only the alarm was missing.

**An `OK` in the surface matrix cites a renderer; only S15 proves the row reaches it (2026-09-13,
Walk tier, S22 × S15).** The instruction cells - the "how to pay" mail, the order-page panel, the
admin panel - were `OK` with a preview fixture each, and empty in production for the primary
gateway: its 取號完成 post was read for the store block only and the number acknowledged and
thrown away; the shop's own 30-minute card clock then cancelled an order the vendor had given
days. Two HIGHs behind one `OK`. **Rule: a matrix cell is `OK` only when the S15 row for that
state names the write that fills it** - the fixture proves the screen, the four-corner walk proves
the data. And the class re-walk that followed found the same post's lost-in-the-browser case had
no advancer at all, though the vendor's query carried the number the whole time (`PayInfo`,
§4.3.2 註2): **when a browser POST is the only carrier of a fact, the vendor's query is read for
the same fact and a poller writes it.** Second lesson from the same evening, S20: **a class fix
applied to the provider under audit is not a class fix.** The blind-run finding of the morning
went onto the two workers of the new provider and not the six older ones with the identical
shape; "its whole class gets re-walked" means every worker with a `failed` counter, listed by
`grep`, not the ones in the diff. Third, §7 crash recovery on a two-statement intent: "write the
row, then extend the deadline" on three paths - a crash between the statements leaves a customer
holding a live number under the shop's shorter clock; the fix was not a transaction but making the
sweep read the row's own expiry, so the second statement stopped being load-bearing.

**"Handled" needs a surface too, and an audit table with no page is not one (2026-09-14, S22
after-resolve).** The exceptions panel had a "Mark handled" button that asked *what did you do
about it?* and sent the answer to the credential audit log - a table whose admin page was still a
wireframe. So the closing was recorded and invisible: the next person to open the order saw
nothing, and a problem dealt with looked exactly like a problem that never happened. The matrix
had said `OK` for the exception row because the *open* state rendered; nobody had asked what the
screen shows one second after the button. **Rule: for every operator action that closes a state,
walk the screen after the click** - the loop is closed when the closing is visible where the
problem was, with who, when and what they did; a write to a table nobody reads is the report
storey of silence wearing a success notice. Second, the ratchet lesson: a coverage test keyed on
Page classes or scenario enums cannot see a *conditional section inside a covered page* - the
panel that renders in one state only is exactly the surface nobody previews. Mark such sections
(`data-panel="…"`) and ratchet on the markers: every marker on disk must be rendered by some
scenario. Third, S14.1 again: nine plan rows read "patch ready" while the patches had been merged
for two days, and the gate check ("every row ticked") would have been answered wrong by anyone
reading the plan instead of `git log -S`. **Drift check runs against the commits, not the prose.**

**A flake with no evidence in its failure message is the proof storey dying quietly (2026-09-14,
S21 / S12.1).** A CLI-worker test had failed "about one run in three" for a month with the message
`processed=0 stop=no_available_jobs`, and the gap register said *not investigated to root* with
three guesses and two cheap fixes, "neither done because the flake is harmless". It failed once
more at the end of a seven-hour run, on the commit that was to be the gate, with the visibility
wait that was supposed to close guess one already in place — so guess one was wrong and the other
two were still guesses. Twenty-five isolated re-runs passed, which proves only that the failure
needs the seven hours. **Rule: a test that spans a boundary (subprocess, second connection,
container, clock) asserts with the other side's view in the message** — the row as the server
holds it next to the server's own clock, the process list, the exit code and stderr — so that the
first recurrence is the investigation and not another retry. A retry that passes is not a root
cause; "harmless" is the word the register uses for a defect it has stopped looking at. File such
a test under S12.1 as a failure mode of the *proof* (detection: the message; surface: the
register row; recovery: never "re-run until green").
| A field the operator cannot use | disabled, **with the reason beside it** |

**Improve only where the domain genuinely differs**, and say why in the commit: a 字軌 invoice book,
a two-month filing 期, 取貨付款's money-at-the-counter, a carrier upload that takes a spreadsheet.
Those have no equivalent in a Shopify admin and are where invention is warranted. **A paging
control is not.**

**The audit question, then, is not "is this well designed?"** — it is **"which established pattern
is this, and if none, what does the domain require that the established one could not express?"** An
answer of *"it just grew that way"* is a finding, and it is the cheapest kind to fix while the
screens are still being built.

### S22.8 — The parameter diff: a page's render signature is its story list, and the fixture call sites are the stories written (2026-09-16)

**How this was found and lost before it was found again — both halves are the lesson.** The Walk
run three days earlier *had* found part of it: *"S22 UNVERIFIED ×9 — the customer's order page in
eight reversal / refusal states + account-required — open — the next fixture batch."* Then the
plan row for that sweep was ticked with those words written inside the tick, and the batch never
became a row of its own. **Closure rule, added here because step 5's "treat UNVERIFIED as a task"
never said where the task must live: an UNVERIFIED cell lands as a row in the plan the project
resumes from — not in the audit report, not inside a ticked row — before the sweep's own row may
be ticked. A ticked row carrying open cells is the vacuous pass of planning (S8).** The other half
was never in scope at all: the matrix is step × *outcome*, so it holds the failure states of money
steps and has no cell for the *ideal* state of an ordinary page — the account page's order list,
the cart's saved addresses, the catalogue's category tree, a coupon that was accepted. No failure,
no cell, never looked at. That is what the diff below covers and the matrix cannot. Then the owner
asked whether *every combination of the checkout page* could be previewed, and the answer was no: the checkout review
had three fixtures and the account gate — three identity states and a disabled Pay, the largest
block on the page — had never been rendered by any of them. The order page's `render()` takes
**seventeen** parameters; the previews pass **four**. The account page's signed-in previews pass
empty lists for orders, downloads and addresses, so the sections every customer opens the page
for had never been drawn. The reason the guard-grep missed it: a guard on a *parameter* that
every caller leaves at its default is invisible to a grep that reads the page alone. **You have
to read the page and the fixtures together.**

**The method, mechanical, and it is a diff:**

1. For every page or component class the preview hub renders, list the **render method's
   parameters** — especially the optional, nullable and defaulted ones, because a default is a
   branch nobody has to choose — and every `if` / `match` / early return inside it that adds,
   swaps or removes a section.
2. For every fixture that calls it, list the **arguments actually passed**, non-default only.
3. **The set difference is the unrendered list**, page by page, and the count goes in the
   report as *parameters P, passed non-default by any fixture Q*. Seventeen and four is a
   finding; "render guards found R, with a fixture X" is not, because it lets a page with a
   single fixture count every guard as covered.

**Four shapes found the same morning that a page-level or guard-level pass cannot see:**

- **The mislabelled story.** A fixture whose label promises one state and whose HTML shows
  another. `Order — pending bank transfer` passed no transfer panel and no redirect, so it rendered
  the *pay-unavailable* branch — a disabled button and an apology — and the ratchet, the
  reflection check and the eye all passed it. A twin fails by drawing its own markup; a mislabelled
  story fails by drawing the wrong real markup. **Assert per scenario that the rendered HTML
  carries the marker of the state the label names** — a class, a heading, a copy key — never
  only that it rendered.
- **The hub's own pointers.** The theming hub is the operator's map of what can be themed. One row
  linked to a scenario with no fixture (the hub said *Download — active*, the page said *No
  fixture*); seven rows named template files that do not exist. A shape test — five columns per
  row — passed. **The map is a control (S5): every link resolves to a fixture, every file named
  exists, or the row is a dead control in the audit instrument itself.** Three lines of
  `file_exists` and `catalog::has()`.
- **No class, no story.** Four templates (redeem, free download, find order, stock notification)
  build their `<main>` inline in the template file, each with form / success / error states.
  They cannot be fixtured at all, so every state on them is UNVERIFIED **by construction**, and
  the fix is extraction to a page class, not a fixture. Grade as S22 does — MEDIUM until
  themed, then HIGH the day a theme lands on markup nobody previewed.
- **One conversation, two faces, neither drawn.** The customer ↔ shop message thread on an order
  renders on the customer's order page and on the operator's order page; both fixtures left it
  null. The S22 audience column applies to *conversations* too: a thread is a surface with two
  audiences, and a fixture for one side is not a fixture for the other.

**Disposition, not score — the owner's correction the same day.** The sweep's deliverable is the
enumerated list with a decision per branch, and a grade only where the owner asks for one or the
branch sits on a money path. Three dispositions, and every branch gets exactly one:

| Disposition | When | What exists afterwards |
|---|---|---|
| **story** | somebody will theme or design against it | a hub fixture, labelled, marker-asserted |
| **render test** | nobody themes it, but it must not throw and must draw the state it claims | a fast-suite test that renders the branch once with the non-default arguments and asserts its marker — no hub row, no fixture data beyond the call |
| **none** | the branch cannot occur, or its output is a single line the base styles already cover | the reason, written next to the branch, so the next reader does not re-derive it |

The point of the second row is the owner's: *make sure nothing is broken for those who do not
need a fixture preview*. A page that threw a `TypeError` on every request for days had a fixture
for its happy path and none for the branch that broke; a render test costs a hundred milliseconds
and would have named it the same commit. **Enumerate everything; fixture what is themed; render-test
the rest; write down the remainder.** Counting unrendered branches as findings by default makes the
list look like a backlog of defects, and it is not — it is a map with three colours.

**The kitchen-sink half — extreme data, not only extreme states (owner, 2026-09-16).** The parameter
diff finds *which* branches render; it says nothing about *what* they render on. A page proven on
"Demo Ceramic Cup, NT$380, qty 2" has not been proven on a 60-character Japanese title, a 99-line
basket, NT$9,999,999, an address of five lines, twelve parcels, an emoji in a note, an empty
string where a name should be. Those are the kitchen-sink values, and they belong to the same
fixtures: **a second persona on every story** — `?persona=extreme` — that swaps the demo values for
the longest, largest, emptiest and most foreign ones the schema allows, rendered through the same
page class and the same stylesheet. The same three dispositions apply, and the render test is
where most extreme values land: it costs nothing to assert that a 99-line basket does not throw.
**Keep the extremes in the fixture layer, not in a demo table.** A table is a third data store to
migrate, seed and keep in step with the schema, it cannot produce the states the *code* decides
(a gate state, a gateway redirect, a missing token), and the quarantine it promises the in-memory
fixture already gives. Where the shop needs a database walk with dummy rows, that is the dev
store and the demo persona cookie, which already exist.

**When to run it.** Before theming, as a gate, alongside the twin ratchet — because every branch
without a story becomes a theme defect a customer finds; and again whenever a render method
gains a parameter, because a new optional parameter is a new unwritten story by definition. The
cheapest ratchet: a test that, per page class, counts parameters passed non-default across all
fixtures and refuses to go down.

**Words for the finding** (S22.1 applies): *"the account gate has no story"*, *"the order page
renders four of seventeen props"*, *"the pending-transfer story is mislabelled"*, *"the redeem
page has no component, so no story is possible"*.

### S22 report line

Report line format: `S22 — F flows; St steps × O outcomes × Au audiences = Nc cells, money paths at full depth and the rest pairwise (say which); K OK, G GAP, U UNVERIFIED; action loops Lw walked, Lb ambiguous / not closed; render guards found Rg, with a fixture Rf of Rg, of which Rt are hand-drawn twins (each UNVERIFIED); per page class, render parameters P / passed non-default by any fixture Q (S22.8), branches dispositioned story Bs / render-test Br / none Bn with reasons, mislabelled stories M, hub rows with a dead pointer Hd, templates with no page class Tn; enum state coverage Es/Es', transition coverage Et/Et'; provider codes C across Ck surface kinds; caught Ca, classified Cl, raised Cr, closable Cx, designed Cd; outcomes needing follow-up that are only logged: Lo (each HIGH); environment mode switch: <path:line | NONE>.`

*Step 6, from a six-day blind spot (2026-09-18).* **Assert the linked assets, not only the page.**
An admin panel served every page with a 200 and every stylesheet with a 403 for six days: the
root of the install had moved and every derived asset URL landed under a directory the web server
denies on purpose. Every test and every headless walk read the page's markup and status; none
fetched what the markup linked. A rendering walk on a surface people use ends by fetching every
`<link rel="stylesheet">` and `<script src>` the page emits and holding each to a 200 — the page
is not rendered until what it links arrives. Cheap to add (one loop over the HTML), and the only
check that sees a page that is technically served and practically unusable.

*Step 7, from the same morning (2026-09-18).* **Run the surface, then read it.** S22's grid is
filled from source: which class renders which state. It was filled correctly for a shop whose
every preview loaded the wrong stylesheets, whose admin had no stylesheet at all, and whose
invoice desk answered 500 on the data the operator sees — three findings, zero of them visible
to reading, all three visible to one logged-in script that fetches every listed surface and
what it links (SKILL.md, the runtime walk, now with a receipt line in the report). A cell is
`OK` in this grid only after the walk fetched it; before that it is `RENDERS-IN-SOURCE`, which
is the honest name for what reading proves.

### S22.9 — A rendered button is not a wired control; grep every `data-action=` for its handler (2026-09-20)

A surface can pass every earlier test in this sweep — it exists, it is reachable, it says what happened, it says what to do next — and still be a dead control if the button meant to *do* the next thing has nothing behind it, and nothing about reading the page shows the wiring is missing. A shop's Payment + delivery providers page rendered two buttons on every gateway card, `Test connection` and `Start taking real payments`, each a `data-action` attribute with no JavaScript handler and no server route reading it; the one method that would actually switch a gateway from sandbox to live money was unit-tested in isolation and called by nothing in the running app. The page read as finished — copy, layout, every state accounted for — because the defect is invisible to source review of the page itself; it only shows up by grepping the *other* end. **For every admin and customer surface in scope, grep every `data-action=`, `type="button"`, `onclick=` or the framework's equivalent for the handler that consumes it**, the same way S5 traces a setting to its runtime reader — a button is a control, and this is its consumer-side check. A control the owner will press on the day they go live, that does nothing, is worse than none: a refusal that explains itself teaches people to trust refusals; a button that silently does nothing teaches them to distrust every button on the page, on the money screen where trust matters most.
