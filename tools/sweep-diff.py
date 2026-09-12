#!/usr/bin/env python3
"""Compare the S1-S22 sweep texts of cia and ecommerce-cia.

The two skills carry the same sweep numbering by design and diverge by design
(ecommerce-cia is the commerce-enhanced case). This script makes the divergence
visible so a lesson that landed in one file only is a decision, not an accident.

Usage:  python tools/sweep-diff.py            (run from either repo)
        python tools/sweep-diff.py --full S12 (unified diff of one sweep)

Exit code 0 always; this is a report, not a gate.
"""
import difflib
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SKILLS = HERE.parent
CIA = SKILLS / "cia" / "references" / "sweeps.md"
ECOM = SKILLS / "ecommerce-cia" / "references" / "sweeps.md"


def sections(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"^## (S\d+) ", text, flags=re.M)
    out = {}
    for i in range(1, len(parts), 2):
        out[parts[i]] = parts[i + 1]
    return out


def bold(s: str) -> set[str]:
    return {m.strip(" .,:;") for m in re.findall(r"\*\*([^*]{12,120})\*\*", s)}


def subheads(s: str) -> set[str]:
    return set(re.findall(r"^### (S\d+\.\d+)", s, flags=re.M))


def main() -> None:
    for p in (CIA, ECOM):
        if not p.exists():
            print(f"missing: {p}")
            sys.exit(0)
    c, e = sections(CIA), sections(ECOM)
    keys = sorted(set(c) | set(e), key=lambda k: int(k[1:]))

    if len(sys.argv) == 3 and sys.argv[1] == "--full":
        k = sys.argv[2]
        diff = difflib.unified_diff(
            c.get(k, "").splitlines(), e.get(k, "").splitlines(),
            fromfile=f"cia {k}", tofile=f"ecommerce-cia {k}", lineterm="", n=1,
        )
        print("\n".join(diff))
        return

    print(f"{'sweep':6} {'cia':>6} {'ecom':>6}  {'sub-sections':22} {'checks only in cia / only in ecommerce-cia'}")
    print("-" * 100)
    for k in keys:
        cs, es = c.get(k, ""), e.get(k, "")
        cw, ew = len(cs.split()), len(es.split())
        ch, eh = subheads(cs), subheads(es)
        cb, eb = bold(cs), bold(es)
        only_c = sorted(cb - eb)
        only_e = sorted(eb - cb)
        subs = ",".join(sorted(ch | eh)) or "-"
        flag = ""
        if ch != eh:
            flag = f"  SUBSECTION MISMATCH cia={sorted(ch)} ecom={sorted(eh)}"
        print(f"{k:6} {cw:6} {ew:6}  {subs:22} {len(only_c):>2} / {len(only_e):<2}{flag}")
        for w in only_c[:4]:
            print(f"{'':6} {'':6} {'':6}  {'':22}   cia-only:  {w[:70]}")
        for w in only_e[:4]:
            print(f"{'':6} {'':6} {'':6}  {'':22}   ecom-only: {w[:70]}")
    print("\nA row is not a defect. A row you cannot explain is. Read the sibling's version before")
    print("deciding the lesson does not apply; record the decision in the commit that changes either file.")


if __name__ == "__main__":
    main()
