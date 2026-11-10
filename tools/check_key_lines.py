"""Fail loudly when a fixture moves under its own answer key.

Ported from cia on 2026-11-10, the day a scorer found this repo's shop-node key four lines off the code
it grades (N1 cited `server.js:60`; the stock write had moved to 64). A run filing the race where it
actually is would have been scored against a stale range, and nothing here could have said so.

What it checks: every `path:line` and `path:line-line` citation in each key resolves (the file exists
and the lines are within it), and the sha256 of every cited file matches the pin recorded at the foot
of the key. A cited file that changed means a person re-reads its ranges, then runs `--repin`
(with `--only <key>` when only one key was re-read). Re-pinning without re-reading is the
silent-permissive failure this exists to refuse.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEYS = {
    "tests/EXPECTED-fixture-shop.md": "tests/fixture-shop",
    "tests/EXPECTED-fixture-shop-live.md": "tests/fixture-shop-live",
    "tests/EXPECTED-fixture-shop-node.md": "tests/fixture-shop-node",
}
PIN_MARKER = "<!-- site-pins (tools/check_key_lines.py) -->"

CITATION = re.compile(r"`([A-Za-z0-9_./-]+\.(?:py|js|php|sql|yaml|yml|json|md)):(\d+)(?:-(\d+))?")


def pins_from(text: str) -> dict[str, str]:
    block = text.split(PIN_MARKER)
    if len(block) < 2:
        return {}
    return dict(
        re.findall(r"^-\s+`([^`]+)`\s+([0-9a-f]{64})$", block[1], re.MULTILINE)
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repin", action="store_true", help="rewrite the pins after a human re-read")
    parser.add_argument(
        "--only", choices=sorted(KEYS), help="check (or re-pin) this one key instead of all of them"
    )
    args = parser.parse_args()

    failures: list[str] = []
    keys = {args.only: KEYS[args.only]} if args.only else KEYS

    for key_rel, fixture_rel in keys.items():
        key_path = ROOT / key_rel
        fixture = ROOT / fixture_rel
        text = key_path.read_text(encoding="utf-8")
        recorded = pins_from(text)
        seen: dict[str, str] = {}

        for rel, start, end in CITATION.findall(text):
            target = fixture / rel
            if not target.is_file():
                failures.append(f"{key_rel}: cites `{rel}` which does not exist under {fixture_rel}/")
                continue

            lines = len(target.read_text(encoding="utf-8").splitlines())
            for label, number in (("start", start), ("end", end)):
                if number and int(number) > lines:
                    failures.append(
                        f"{key_rel}: `{rel}:{number}` is past the end of the file ({lines} lines) "
                        f"- the key's {label} of a range has drifted"
                    )

            # Line endings are normalised before hashing: the same content checked out with CRLF
            # (Windows, core.autocrlf) must not fail a pin that was taken on LF, or the reverse.
            seen[rel] = hashlib.sha256(target.read_bytes().replace(b"\r\n", b"\n")).hexdigest()

        for rel, digest in sorted(seen.items()):
            if rel not in recorded:
                failures.append(f"{key_rel}: `{rel}` is cited but not pinned - run --repin once the ranges are read")
            elif recorded[rel] != digest:
                failures.append(
                    f"{key_rel}: `{rel}` has changed since its ranges were last read by a person. "
                    f"Re-read every citation into it, then --repin."
                )

        if args.repin:
            body = text.split(PIN_MARKER)[0].rstrip()
            pinned = "\n".join(f"- `{rel}` {digest}" for rel, digest in sorted(seen.items()))
            key_path.write_text(
                f"{body}\n\n{PIN_MARKER}\n\n## Site pins\n\n"
                "Every file this key cites, with the sha256 it had when a person last read the "
                "ranges against it. A changed digest fails `tools/check_key_lines.py` — re-read, "
                "then re-pin.\n\n"
                f"{pinned}\n",
                encoding="utf-8",
                newline="\n",
            )
            print(f"{key_rel}: pinned {len(seen)} cited files")
            # No early return: with several keys, returning here would re-pin only the first
            # and leave the rest reporting stale pins as if nothing had been done.

    if args.repin:
        return 0

    if failures:
        print("key-line check FAILED:")
        for line in failures:
            print(f"  - {line}")
        return 1

    print("key lines: every citation resolves and every cited file matches its pin")
    return 0


if __name__ == "__main__":
    sys.exit(main())
