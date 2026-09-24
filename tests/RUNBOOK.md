# Testing `ecommerce-cia` — the fixture run

The skill's own S8 applies to the skill: a doctrine edit nobody has run is a written test, not a run one. This directory is the harness. It is deliberately small — a run takes an agent 20–40 minutes at Screen tier — so it can be run after **every** change to `SKILL.md` or `references/`.

## What is here

```
fixture-shop/              a PHP shop with 11 planted defects and 2 correct controls — audited by READING
fixture-shop-live/         a runnable PHP+sqlite shop with 8 planted defects and 2 controls — audited by RUNNING
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
