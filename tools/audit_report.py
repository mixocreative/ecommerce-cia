#!/usr/bin/env python3
"""Audit report checker: names every part of a Step 7 report that is missing, including each reference the run did not read.

    python tools/audit_report.py check <file|->

Run it from the skill directory on the run's `ecommerce-cia-audit-report.md` (SKILL Step 7) before the
reply; `check -` reads the report from stdin instead.

Why this is a tool and not more wording (ported from cia, 2026-11-10): cold runs of this skill quoted 0
to 6 of its reading receipts and a fixture's score swung 4.5 to 9 on doctrine that did not touch it.
cia had the same collapse and fixed it with this checker: a receipt is a phrase that appears once in
one reference, so a run that did not reach a file cannot pass by guessing, and the MISSING line names
the file to read.

Shape, never truth: the scorer still judges the findings. The trap when extending it: no check may name
a fixture's file, function or defect.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from receipts import scan  # noqa: E402  the receipt of each reference, read from the references

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Read on every Screen audit (SKILL Step 3 order, Step 5's walk, and the two before the first finding).
# Conditional files (an adapter, an onboarding guide, classes.md, build-standard.md) are not demanded.
ALWAYS = ("reference-systems.md", "wiring-walk.md", "theory.md", "sweeps/", "doctrine.md",
          "state-machines.md", "domains.md", "domains-operations.md", "global-compliance.md",
          "battle-testing.md", "browser-walks.md", "reporting.md", "evidence.md")
LINES = range(1, 16)   # Step 7 numbered lines 1-15; the lettered ones (3a, 6b...) are not demanded


def _norm(text: str) -> str:
    return " ".join(re.sub(r"[_*`\"“”'’]", " ", text).lower().split())


def receipts_missing(report: str, need: tuple[str, ...] = ALWAYS) -> list[str]:
    found, _ = scan()
    by_key = {("sweeps/" if k.startswith("sweeps/") else k): phrase for k, phrase in found.items()}
    body = _norm(report)
    return [ref for ref in need if ref in by_key and _norm(by_key[ref]) not in body]


def checks(report: str) -> list[tuple[str, bool, str]]:
    missing_receipts = receipts_missing(report)
    sweeps = [n for n in range(1, 25) if not re.search(rf"\bS{n}\b", report)]
    numbered = {int(n) for n in re.findall(r"(?m)^\s*(?:[-*]\s*)?(?:\*\*)?(\d{1,2})[.)]", report)}
    lines = [n for n in LINES if n not in numbered]
    return [
        ("receipts", not missing_receipts,
         "the receipt of " + ", ".join(missing_receipts) + " - read each file to its receipt line, then quote it"),
        ("sweep lines S1-S24", not sweeps, "a line for " + ", ".join(f"S{n}" for n in sweeps)),
        ("Step 7 lines 1-15", not lines, "numbered line " + ", ".join(map(str, lines))),
        ("owner paragraph", bool(re.search(r"(?i)owner", report)), "the owner paragraph (§0.16) first"),
    ]


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] != ["check"] or len(argv) != 2:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    try:
        text = sys.stdin.read() if argv[1] == "-" else Path(argv[1]).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as e:
        # exit 2, never 1: 1 means "parts missing". The trap: PowerShell's `>` writes UTF-16, and a report
        # that cannot be decoded must not read as a report that failed (cia's checker had this; the port lost it).
        print(f"audit_report: cannot read {argv[1]}: {getattr(e, 'strerror', None) or e}", file=sys.stderr)
        return 2
    results = checks(text)
    for name, ok, hint in results:
        print(f"{'ok     ' if ok else 'MISSING'}  {name}" + ("" if ok else f" - add {hint}"))
    missing = sum(not ok for _, ok, _ in results)
    print(f"audit_report: {len(results) - missing} of {len(results)} parts present"
          + ("" if not missing else " - read and fill what is missing, check again, then reply with the report"))
    return 1 if missing else 0


if __name__ == "__main__":
    if {"-h", "--help"} & set(sys.argv[1:]):   # answered here, before main(): --help must never run the job
        print(__doc__)
        sys.exit(0)
    sys.exit(main())
