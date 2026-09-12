#!/usr/bin/env python3
"""Fetch PAYUNi 統一金流 documentation pages as markdown from docs.payuni.com.tw (a ShowDoc site).

The site is a SPA; its pages are served by a JSON API that needs no login:
  POST /server/index.php?s=/api/item/info  item_id=7      -> the whole menu (page ids + titles)
  POST /server/index.php?s=/api/page/info  page_id=<id>   -> {page_title, page_content (markdown)}
Page ids are the `#/7/<id>` in the browser URL.

Usage:
  python tools/payuni/fetch_docs.py --index                # print every page id + title
  python tools/payuni/fetch_docs.py --page 34              # print one page's markdown
  python tools/payuni/fetch_docs.py --fetch DIR [core|all] # save pages into DIR/payuni/<id>-<slug>.md
Stdlib only. Read 2026-09-13; if the API shape changes, open the site and update.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = "https://docs.payuni.com.tw"
ITEM = 7
CORE = {24: "overview", 34: "upp-request", 374: "test-data", 170: "amount-limits", 29: "crypto-php", 56: "crypto-array",
        80: "notify-upp", 73: "notify-atm-paid", 74: "notify-cvs-paid", 75: "notify-order-expired",
        164: "query-single", 38: "refund-credit", 39: "void-credit", 76: "noncard-refund-request",
        103: "logistics-store-map", 124: "logistics-query", 123: "logistics-label", 291: "logistics-status-notify", 120: "logistics-status-codes",
        156: "errors-common", 44: "errors-upp", 119: "errors-logistics", 245: "forms", 67: "sdk"}


def post(path: str, body: dict) -> dict:
    req = urllib.request.Request(f"{BASE}/server/index.php?s={path}", data=urllib.parse.urlencode(body).encode(),
                                 headers={"User-Agent": "Mozilla/5.0 (ecommerce-cia doc fetcher)", "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 - fixed vendor host
        return json.load(r)


def index() -> list[tuple[int | None, str]]:
    menu = post("/api/item/info", {"item_id": ITEM})["data"]["menu"]
    out: list[tuple[int | None, str]] = []

    def walk(m: dict, d: int = 0) -> None:
        for p in m.get("pages", []):
            out.append((int(p["page_id"]), "  " * d + p["page_title"]))
        for c in m.get("catalogs", []):
            out.append((None, "  " * d + "[" + c["cat_name"] + "]"))
            walk(c, d + 1)

    walk(menu)
    return out


def page(pid: int) -> tuple[str, str]:
    d = post("/api/page/info", {"page_id": pid}).get("data") or {}
    return d.get("page_title", ""), (d.get("page_content") or "").replace("\r", "")


def main(argv: list[str]) -> int:
    today = dt.date.today().isoformat()
    if "--index" in argv:
        for pid, title in index():
            print(f"{pid if pid is not None else '':>5}  {title}")
        return 0
    if "--page" in argv:
        title, body = page(int(argv[argv.index("--page") + 1]))
        print(f"# {title}\n\n{body}")
        return 0
    if "--fetch" in argv:
        target = Path(argv[argv.index("--fetch") + 1]) / "payuni"
        scope = argv[argv.index("--fetch") + 2] if len(argv) > argv.index("--fetch") + 2 else "core"
        target.mkdir(parents=True, exist_ok=True)
        ids = dict(CORE) if scope == "core" else {pid: re.sub(r"[^a-z0-9]+", "-", t.strip().lower())[:40] for pid, t in index() if pid}
        out = []
        for pid, slug in ids.items():
            try:
                title, body = page(pid)
            except Exception as e:  # noqa: BLE001
                out.append({"id": pid, "saved": f"ERROR {e}"}); continue
            dest = target / f"{pid}-{slug or 'page'}.md"
            dest.write_text(f"<!-- {BASE}/web/#/{ITEM}/{pid} read {today} -->\n\n# {title}\n\n{body}", encoding="utf-8")
            out.append({"id": pid, "title": title[:60], "saved": str(dest), "bytes": len(body)})
        print(json.dumps({"read_on": today, "pages": out}, ensure_ascii=False, indent=2))
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
