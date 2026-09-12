# Testing `ecommerce-cia` — the fixture run

The skill's own S8 applies to the skill: a doctrine edit nobody has run is a written test, not a run one. This directory is the harness. It is deliberately small — a run takes an agent 20–40 minutes at Screen tier — so it can be run after **every** change to `SKILL.md` or `references/`.

## What is here

```
fixture-shop/              a PHP shop with 11 planted defects and 2 correct controls
fixture-shop/tests/EXPECTED.md   the answer key: sweep, path:line, minimum grade
RUNS.md                    one row per run (append; never rewrite history)
```

## Procedure

1. **Fresh session.** Open a new Claude Code (or Codex) session with `tests/fixture-shop` as the working directory. No project memory, no CLAUDE.md — the fixture must be audited cold, the way a new shop would be.
2. **Trigger.** Say exactly: `pre-launch audit, Screen tier`. Two things are under test before any sweep runs: the §0.3a gate must PASS on criterion 1 (`src/Gateway/`) and the discovery block must say so; and the run must declare its tier.
3. **Let it run.** Do not answer questions the skill should answer itself (§0.8). If it asks the owner for something the fixture contains, that is a finding against the skill — record it.
4. **Score against `EXPECTED.md`:**
   - **Hit** — the planted row is reported under the right sweep, with a `path:line` inside the cited range and a grade at or above the minimum.
   - **Near** — right site, wrong sweep or grade one level low. Counts half.
   - **Miss** — not reported, or reported only as a count with no path.
   - **False positive** — a finding at a site with no planted defect. List each; decide whether the fixture is wrong (fix the fixture and re-run) or the doctrine is (fix the doctrine).
   - **Control misfiled** — a verified control reported as a defect. Counts as a miss.
   - **Vacuous line** — a sweep line with a count but no paths, or paths but no quoted line (§0.9). Counts as a miss for that sweep even if the finding was elsewhere reported.
5. **Record** a row in `RUNS.md`: date, commit of the skill, runtime (Claude / Codex), tier, hits / near / miss / false positives, minutes, and the one sentence that explains any miss.
6. **Gate for the change.** A change to the skill ships only if the run scores **no worse** than the previous row on hits and misses. A new miss is a regression in the doctrine or in the packaging (the agent did not read the reference file) — find which before committing.

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
