#!/usr/bin/env python3
"""Stripe webhook signatures: a known-answer test, and the four ways verification fails.

Needs no key, no network and no Stripe account. It exists because the signature is the one
part of a Stripe integration that fails identically whether the bug is in the secret, the
body, the clock or the code — and an audit that cannot tell those apart guesses.

    python tools/stripe/sign_test.py              # self-test: the construction and its failures
    python tools/stripe/sign_test.py --verify FILE --secret whsec_... --header "t=...,v1=..."

The construction, from docs.stripe.com/webhooks/signature (read 2026-09-24):
  header  Stripe-Signature: t=<unix ts>,v1=<hex hmac>[,v0=<older scheme>]
  payload <t> "." <the raw request body, byte for byte>
  mac     HMAC-SHA256(payload, endpoint secret), compared in constant time
  clock   <t> is checked against now; a verifier that ignores it accepts replays forever
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import sys
import time

DEFAULT_TOLERANCE = 300  # seconds; Stripe's libraries default to five minutes


def sign(payload: bytes, secret: str, timestamp: int) -> str:
    """Return the v1 signature for this exact body."""
    signed = f"{timestamp}.".encode() + payload
    return hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()


def header_for(payload: bytes, secret: str, timestamp: int | None = None) -> str:
    ts = int(time.time()) if timestamp is None else timestamp
    return f"t={ts},v1={sign(payload, secret, ts)}"


def parse(header: str) -> tuple[int | None, list[str]]:
    ts, v1s = None, []
    for part in header.split(","):
        key, _, value = part.strip().partition("=")
        if key == "t" and value.isdigit():
            ts = int(value)
        elif key == "v1":
            v1s.append(value)
    return ts, v1s


def verify(payload: bytes, header: str, secret: str, tolerance: int = DEFAULT_TOLERANCE,
           now: int | None = None) -> tuple[bool, str]:
    """Return (ok, reason). The reason is the point of this function."""
    ts, v1s = parse(header)
    if ts is None:
        return False, "no t= in the header: the timestamp is missing, so replay cannot be detected"
    if not v1s:
        return False, "no v1= in the header: nothing to compare"

    expected = sign(payload, secret, ts)
    if not any(hmac.compare_digest(expected, given) for given in v1s):
        return False, ("no v1 matches. The secret is wrong, or the body is not the bytes Stripe "
                       "sent (a framework parsed and re-serialised it)")

    age = (int(time.time()) if now is None else now) - ts
    if abs(age) > tolerance:
        return False, f"signature is valid but {age}s old, outside the {tolerance}s tolerance: a replay"

    return True, "ok"


def self_test() -> int:
    secret = "whsec_test_fixture_secret"
    body = json.dumps({"id": "evt_1", "type": "payment_intent.succeeded"},
                      separators=(",", ":")).encode()
    now = 1_700_000_000
    good = header_for(body, secret, now)

    cases = [
        ("the happy path", body, good, secret, True),
        ("a wrong endpoint secret (CLI secret against a Dashboard endpoint)",
         body, good, "whsec_the_other_one", False),
        ("a body a framework re-serialised (same JSON, different bytes)",
         json.dumps(json.loads(body)).encode(), good, secret, False),
        ("a header with no t=", body, good.split(",", 1)[1], secret, False),
        ("a replayed event, correctly signed, six minutes old",
         body, header_for(body, secret, now - 360), secret, False),
    ]

    failures = 0
    for name, payload, header, key, want in cases:
        ok, why = verify(payload, header, key, now=now)
        mark = "ok  " if ok == want else "FAIL"
        if ok != want:
            failures += 1
        print(f"  {mark} {name}\n         -> {why}")

    # The re-serialisation case is the one people do not believe until they see it.
    reparsed = json.dumps(json.loads(body)).encode()
    print(f"\n  the two bodies differ by {abs(len(reparsed) - len(body))} bytes of whitespace "
          f"and verify differently; that is the whole bug")

    print("\nOK" if failures == 0 else f"\n{failures} FAILURES")
    return 0 if failures == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verify", metavar="FILE", help="a file holding the raw request body")
    ap.add_argument("--secret")
    ap.add_argument("--header")
    ap.add_argument("--tolerance", type=int, default=DEFAULT_TOLERANCE)
    args = ap.parse_args()

    if not args.verify:
        print("Stripe webhook signature - known-answer test\n")
        return self_test()

    if not (args.secret and args.header):
        print("--verify needs --secret and --header", file=sys.stderr)
        return 2

    with open(args.verify, "rb") as fh:           # rb: the bytes, not a decoded string
        payload = fh.read()
    ok, why = verify(payload, args.header, args.secret, args.tolerance)
    print(("VERIFIED: " if ok else "REFUSED: ") + why)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
