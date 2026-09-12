#!/usr/bin/env python3
"""Render a provider readiness card from a small YAML-ish status file.

Templates exist for NewebPay (default), ECPay, LINE Pay and PAYUNi; the renderer is the same for all.
The file is `docs/integrations/<provider>-readiness.yaml` (create with --init). Each line is
`key: status | note` where status is one of  ok  wait  missing  skip . Keep it beside the shop;
setup mode updates it every session and prints the card at the end.

Usage:
  python tools/newebpay/readiness.py --init [path]                      # NewebPay template
  python tools/newebpay/readiness.py --init --provider linepay [path]    # ecpay | linepay | payuni
  python tools/newebpay/readiness.py [path]                              # print the card; exit 1 if anything is missing
No third-party modules.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp950/cp1252; the output carries CJK and emoji
    sys.stdout.reconfigure(encoding="utf-8")


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


TEMPLATES = {
    "newebpay": TEMPLATE,
    "ecpay": """# ECPay readiness — edit the status word (ok | wait | missing | skip) and the note.
# A `wait` needs a who + since date in the note. A `missing` needs a who. Nothing stays blank.
shop: missing | shop name
mode: missing | stage or production
docs: missing | markdown twins fetched (fetch_docs.py), date; 2864 (AIO), 2878 (result codes), 2902 (CheckMacValue)
account.stage: skip | none needed — public MerchantID 3002607 + keys from p=2856
account.production: missing | contract signed, under review since ...
shop.keys.production: missing | production MerchantID / HashKey / HashIV in .env, gitignored
methods.credit: missing | probe_aio.php Credit PASS + date
methods.webatm: skip |
methods.atm: skip | RtnCode 2 = 取號, not paid
methods.cvs: skip | 10100073 = 取號, not paid; cap
methods.barcode: skip |
methods.bnpl: skip | product activation (10200079 until then)
callback.return_url: missing | 1|OK ack; CheckMacValue verified before anything
callback.payment_info_url: missing | ATM / CVS 取號 lands here, never fulfils
refund: skip | DoAction is production-only — first refund proof is a real order
delivery.logistics: skip | 全方位物流 vs C2C family; 測標 per sub-type
host.inbound_443: missing | domain + valid cert, or tunnel
host.clock: missing | NTP
walk.credit: missing | stage round-trip artefacts at ...
walk.simulate_paid: skip | SimulatePaid=1 is not money
waits: skip | one per line in notes: who, question, since, blocks
next: missing | 1 ... 2 ... 3 ...
""",
    "linepay": """# LINE Pay readiness — edit the status word (ok | wait | missing | skip) and the note.
# A `wait` needs a who + since date in the note. A `missing` needs a who. Nothing stays blank.
shop: missing | shop name
route: missing | direct Online API v3 | v4 | via NewebPay LINEPAY | via PAYUNi LinePay
reference: missing | developers-pay.line.me read <date>; versions listed by fetch_docs.py --latest
account.sandbox: missing | sandbox account (one per e-mail) or merchant account reused
account.production: missing | LINE Pay TW merchant application, under review since ...
keys.sandbox: missing | Channel ID / Secret from Manage Link Key, in .env, gitignored
keys.production: missing |
payer.test_account: skip | the sandbox payer account, used only on the LINE-login page; never pasted anywhere
probe.request: missing | probe_request.php PASS (transactionId kept as string) + date
walk.approve: missing | pop-up simulator PAY NOW, or LINE web login with the payer account
walk.check_0110: missing |
walk.confirm: missing | --confirm 0000 + payInfo
walk.details: missing | --details payStatus CAPTURE
walk.refund: missing | --refund 0000 refundTransactionId; re-refund 1165
walk.double_confirm: missing | 1172 / 1145 / 1152 read as done
walk.cancel: skip | cancelUrl path
capture_separated: skip | 2103 on the sandbox unless the contract enables it
urls.confirm: missing | HTTPS TLS 1.2+; GET with orderId + transactionId
urls.cancel: missing |
host.inbound_allowlist: skip | only if confirmUrlType=SERVER; LINE Pay IPs from the redirection-pages page
host.static_ip: skip | not required by the Online API
host.timeouts: missing | read timeouts 10 / 40 / 20 s; no blind retries
waits: skip | one per line in notes: who, question, since, blocks
next: missing | 1 ... 2 ... 3 ...
""",
    "payuni": """# PAYUNi readiness — edit the status word (ok | wait | missing | skip) and the note.
# A `wait` needs a who + since date in the note. A `missing` needs a who. Nothing stays blank.
shop: missing | shop name
mode: missing | sandbox or production
docs: missing | fetch_docs.py --fetch, date; pages 34 (UPP), 374 (test data), 156/44 (errors)
account.sandbox: missing | self-registered on the sandbox, date
account.production: missing | registration + review, since ...
keys: missing | MerID / Hash Key / Hash IV in .env, gitignored; crypto.php selftest PASS
methods.credit: missing | probe_upp.php PASS (JS_INFO.success) + date
methods.atm: skip | 模擬繳費
methods.cvs: skip | 超商代碼 cap 20,000; 模擬繳費
methods.linepay: skip | sandbox accepts any Channel ID; production needs the real channel
methods.icash: skip | application form
methods.aftee: skip | application form; test phones on p.374
delivery.7eleven: skip | ShipTag / Ship flags on the same page; B2C / C2C / C2B
host.notify_port: missing | NotifyURL on 80 / 443 only
host.inbound_443: missing | domain + valid cert, or tunnel
callback.notify: missing | Status + TradeStatus semantics; ack
refund: skip | cards via 請退款; non-card via 轉匯
walk.credit: missing | sandbox round-trip artefacts at ...
waits: skip | one per line in notes: who, question, since, blocks
next: missing | 1 ... 2 ... 3 ...
""",
}
NAMES = {"newebpay": "NewebPay", "ecpay": "ECPay", "linepay": "LINE Pay", "payuni": "PAYUNi"}


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
    first = path.read_text(encoding="utf-8").lstrip().splitlines()[0] if path.stat().st_size else ""
    provider = next((v for v in NAMES.values() if first.startswith("# " + v)), "NewebPay")
    print(f"{provider} readiness — {title}")
    print("-" * (width + 40))
    blocking = 0
    for key, status, note in rows:
        icon = ICON.get(status, "?")
        flag = ""
        if status == "missing":
            blocking += 1
        if status in ("wait", "missing") and not note:
            flag = "   <- no owner / date: finding against the guide"
        elif status == "wait" and not (re.search(r"\d{4}-\d{2}-\d{2}", note) and "," in note):
            # a wait must name who is being waited on and since when; "applied" alone is the silent wait S16 forbids
            flag = "   <- wait without who/since date: finding against the guide"
        if flag:
            blocking += 1
        print(f"{icon} {key.ljust(width)}  {note}{flag}")
    print("-" * (width + 40))
    print(f"{blocking} item(s) missing. " + ("Not ready." if blocking else "Every row is ok, waiting with a date, or deliberately skipped."))
    return 1 if blocking else 0


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--init":
        rest = argv[1:]
        provider = "newebpay"
        if rest and rest[0] == "--provider":
            if len(rest) < 2 or rest[1] not in TEMPLATES:
                print("--provider must be one of: " + ", ".join(TEMPLATES)); return 1
            provider, rest = rest[1], rest[2:]
        p = Path(rest[0]) if rest else Path(f"docs/integrations/{provider}-readiness.yaml")
        if p.exists():
            print(f"exists: {p}"); return 1
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(TEMPLATES[provider], encoding="utf-8")
        print(f"wrote {p}"); return 0
    p = Path(argv[0]) if argv else DEFAULT
    if not p.exists():
        print(f"no readiness file at {p}; run --init"); return 1
    return render(p)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
