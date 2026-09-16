#!/usr/bin/env python3
"""The skill's own score, read from tests/RUNS.md - and the gate the RUNBOOK states in prose.

    python tools/score.py            # print the newest scored row as one line
    python tools/score.py --gate     # exit 1 when the newest row scores below the row before it
    python tools/score.py --badge    # a Markdown badge line for the README

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
    print("score: " + line(rs[-1]))
    if "--gate" in sys.argv and len(rs) >= 2:
        prev, last = rs[-2], rs[-1]
        if last["score"] < prev["score"] or last["miss"] > prev["miss"]:
            print(f"GATE: the newest run ({last['score']:g}, {last['miss']} miss) scores below the one before "
                  f"({prev['score']:g}, {prev['miss']} miss). A doctrine change that lowers the score does not ship "
                  f"(RUNBOOK step 6). Fix the doctrine or the fixture, run again, then push.", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
