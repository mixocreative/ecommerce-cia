#!/usr/bin/env python3
"""Render the NewebPay readiness card from a small YAML-ish status file.

The file is `docs/integrations/newebpay-readiness.yaml` (create with --init). Each line is
`key: status | note` where status is one of  ok  wait  missing  skip . Keep it beside the shop;
setup mode updates it every session and prints the card at the end.

Usage:
  python tools/newebpay/readiness.py --init [path]     # write the template
  python tools/newebpay/readiness.py [path]            # print the card; exit 1 if anything is missing
No third-party modules.
"""
from __future__ import annotations

import sys
from pathlib import Path

DEFAULT = Path("docs/integrations/newebpay-readiness.yaml")
ICON = {"ok": "✅", "wait": "⏳", "missing": "❌", "skip": "⏭"}

TEMPLATE = """# NewebPay readiness — edit the status word (ok | wait | missing | skip) and the note.
# A `wait` needs a who + since date in the note. A `missing` needs a who. Nothing stays blank.
shop: missing | shop name
mode: missing | sandbox or production
manuals.ndnf: missing | NDNF version + date, path on disk
manuals.ndnp: skip | only for subscriptions
manuals.ndns: skip | only for 超商取貨
account.sandbox: missing | who registered, personal/company, date
account.production: missing | under review since ...
shop.keys.sandbox: missing | in .env, lengths 32/16, gitignored
shop.keys.production: missing |
methods.credit: missing | console toggle + probe result + date
methods.webatm: skip |
methods.vacc: skip |
methods.cvs: skip | cap NT$6,000
methods.barcode: skip |
methods.linepay: skip | application form sent on ...
delivery.cvs_pickup: skip | 取貨付款 / 取貨不付款, chains
delivery.return_store: skip | 退貨門市 set
delivery.sender: skip | ≤5 Chinese characters for 7-ELEVEN
delivery.prepaid_balance: skip | 預付費用 funded
delivery.push_url: skip | NPA-B58 URL registered
delivery.outbound_ip: skip | registered; host confirmed stable
host.inbound_443: missing | domain + valid cert, or tunnel
host.outbound_ip_stable: missing | asked host on ...
host.cron: missing |
host.clock: missing | NTP
urls.notify: missing |
urls.return: missing |
urls.customer: missing | ATM / CVS instruction result
walk.credit: missing | round-trip artefacts at ...
walk.async: skip | 模擬付款 found / not found
walk.pickup: skip | real parcel needed for pushes
waits: skip | one per line in notes: who, question, since, blocks
next: missing | 1 ... 2 ... 3 ...
"""


def render(path: Path) -> int:
    rows = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, rest = line.split(":", 1)
        status, _, note = rest.partition("|")
        status = status.strip().lower() or "missing"
        rows.append((key.strip(), status, note.strip()))
    if not rows:
        print("empty readiness file"); return 1
    width = max(len(k) for k, _, _ in rows)
    title = next((n for k, _, n in rows if k == "shop"), "")
    print(f"NewebPay readiness — {title}")
    print("-" * (width + 40))
    blocking = 0
    for key, status, note in rows:
        icon = ICON.get(status, "?")
        flag = ""
        if status == "missing":
            blocking += 1
        if status in ("wait", "missing") and not note:
            flag = "   <- no owner / date: finding against the guide"
        print(f"{icon} {key.ljust(width)}  {note}{flag}")
    print("-" * (width + 40))
    print(f"{blocking} item(s) missing. " + ("Not ready." if blocking else "Every row is ok, waiting with a date, or deliberately skipped."))
    return 1 if blocking else 0


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--init":
        p = Path(argv[1]) if len(argv) > 1 else DEFAULT
        if p.exists():
            print(f"exists: {p}"); return 1
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(TEMPLATE, encoding="utf-8")
        print(f"wrote {p}"); return 0
    p = Path(argv[0]) if argv else DEFAULT
    if not p.exists():
        print(f"no readiness file at {p}; run --init"); return 1
    return render(p)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
