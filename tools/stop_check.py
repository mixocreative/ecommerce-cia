#!/usr/bin/env python3
"""Stop hook: a session that wrote this skill's audit report may not finish while the report checker fails.

    python tools/stop_check.py        # Claude Code runs it on Stop, with the hook payload on stdin

Why a hook and not more wording (2026-11-10): SKILL Step 7 already says "check it before you reply ...
check again until it exits 0", and about half the cold runs replied anyway, naming the references they
had not read. A rule a hook can run is a rule that holds (S8). This blocks the stop ONCE, handing the
checker's MISSING lines back as the reason; `stop_hook_active` is true on the retry, so it can never
trap a session in a loop.

It acts only on this skill's own report (`<skill>-audit-report.md` in the session's working directory),
and only when that file was written during this session (newer than the session's transcript file), so
an old report in a project never blocks an unrelated session.

The trap the reason names (2026-11-10, RUNS second stage on 9f8f9b0): a blocked run backfills the sweep
lines the checker asks for, and it wrote defects onto them as prose without filing them; every miss of
that stage had this shape. So the reason says a defect on a sweep line is a finding, before the lines go in.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPORT = f"{HERE.parent.name}-audit-report.md"   # cia-audit-report.md, ecommerce-cia-audit-report.md


def decide(payload: dict, checks) -> dict | None:
    """The hook's answer for one Stop payload: a block with the checker's MISSING lines, or None to allow."""
    if payload.get("stop_hook_active"):
        return None                                  # already blocked once on this stop: never loop
    cwd = payload.get("cwd")
    report = Path(cwd) / REPORT if cwd else None
    if report is None or not report.is_file():
        return None
    transcript = payload.get("transcript_path")
    try:
        started = Path(transcript).stat().st_ctime if transcript else None
    except OSError:
        started = None
    if started is not None and report.stat().st_mtime < started:
        return None                                  # a report from an earlier session: not this one's
    try:
        results = checks(report.read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        return None
    missing = [f"MISSING  {name} - add {hint}" for name, ok, hint in results if not ok]
    if not missing:
        return None
    return {"decision": "block",
            "reason": (f"{REPORT} fails the skill's report checker. Do what each line says, update the report, "
                       f"run tools/audit_report.py check on it again, and only then reply. A sweep line you add names "
                       f"finding IDs: anything wrong you write on it is filed as a numbered finding first:\n"
                       + "\n".join(missing))}


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0                                     # not a hook payload: allow, never break a session
    sys.path.insert(0, str(HERE))
    from audit_report import checks                  # this skill's own checker
    answer = decide(payload, checks)
    if answer:
        print(json.dumps(answer))
    return 0


if __name__ == "__main__":
    if {"-h", "--help"} & set(sys.argv[1:]):   # answered here, before main(): --help must never run the job
        print(__doc__)
        sys.exit(0)
    sys.exit(main())
