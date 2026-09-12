#!/usr/bin/env python3
"""Detect ECPay 綠界 usage in a project and say which mode the skill should enter.

Usage:  python tools/ecpay/detect.py [project-dir]        (default: cwd)
Prints JSON. Never prints secret values - only the names of env keys found.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp950/cp1252; the output carries CJK and emoji
    sys.stdout.reconfigure(encoding="utf-8")


SIGNALS = {
    "host_stage": re.compile(r"(payment|logistics|ecpayment|einvoice)-stage\.ecpay\.com\.tw"),
    "host_production": re.compile(r"(?<![\w-])(payment|logistics|ecpayment|einvoice)\.ecpay\.com\.tw"),
    "aio_checkout": re.compile(r"AioCheckOut"),
    "check_mac": re.compile(r"\bCheckMacValue\b"),
    "merchant_trade_no": re.compile(r"\bMerchantTradeNo\b"),
    "doaction_envelope": re.compile(r"Credit/DoAction|\bRqHeader\b|\bRpHeader\b"),
    "logistics_api": re.compile(r"Express/(map|Create|PrintTradeDocument|QueryLogisticsTradeInfo)|\bLogisticsSubType\b|\bAllPayLogisticsID\b"),
    "docs_ref": re.compile(r"developers\.ecpay\.com\.tw"),
    "brand": re.compile(r"ecpay|綠界", re.I),
}
ENV_KEYS = re.compile(r"^\s*(ECPAY_[A-Z0-9_]+|MERCHANT_?ID|HASH_?KEY|HASH_?IV)\s*=", re.M | re.I)
SKIP_DIRS = {".git", "node_modules", "vendor", "var", "cache", ".vendor-docs", "dist", "build"}
TEXT_EXT = {".php", ".py", ".js", ".ts", ".rb", ".go", ".java", ".cs", ".md", ".yml", ".yaml", ".json", ".env", ".txt", ".html", ".twig", ".blade"}


def scan(root: Path) -> dict:
    hits: dict[str, list[str]] = {k: [] for k in SIGNALS}
    env_keys: dict[str, list[str]] = {}
    callback_files: list[str] = []
    woocommerce_plugin = False
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            p = Path(dirpath) / name
            rel = str(p.relative_to(root)).replace("\\", "/")
            if re.search(r"wp-content/plugins/[^/]*ecpay", rel, re.I):
                woocommerce_plugin = True
            if p.suffix.lower() not in TEXT_EXT and not name.startswith(".env"):
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for key, rx in SIGNALS.items():
                if rx.search(text) and len(hits[key]) < 12:
                    hits[key].append(rel)
            if name.startswith(".env"):
                found = sorted({m.group(1).upper() for m in ENV_KEYS.finditer(text)})
                if found:
                    env_keys[rel] = found
            if re.search(r"notify|return|callback|webhook|paymentinfo", rel, re.I) and re.search(r"CheckMacValue|RtnCode", text):
                callback_files.append(rel)

    strong = ("host_stage", "host_production", "aio_checkout", "check_mac", "doaction_envelope", "logistics_api", "docs_ref")
    detected = any(hits[k] for k in strong) or bool(env_keys) or woocommerce_plugin
    brand_only = bool(hits["brand"]) and not detected

    if not detected and not brand_only:
        mode = "not-ecpay"
    elif woocommerce_plugin:
        mode = "setup (WooCommerce ECPay module present: configure it, do not hand-write a gateway)"
    elif callback_files and (hits["host_stage"] or hits["host_production"]):
        mode = "audit (integration exists: callback endpoint + gateway host found) - offer setup mode if no sandbox record"
    else:
        mode = "setup (ECPay named or configured, no working callback endpoint found)"

    vendor_docs = sorted(p.name for p in root.glob(".vendor-docs/ecpay/*.md")) if (root / ".vendor-docs" / "ecpay").exists() else []
    sandbox_record = [str(p.relative_to(root)) for p in root.glob("docs/integrations/sandbox*.md")]

    return {
        "root": str(root),
        "detected": detected or brand_only,
        "mode": mode,
        "signals": {k: v for k, v in hits.items() if v},
        "env_files_with_keys": env_keys,
        "callback_files": callback_files,
        "woocommerce_module": woocommerce_plugin,
        "vendor_docs_on_disk": vendor_docs,
        "sandbox_record": sandbox_record,
        "next": (
            "read references/ecpay-onboarding.md section 0, then run tools/ecpay/fetch_docs.py --fetch .vendor-docs"
            if detected or brand_only
            else "no ECPay signals; if the user wants ECPay, start at ecpay-onboarding.md section 2"
        ),
    }


if __name__ == "__main__":
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    print(json.dumps(scan(root), ensure_ascii=False, indent=2))
