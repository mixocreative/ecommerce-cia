#!/usr/bin/env python3
"""Adyen webhook HMAC: a known-answer test, and the ways it fails.

No key, no account, no network. Adyen's test environment needs a merchant account, so this is
the only part of an Adyen integration an agent can prove on its own - and it is the part that
breaks most often.

    python tools/adyen/hmac_test.py
    python tools/adyen/hmac_test.py --verify FILE --key <hex hmac key> --signature <base64>

The construction, from docs.adyen.com/development-resources/webhooks/secure-webhooks/
verify-hmac-signatures (read 2026-09-24):
  header  hmacsignature
  payload the BINARY body, exactly as received - "do not deserialize it"
  key     the BINARY form of the HMAC key (the Customer Area shows it as hex)
  mac     HMAC-SHA256, then Base64-encode the result, then compare
  scope   one key per endpoint; a NEW key when switching test -> live
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import hmac
import json
import sys


def sign(payload: bytes, key_hex: str) -> str:
    """Adyen's signature: HMAC-SHA256 over the raw bytes with the key's binary form, base64'd."""
    key = binascii.unhexlify(key_hex)
    return base64.b64encode(hmac.new(key, payload, hashlib.sha256).digest()).decode()


def verify(payload: bytes, signature: str, key_hex: str) -> tuple[bool, str]:
    try:
        expected = sign(payload, key_hex)
    except binascii.Error:
        return False, ("the key is not valid hex. The Customer Area shows the HMAC key as hex and it "
                       "must be unhexlified before use - a key used as ASCII verifies nothing")
    if not hmac.compare_digest(expected, signature):
        return False, ("no match. Either the key is the other endpoint's (Adyen binds one key per "
                       "endpoint), or it is the test key against a live event (a new key is required "
                       "on that switch), or the body is not the bytes Adyen sent")
    return True, "ok"


def self_test() -> int:
    key = "DFB1EB5485895CFA84146406857104ABB4CBCABDC8AAF103A624C8F6A3EAAB00"
    body = json.dumps({
        "live": "false",
        "notificationItems": [{
            "NotificationRequestItem": {
                "eventCode": "AUTHORISATION",
                "pspReference": "7914073381342284",
                "success": "true",
                "eventDate": "2026-09-24T10:00:00+02:00",
            }
        }],
    }, separators=(",", ":")).encode()
    good = sign(body, key)

    cases = [
        ("the happy path", body, good, key, True),
        ("the other endpoint's key (Adyen binds one key per endpoint)",
         body, good, "00" + key[2:], False),
        ("the key used as ASCII instead of unhexlified",
         body, base64.b64encode(hmac.new(key.encode(), body, hashlib.sha256).digest()).decode(),
         key, False),
        ("a body the framework deserialised and re-serialised",
         json.dumps(json.loads(body)).encode(), good, key, False),
    ]

    failures = 0
    for name, payload, signature, k, want in cases:
        ok, why = verify(payload, signature, k)
        if ok != want:
            failures += 1
        print(f"  {'ok  ' if ok == want else 'FAIL'} {name}\n         -> {why}")

    print("\n  The duplicate's identity is a PAIR, not an id: the same eventCode + pspReference with a\n"
          "  different eventDate is a re-delivery, and a handler keyed on one field alone treats it as new.")
    print("\nOK" if failures == 0 else f"\n{failures} FAILURES")
    return 0 if failures == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verify", metavar="FILE", help="a file holding the raw webhook body")
    ap.add_argument("--key", help="the HMAC key, as hex, from the Customer Area")
    ap.add_argument("--signature", help="the hmacsignature header value")
    args = ap.parse_args()

    if not args.verify:
        print("Adyen webhook HMAC - known-answer test\n")
        return self_test()
    if not (args.key and args.signature):
        print("--verify needs --key and --signature", file=sys.stderr)
        return 2
    with open(args.verify, "rb") as fh:       # rb: the bytes, never a decoded string
        payload = fh.read()
    ok, why = verify(payload, args.signature, args.key)
    print(("VERIFIED: " if ok else "REFUSED: ") + why)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
