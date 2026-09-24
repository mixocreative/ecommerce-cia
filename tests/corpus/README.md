# The corpus — ground truth nobody planted

The fixtures measure whether the skill finds defects **I wrote for it to find**. That is the
weakest possible evidence about a real codebase, and no amount of 10/10 fixes it: the defects
planted are the defects the doctrine hunts, so the score is close to a tautology.

This harness measures something else. For each entry, a real open-source project has a commit
that **fixed a genuine integrity bug**. The corpus checks out the commit *before* the fix, runs
the audit on it cold, and asks one question:

> Did the skill report the thing the next commit had to fix?

Nobody planted it. Nobody wrote a sweep for it. The ground truth is a maintainer's own commit
message and diff, written without knowing this skill exists.

## The rules that keep it honest

1. **The auditor never sees this directory.** Same rule as the answer keys: the entry file names
   the bug. A run reads only the checked-out worktree.
2. **The fix commit is the oracle, not my reading of it.** An entry records the upstream commit
   hash, its subject line, and the files it touched. If the audit reports a defect at one of
   those files *for the reason the commit gives*, that is a hit. A defect at those files for an
   unrelated reason is not.
3. **A miss is recorded, not explained away.** The corpus exists to find the doctrine's blind
   spots; an entry that keeps missing is the most valuable row in the table.
4. **Scope is the tier's.** A Screen-tier run on a large repository cannot read everything. The
   entry records the tier and the scope given to the run, and a miss outside the declared scope
   is recorded as `out-of-scope`, which is neither a hit nor a miss but a note about the tier.

## Entry format

One YAML-ish file per entry in `entries/`, kept deliberately small:

```
repo:        https://github.com/<owner>/<name>
fix_commit:  <sha of the commit that FIXED the bug>
audit_commit: <sha of its parent - this is what gets audited>
subject:     <the fix commit's subject line, verbatim>
files:       <the files the fix touched>
class:       <the defect class, in this skill's taxonomy: S2, S3, S16, ...>
why_it_counts: <one sentence: what a hit must say>
scope:       <what the run was told to audit, if not the whole repo>
```

## Running one

```
python tests/corpus/run.py list
python tests/corpus/run.py prepare <entry>     # clone at audit_commit into a scratch worktree
python tests/corpus/run.py oracle <entry>      # show the fix diff - SCORER ONLY, never the auditor
```

Then audit the prepared worktree cold, in a fresh session, and record the result in
`RUNS.md`'s corpus table.

## Status, stated rather than implied

This harness is **new (2026-09-24)** and its value is entirely in being filled. An empty corpus
proves nothing; a corpus of three entries proves very little. The number to watch is not the hit
rate on the first few entries — it is whether the hit rate holds as entries are added by someone
who is not choosing them to flatter the instrument.
