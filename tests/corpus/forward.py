#!/usr/bin/env python3
"""Blind-forward validation — the corpus mode with no oracle chosen in advance.

The retrospective corpus (`run.py`) has a bias it cannot remove: every entry is a commit whose
author had already diagnosed the bug and written its name in the subject line. That flatters the
instrument even though the auditor never sees the message, because the *class* was known to
somebody before the audit started. It measures recall on characterised defects.

This mode removes the chooser. The procedure:

  1. Pick a repository and a commit **well back in its history** - nobody looks at what comes
     after. `pick` does this and prints only the checkout path.
  2. Audit that snapshot cold. The auditor has no oracle, because none exists yet.
  3. `confirm` replays the repository's own future: every commit AFTER the audited one that
     touched the files the audit named. A finding the maintainers later went and fixed is
     confirmed **by them**, months later, with no knowledge of this skill.

A hit here is not "the audit found the bug somebody told us about". It is "the audit named
something the project itself later decided was worth fixing". That is the only measurement in
this harness that can find a defect **nobody had collected** - which is the ceiling the
retrospective corpus cannot reach.

    python tests/corpus/forward.py pick <repo-url> [--back N]
    python tests/corpus/forward.py confirm <name> --files a.ts,b.ts [--since-audit]

Both halves stay honest only if step 2 happens between them. Running `confirm` before the audit
is reading the answer key.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(tempfile.gettempdir()) / "cia-forward"


def git(args: list[str], cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True,
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace").stdout


def cmd_pick(url: str, back: int) -> int:
    name = url.rstrip("/").split("/")[-1].replace(".git", "")
    dest = ROOT / name
    ROOT.mkdir(parents=True, exist_ok=True)

    if not dest.exists():
        print(f"cloning {url} ...", file=sys.stderr)
        subprocess.run(["git", "clone", "--quiet", url, str(dest)], check=True)

    # Always count from the repository's real tip: a clone left detached at an old commit by
    # another harness would otherwise count from there and pick a snapshot nobody meant.
    tip = "origin/HEAD"
    if subprocess.run(["git", "rev-parse", "--verify", "--quiet", tip],
                      cwd=dest, capture_output=True).returncode != 0:
        tip = "origin/main"
    git(["checkout", "--quiet", "--detach", tip], dest)

    # Count the chain HEAD~N actually walks. `rev-list --count HEAD` includes every commit
    # merged in from branches, so on a merge-heavy repo it says 426 while HEAD~220 does not
    # exist - which is a measurement of one thing used to index another.
    chain = [ln for ln in git(["rev-list", "--first-parent", "HEAD"], dest).splitlines() if ln]
    total = len(chain)
    if back >= total:
        back = max(total // 2, 1)

    target = chain[back]
    git(["checkout", "--quiet", target], dest)

    # Deliberately prints no subject, no date, no diff - nothing about what comes next.
    print(f"\naudit this, cold:\n  {dest}\n")
    print(f"snapshot: {target[:12]}   ({back} first-parent commits before the tip, of {total})")
    print("\nDo not run `confirm` until the audit is written down. Doing so is reading an")
    print("answer key that does not exist yet, which is the one thing this mode is for.")
    return 0


def cmd_confirm(name: str, files: list[str]) -> int:
    dest = ROOT / name
    if not dest.exists():
        sys.exit(f"no snapshot at {dest}. Run `pick` first.")

    audited = git(["rev-parse", "HEAD"], dest).strip()
    default = git(["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"], dest).strip() \
        if subprocess.run(["git", "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"],
                          cwd=dest, capture_output=True).returncode == 0 else "origin/main"

    print(f"audited snapshot : {audited[:12]}")
    print(f"replaying the project's own future against {default}\n")

    for path in files:
        log = git(["log", "--oneline", "--no-merges", f"{audited}..{default}", "--", path], dest)
        lines = [ln for ln in log.splitlines() if ln.strip()]
        print(f"{path}")
        if not lines:
            print("    (no later commit touched this file - the finding is unconfirmed either way)")
        for ln in lines:
            print(f"    {ln}")
        print()

    print("Scoring, and it is stricter than it looks:")
    print("  CONFIRMED-BY-FUTURE - a later commit changes the exact thing the finding named,")
    print("                        for the reason the finding gave. The maintainers agreed,")
    print("                        without knowing this audit existed.")
    print("  OPEN                - nobody has touched it yet. Not a miss: the defect may still")
    print("                        be there, and an audit ahead of its project is the point.")
    print("  WRONG               - a later commit shows the finding was mistaken about the code.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="verb", required=True)

    p = sub.add_parser("pick")
    p.add_argument("url")
    p.add_argument("--back", type=int, default=150)

    c = sub.add_parser("confirm")
    c.add_argument("name")
    c.add_argument("--files", required=True)

    args = ap.parse_args()
    if args.verb == "pick":
        return cmd_pick(args.url, args.back)
    return cmd_confirm(args.name, [f.strip() for f in args.files.split(",") if f.strip()])


if __name__ == "__main__":
    os.environ.setdefault("GIT_TERMINAL_PROMPT", "0")
    sys.exit(main())
