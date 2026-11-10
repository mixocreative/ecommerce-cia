#!/usr/bin/env python3
"""Refuse to ship doctrine nobody ran: the newest commit that changed SKILL.md or references/ must have scored runs.

    python tools/untested.py          # exit 1 when the newest doctrine commit has no live row in tests/RUNS.md

Why it exists: tools/score.py --gate judges the newest commit that HAS rows. A commit that changed the
doctrine and was never run has no rows, so the gate judged the commit before it and passed, and the
pre-push hook would have shipped untested doctrine (seen in cia on 2026-11-09, commit 73d3c70, while its
runs were still going; ported here the same day). This closes that: the commit that last touched the doctrine is the one that must
have been measured.

Accepted without rows: a revert (its message says "This reverts commit" or starts with "revert"),
because it returns to doctrine the gate already measured. Debt, named: a partial revert is trusted the
same way, though the mix it leaves was never run as a whole.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCTRINE = ["SKILL.md", "references"]
RUNS = ROOT / "tests" / "RUNS.md"


def git(*args: str) -> str:
    # encoding pinned: text=True alone decodes with the locale (cp950 on a Traditional Chinese Windows),
    # and one em dash in a commit message then crashed the gate instead of answering it.
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout.strip()


def live_tokens(runs_text: str) -> set[str]:
    """Short hashes of every scored row whose commit cell does not say it was reverted."""
    out = set()
    for line in runs_text.splitlines():
        if not line.startswith("| 20"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 9 or "reverted" in cells[1].lower() or not re.match(r"\d", cells[4]):
            continue
        m = re.search(r"`([0-9a-f]{7})", cells[1])
        if m:
            out.add(m.group(1))
    return out


def verdict(commit: str, subject_and_body: str, tokens: set[str]) -> tuple[bool, str]:
    if not commit:
        return True, "no doctrine commit found (shallow clone?)"
    if commit[:7] in tokens:
        return True, f"{commit[:7]} changed the doctrine and has scored runs"
    if re.search(r"This reverts commit|^\s*revert", subject_and_body, re.I | re.M):
        return True, f"{commit[:7]} is a revert to measured doctrine"
    return False, (f"{commit[:7]} changed SKILL.md or references/ and has no live scored run in tests/RUNS.md. "
                   f"Run it (RUNBOOK steps 1-6), record the rows, then push.")


def main() -> int:
    commit = git("log", "-1", "--format=%H", "--", *DOCTRINE)
    message = git("log", "-1", "--format=%s%n%b", commit) if commit else ""
    ok, why = verdict(commit, message, live_tokens(RUNS.read_text(encoding="utf-8")))
    print(("untested: " if ok else "GATE: ") + why, file=sys.stdout if ok else sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
