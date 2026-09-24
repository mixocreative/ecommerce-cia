#!/usr/bin/env python3
"""Every reference file carries a reading receipt, and every receipt is unique.

    python tools/receipts.py          # report
    python tools/receipts.py --gate   # exit 1 if a file is missing one, or two share a phrase

Why this is a tool and not a habit: on the day receipts were introduced, four reference files
got one and the rest did not. A cold run read `theory.md`, looked for its receipt, found none,
and reported that plainly - which was the right behaviour and also the proof that a file with no
receipt is indistinguishable from a file nobody opened. That is the exact confusion receipts
exist to remove, so the rule needs an enforcer rather than an intention.

A phrase must also be unique: two files sharing one means a run can quote a receipt for a file
it never read, which turns the instrument into scaffolding for a claim.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REFERENCES = HERE / "references"
PATTERN = re.compile(r"\*\*Reading receipt: _(.+?)_\.\*\*")


def scan() -> tuple[dict[str, str], list[str]]:
    found: dict[str, str] = {}
    missing: list[str] = []
    for path in sorted(REFERENCES.glob("*.md")):
        m = PATTERN.search(path.read_text(encoding="utf-8"))
        if m:
            found[path.name] = m.group(1)
        else:
            missing.append(path.name)
    return found, missing


def main() -> int:
    if not REFERENCES.is_dir():
        print(f"no references directory at {REFERENCES}", file=sys.stderr)
        return 1

    found, missing = scan()
    for name, phrase in found.items():
        print(f"  {name:28} {phrase}")

    problems = 0
    for name in missing:
        print(f"  {name:28} *** NO RECEIPT ***")
        problems += 1

    seen: dict[str, str] = {}
    for name, phrase in found.items():
        if phrase in seen:
            print(f"  DUPLICATE PHRASE: {name} and {seen[phrase]} both say {phrase!r}")
            problems += 1
        seen[phrase] = name

    print(f"\n{len(found)} reference files with a receipt, {len(missing)} without.")
    if problems and "--gate" in sys.argv:
        print("GATE: a reference file with no receipt cannot be told apart from one nobody opened, "
              "and a shared phrase lets a run quote a file it never read. Fix before pushing.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
