#!/usr/bin/env python3
"""Detect NewebPay usage in a project and say which mode the skill should enter.

Usage:  python tools/newebpay/detect.py [project-dir]        (default: cwd)
Prints JSON. Never prints secret values - only the names of env keys found.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

SIGNALS = {
    "host_sandbox": re.compile(r"ccore\.newebpay\.com"),
    "host_production": re.compile(r"(?<!c)core\.newebpay\.com"),
    "mpg_gateway": re.compile(r"MPG/mpg_gateway"),
    "trade_info": re.compile(r"\bTradeInfo\b"),
    "trade_sha": re.compile(r"\bTradeSha\b"),
    "cvscom": re.compile(r"\bCVSCOM\b"),
    "logistics_api": re.compile(r"API/Logistic/|EncryptData_|HashData_"),
    "manual_ref": re.compile(r"\bNDN[FSP]-?\d"),
    "brand": re.compile(r"newebpay|藍新", re.I),
}
ENV_KEYS = re.compile(r"^\s*(NEWEBPAY_[A-Z0-9_]+|MERCHANT_?ID|HASH_?KEY|HASH_?IV)\s*=", re.M | re.I)
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
            if "newebpay-payment" in str(p).replace("\\", "/"):
                woocommerce_plugin = True
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
            if re.search(r"notify|callback|webhook", rel, re.I) and re.search(r"TradeInfo|TradeSha|EncryptData_", text):
                callback_files.append(rel)

    detected = any(hits[k] for k in ("host_sandbox", "host_production", "mpg_gateway", "trade_sha", "cvscom", "logistics_api", "manual_ref")) or bool(env_keys) or woocommerce_plugin
    brand_only = bool(hits["brand"]) and not detected

    if not detected and not brand_only:
        mode = "not-newebpay"
    elif woocommerce_plugin:
        mode = "setup (WooCommerce module present: configure it, do not hand-write a gateway)"
    elif callback_files and (hits["host_sandbox"] or hits["host_production"]):
        mode = "audit (integration exists: callback endpoint + gateway host found) - offer setup mode if no sandbox record"
    else:
        mode = "setup (NewebPay named or configured, no working callback endpoint found)"

    vendor_docs = sorted(str(p.name) for p in root.glob(".vendor-docs/*NDN*")) if (root / ".vendor-docs").exists() else []
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
            "read references/newebpay-onboarding.md section 0, then run fetch-manuals.py"
            if detected or brand_only
            else "no NewebPay signals; if the user wants NewebPay, start at newebpay-onboarding.md section 2"
        ),
    }


if __name__ == "__main__":
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    print(json.dumps(scan(root), ensure_ascii=False, indent=2))
