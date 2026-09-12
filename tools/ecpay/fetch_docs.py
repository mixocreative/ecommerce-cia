#!/usr/bin/env python3
"""Fetch ECPay's developer documentation as markdown.

Every page on developers.ecpay.com.tw has a markdown twin at https://developers.ecpay.com.tw/<id>.md
(the HTML at ?p=<id> is the same content rendered). Read the markdown: a shipped integration
misread the HTML three times on one page. This script saves the pages for one product family
into a folder and prints a dated inventory for docs/integrations/vendor-doc-locations.md.

Usage:
  python tools/ecpay/fetch_docs.py                     # list the known page ids (no network)
  python tools/ecpay/fetch_docs.py --fetch DIR [family] # save pages into DIR/ecpay/<id>-<slug>.md
  python tools/ecpay/fetch_docs.py --page 2902         # print one page to stdout
Families: aio (default), logistics, invoice, all.  Stdlib only.

Page ids as of 2026-09-12 - ECPay adds pages; if a fetch returns HTML instead of markdown or a
404, open https://developers.ecpay.com.tw/ in a browser and update the table.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
import urllib.request
from pathlib import Path

BASE = "https://developers.ecpay.com.tw/"
PAGES = {
    "aio": {
        2856: "test-environment: 測試介接資訊 - public stage MerchantIDs, HashKey/HashIV, test cards, 3D OTP 1234, stage backoffice logins",
        2864: "aio-request: 全方位金流付款 request parameters, ChoosePayment values, stage/prod hosts",
        2902: "checkmacvalue: 檢查碼機制 algorithm and worked example (known-answer test)",
        2878: "payment-result: 付款結果通知 - reply '1|OK', RtnCode 1, retries 4/day, duplicates, OrderResultURL warning",
        2881: "payment-info: ATM / CVS / BARCODE 取號結果通知 (PaymentInfoURL)",
        2866: "credit-once: 信用卡一次付清",
        2890: "query-trade: 查詢訂單 (use before showing a result when the callback is late)",
        2862: "create-order: 產生訂單 - the AIO flow overview",
        5679: "payment-methods: 付款方式一覽表 - every ChoosePayment / ChooseSubPayment value",
        5675: "extra-returned: 額外回傳的參數 (NeedExtraPaidInfo)",
        45919: "doaction: 信用卡請退款 DoAction - production only, stage cannot authorise; JSON + AES-128 Data",
        45948: "aes-param-encryption: 參數加密方式說明 - AES-128-CBC PKCS7, urlencode then encrypt, base64",
        10092: "connection-rules: 介接注意事項 - TLS 1.2, 443, no IDN, no HTML in values, keys never in front-end",
        2887: "query-intro: 查詢訂單 / 簡介",
    },
    "logistics": {
        10075: "full-logistics: 全方位物流服務 (AES Data envelope family) - index",
        10127: "full-logistics-notify: 物流狀態通知 - reply is the same encrypted envelope with RtnCode 1; retry hourly x3",
        7380: "logistics-integration: 物流整合 (CheckMacValue family) - index",
        7420: "logistics-integration-notify: 貨態通知 - reply the bare string 1|OK",
    },
    "invoice": {
        7849: "invoice-test-environment: 電子發票 測試環境 - public test MerchantID/PlatformID, stage backoffice",
    },
}


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (ecommerce-cia doc fetcher)", "Accept": "text/markdown,text/plain,*/*"})
    with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 - fixed vendor host
        return r.read()


def is_markdown(text: str) -> bool:
    head = text.lstrip()[:400].lower()
    return not head.startswith("<!doctype") and not head.startswith("<html")


def slug(desc: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", desc.split(":", 1)[0].lower()).strip("-")


def main(argv: list[str]) -> int:
    today = dt.date.today().isoformat()
    if "--page" in argv:
        pid = argv[argv.index("--page") + 1]
        sys.stdout.write(get(f"{BASE}{pid}.md").decode("utf-8", "replace"))
        return 0
    if "--fetch" in argv:
        target = Path(argv[argv.index("--fetch") + 1]) / "ecpay"
        fam = argv[argv.index("--fetch") + 2] if len(argv) > argv.index("--fetch") + 2 else "aio"
        families = list(PAGES) if fam == "all" else [fam]
        target.mkdir(parents=True, exist_ok=True)
        out = []
        for f in families:
            for pid, desc in PAGES[f].items():
                url = f"{BASE}{pid}.md"
                try:
                    text = get(url).decode("utf-8", "replace")
                except Exception as e:  # noqa: BLE001
                    out.append({"id": pid, "family": f, "url": url, "saved": f"ERROR {e}"}); continue
                if not is_markdown(text):
                    out.append({"id": pid, "family": f, "url": url, "saved": "NOT MARKDOWN - page id moved; open the site and update PAGES"}); continue
                dest = target / f"{pid}-{slug(desc)}.md"
                dest.write_text(f"<!-- {url} read {today} -->\n\n{text}", encoding="utf-8")
                title = next((l.strip('# ').strip() for l in text.splitlines() if l.startswith('#')), "")
                out.append({"id": pid, "family": f, "url": url, "title": title[:80], "saved": str(dest), "bytes": len(text)})
        print(json.dumps({"read_on": today, "pages": out}, ensure_ascii=False, indent=2))
        return 0 if all("ERROR" not in p["saved"] and "NOT MARKDOWN" not in p["saved"] for p in out) else 1
    print(json.dumps({"base": BASE, "note": "append .md to a page id for markdown; ?p=<id> is the HTML twin", "pages": PAGES}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
