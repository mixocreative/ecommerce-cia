#!/usr/bin/env python3
"""Structure guard for the ecommerce-cia skill - fails when its files stop agreeing with each other.

One job: keep the skill's own bookkeeping honest, so "nothing loose" and the size rule are checked,
not hoped for. Ported from cia's tools/check_structure.py on 2026-11-10, when a 1,919-line
references/sweeps.md was found here with no rule that would ever have said so. Stdlib only.
Exit 0 = every check green; exit 1 = at least one check failed (CI runs this).

Checks:
  1. SKILL.md frontmatter: name present; description <= 1024 characters, no double quote inside it.
  2. Nothing loose: every references/*.md is named by SKILL.md, and the references/sweeps/ folder is
     named; every tests/EXPECTED-*.md is named in tests/RUNBOOK.md.
  3. Nothing missing: every references/... path SKILL.md names exists.
  4. Sweeps S1-S24: each sweep heading appears exactly once across references/sweeps/*.md.
  5. No stale path: no `references/sweeps.md` left in a live doc (historical wording is allowed).
  6. Size: no file over HARD_LIMIT lines (the cut is taken); a file over DEBT_LIMIT lines needs an
     entry in DEBT with its next cut written down. An entry for a file now under the limit fails too.
     Read: SKILL, README, references/, docs/, tools/ (every folder), the test scripts and the RUNBOOK;
     not the fixtures (their defects are planted) and not RUNS.md (a log that only grows).
  7. Line length: no line of SKILL.md or a reference over READ_LIMIT characters. The trap: the Read tool
     cuts a longer line, and on 2026-11-10 ecommerce-cia's Step 3 lost half its reading list that way.

Usage: python tools/check_structure.py
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REFS = HERE / "references"
SWEEPS = REFS / "sweeps"
SKILL = HERE / "SKILL.md"

HARD_LIMIT = 1000   # over this, the cut is taken in the same change
DEBT_LIMIT = 600    # over this, the file is named as debt below, with its next cut

# file (relative to HERE) -> the next cut, written down. Each cut that moves SKILL.md or references/
# text is a doctrine change: it ships with scored runs (tools/untested.py), so it is named, not taken.
DEBT: dict[str, str] = {}
# The four entries named on 2026-11-10 were cut the same day: domains.md at §17 (domains-operations.md),
# doctrine.md at §5 (state-machines.md), SKILL.md §0.15 (references/setup-mode.md), README's theory
# sections (docs/theory.md). Next cut when one nears 600 again: none named; measure first.

failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def rel(p: Path) -> str:
    return p.relative_to(HERE).as_posix()


def check_frontmatter(skill_text: str) -> None:
    m = re.match(r'---\nname: (\S+)\ndescription: "(.*)"\n---\n', skill_text.replace("\r\n", "\n"), re.S)
    if not m:
        fail("SKILL.md: frontmatter does not match the expected pattern (name, then description in double quotes)")
        return
    desc = m.group(2)
    if len(desc) > 1024:
        fail(f"SKILL.md: description is {len(desc)} characters; the limit is 1024")
    if '"' in desc:
        fail("SKILL.md: description contains a double quote")


def check_nothing_loose_or_missing(skill_text: str) -> None:
    # (?<!cia/): SKILL also points at the sibling's files (`../cia/references/...`), which live in cia, not here.
    named = {m.rstrip(".") for m in re.findall(r"(?<!cia/)references/[A-Za-z0-9_./-]+", skill_text)}
    for name in sorted(named):
        target = HERE / name
        if name.endswith("/"):
            if not target.is_dir():
                fail(f"SKILL.md names {name} but that folder does not exist")
        elif not target.exists():
            fail(f"SKILL.md names {name} but that file does not exist")
    for f in sorted(REFS.glob("*.md")):
        if rel(f) not in named:
            fail(f"loose file: {rel(f)} is not named by SKILL.md")
    if SWEEPS.is_dir() and "references/sweeps/" not in skill_text:
        fail("loose folder: references/sweeps/ is not named by SKILL.md")
    runbook = read(HERE / "tests" / "RUNBOOK.md")
    for f in sorted((HERE / "tests").glob("EXPECTED-*.md")):
        if f.name not in runbook:
            fail(f"loose file: {rel(f)} is not named in tests/RUNBOOK.md")


def check_sweeps() -> None:
    found: dict[str, int] = {}
    for f in sorted(SWEEPS.glob("*.md")):
        for s in re.findall(r"^## (S\d+) ", read(f), flags=re.M):
            found[s] = found.get(s, 0) + 1
    for n in range(1, 25):
        key = f"S{n}"
        if found.get(key, 0) != 1:
            fail(f"sweep {key}: found {found.get(key, 0)} headings across references/sweeps/ (expected exactly 1)")


def check_stale_paths() -> None:
    # The trap this names: after cia split its sweeps, this repo's SKILL §0.14 and sweep-diff.py kept
    # pointing at cia's old references/sweeps.md for a day, and no check here could see it.
    stale = re.compile(r"(?<!former `)references/sweeps\.md")
    live = [SKILL, HERE / "README.md", *REFS.glob("*.md"), *SWEEPS.glob("*.md"), *(HERE / "tests").glob("*.md")]
    for f in live:
        if f.name == "RUNS.md":  # the run log quotes history on purpose
            continue
        for i, line in enumerate(read(f).splitlines(), 1):
            if stale.search(line):
                fail(f"stale path {rel(f)}:{i} names references/sweeps.md, which is now references/sweeps/")


def check_size() -> None:
    # docs/ and the provider folders under tools/ count too: text cut out of a checked file must not
    # land where no check reads (README's theory moved to docs/ on 2026-11-10). Fixtures are not ours to cut.
    files = [SKILL, HERE / "README.md", *REFS.glob("*.md"), *SWEEPS.glob("*.md"), *(HERE / "docs").glob("*.md"),
             *(HERE / "tools").rglob("*.py"), *(HERE / "tools").rglob("*.php"), *(HERE / "tests").glob("*.py"),
             *(HERE / "tests").glob("*.js"), HERE / "tests" / "RUNBOOK.md"]
    over_debt = set()
    for f in files:
        n = len(read(f).splitlines())
        key = rel(f)
        if n > HARD_LIMIT:
            fail(f"{key} is {n} lines; over {HARD_LIMIT} the cut is taken, not named")
        if n > DEBT_LIMIT:
            over_debt.add(key)
            if key not in DEBT:
                fail(f"{key} is {n} lines; over {DEBT_LIMIT} it must be named in DEBT with its next cut")
    for key in DEBT:
        if key not in over_debt:
            fail(f"DEBT entry {key} is no longer over {DEBT_LIMIT} lines: remove the entry")


READ_LIMIT = 2000   # characters per line the Read tool shows; past it, a run never sees the rest


def check_line_length() -> None:
    for f in [SKILL, *REFS.glob("*.md"), *SWEEPS.glob("*.md")]:
        for i, line in enumerate(read(f).splitlines(), 1):
            if len(line) > READ_LIMIT:
                fail(f"{rel(f)}:{i} is {len(line)} characters; the Read tool cuts it at {READ_LIMIT}: wrap it")


def main() -> int:
    failures.clear()
    skill_text = read(SKILL)
    check_frontmatter(skill_text)
    check_nothing_loose_or_missing(skill_text)
    check_sweeps()
    check_stale_paths()
    check_size()
    check_line_length()
    if failures:
        print(f"check_structure: {len(failures)} failure(s)")
        for msg in failures:
            print(f"  - {msg}")
        return 1
    print("check_structure: all green")
    return 0


if __name__ == "__main__":
    if {"-h", "--help"} & set(sys.argv[1:]):   # answered here, before main(): --help must never run the job
        sys.stdout.reconfigure(encoding="utf-8")
        print(__doc__)
        sys.exit(0)
    sys.exit(main())
