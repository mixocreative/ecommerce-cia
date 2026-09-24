#!/usr/bin/env python3
"""The skill's own score, read from tests/RUNS.md - and the gate the RUNBOOK states in prose.

    python tools/score.py            # print the newest scored row as one line
    python tools/score.py --gate     # exit 1 when the newest row scores below the row before it
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
    for line in text.split("## Runtime evidence", 1)[1].splitlines():
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
    for name in ("fixture-shop-live", "fixture-service", "fixture-shop"):
        if name in low:
            return name
    return "default"


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
        last = rs[-1]
        same = [r for r in rs[:-1]
                if r["fixture"] == last["fixture"] and r["model"] == last["model"]]
        if not same:
            print(f"gate: {last['date']} is the first scored run on {last['fixture']} with "
                  f"{last['model']} - a baseline, nothing to compare it against. Recorded, not blocked.")
        if same:
            prev = same[-1]
            if last["score"] < prev["score"] or last["miss"] > prev["miss"]:
                print(f"GATE: the newest run on {last['fixture']} with {last['model']} ({last['score']:g}, "
                      f"{last['miss']} miss) scores below the previous run on the same fixture with the same model "
                      f"({prev['date']}: {prev['score']:g}, {prev['miss']} miss). "
                      f"A doctrine change that lowers the score does not ship "
                      f"(RUNBOOK step 6). Fix the doctrine or the fixture, run again, then push.", file=sys.stderr)
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
    sys.exit(main())
