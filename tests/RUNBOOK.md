# Testing `ecommerce-cia` — the fixture run

The skill's own S8 applies to the skill: a doctrine edit nobody has run is a written test, not a run one. This directory is the harness. It is deliberately small — a run takes an agent 20–40 minutes at Screen tier — so it can be run after **every** change to `SKILL.md` or `references/`.

## What is here

```
fixture-shop/              a PHP shop with 11 planted defects and 2 correct controls — audited by READING
fixture-shop-live/         a runnable PHP+sqlite shop, 9 defects and 7 controls — audited by RUNNING
fixture-shop-node/         the same defect classes in Node 22 + node:sqlite — audited by RUNNING, on another stack
EXPECTED-fixture-shop.md      the answer key for the read fixture — kept OUTSIDE the fixture on purpose
EXPECTED-fixture-shop-live.md the answer key for the live fixture, same rule
verify-fixture-shop-live.py   proves every planted live row still reproduces; run it before scoring
RUNS.md                    one row per run (append; never rewrite history)
```

**Two fixtures, because the skill makes two kinds of claim.** Everything the read fixture scores
is found by reading source. Everything §0.6 Steps 4–6 and `browser-walks.md` §§12–14 ask for is
found by running a system, and for four months this harness measured none of it — the
instrument scored the half of the doctrine that was easiest to score, which is S20's blind
detector filed against the audit itself.

## Procedure

1. **Fresh session.** Open a new Claude Code (or Codex) session with `tests/fixture-shop` as the working directory. No project memory, no CLAUDE.md — the fixture must be audited cold, the way a new shop would be.
2. **Trigger.** Say exactly: `pre-launch audit, Screen tier`. Two things are under test before any sweep runs: the §0.3a gate must PASS on criterion 1 (`src/Gateway/`) and the discovery block must say so; and the run must declare its tier.
3. **Let it run.** Do not answer questions the skill should answer itself (§0.8). If it asks the owner for something the fixture contains, that is a finding against the skill — record it.
4. **Score against `EXPECTED-fixture-shop.md`** (the scorer reads it; the auditor never does — it sits beside this file, outside the fixture, because two cold runs on 2026-09-19 leaked it through the S6 deferred-work grep the doctrine itself prescribes over `tests/`; an answer key inside the audited tree is a key the auditor will hit)**:**
   - **Hit** — the planted row is reported under the right sweep, with a `path:line` inside the cited range and a grade at or above the minimum.
   - **Near** — right site, wrong sweep or grade one level low. Counts half.
   - **Miss** — not reported, or reported only as a count with no path.
   - **False positive** — a finding at a site with no planted defect. List each; decide whether the fixture is wrong (fix the fixture and re-run) or the doctrine is (fix the doctrine).
   - **Control misfiled** — a verified control reported as a defect. Counts as a miss.
   - **Vacuous line** — a sweep line with a count but no paths, or paths but no quoted line (§0.9). Counts as a miss for that sweep even if the finding was elsewhere reported.
5. **Record** a row in `RUNS.md`: date, commit of the skill, runtime (Claude / Codex), tier, hits / near / miss / false positives, minutes, and the one sentence that explains any miss.
6. **Gate for the change** (`python tools/score.py --gate`; installed as a pre-push hook by `tools/install-hooks.sh`). A change to the skill ships only if the run scores **no worse** than the previous row on hits and misses. A new miss is a regression in the doctrine or in the packaging (the agent did not read the reference file) — find which before committing.

## The live fixture run (`fixture-shop-live`)

Same shape, different question: not *did the auditor find the defect in the source* but *did the
auditor run anything, and did it believe the right observer*. Most of these defects read
correctly. Every one of them is visible in under a minute to somebody who actually buys
something.

1. **Prove the fixture first.** `python tests/verify-fixture-shop-live.py --serve` must print
   `OK: 10 rows reproduce`. A key that no longer matches the fixture scores the auditor against
   fiction (§0.11 applied to the harness).
2. **Fresh session** with `tests/fixture-shop-live` as the working directory. The shop is not
   running; starting it is rung 1 of §0.8 and **the agent is expected to start it itself**. An
   auditor that asks the owner to run `php -S` has already failed one of the things under test.
3. **Trigger.** `pre-launch audit, Screen tier`.
4. **Score the eight planted rows and two controls** against `EXPECTED-fixture-shop-live.md`,
   by the same hit / near / miss / false-positive rules as above.
5. **Score the three runtime columns, which are what this fixture exists for:**
   - **Ladders** — how many state-delta ladders ran (`browser-walks.md` §12), out of the flows
     the tier owes.
   - **Adversarial rows** — how many of §12's nine, and which.
   - **Ledger** — was an evidence ledger produced, and is every PASS carrying an artefact path?
     **A ledger that reports the stock chain PASS is the fixture's central false positive**: not
     one capability in this shop can honestly be PASS, and an auditor that promotes a row from
     reading has failed the rule the ledger exists to enforce, however many defects it found.
6. **Record** a row in `RUNS.md`'s runtime table, then gate with
   `python tools/score.py --gate` as usual.

A run that files all eight defects and produces no ledger, no ladder and no probe is recorded as
what it is: a good code review of a running system nobody ran.

## The second-stack run (`fixture-shop-node`)

Same defect classes, different language. It exists to answer a question the prose could only
assert — *does this doctrine transfer, or was it written for PHP shops?* — and it is cheap,
because the answer only needs four rows.

1. `node tests/verify-fixture-shop-node.js` must print `OK: 5 rows reproduce`.
2. Fresh session with `tests/fixture-shop-node` as the working directory; `pre-launch audit,
   Screen tier`. The shop is not running; starting it is rung 1 and the agent's job.
3. Score the four defects and the one control. **The number that matters is transfer**: a run
   that scores well on `fixture-shop-live` and badly here has found a doctrine tuned to PHP, and
   that is a finding about the skill rather than about the run.
4. Record it in `RUNS.md` with `fixture-shop-node` in the tier cell, so the gate compares it
   only against its own history.

The Node fixture's control is worth reading before scoring: `crypto.timingSafeEqual` **throws**
on unequal-length inputs, so the length guard in front of it is load-bearing and its absence
would be a crash, not a weakness. An auditor that flags the guard has not read the API.

## The corpus run — ground truth nobody planted

Everything above scores the skill against defects its own author wrote for it to find, which is
close to a tautology. `tests/corpus/` is the answer: real repositories, checked out at the commit
**before** a maintainer's own fix commit, with that commit's diff as the oracle.

```
python tests/corpus/run.py list
python tests/corpus/run.py prepare <entry>     # clone at the pre-fix commit; prints the path
python tests/corpus/run.py oracle <entry>      # SCORER ONLY - never shown to a run
```

Audit the prepared path cold, at the tier the entry names, then score one question: **did the run
report the thing the next commit had to fix, for the reason the commit gives?** Record HIT, MISS
or OUT-OF-SCOPE in `RUNS.md`'s corpus table.

Three rules keep it honest: the auditor never reads `tests/corpus/`; the fix commit is the
oracle rather than anybody's reading of the code; and a miss is recorded rather than explained
away, because a miss here is the doctrine's blind spot showing itself on real code. An entry that
keeps missing is the most valuable row in the harness.

## Blind-forward validation — the mode with no oracle

The corpus above has a bias it cannot remove by growing: **every entry is a commit whose author
had already diagnosed the bug and written its name in the subject line.** The auditor never sees
that message, but the defect had still been characterised by somebody before the audit began, and
the entry was chosen *because* it had been. It measures recall on named defect classes, which is
worth measuring and is not the same as finding something nobody knew about.

`tests/corpus/forward.py` removes the chooser:

```
python tests/corpus/forward.py pick <repo-url> --back 220
   ... audit the printed path, cold, and write the findings down ...
python tests/corpus/forward.py confirm <name> --files a.ts,b.ts
```

`pick` checks a repository out at a commit well back along its first-parent chain and prints the
path and nothing else — no subject, no date, no diff, nothing about what came next. **No oracle
exists at audit time.** `confirm` then replays the project's own future: every later commit that
touched the files the audit named.

| Verdict | Meaning |
|---|---|
| **CONFIRMED-BY-FUTURE** | a later commit changes the exact thing the finding named, for the reason the finding gave. The maintainers agreed, months later, knowing nothing about this skill |
| **OPEN** | nobody has touched it. **Not a miss** — the defect may well still be there, and an audit running ahead of its project is the thing you want |
| **WRONG** | a later commit shows the finding was mistaken about the code |

This is the only measurement in the harness that can register a defect **nobody had collected**,
which is the ceiling the retrospective corpus cannot reach by any amount of growth. It is also
the only one where `OPEN` is an honest outcome rather than a hole, so read the three verdicts
together and never quote a hit rate from this table alone.

**The rule that keeps it worth anything: step two happens between the other two.** Running
`confirm` before the audit is written down is reading an answer key — one that did not exist
until you looked. The audit prompt says so, and it also forbids the auditor from running `git`
at all inside the snapshot, because the history is right there and one `git log` would end the
measurement.

### The hard rule in the prompt fences the oracle, not the doctrine

Three cold runs on 2026-09-24 opened their reports by saying they had worked from `SKILL.md`
alone, because the prompt told them not to read anything under the skills directory - and
`references/` lives there. They were right to say so, and the receipts line is why it was
visible rather than mistaken for a doctrine gap. But every one of those runs was weaker than it
needed to be, and the prompt caused it.

**What the run must not read** is the answer: `tests/corpus/entries/`, `tests/EXPECTED-*.md`,
`tests/RUNS.md`, and - in a blind-forward run - the repository's own future, which means no
`git` command at all inside the snapshot.

**What the run must read** is the doctrine: `references/*.md`, in full, per §0.13.

So phrase it as a fence around the oracle:

```
HARD RULES:
- Do not read `tests/corpus/entries/`, `tests/EXPECTED-*.md` or `tests/RUNS.md` - those hold
  the scorer's answer key.
- (blind-forward only) Do not run any `git` command and do not read `.git/`. The snapshot sits
  in the middle of the project's history on purpose; one `git log` ends the measurement.
- You MAY and SHOULD read the skill's own `references/*.md`. They are your instructions, not
  part of the audited project.
```

A run that cannot quote the receipts is a run that worked from the index. If the prompt caused
that, the prompt is the finding.

## Reading a miss

| Symptom | Usually means |
|---|---|
| Sweep line present, path absent | agent read the §0.9 index and not `references/sweeps.md` — packaging |
| Right site, wrong sweep | taxonomy wording; the two sweeps' boundaries are unclear in `sweeps.md` |
| Control filed as defect | the §29 "verified controls" habit is not binding enough in `reporting.md` |
| Asked the owner for the vendor manual | §1.4 / §0.5 discovery did not look under `docs/vendor/` |
| Reported tier but ran deeper or shallower | the tier table in Step 3 is not shaping the run |

## Paired run

Once per release of either skill, run the fixture with `run /cia and /ecommerce-cia, Screen tier`. Expected: one discovery block naming both, one map, **one** line per sweep tagged `[cia + ecommerce-cia]`, no duplicated finding, and the cia-only additions (§3 profile, §7 matrix, §8 checklist) present. Record it as a separate row with runtime `paired`.
