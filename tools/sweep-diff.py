#!/usr/bin/env python3
"""Compare the shared doctrine of cia and ecommerce-cia - the sweeps, and the files around them.

The two skills carry the same sweep numbering by design and diverge by design
(ecommerce-cia is the commerce-enhanced case). This script makes the divergence
visible so a lesson that landed in one file only is a decision, not an accident.

Until 2026-09-24 it watched `sweeps.md` alone, which left the other four shared reference files
unwatched - and `browser-walks.md`, byte-identical in both repos and carrying the whole runtime
half of the doctrine, had no drift detector at all. The file table below closes that.

Usage:  python tools/sweep-diff.py            (run from either repo)
        python tools/sweep-diff.py --full S12 (unified diff of one sweep)
        python tools/sweep-diff.py --files    (the shared-file table only)

Exit code 0 always; this is a report, not a gate.
"""
import difflib
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp950/cp1252; the output carries CJK and emoji
    sys.stdout.reconfigure(encoding="utf-8")


HERE = Path(__file__).resolve().parent.parent
SKILLS = HERE.parent
CIA = SKILLS / "cia" / "references"
ECOM = SKILLS / "ecommerce-cia" / "references"


def ref_text(refs: Path, name: str) -> "str | None":
    """One side's copy of a shared reference file. sweeps.md is a folder on both sides now (cia split it
    on 2026-11-09, ecommerce-cia on 2026-11-10): its files are joined in name order, so the section parser
    sees one document. The trap: a hard-coded path to one side's old sweeps.md made this report print
    "missing" for a month on the side that had already split, and nobody read the line."""
    if name == "sweeps.md" and (refs / "sweeps").is_dir():
        return "\n".join(f.read_text(encoding="utf-8") for f in sorted((refs / "sweeps").glob("*.md")))
    f = refs / name
    return f.read_text(encoding="utf-8") if f.exists() else None


def sections(source) -> dict[str, str]:
    text = source.read_text(encoding="utf-8") if isinstance(source, Path) else source
    # Split on every level-1 and level-2 heading, then keep the sweeps: a non-sweep section after S24 (cia's
    # "Audit-derived classes", 2026-10-22) must end S24 rather than be counted as part of it. The level-1
    # "# Sweeps ..." header that opens each split-out file must end the previous sweep too.
    parts = re.split(r"^#{1,2} (\S+)", text, flags=re.M)
    out = {}
    for i in range(1, len(parts), 2):
        if re.fullmatch(r"S\d+", parts[i]):
            out[parts[i]] = parts[i + 1]
    return out


def bold(s: str) -> set[str]:
    return {m.strip(" .,:;") for m in re.findall(r"\*\*([^*]{12,120})\*\*", s)}


def subheads(s: str) -> set[str]:
    return set(re.findall(r"^### (S\d+\.\d+)", s, flags=re.M))




SHARED = ["sweeps.md", "doctrine.md", "reporting.md", "theory.md", "browser-walks.md", "evidence.md"]


def file_table() -> None:
    """Every shared reference file: size on each side, and whether they are still identical."""
    print(f"{'file':22} {'cia':>7} {'ecom':>7}  state")
    print("-" * 100)
    for name in SHARED:
        ct, et = ref_text(CIA, name), ref_text(ECOM, name)
        if ct is None or et is None:
            print(f"{name:22} {'-':>7} {'-':>7}  MISSING ON ONE SIDE "
                  f"({'cia' if ct is None else 'ecommerce-cia'})")
            continue
        cw, ew = len(ct.split()), len(et.split())
        if ct == et:
            state = ("identical - a duplicate, so an edit to one is a silent drift in the other; "
                     "change both in the same commit")
        else:
            cb, eb = bold(ct), bold(et)
            state = f"diverged - {len(cb - eb)} claim(s) only in cia, {len(eb - cb)} only in ecommerce-cia"
        print(f"{name:22} {cw:7} {ew:7}  {state}")
    print()

def main() -> None:
    file_table()
    if "--files" in sys.argv:
        return
    ct, et = ref_text(CIA, "sweeps.md"), ref_text(ECOM, "sweeps.md")
    if ct is None or et is None:
        print(f"missing: the sweeps of {'cia' if ct is None else 'ecommerce-cia'}")
        sys.exit(0)
    c, e = sections(ct), sections(et)
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
    if {"-h", "--help"} & set(sys.argv[1:]):   # answered here, before main(): --help must never run the job
        sys.stdout.reconfigure(encoding="utf-8")
        print(__doc__)
        sys.exit(0)
    main()
