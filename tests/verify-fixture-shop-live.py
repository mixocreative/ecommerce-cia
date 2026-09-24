#!/usr/bin/env python3
"""Prove that every row of EXPECTED-fixture-shop-live.md still reproduces.

This is the scorer's tool and the fixture's own regression test. It is NOT for the auditor:
it names every planted defect. It lives here, beside the answer key and outside the audited
directory, for the reason the RUNBOOK gives — a key inside the tree is a key the auditor hits.

    python tests/verify-fixture-shop-live.py            # assumes the shop is already serving
    python tests/verify-fixture-shop-live.py --serve    # start and stop the shop itself

Exit 0 when every planted defect reproduced and both controls held.
"""
from __future__ import annotations

import hashlib
import os
import hmac
import json
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHOP = HERE / "fixture-shop-live"
BASE = "http://127.0.0.1:8123"
SECRET = b"fixture-shared-secret"

results: list[tuple[str, bool, str]] = []


def check(row: str, condition: bool, detail: str) -> None:
    results.append((row, condition, detail))
    print(f"  {'REPRODUCED' if condition else 'GONE      '}  {row:<28} {detail}")


def get(path: str) -> str:
    with urllib.request.urlopen(BASE + path, timeout=10) as r:
        return r.read().decode()


def post(path: str, fields: dict) -> str:
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(BASE + path, data=data)
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.read().decode()


def state() -> dict:
    return json.loads(get("/debug/state"))


def stock(st: dict, sku: str) -> int:
    return next(p["stock"] for p in st["products"] if p["sku"] == sku)


def cached(st: dict, sku: str) -> int:
    return next(c["qty"] for c in st["cache"] if c["sku"] == sku)


def sign(fields: dict) -> str:
    flat = "&".join(f"{k}={fields[k]}" for k in sorted(fields))
    return hmac.new(SECRET, flat.encode(), hashlib.sha256).hexdigest()


def notify(order_id, result, event_id, tamper=False) -> str:
    f = {"order_id": str(order_id), "result": result, "event_id": event_id}
    f["sig"] = sign(f)
    if tamper:
        f["result"] = "paid" if result == "declined" else "declined"
    return post("/gateway/callback", f)


def reset() -> None:
    subprocess.run(["php", "bin/reset.php"], cwd=SHOP,
                   check=True, capture_output=True)


def main() -> int:
    server = None
    if "--serve" in sys.argv:
        subprocess.run(["php", "bin/reset.php"], cwd=SHOP, check=True, capture_output=True)
        server = subprocess.Popen(["php", "-S", "127.0.0.1:8123", "-t", "public"], cwd=SHOP,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)

    try:
        print("fixture-shop-live — planted rows\n")

        # L2 — the storefront reads a cache nothing refreshes
        reset()
        before = get("/product?sku=CUP-STD")
        post("/checkout", {"sku": "CUP-STD", "qty": "2", "email": "walk@example.com"})
        after = get("/product?sku=CUP-STD")
        st = state()
        check("L2 stale storefront",
              '>5</span> in stock' in before and '>5</span> in stock' in after and stock(st, "CUP-STD") == 3,
              f"page said 5 before and after; the row holds {stock(st, 'CUP-STD')}")

        # L4 — the admin stock screen cannot show a variant at all
        reset()
        post("/checkout", {"sku": "CUP-STD-BLK", "qty": "2", "email": "walk@example.com"})
        admin = get("/admin/stock")
        st = state()
        check("L4 admin blind to variant",
              'data-admin-stock="CUP-STD-BLK"' not in admin and stock(st, "CUP-STD-BLK") == 3,
              f"no admin row for the variant; the row holds {stock(st, 'CUP-STD-BLK')}")

        # L6 — no server-side floor on quantity
        reset()
        post("/checkout", {"sku": "CUP-STD", "qty": "-3", "email": "walk@example.com"})
        st = state()
        neg = [o for o in st["orders"] if o["total_cents"] < 0]
        check("L6 negative quantity",
              stock(st, "CUP-STD") == 8 and len(neg) == 1,
              f"stock rose to {stock(st, 'CUP-STD')}; order total {neg[0]['total_cents'] if neg else 'n/a'}")

        # L1 — two customers take the last unit at once
        # Two processes, not two threads: PHP's built-in server answers one request at a time,
        # so an HTTP probe on this fixture serialises and proves nothing. On a server that
        # forks (PHP_CLI_SERVER_WORKERS=4, Unix) the same race reproduces over HTTP.
        reset()
        post("/admin/stock", {"sku": "BOWL-LG", "qty": "1"})
        env = {**os.environ, "FIXTURE_SLOW_MS": "400"}
        racers = [subprocess.Popen(["php", "bin/place.php", "BOWL-LG", "1", f"race{i}@example.com"],
                                   cwd=SHOP, env=env, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                  for i in (1, 2)]
        for r in racers:
            r.wait(timeout=30)
        st = state()
        placed = [o for o in st["orders"] if o["sku"] == "BOWL-LG"]
        check("L1 oversell race",
              len(placed) == 2 and stock(st, "BOWL-LG") <= 0,
              f"{len(placed)} orders for 1 unit; stock now {stock(st, 'BOWL-LG')}")

        # L3 — the same declined notification twice releases twice
        reset()
        post("/checkout", {"sku": "CUP-STD", "qty": "2", "email": "walk@example.com"})
        oid = state()["orders"][0]["id"]
        notify(oid, "declined", "evt-dup")
        mid = stock(state(), "CUP-STD")
        notify(oid, "declined", "evt-dup")
        st = state()
        check("L3 duplicate release",
              mid == 5 and stock(st, "CUP-STD") == 7,
              f"one release -> {mid}, the same notification again -> {stock(st, 'CUP-STD')}")

        # L9 — a notification for an order that does not exist is acknowledged
        reset()
        body = notify(9999, "paid", "evt-ghost")
        st = state()
        check("L9 ghost acknowledged",
              body.strip() == "1|OK" and not st["notices"],
              f"answered {body.strip()!r}; notices written: {len(st['notices'])}")

        # L7 — the page links a stylesheet the documented run command cannot serve
        import urllib.error
        try:
            get("/shop.css")
            css = 200
        except urllib.error.HTTPError as e:
            css = e.code
        check("L7 stylesheet 404",
              css == 404 and 'href="/shop.css"' in get("/"),
              f"every page links /shop.css; it answers {css}")

        # L8 — a refusal the customer is never told about
        reset()
        post("/checkout", {"sku": "CUP-STD", "qty": "999", "email": "walk@example.com"})
        st = state()
        check("L8 silent refusal",
              not st["orders"] and not st["notices"],
              "no order, no notice, no message anywhere")

        # L5 — a refund inside the policy window does not return the unit
        reset()
        post("/checkout", {"sku": "CUP-STD", "qty": "2", "email": "walk@example.com"})
        oid = state()["orders"][0]["id"]
        notify(oid, "paid", "evt-paid")
        post("/admin/refund", {"order_id": str(oid)})
        st = state()
        order = next(o for o in st["orders"] if o["id"] == oid)
        check("L5 refund never restocks",
              order["status"] == "refunded" and stock(st, "CUP-STD") == 3,
              f"order {order['status']}, stock still {stock(st, 'CUP-STD')} (POLICY.md §8 says 5)")

        # C1 — expiry is correct and tells the operator
        reset()
        post("/checkout", {"sku": "CUP-STD", "qty": "2", "email": "walk@example.com"})
        subprocess.run(["php", "-r",
                        "require 'src/Db.php'; Fixture\\Db::conn()->exec(\"UPDATE orders SET deadline_at='2000-01-01 00:00:00'\");"],
                       cwd=SHOP, check=True, capture_output=True)
        subprocess.run(["php", "bin/cron.php", "expire"], cwd=SHOP, check=True, capture_output=True)
        st = state()
        check("C1 control: expiry",
              stock(st, "CUP-STD") == 5 and any(n["audience"] == "operator" for n in st["notices"]),
              "unit returned and the operator was told — must NOT be filed as a defect")

        # C3 — the availability sentence degrades visibly, never to a number
        reset()
        page = get("/checkout/express?sku=CUP-STD")
        check("C3 control: availability",
              "5 available." in page,
              "the sentence states the live number — must NOT be filed as a defect")

        # C4 — the correct twin of L1: two processes, one unit, exactly one winner
        reset()
        post("/admin/stock", {"sku": "BOWL-LG", "qty": "1"})
        env = {**os.environ, "FIXTURE_SLOW_MS": "400"}
        racers = [subprocess.Popen(["php", "bin/take.php", "BOWL-LG", "1"], cwd=SHOP, env=env,
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                  for _ in (1, 2)]
        outs = [r.communicate()[0].decode().strip() for r in racers]
        st = state()
        check("C4 control: safe take",
              sorted(outs) == ['{"ok":false}', '{"ok":true}'] and stock(st, "BOWL-LG") == 0,
              f"one winner, one refusal, stock {stock(st, 'BOWL-LG')} — must NOT be filed as a defect")

        # C5 — the correct twin of L8: a refusal the customer is actually told about
        reset()
        post("/checkout/express", {"sku": "CUP-STD", "qty": "99", "email": "walk@example.com"})
        st = state()
        said = get("/checkout/express?sku=CUP-STD&sorry=x")
        check("C5 control: spoken refusal",
              not st["orders"] and any(n["audience"] == "customer" for n in st["notices"])
              and stock(st, "CUP-STD") == 5 and 'data-notice="refused"' in said,
              "nothing taken, a customer notice written, the sentence rendered — must NOT be filed as a defect")

        # C2 — the signature check is correct
        reset()
        post("/checkout", {"sku": "CUP-STD", "qty": "1", "email": "walk@example.com"})
        oid = state()["orders"][0]["id"]
        body = notify(oid, "declined", "evt-tampered", tamper=True)
        st = state()
        check("C2 control: signature",
              body.strip() == "0|signature" and stock(st, "CUP-STD") == 4,
              "a tampered notification is refused — must NOT be filed as a defect")

        reset()

    finally:
        if server is not None:
            server.terminate()

    gone = [r for r, ok_, _ in results if not ok_]
    print()
    if gone:
        print(f"FAIL: {len(gone)} row(s) no longer reproduce: {', '.join(gone)}")
        print("The fixture changed, or the shop was not freshly seeded. The answer key is wrong until this passes.")
        return 1
    print(f"OK: {len(results)} rows reproduce (9 defects + 7 controls).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
