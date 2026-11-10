#!/usr/bin/env python3
"""The skill's own score, read from tests/RUNS.md - and the gate the RUNBOOK states in prose.

    python tools/score.py            # print the newest scored row as one line
    python tools/score.py --gate     # exit 1 when the commit under test fails on any fixture it was run on
    python tools/score.py --badge    # a Markdown badge line for the README
    python tools/score.py --runtime  # print the newest runtime row (what the run RAN, not found)
    python tools/score.py --corpus   # the corpus table: ground truth nobody planted

A doctrine change ships only if the fixture run scores no worse than the last one (RUNBOOK
step 6). Written down, that rule was skipped the first day seven edits landed before the run
started; a rule a hook can run is a rule that holds (S8: a written test is not a run test).
The score is hits minus misses, on the same fixture; "near" counts half and a false positive
counts against. Rows with no numbers (the placeholder row) are ignored.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RUNS = Path(__file__).resolve().parent.parent / "tests" / "RUNS.md"


def runtime_rows() -> list[dict]:
    """Rows of the second table in RUNS.md: what a run executed, not what it found.

    Added 2026-09-24. The first table scores reading; a doctrine that asks for ladders, probes
    and an evidence ledger and never measures them is scoring the half that was easy to score.
    """
    text = RUNS.read_text(encoding="utf-8")
    if "## Runtime evidence" not in text:
        return []
    out = []
    section = text.split("## Runtime evidence", 1)[1]
    section = section.split(chr(10) + "## ", 1)[0]   # stop at the next heading, not at EOF
    for line in section.splitlines():
        if not line.startswith("| 20"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 7:
            continue
        try:
            unproved = int(re.match(r"\d+", cells[6]).group())
        except (AttributeError, ValueError):
            continue
        out.append({
            "date": cells[0], "fixture": cells[1], "ladders": cells[2],
            "adversarial": cells[3], "probes": cells[4], "ledger": cells[5],
            "pass_without_artefact": unproved,
        })
    return out


RUNTIME_SINCE = "2026-09-24"


def model_of(runtime: str) -> str:
    """Which model produced a row. A doctrine regression is a drop against the same one.

    Added 2026-09-24, when the first Sonnet rows made both gates fail by being compared against
    Opus rows on the same fixture - a model comparison wearing a regression's clothes.
    """
    low = runtime.lower()
    if "paired" in low:
        return "paired"
    for name in ("opus", "sonnet", "haiku", "fable", "codex", "gpt"):
        if name in low:
            return name
    if "live" in low:
        return "live"
    return "unknown"


CHEAP = ("sonnet", "haiku")


def instrument_of(runtime: str) -> str:
    """Which instrument ran a row: the headless launcher (cia's cold_run.py) or a cold subagent.

    Added 2026-11-09, after a red gate - said plainly, because a rule added after a failure needs
    its evidence to predate the failure. It does: the same doctrine (`e4225af`) scored 4 in a cold
    subagent and 3.5 on the launcher (runs G, H), so a launcher row judged against subagent floors
    reads half a row of instrument as a regression - the model comparison of model_of, again.
    """
    return "harness" if "harness" in runtime.lower() else "agent"


def corpus_rows() -> list[dict]:
    """Rows of the corpus table: real repositories, audited at the commit before a real fix.

    Added 2026-09-24. The fixture score measures whether the skill finds defects its own author
    planted, which is close to a tautology. These rows measure whether it finds a defect a
    maintainer had to fix, chosen by somebody else, in code nobody wrote for this harness.
    """
    text = RUNS.read_text(encoding="utf-8")
    if "## Corpus" not in text:
        return []
    out = []
    section = text.split("## Corpus", 1)[1]
    section = section.split(chr(10) + "## ", 1)[0]   # stop at the next heading; the cost table is not the corpus
    for line in section.splitlines():
        if not line.startswith("| 20"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        out.append({"date": cells[0], "entry": cells[1],
                    "verdict": cells[2].upper().strip("* "),
                    "note": cells[-1]})
    return out


def fixture_of(tier: str) -> str:
    """Which harness a row was scored on.

    Added 2026-09-24 with the live fixture. The gate compares like with like: a run on a
    runnable shop and a run on a source tree measure different things, and comparing their
    scores would either block an honest first baseline or hide a real regression behind a
    higher number from the other harness. The RUNS row names its fixture in the tier cell.
    """
    low = tier.lower()
    # Longest first: "fixture-shop-node" contains "fixture-shop", and matching the shorter one
    # compared the node fixture against the read fixture's history on the day it was added.
    for name in ("fixture-shop-live", "fixture-shop-node", "fixture-service", "fixture-shop"):
        if name in low:
            return name
    return "default"


def commit_of(cell: str) -> str:
    """The skill commit a row measured: the first backticked hex token, else the commit cell's first word."""
    m = re.search(r"`?([0-9a-f]{7})[0-9a-f]*`?", cell)
    return m.group(1) if m else cell.strip().split(" ")[0]


# Half a row: one near or unanchored slip, the smallest unit the answer keys score. Ported from cia
# (2026-11-09), where six sonnet rows varied by about this much and every half-row was a reporting slip.
NOISE = 0.5
# The floor's baseline: the MEDIAN of the last RECENT live per-commit means, bounded DRIFT under the best
# ever. Ported from cia (2026-11-09), where the best-ever floor ratcheted up on one lucky pair and then
# failed about half of neutral commits; the median does not chase luck, DRIFT stops it sliding down.
RECENT = 5
DRIFT = 1.0
# Two runs within one row under the floor earn ONE second stage of two more runs, gated on the four-run mean.
# Ported from cia (2026-11-10): one seat's attention can cost a row on a neutral commit; any further stage
# would be sampling until it passes.
SECOND_STAGE = 1.0

# The per-commit rule starts here. Every earlier commit was scored under the old newest-vs-previous rule,
# one run each, and passed it; judging those rows by a rule written later would block every push on
# history nobody can re-run. They still count as the floor.
GATE_SINCE = "2026-11-09"


MISSED = re.compile(r"missed:\s*([^.;|*]+)", re.I)
ROW_ID = re.compile(r"row\s+\d+|#?\w+")   # `row 10`, `E8`, `#15`: what a key calls a row


def missed_of(note: str):
    """Row ids from a `missed: L9, #15` tag in the note, as a set; None when there is no tag."""
    m = MISSED.search(note)
    if not m:
        return None
    # The id alone: `E8 (the overlap is noted, not filed)` and `E8` are one row. Compared as whole
    # strings, two runs that both missed it shared nothing, and the gate passed a row every run lost.
    # shortcut: a comma inside a parenthesis leaves a stray word as an id, which can only add a block.
    ids = (ROW_ID.match(x.strip().lower()) for x in m.group(1).split(","))
    return {" ".join(i.group().split()) for i in ids if i}


def doctrine_misses(group: list[dict]) -> str:
    """What blocks a commit: any false positive, an untagged miss, or a row EVERY run on it missed.

    Ported from cia (its rule since 2026-11-09) on 2026-11-10. Before this, one run's miss blocked here,
    so a row a sound run finds most of the time made the gate a coin flip on a sound commit. A row one run
    missed and its paired run found still costs a row in the mean; a row lost by every run is doctrine and
    blocks. Recorded honestly: ported while a live-fixture pair (L9 missed by one run, found by the other)
    was the open case, and before the runs on the next commit."""
    false = [r for r in group if r["false"]]
    if false:
        return f"a run has {false[-1]['false']} false positive"
    dirty = [r for r in group if r["miss"]]
    if not dirty:
        return ""
    if any(not r.get("missed") for r in dirty):   # no tag, or a tag naming no row: both are unreadable
        return f"a run has {dirty[-1]['miss']} miss with no `missed:` tag naming the rows"
    common = set.intersection(*[(r.get("missed") or set()) for r in group])
    return f"every run missed {', '.join(sorted(common))}" if common else ""


def audit_gate(rs: list[dict]) -> int:
    """Per-commit gate, once per fixture the commit under test was run on. A false positive, an untagged
    miss and a row every run missed are doctrine: zero tolerance (doctrine_misses). Half-rows are noise: the mean of at least two runs on the commit under
    test must stay within NOISE of the median of the last RECENT live per-commit means on the same
    fixture, model and instrument, and never more than DRIFT under the best ever.

    The trap this loop closes (2026-11-10): the gate judged only the fixture of the newest row, so the
    order rows were written in decided which fixture was checked, and a fixture recorded first was
    never examined at all. cia's gate has run per fixture since 2026-11-09."""
    live = [r for r in rs if not r.get("reverted")]
    if not live:
        print("gate: every scored run is on a reverted commit - nothing under test.")
        return 0
    token = live[-1]["token"]
    fixtures = list(dict.fromkeys(r["fixture"] for r in live if r["token"] == token))
    return max(_gate_one(rs, [r for r in live if r["token"] == token and r["fixture"] == f][-1])
               for f in fixtures)


def _gate_one(rs: list[dict], last: dict) -> int:
    """The gate for one fixture: `last` is the newest live row of the commit under test on it."""
    if last["date"] < GATE_SINCE:
        print(f"gate: the newest live run ({last['date']}, {last['token']}) predates the per-commit rule "
              f"({GATE_SINCE}) and passed the rule of its day - nothing new under test.")
        return 0
    pool = [r for r in rs if r["fixture"] == last["fixture"] and r["model"] == last["model"]
            and r.get("instrument") == last.get("instrument")]
    group = [r for r in pool if r["token"] == last["token"]]
    # A commit is judged only against what was measured before it. After a revert the shipped commit is
    # the newest live one, and later reverted experiments must not raise its floor or its miss bar.
    first = next(i for i, r in enumerate(rs) if r["token"] == last["token"])
    earlier = [r for r in rs[:first] if r in pool]
    # The miss rule asks whether the fixture's rows are findable at all, which any clean run proves on
    # any model or instrument; so it is not pooled, and it runs before the first-commit exit (as in cia).
    # Only a clean run recorded BEFORE the commit under test makes its misses a regression (as in cia,
    # 2026-11-09): a clean run on a later, reverted commit would otherwise hold the still-shipped commit
    # to a standard it was never measured against and block every push.
    findable = [r for r in rs[:first] if r["fixture"] == last["fixture"]]
    if any(r["miss"] == 0 and r["false"] == 0 for r in findable):
        why = doctrine_misses(group)
        if why:
            print(f"GATE: on {last['token']}, {why}, on {last['fixture']}, where an earlier run had none. "
                  f"A miss the paired run did not make up for is doctrine, never noise (RUNBOOK step 6).",
                  file=sys.stderr)
            return 1
    if not earlier:
        print(f"gate: {last['token']} is the first scored commit on {last['fixture']} with {last['model']} - "
              f"a baseline. Recorded, not blocked.")
        return 0
    if len(group) < 2:
        print(f"GATE: {last['token']} has one scored run on {last['fixture']} with {last['model']}. One run is a "
              f"sample - run again, then gate on the mean (RUNBOOK step 6).", file=sys.stderr)
        return 1
    if len(group) not in (2, 4):
        # Two runs, or four after one second stage: a commit is never sampled until it passes (optional stopping).
        print(f"GATE: {last['token']} has {len(group)} scored runs on {last['fixture']}. The gate reads two, or four "
              f"after one second stage (RUNBOOK step 6); a third stage is optional stopping.", file=sys.stderr)
        return 1
    best, baseline = floor_parts(earlier)
    floor = max(baseline - NOISE, best - DRIFT)
    mean = sum(r["score"] for r in group) / len(group)
    why = f"median of the last {RECENT} live per-commit means {baseline:g}, best ever {best:g}"
    if mean < floor:
        second = len(group) == 2 and floor - mean <= SECOND_STAGE
        print(f"GATE: {last['token']} scores a mean of {mean:g} over {len(group)} runs, below the floor "
              f"{floor:g} ({why}). "
              + ("Within one row: run it twice more, once, and gate on the four-run mean (RUNBOOK step 6)."
                 if second else "Fix the doctrine or the fixture, run again, then push."), file=sys.stderr)
        return 1
    # Say what was checked, and where: a row one run missed and its pair found passes (doctrine_misses),
    # so "no miss" over such a pair claimed more than the gate knows (cia's wording, same reason).
    misses = "no row missed by every run" if any(r["miss"] for r in group) else "no miss"
    print(f"gate: {last['token']} on {last['fixture']}: mean {mean:g} over {len(group)} runs, floor {floor:g} "
          f"({why}); {misses}, no false positive.")
    return 0


def floor_parts(earlier: list[dict]) -> tuple[float, float]:
    """(best per-commit mean ever, median of the last RECENT live per-commit means), in row order.
    Reverted commits bound drift through the best but do not set the baseline."""
    means: dict[str, list[float]] = {}
    live: list[str] = []
    for r in earlier:
        means.setdefault(r["token"], []).append(r["score"])
        if not r.get("reverted") and r["token"] not in live:
            live.append(r["token"])
    avg = {t: sum(v) / len(v) for t, v in means.items()}
    best = max(avg.values())
    recent = sorted(avg[t] for t in live[-RECENT:]) or [best]
    mid = len(recent) // 2
    return best, (recent[mid] if len(recent) % 2 else (recent[mid - 1] + recent[mid]) / 2)


def rows() -> list[dict]:
    out = []
    for line in RUNS.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| 20"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 9:
            continue
        try:
            hits = int(re.match(r"\d+", cells[4]).group())
            near = int(re.match(r"\d+", cells[5]).group())
            miss = int(re.match(r"\d+", cells[6]).group())
            false = int(re.match(r"\d+", cells[7]).group())
        except (AttributeError, ValueError):
            continue
        out.append({
            "date": cells[0], "commit": cells[1][:40], "tier": cells[3][:60],
            "hits": hits, "near": near, "miss": miss, "false": false,
            "score": hits + 0.5 * near - miss - false,
            "fixture": fixture_of(cells[3]),
            "model": model_of(cells[2]),
            "instrument": instrument_of(cells[2]),
            "token": commit_of(cells[1]),
            # A row on a reverted commit measured doctrine that no longer ships: history and floor, never under test.
            "reverted": "reverted" in cells[1].lower(),
            # The rows a run missed, when the scorer tags them in the note (`missed: N3, #15`). None when
            # untagged: the paired-miss rule then cannot tell variance from doctrine and blocks.
            "missed": missed_of(cells[9]) if len(cells) > 9 else None,
        })
    return out


def line(r: dict) -> str:
    return (f"{r['date']} {r['commit']}: hits {r['hits']} / near {r['near']} / miss {r['miss']} / "
            f"false+ {r['false']} -> score {r['score']:g}")


def main() -> int:
    rs = rows()
    if not rs:
        print("score: no scored run in tests/RUNS.md - the gate has nothing to hold", file=sys.stderr)
        return 1
    if "--badge" in sys.argv:
        r = rs[-1]
        print(f"**Last scored fixture run:** {r['date']} - {r['hits']} hits / {r['near']} near / "
              f"{r['miss']} miss / {r['false']} false positives (`python tools/score.py`)")
        return 0
    rt = runtime_rows()
    if "--runtime" in sys.argv:
        if not rt:
            print("runtime: no runtime-scored run in tests/RUNS.md - the running half is unmeasured",
                  file=sys.stderr)
            return 1
        r = rt[-1]
        print(f"runtime: {r['date']} {r['fixture']}: ladders {r['ladders']} / adversarial {r['adversarial']} / "
              f"probes {r['probes']} / ledger {r['ledger']} / PASS without artefact {r['pass_without_artefact']}")
        return 0

    print(f"score: [{rs[-1]['fixture']} / {rs[-1]['model']}] " + line(rs[-1]))

    # A doctrine that scores well only on the expensive model works on one budget. Say the cheap
    # number next to the expensive one, every time, so the gap is never invisible.
    cheap = [r for r in rs if r["model"] in CHEAP]
    if cheap:
        c = cheap[-1]
        dear = [r for r in rs if r["fixture"] == c["fixture"] and r["model"] not in CHEAP + ("unknown",)]
        gap = f", against {dear[-1]['score']:g} on {dear[-1]['model']}" if dear else ""
        print(f"cheap model: {c['date']} [{c['fixture']} / {c['model']}] scored {c['score']:g}{gap}")

    cr = corpus_rows()
    if "--corpus" in sys.argv:
        if not cr:
            print("corpus: no entries scored yet - the ground truth nobody planted is still empty,"
                  " and an empty corpus proves nothing (tests/corpus/README.md)", file=sys.stderr)
            return 1
        hits = sum(1 for r in cr if r["verdict"].startswith("HIT"))
        print(f"corpus: {hits} hit / {len(cr) - hits} other, of {len(cr)} scored entries")
        for r in cr:
            print(f"  {r['date']}  {r['verdict']:12} {r['entry']}")
        return 0
    if cr:
        hits = sum(1 for r in cr if r["verdict"].startswith("HIT"))
        print(f"corpus: {hits}/{len(cr)} real fix commits found before the fix")
    if rt:
        r = rt[-1]
        print(f"runtime: {r['date']} {r['fixture']}: ladders {r['ladders']} / probes {r['probes']} / "
              f"ledger {r['ledger']} / PASS without artefact {r['pass_without_artefact']}")

    if "--gate" in sys.argv:
        if audit_gate(rs):
            return 1

        # A PASS the run cannot point at is the one thing the evidence ledger forbids
        # (reporting.md). It is scored as a false positive and it blocks the push.
        bad = [r for r in rt if r["pass_without_artefact"] > 0]
        if bad:
            r = bad[-1]
            print(f"GATE: the runtime row of {r['date']} carries {r['pass_without_artefact']} ledger PASS row(s) with "
                  f"no artefact. Reading never produces PASS (reporting.md, the evidence ledger). Either the artefact "
                  f"exists and is uncited, or the row is UNVERIFIED.", file=sys.stderr)
            return 1

        # From RUNTIME_SINCE on, a scored run with nothing recorded about what it executed is a
        # code review, and the harness says so instead of quietly scoring half the doctrine.
        newest = rs[-1]
        if newest["date"] >= RUNTIME_SINCE and not any(r["date"] == newest["date"] for r in rt):
            print(f"GATE: the scored run of {newest['date']} has no row in the runtime table. Since {RUNTIME_SINCE} a "
                  f"run also records what it RAN - ladders, adversarial rows, probes, ledger (RUNBOOK, the live "
                  f"fixture run). Add the row, or record it as a code review.", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    if {"-h", "--help"} & set(sys.argv[1:]):   # answered here, before main(): --help must never run the job
        sys.stdout.reconfigure(encoding="utf-8")
        print(__doc__)
        sys.exit(0)
    sys.exit(main())
