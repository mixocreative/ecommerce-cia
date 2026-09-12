#!/usr/bin/env python3
"""Detect LINE Pay usage in a project and say which mode the skill should enter - and, crucially, WHICH
LINE Pay: direct (Online API, your own Channel ID/Secret) or via an aggregator (NewebPay LINEPAY=1,
PAYUNi LinePay=1). ECPay's AIO has no LINE Pay flag (2864.md, 2026-09-13) - code that claims one is reported as suspect. The two are different contracts, different prerequisites, different
failure codes; a project that has both is audited as two channels.

Usage:  python tools/linepay/detect.py [project-dir]        (default: cwd)
Prints JSON. Never prints secret values - only the names of env keys found.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SIGNALS = {
    "host_sandbox": re.compile(r"sandbox-api-pay\.line\.me"),
    "host_production": re.compile(r"(?<![\w-])api-pay\.line\.me"),
    "online_api_path": re.compile(r"/v[34]/payments/(request|requests|authorizations|preapprovedPay)|/v[34]/payments\b"),
    "auth_headers": re.compile(r"X-LINE-Authorization(-Nonce)?|X-LINE-ChannelId"),
    "offline_api": re.compile(r"/v2(\.4)?/payments/oneTimeKeys|/v4/payments/oneTimeKeys"),
    "via_newebpay": re.compile(r"\bLINEPAY\b\s*(=>|=|:)\s*['\"]?1|'LINEPAY'\s*=>|\"LINEPAY\"\s*:"),
    "via_ecpay": re.compile(r"ChoosePayment.{0,40}(LINEPay|LinePay)|ECPAY.{0,60}LINE ?PAY", re.I | re.S),
    "via_payuni": re.compile(r"payuni.{0,80}line ?pay|LinePay.{0,20}(MerID|EncryptInfo)", re.I | re.S),
    "brand": re.compile(r"LINE ?Pay|LINEPAY", re.I),
}
ENV_KEYS = re.compile(r"^\s*(LINE_?PAY_[A-Z0-9_]+|LINEPAY[A-Z0-9_]*|CHANNEL_?ID|CHANNEL_?SECRET)\s*=", re.M | re.I)
SKIP_DIRS = {".git", "node_modules", "vendor", "var", "cache", ".vendor-docs", "dist", "build"}
TEXT_EXT = {".php", ".py", ".js", ".ts", ".rb", ".go", ".java", ".cs", ".md", ".yml", ".yaml", ".json", ".env", ".txt", ".html", ".twig", ".blade"}


def scan(root: Path) -> dict:
    hits: dict[str, list[str]] = {k: [] for k in SIGNALS}
    env_keys: dict[str, list[str]] = {}
    confirm_files: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            p = Path(dirpath) / name
            if p.suffix.lower() not in TEXT_EXT and not name.startswith(".env"):
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            rel = str(p.relative_to(root)).replace("\\", "/")
            for key, rx in SIGNALS.items():
                if rx.search(text) and len(hits[key]) < 12:
                    hits[key].append(rel)
            if name.startswith(".env"):
                found = sorted({m.group(1).upper() for m in ENV_KEYS.finditer(text)})
                if found:
                    env_keys[rel] = found
            if re.search(r"confirm|linepay|line_pay", rel, re.I) and re.search(r"/payments/[^/'\"]*/confirm|transactionId", text):
                confirm_files.append(rel)

    direct = bool(hits["host_sandbox"] or hits["host_production"] or hits["online_api_path"] or hits["auth_headers"] or hits["offline_api"]) or bool(env_keys)
    via = [k[4:] for k in ("via_newebpay", "via_payuni") if hits[k]]
    suspect_ecpay = bool(hits["via_ecpay"])  # ECPay AIO cannot render LINE Pay; the code promises what the hosted page will not show
    brand_only = bool(hits["brand"]) and not direct and not via

    if not direct and not via and not brand_only and not suspect_ecpay:
        mode = "not-linepay"
    elif direct and confirm_files:
        mode = "audit (direct Online API integration exists: confirm step found) - walk request -> confirmUrl -> confirm as one channel"
    elif direct:
        mode = "setup-direct (Online API host/headers or LINEPAY_* env named, no confirm handler found)"
    elif via:
        mode = f"via-aggregator ({', '.join(via)}): LINE Pay is one method flag of that gateway - use that provider's guide; the only LINE-Pay-specific fact is that the vendor's 客服 must enable it"
    elif suspect_ecpay:
        mode = "suspect: code names LINE Pay under ECPay, but ECPay's AIO has no LINE Pay flag (developers.ecpay.com.tw/2864.md) - S17 finding: a method promised that the hosted page cannot show"
    else:
        mode = "setup-undecided (LINE Pay named, nothing wired) - ask direct vs via NewebPay/PAYUNi first (linepay-onboarding.md section 0)"

    return {
        "root": str(root),
        "detected": direct or bool(via) or brand_only or suspect_ecpay,
        "direct_online_api": direct,
        "via_aggregator": via,
        "suspect_ecpay_linepay": suspect_ecpay,
        "offline_api_present": bool(hits["offline_api"]),
        "mode": mode,
        "signals": {k: v for k, v in hits.items() if v},
        "env_files_with_keys": env_keys,
        "confirm_files": confirm_files,
        "next": (
            "read references/linepay-onboarding.md section 0 (direct vs via), then run fetch_docs.py --latest"
            if direct or via or brand_only or suspect_ecpay
            else "no LINE Pay signals; if the user wants LINE Pay, start at linepay-onboarding.md section 0"
        ),
    }


if __name__ == "__main__":
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    print(json.dumps(scan(root), ensure_ascii=False, indent=2))
