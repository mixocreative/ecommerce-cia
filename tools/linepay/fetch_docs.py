#!/usr/bin/env python3
"""Fetch the LINE Pay developer documentation (developers-pay.line.me) as plain text, and say which
Online API version is current.

The site is a Docusaurus build; pages are static HTML and need only a browser User-Agent. There is no
PDF and no login. Read 2026-09-13: the reference lists Online API v3 AND v4 (v4 added Nov 2025 for
Taiwan's Electronic Payment Institution rules; same authentication, same endpoints under /v4, plus
info.paymentProvider on confirm/capture/details and options.regPayRequest on request).

Usage:
  python tools/linepay/fetch_docs.py --latest              # which Online API versions exist, endpoints, change-log head
  python tools/linepay/fetch_docs.py --page online-api-v3/request-payment   # one page as text
  python tools/linepay/fetch_docs.py --fetch DIR [core|all] # save pages under DIR/linepay/<slug>.txt
Stdlib only.
"""
from __future__ import annotations

import datetime as dt
import html as htmllib
import re
import sys
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = "https://developers-pay.line.me"
CORE = [
    "online/prerequisites", "online/implement-basic-payment", "sandbox", "join-as-merchant", "api-change-log", "faq",
    "online-api-v3", "online-api-v3/request-payment", "online-api-v3/check-payment-request-status", "online-api-v3/confirm-payment",
    "online-api-v3/capture", "online-api-v3/void", "online-api-v3/retrieve-payment-details", "online-api-v3/refund",
    "online-api-v3/merchant/redirection-pages",
    "online-api-v4", "online-api-v4/request-payment", "online-api-v4/confirm-payment", "online-api-v4/refund",
]
ALL_EXTRA = ["online-api-v3/check-preapproved-payment-key-status", "online-api-v3/request-preapproved-payment",
             "online-api-v3/discard-preapproved-payment-key", "online-api-v4/check-payment-request-status", "online-api-v4/capture",
             "online-api-v4/void", "online-api-v4/retrieve-payment-details", "online-api-v4/merchant/redirection-pages", "glossary"]


def get(path: str) -> str:
    req = urllib.request.Request(f"{BASE}/{path}", headers={"User-Agent": "Mozilla/5.0 (ecommerce-cia doc fetcher)"})
    with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 - fixed vendor host
        return r.read().decode("utf-8", "replace")


def to_text(h: str) -> str:
    h = re.sub(r"<script.*?</script>|<style.*?</style>|<svg.*?</svg>", "", h, flags=re.S)
    h = re.sub(r"</(p|h\d|li|tr|div|pre|table)>", "\n", h)
    h = re.sub(r"<br\s*/?>", "\n", h)
    h = re.sub(r"</t[dh]>", " | ", h)
    t = htmllib.unescape(re.sub(r"<[^>]+>", "", h))
    t = re.sub(r"[ \t​]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t).strip()


def versions(index_html: str) -> list[str]:
    return sorted(set(re.findall(r"href=/?(online-api-v\d+)(?:[ >\"/])", index_html)))


def endpoints(text: str) -> list[str]:
    return re.findall(r"^(?:GET|POST) /v\d+/[^\s]+$", text, re.M)


def latest() -> str:
    idx = get("online-api-v3")
    vs = versions(idx)
    out = [f"Online API versions listed in the reference nav: {', '.join(vs) or 'none found (site changed?)'}"]
    for v in vs:
        t = to_text(get(v))
        out.append(f"\n{v}: {len(endpoints(t))} endpoints")
        out.extend("  " + e for e in endpoints(t))
    cl = to_text(get("api-change-log"))
    m = re.search(r"This page provides the LINE Pay API change log.*?\n(.*?)\n", cl, re.S)
    out.append("\nChange log, most recent heading: " + (m.group(1).strip() if m else "(unparsed)"))
    out.append("Prerequisites page: " + f"{BASE}/online/prerequisites  (HMAC headers)")
    out.append("Sandbox page: " + f"{BASE}/sandbox  (one sandbox account per email; credentials in Merchant Center > Developer Tools > Manage Link Key)")
    return "\n".join(out)


def fetch(outdir: Path, which: str) -> None:
    pages = CORE + (ALL_EXTRA if which == "all" else [])
    d = outdir / "linepay"
    d.mkdir(parents=True, exist_ok=True)
    stamp = dt.date.today().isoformat()
    for p in pages:
        try:
            t = to_text(get(p))
        except Exception as e:  # noqa: BLE001 - report and continue
            print(f"  ! {p}: {e}")
            continue
        f = d / (p.replace("/", "_") + ".txt")
        f.write_text(f"# {BASE}/{p}\n# fetched {stamp}\n\n{t}\n", encoding="utf-8")
        print(f"  {f} ({len(t)} chars)")


def main(argv: list[str]) -> int:
    if "--latest" in argv:
        print(latest())
        return 0
    if "--page" in argv:
        print(to_text(get(argv[argv.index("--page") + 1])))
        return 0
    if "--fetch" in argv:
        i = argv.index("--fetch")
        fetch(Path(argv[i + 1]), argv[i + 2] if len(argv) > i + 2 else "core")
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
