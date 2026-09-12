#!/usr/bin/env python3
"""List, and optionally download, NewebPay's API manuals from the PRODUCTION download page.

The page returns 403 to a bare client; a browser User-Agent and Referer are enough.
Never use the sandbox portal (cwww.newebpay.com) for manuals - it has served a manual two
years older than production.

Usage:
  python tools/newebpay/fetch_manuals.py                 # list (JSON)
  python tools/newebpay/fetch_manuals.py --download DIR  # save the PDFs into DIR (e.g. .vendor-docs)
  python tools/newebpay/fetch_manuals.py --record FILE   # append a dated line per manual to FILE
                                                         #   (docs/integrations/vendor-doc-locations.md)
Stdlib only.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp950/cp1252; the output carries CJK and emoji
    sys.stdout.reconfigure(encoding="utf-8")


PAGE = "https://www.newebpay.com/website/Page/content/download_api"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36",
    "Referer": "https://www.newebpay.com/",
    "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 - fixed vendor host
        return r.read()


def strip(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", s)).replace("\xa0", " ").strip()


def parse(page: str) -> list[dict]:
    """The table is rendered client-side from JSON objects embedded in the page (keys WDI_*)."""
    docs = []
    seen = set()
    for m in re.finditer(r'\{[^{}]*"WDI_File_Name"[^{}]*\}', page):
        try:
            o = json.loads(m.group(0))
        except json.JSONDecodeError:
            continue
        name = o.get("WDI_File_Name") or ""
        if not name or name in seen:
            continue
        seen.add(name)
        upper = (o.get("WDI_Document_Number") or name).upper()
        if not name.lower().endswith(".pdf"):
            kind = "module-or-sample"
        elif "NDN" in upper:
            kind = "manual"
        elif re.search(r"申請|同意書|切結書|證明書|訪查表", name):
            kind = "form"
        elif re.search(r"條款|規範|注意事項", name):
            kind = "terms"
        elif re.search(r"手冊|Guide|API|Datachange|Flow", name, re.I):
            kind = "guide"
        else:
            kind = "other"
        family = "other"
        for tag, fam in (("NDNF", "payment MPG + query/cancel/close/wallet/BNPL"), ("NDNP", "recurring card 定期定額"), ("NDNS", "logistics 物流"), ("LINE PAY", "LINE Pay"), ("信用卡", "credit card"), ("非信用卡", "non-card methods"), ("行動支付", "mobile payment"), ("電子收據", "e-receipt"), ("NWP_", "platform / MID APIs"), ("會員", "member / account")):
            if tag in name.upper():
                family = fam
                break
        docs.append({
            "title": (o.get("WDI_Document_Name") or o.get("WDI_Model_Name") or name)[:80],
            "file": name,
            "kind": kind,
            "family": family,
            "document_version": o.get("WDI_Document_Number"),
            "program_version": o.get("WDI_Program_Number"),
            "dated": (o.get("WDI_Latest_Date") or "")[:10],
            "cms": o.get("WDI_CMS_Number"),
            "summary": (o.get("WDI_Content") or "")[:160],
            "url": "https://www.newebpay.com/website/Page/download_file?name=" + urllib.parse.quote(name),
        })
    # manuals first; within a family the newest date first - "always use latest" (owner, 2026-09-12)
    docs.sort(key=lambda d: d["file"])
    docs.sort(key=lambda d: d["dated"], reverse=True)
    docs.sort(key=lambda d: (d["kind"] != "manual", d["kind"], d["family"]))
    return docs


def main(argv: list[str]) -> int:
    page = get(PAGE).decode("utf-8", errors="replace")
    docs = parse(page)
    manuals = [d for d in docs if d["kind"] == "manual"]
    today = dt.date.today().isoformat()
    out = {"page": PAGE, "read_on": today, "manuals": manuals,
           "forms": [d for d in docs if d["kind"] == "form"],
           "guides": [d for d in docs if d["kind"] == "guide"],
           "terms": [d for d in docs if d["kind"] == "terms"],
           "modules": [d for d in docs if d["kind"] == "module-or-sample"],
           "other": [d for d in docs if d["kind"] == "other"]}

    if "--download" in argv:
        target = Path(argv[argv.index("--download") + 1])
        target.mkdir(parents=True, exist_ok=True)
        for d in manuals:
            dest = target / d["file"]
            if dest.exists():
                d["saved"] = f"exists: {dest}"
                continue
            data = get(d["url"])
            if not data.startswith(b"%PDF"):
                d["saved"] = f"NOT A PDF ({len(data)} bytes) - open the page in a browser and download by hand"
                continue
            dest.write_bytes(data)
            d["saved"] = f"{dest} ({len(data)} bytes)"

    if "--record" in argv:
        rec = Path(argv[argv.index("--record") + 1])
        rec.parent.mkdir(parents=True, exist_ok=True)
        with rec.open("a", encoding="utf-8") as f:
            f.write(f"\n## NewebPay manuals — read {today} from {PAGE}\n\n| Manual | Versions / date | URL |\n|---|---|---|\n")
            for d in manuals:
                f.write(f"| {d['title']} | {' / '.join(d['columns'])} | {d['url']} |\n")
        out["recorded_in"] = str(rec)

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if manuals else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
