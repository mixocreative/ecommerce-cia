#!/usr/bin/env python3
"""Drive the corpus: prepare a real repository at the commit before a real fix.

    python tests/corpus/run.py list
    python tests/corpus/run.py prepare <entry>
    python tests/corpus/run.py oracle <entry>     # SCORER ONLY - prints the fix

`prepare` clones at the parent of the fix commit into a scratch directory and prints the path
to audit. It deliberately does NOT print the subject, the files or the class: the whole point is
that the auditor meets the code the way a maintainer did, without knowing what is wrong.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENTRIES = HERE / "entries"


def load(name: str) -> dict:
    path = ENTRIES / (name if name.endswith(".txt") else name + ".txt")
    if not path.exists():
        sys.exit(f"no such entry: {path.name}. Try `list`.")
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, _, value = line.partition(":")
        if _:
            out[key.strip()] = value.strip()
    return out


def cmd_list() -> int:
    if not ENTRIES.exists() or not any(ENTRIES.glob("*.txt")):
        print("corpus: no entries yet.")
        print("An empty corpus proves nothing, and the README says so. Add one per real fix commit.")
        return 1
    print(f"{'entry':28} {'class':8} {'repo'}")
    print("-" * 100)
    for path in sorted(ENTRIES.glob("*.txt")):
        e = load(path.stem)
        print(f"{path.stem:28} {e.get('class', '?'):8} {e.get('repo', '?')}")
    return 0


def cmd_prepare(name: str) -> int:
    e = load(name)
    repo, sha = e.get("repo"), e.get("audit_commit")
    if not repo or not sha:
        sys.exit(f"entry {name} needs repo and audit_commit")

    dest = Path(tempfile.gettempdir()) / "cia-corpus" / name
    dest.parent.mkdir(parents=True, exist_ok=True)

    if not dest.exists():
        print(f"cloning {repo} ...", file=sys.stderr)
        subprocess.run(["git", "clone", "--quiet", repo, str(dest)], check=True)
    subprocess.run(["git", "-C", str(dest), "checkout", "--quiet", sha], check=True)

    # The oracle must not be reachable from inside the audited tree.
    print(f"\nprepared at the commit BEFORE the fix:\n  {dest}\n")
    if e.get("scope"):
        print(f"scope for the run: {e['scope']}\n")
    print("Audit that path cold, in a fresh session, at the tier the entry names.")
    print("Do not read this directory's entries/ or RUNS.md from that session.")
    return 0


def cmd_oracle(name: str) -> int:
    e = load(name)
    print(f"ORACLE for {name} - the scorer's view. Never show this to a run.\n")
    for key in ("repo", "fix_commit", "audit_commit", "class", "subject", "files", "why_it_counts"):
        if e.get(key):
            print(f"  {key:14} {e[key]}")
    dest = Path(tempfile.gettempdir()) / "cia-corpus" / name
    if dest.exists() and e.get("fix_commit"):
        print("\n--- the fix diff ---")
        subprocess.run(["git", "-C", str(dest), "show", "--stat", e["fix_commit"]], check=False)
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    verb = sys.argv[1]
    if verb == "list":
        return cmd_list()
    if verb in ("prepare", "oracle"):
        if len(sys.argv) < 3:
            sys.exit(f"{verb} needs an entry name")
        return cmd_prepare(sys.argv[2]) if verb == "prepare" else cmd_oracle(sys.argv[2])
    print(__doc__)
    return 2


if __name__ == "__main__":
    os.environ.setdefault("GIT_TERMINAL_PROMPT", "0")
    sys.exit(main())
