# The build standard — what production-ready means, and the proof each property needs

Everything else in this skill answers *"is this wrong?"*. This answers the question that comes
first in real work and that an auditor is uniquely placed to answer: **"what does right look
like, and how would I know?"**

It exists because of an objection worth taking seriously — that an AI cannot write a shop that
handles money correctly. The objection is right about one thing: code that *looks* correct is
cheap, and looking correct is exactly what an LLM is good at. The answer is not to write more
careful-sounding code. It is to name the properties an operation must have, and to **prove each
one by running something that fails when the property is absent**.

`tools/reference/stock_reduction.php` is that, for the operation shops get wrong most often, and
`tools/reference/prove_stock_reduction.php` proves all four properties in eight checks. Read the
proof before the implementation: it is the part that cannot be faked by prose.

---

## §1 — The four properties of a primary-path write

Any operation that moves money, stock, or an entitlement needs all four. Three out of four is a
shop that loses money slowly.

| # | Property | What it means | The mechanism | The proof that it holds |
|---|---|---|---|---|
| 1 | **Atomic** | every write of one operation lands together or not at all | one explicit transaction, rollback on every failure path | **inject a fault after the first write and before commit**, then read the store: the first write must be gone |
| 2 | **Race-free** | two concurrent callers cannot both win | the predicate lives **in** the `UPDATE`, and the affected-row count decides | fire the operation twice concurrently against a row where only one may win; read the row after |
| 3 | **Idempotent** | a retry does not re-apply | a caller-supplied key under a **UNIQUE constraint**, written inside the same transaction | send the same key twice; the second returns the first answer and changes nothing |
| 4 | **Loud** | nothing is swallowed | a refusal is a **returned value**; a fault is an **exception** — and the two are never the same type | assert both: a refusal returns a named outcome, a fault propagates |

### 1.1 Atomic

One `BEGIN` … `COMMIT`, and a `ROLLBACK` on every path out. The rollback's own failure is
attached to the exception rather than discarded, because a transaction that will not roll back is
the worst news the function can carry.

**The proof is the part teams skip.** A happy-path test passes against an implementation with no
transaction at all. The only check that separates atomic from transaction-shaped is a fault
injected *after* the first write: drop the table the second write needs, run the operation, and
assert the first write is gone. The reference proves exactly this, and it is check seven.

### 1.2 Race-free

```sql
UPDATE products SET stock = stock - ? WHERE sku = ? AND stock >= ?
```

The `SELECT` above it may inform the message. It must not authorise the write. Two callers, one
unit: the database arbitrates, one `UPDATE` matches, the other matches nothing, and `rowCount()`
is what the code reads — not the value it read a moment earlier.

**`BEGIN IMMEDIATE` (or `SELECT … FOR UPDATE`, or the engine's equivalent) takes the write lock
up front** rather than on first write, so two writers serialise at the door instead of colliding
half-way through.

Two corollaries the corpus taught, both from real fix commits:

- **An absolute write is worse than a wrong write.** `SET stock = ?` with a value computed in the
  application loses the loser's update *and* leaves a plausible number behind, so the oversell is
  invisible afterwards. `SET stock = stock - ?` at least leaves arithmetic that can be audited.
- **A lock documented as atomic is not atomic.** A corpus entry's lock helper was a
  read-modify-write on the backend the app selected by default, while its own comment claimed
  `hincrby` was "guaranteed atomic on every backend". Read the storage adapter, not the helper.

### 1.3 Idempotent

The key is the caller's, not the server's, and it identifies **the intent** — a cart, a checkout
attempt, a provider's event id — never the attempt. Three rules:

1. **The UNIQUE constraint is the arbiter**, not a `SELECT … WHERE key = ?` before the write. A
   check outside the write is a prediction (S2); the constraint is a decision. Keep the read as a
   fast path if you like, but the insert must be able to lose.
2. **Record the refusal too.** A replayed refusal must refuse identically. An implementation that
   records only successes turns a retry of "insufficient stock" into a fresh attempt that may
   succeed — and the customer is charged for a decision the shop already made.
3. **The key's identity is the provider's, when the provider supplies one** — and it is sometimes
   a *pair*. Adyen's duplicate is `eventCode` + `pspReference` with a differing `eventDate`
   (`adyen-onboarding.md` §3); a handler keyed on one field treats a duplicate as new.

### 1.4 Loud

**A refusal is a value. A fault is an exception. Collapsing the two is how a shop records a sale
it did not make.**

- "Not enough stock" is a business outcome: return it, named, in a type the caller must handle.
- "The database is unreachable" is a fault: roll back and raise. Do not return `false`, `null`,
  or an empty result that a caller will read as "no".
- **A caller bug is neither**: `qty = -3` is not a refusal to be recorded, it is an argument that
  should never have reached the SQL. Throw immediately — this is the under-quantity row
  (`browser-walks.md` §12) at the function boundary, and two independent audit runs missed it in
  a shop that accepted it.
- **The log level is part of the posture.** `log.debug` on a failure path is silence with a
  receipt, because production runs at INFO (`sweeps.md`, S3). If the catch exists to record
  something, record it where a person will see it.
- **One documented exception**: Adyen instructs merchants to acknowledge *before* processing.
  Read `adyen-onboarding.md` §1 before grading any `catch` on an Adyen notify path.

---

## §2 — Beyond the four: what the operation still owes

The four properties make the write *correct*. They do not make the shop *viable*, and an audit
that stops at four has stopped early:

- **An explanation.** A movement row that commits with the number it explains. "Why is stock 3?"
  is a question somebody will ask six months later, and `stock = 3` is not an answer.
- **A surface.** Every outcome — including the refusal — reaches a screen a person can act on
  (S22). A refusal that only the HTTP status knows about is silent to the customer and invisible
  to the operator.
- **A boundary.** The function decides what is true; it does not decide *who may ask*. Authorisation
  belongs to the caller, and a corpus entry showed why: a basket module where every handler took
  the id from the request and none established ownership.
- **A test that can fail.** The reference's proof is eight checks, and the two that matter most —
  the concurrent race and the injected fault — are the two a green suite most often lacks.

---

## §3 — Using this in build mode

When the request is *"write this"* rather than *"audit this"*:

1. **Name the operation's primary quantity and its observers** (`browser-walks.md` §12). If you
   cannot say what number must be right afterwards, nothing below matters yet.
2. **Write the proof first.** The four checks in §1's last column, against the operation you are
   about to write. They must fail before it exists.
3. **Write the operation** to the mechanisms in §1.
4. **Run the proof**, and paste its output. A property nobody can point at is a property nobody
   has — the same rule this skill applies to its own reference (`prove_stock_reduction.php`) and
   to its own score.
5. **Fill the evidence ledger row** (`reporting.md` §29a) from the proof's artefact, not from the
   implementation's comments. Reading never produces PASS, and that includes reading code you
   wrote yourself an hour ago.

**On the objection this file answers.** "An AI cannot write a production e-commerce backend" is
true of any author — human or otherwise — who writes plausible code and ships it unproven. It is
false where the properties are named and each one is demonstrated by something that fails when
the property is absent. The difference is not the author. It is whether the proof exists, and
whether anyone ran it.

---

**Reading receipt: _a property nobody can prove is a property nobody has_.** Quote this phrase on
the report's receipts line (Step 6 in cia, Step 7 in ecommerce-cia) to show this file was read
rather than inferred from the skill's index. It appears nowhere else.
