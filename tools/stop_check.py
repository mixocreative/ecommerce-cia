#!/usr/bin/env python3
"""Stop hook: a session that wrote this skill's audit report may not finish while the report checker fails.

    python tools/stop_check.py        # Claude Code runs it on Stop, with the hook payload on stdin

Why a hook and not more wording (2026-11-10): SKILL Step 7 already says "check it before you reply ...
check again until it exits 0", and about half the cold runs replied anyway, naming the references they
had not read. A rule a hook can run is a rule that holds (S8). This blocks the stop ONCE, handing the
checker's MISSING lines back as the reason; `stop_hook_active` is true on the retry, so it can never
trap a session in a loop.

It acts only on this skill's own report (`ecommerce-cia-audit-report.md` in the session's working directory, or
wherever a tool call in this turn named a file of that name, a Bash redirect included), and only when that file was written during the
turn now ending: newer than the turn's prompt, read from the transcript's timestamps. So an old report,
a resumed session, or a later turn that did not touch the report is never blocked. The trap this
replaced: the transcript file's st_ctime is its creation time only on Windows; on macOS and Linux it
moves on every append, so every report looked older than the session and the hook never fired.

hooks/hooks.json's command is `python3 <this>; python <this>; exit 0`, which bash, sh and PowerShell all parse:
Claude Code runs hooks in bash where it can and in PowerShell on Windows without Git Bash. Whichever
interpreter runs first reads the payload; the second reads an empty stdin, and main() then allows silently.
The trailing `exit 0` matters: Claude Code reads the JSON only on exit 0, and where `python` is missing
(stock macOS) the last statement's 127 would have discarded the block.

The trap the reason names (2026-11-10, RUNS second stage on 9f8f9b0): a blocked run backfills the sweep
lines the checker asks for, and it wrote defects onto them as prose without filing them; every miss of
that stage had this shape. So the reason says a defect on a sweep line is a finding, before the lines go in.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
# A literal, never the folder name: an installed plugin lives in .../<plugin>/<version>/, so a name taken
# from the folder was "2.5.0-audit-report.md" and the hook never fired outside a repo checkout (Fable, 2026-11-10).
REPORT = "ecommerce-cia-audit-report.md"

# Any path ending in the report's name, in any tool's input: a Write's file_path, an Edit's, or a Bash redirect.
NAMED = re.compile(r"[^\s\"'<>|;&()`]*" + re.escape(REPORT))


def _strings(value):
    """Every string inside a tool input, however nested; a malformed input yields nothing instead of raising."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v)


def this_turn(transcript_path) -> tuple[float | None, list[Path]]:
    """The turn now ending, from a Claude Code transcript (JSONL): its prompt's epoch seconds, and every path
    named this skill's report that a tool in that turn touched (newest first). (None, []) when unreadable.

    A prompt is a `user` entry that is neither a tool result nor meta; tool results and injected entries (hook
    feedback, notifications: `isMeta`) are `user` entries too, and taking one as the turn start would hide a
    report written earlier in the same turn, so the hook would silently not fire. The paths are why a report
    the owner asked for outside the working directory is guarded too."""
    try:
        lines = Path(transcript_path).read_text(encoding="utf-8", errors="replace").splitlines()
    except (OSError, TypeError):
        return None, []
    written: list[Path] = []
    for line in reversed(lines):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if not isinstance(d, dict) or d.get("isSidechain"):
            continue
        content = (d.get("message") or {}).get("content")
        if d.get("type") == "assistant" and isinstance(content, list):
            for c in content:
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    written += [Path(m) for s in _strings(c.get("input")) for m in NAMED.findall(s)
                                if re.split(r"[\\/]", m)[-1] == REPORT]   # whole name: "ecommerce-cia-audit-report.md" ends in cia's
            continue
        if d.get("type") != "user" or d.get("isMeta") or not d.get("timestamp"):
            continue
        if isinstance(content, list) and any(isinstance(c, dict) and c.get("type") == "tool_result" for c in content):
            continue
        try:
            return datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00")).timestamp(), written
        except ValueError:
            return None, []
    return None, []


def decide(payload: dict, checks) -> dict | None:
    """The hook's answer for one Stop payload: a block with the checker's MISSING lines, or None to allow."""
    if payload.get("stop_hook_active"):
        return None                                  # already blocked once on this stop: never loop
    started, written = this_turn(payload.get("transcript_path"))
    if started is None:
        return None                                  # no turn to place a report in: never guess
    cwd = Path(payload.get("cwd") or ".")
    candidates = list(dict.fromkeys([cwd / REPORT] + [p if p.is_absolute() else cwd / p for p in written]))
    for report in candidates:
        if report.is_file() and report.stat().st_mtime >= started:   # written this turn, not an older report
            answer = _check(report, cwd, checks)
            if answer:
                return answer
    return None


def _check(report: Path, cwd: Path, checks) -> dict | None:
    """A block naming one report's MISSING lines, or None when its checker passes or it cannot be read."""
    label = REPORT if report.parent == cwd else str(report)   # the full path only when it is not the usual one
    try:
        results = checks(report.read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        return None
    missing = [f"MISSING  {name} - add {hint}" for name, ok, hint in results if not ok]
    if not missing:
        return None
    return {"decision": "block",
            "reason": (f"{label} fails the skill's report checker. Do what each line says, update the report, "
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
        answer = decide(payload, checks)
    except Exception as e:                           # noqa: BLE001  never block on our own bug, but say so:
        # the command ends `exit 0`, so a crash here would otherwise leave the guard off with nobody told.
        answer = {"systemMessage": f"{REPORT}'s Stop hook could not run ({type(e).__name__}: {e}); "
                                   f"the report was not checked."}
    if answer:
        print(json.dumps(answer))
    return 0


if __name__ == "__main__":
    if {"-h", "--help"} & set(sys.argv[1:]):   # answered here, before main(): --help must never run the job
        print(__doc__)
        sys.exit(0)
    sys.exit(main())
