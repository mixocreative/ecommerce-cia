#!/usr/bin/env python3
"""Stop hook: a session that wrote this skill's audit report may not finish while the report checker fails.

    python tools/stop_check.py        # Claude Code runs it on Stop, with the hook payload on stdin

Why a hook and not more wording (2026-11-10): SKILL Step 7 already says "check it before you reply ...
check again until it exits 0", and about half the cold runs replied anyway, naming the references they
had not read. A rule a hook can run is a rule that holds (S8). This blocks the stop ONCE, handing the
checker's MISSING lines back as the reason; `stop_hook_active` is true on the retry, so it can never
trap a session in a loop.

It acts only on this skill's own report (`ecommerce-cia-audit-report.md` in the session's working directory;
a report the owner asked for elsewhere is not guarded), and only when that file was written during the
turn now ending: newer than the turn's prompt, read from the transcript's timestamps. So an old report,
a resumed session, or a later turn that did not touch the report is never blocked. The trap this
replaced: the transcript file's st_ctime is its creation time only on Windows; on macOS and Linux it
moves on every append, so every report looked older than the session and the hook never fired.

The trap the reason names (2026-11-10, RUNS second stage on 9f8f9b0): a blocked run backfills the sweep
lines the checker asks for, and it wrote defects onto them as prose without filing them; every miss of
that stage had this shape. So the reason says a defect on a sweep line is a finding, before the lines go in.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
# A literal, never the folder name: an installed plugin lives in .../<plugin>/<version>/, so a name taken
# from the folder was "2.5.0-audit-report.md" and the hook never fired outside a repo checkout (Fable, 2026-11-10).
REPORT = "ecommerce-cia-audit-report.md"


def turn_started(transcript_path) -> float | None:
    """Epoch seconds of the newest prompt in a Claude Code transcript (JSONL): the start of the turn now ending.

    A prompt is a `user` entry that is neither a tool result nor meta; tool results and injected entries (hook
    feedback, notifications: `isMeta`) are `user` entries too, and taking one as the turn start would hide a
    report written earlier in the same turn, so the hook would silently not fire. None when unreadable."""
    try:
        lines = Path(transcript_path).read_text(encoding="utf-8", errors="replace").splitlines()
    except (OSError, TypeError):
        return None
    for line in reversed(lines):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if not isinstance(d, dict) or d.get("type") != "user" or d.get("isSidechain") or d.get("isMeta") or not d.get("timestamp"):
            continue
        content = (d.get("message") or {}).get("content")
        if isinstance(content, list) and any(isinstance(c, dict) and c.get("type") == "tool_result" for c in content):
            continue
        try:
            return datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None
    return None


def decide(payload: dict, checks) -> dict | None:
    """The hook's answer for one Stop payload: a block with the checker's MISSING lines, or None to allow."""
    if payload.get("stop_hook_active"):
        return None                                  # already blocked once on this stop: never loop
    cwd = payload.get("cwd")
    report = Path(cwd) / REPORT if cwd else None
    if report is None or not report.is_file():
        return None
    started = turn_started(payload.get("transcript_path"))
    if started is None or report.stat().st_mtime < started:
        return None                                  # no turn to place it in, or written before this turn
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
    try:
        from audit_report import checks              # this skill's own checker
    except Exception:                                # noqa: BLE001  a broken install must not error on every Stop
        return 0
    answer = decide(payload, checks)
    if answer:
        print(json.dumps(answer))
    return 0


if __name__ == "__main__":
    if {"-h", "--help"} & set(sys.argv[1:]):   # answered here, before main(): --help must never run the job
        print(__doc__)
        sys.exit(0)
    sys.exit(main())
