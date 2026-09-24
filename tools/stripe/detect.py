#!/usr/bin/env python3
"""Is this codebase on Stripe, which API, and where is the webhook route?

    python tools/stripe/detect.py [path]

Answers the three questions §0.5 needs before the Stripe guide is worth loading, and one the
guide cares about more than Stripe's own docs do: whether anything between the socket and the
signature check can have re-serialised the body.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SKIP = {".git", "node_modules", "vendor", "dist", "build", "__pycache__", ".venv", "venv"}
EXT = {".php", ".py", ".js", ".ts", ".jsx", ".tsx", ".rb", ".go", ".java", ".cs", ".json", ".env",
       ".yml", ".yaml", ".toml", ".lock"}

SIGNALS = {
    "sdk": [r"stripe/stripe-php", r"\bstripe\b\s*[:=]", r"@stripe/stripe-js", r"stripe-node",
            r"import\s+stripe", r"require\(['\"]stripe['\"]\)", r"Stripe\\\\StripeClient"],
    "checkout_sessions": [r"checkout\.sessions?\.create", r"Checkout\\\\Session", r"initCheckoutElementsSdk",
                          r"CheckoutElementsProvider"],
    "payment_intents": [r"payment_?intents?\.create", r"PaymentIntent", r"confirmCardPayment",
                        r"client_secret"],
    "webhook": [r"Stripe-Signature", r"constructEvent", r"Webhook::constructEvent",
                r"construct_event", r"whsec_"],
    "keys_in_source": [r"sk_live_[A-Za-z0-9]", r"sk_test_[A-Za-z0-9]", r"rk_live_[A-Za-z0-9]"],
    "body_reserialised": [r"json_encode\s*\(\s*json_decode", r"JSON\.stringify\s*\(\s*JSON\.parse",
                          r"express\.json\(\)", r"bodyParser"],
}


def scan(root: Path) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {k: [] for k in SIGNALS}
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in EXT:
            continue
        if any(part in SKIP for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for name, patterns in SIGNALS.items():
            for pat in patterns:
                for m in re.finditer(pat, text):
                    line = text.count("\n", 0, m.start()) + 1
                    hits[name].append(f"{path.relative_to(root)}:{line}")
                    break
    return hits


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    hits = scan(root)

    if not hits["sdk"] and not hits["webhook"] and not hits["payment_intents"]:
        print(f"stripe: NOT DETECTED under {root}")
        return 1

    api = ("Checkout Sessions" if hits["checkout_sessions"]
           else "Payment Intents (raw)" if hits["payment_intents"] else "unclear")
    print(f"stripe: DETECTED under {root}")
    print(f"  api: {api}"
          + ("" if api != "Payment Intents (raw)" else
             "  <- Stripe recommends Checkout Sessions for most shops; the whole status machine"
             " in references/stripe-onboarding.md §2 is this shop's to get right"))

    for name, label in (("sdk", "sdk / dependency"), ("checkout_sessions", "checkout sessions"),
                        ("payment_intents", "payment intents"), ("webhook", "webhook / signature")):
        if hits[name]:
            print(f"  {label}: " + ", ".join(sorted(set(hits[name]))[:6]))

    if not hits["webhook"]:
        print("  webhook: NONE FOUND - a shop taking Stripe payments with no signed-event handler"
              " learns about payments only from the browser (invariant 1)")

    if hits["body_reserialised"]:
        print("  BODY RISK: " + ", ".join(sorted(set(hits["body_reserialised"]))[:6]))
        print("    read §3: a parsed-and-re-serialised body fails signature verification for every"
              " event, and in Express the middleware ORDER decides it")

    if hits["keys_in_source"]:
        print("  SECRET IN SOURCE: " + ", ".join(sorted(set(hits["keys_in_source"]))[:6]))
        print("    a secret key in a tracked file is a finding regardless of environment")

    return 0


if __name__ == "__main__":
    sys.exit(main())
