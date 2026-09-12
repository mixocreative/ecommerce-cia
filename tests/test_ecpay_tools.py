"""Tests for tools/ecpay and tools/explain_error.py. Run from the repo root:  python tests/test_ecpay_tools.py

Offline except the live tests, which run only with ECPAY_LIVE=1 (they use ECPay's public stage
merchant 3002607 - published test credentials, stage host only).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools" / "ecpay"
PHP = shutil.which("php")
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(ROOT / "tools"))

import detect  # noqa: E402
import explain_error  # noqa: E402
import fetch_docs  # noqa: E402

STAGE_ENV = {"ECPAY_MERCHANT_ID": "3002607", "ECPAY_HASH_KEY": "pwFHCqoQZGmho4w6", "ECPAY_HASH_IV": "EkRm7iFT261dpevs", "ECPAY_CALLBACK_BASE": "https://example.test", "ECPAY_ENV": "stage"}


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", **kw)


class DetectTests(unittest.TestCase):
    def test_fixture_shop_is_not_ecpay(self):
        self.assertEqual(detect.scan(ROOT / "tests" / "fixture-shop")["mode"], "not-ecpay")

    def test_env_and_host_mean_setup(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / ".env").write_text("ECPAY_MERCHANT_ID=3002607\nECPAY_HASH_KEY=x\n", encoding="utf-8")
            (p / "pay.php").write_text("$u='https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5';", encoding="utf-8")
            r = detect.scan(p)
            self.assertTrue(r["mode"].startswith("setup"))
            self.assertNotIn("3002607", json.dumps(r))

    def test_docs_named_ecpay_payment_are_not_a_woocommerce_module(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "docs"
            p.mkdir()
            (p / "ecpay-payment-fees.md").write_text("CheckMacValue rules", encoding="utf-8")
            r = detect.scan(Path(d))
            self.assertFalse(r["woocommerce_module"])

    def test_callback_plus_host_means_audit(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "src"
            p.mkdir()
            (p / "EcpayReturn.php").write_text("if ($post['RtnCode'] === '1') {} // payment.ecpay.com.tw", encoding="utf-8")
            self.assertTrue(detect.scan(Path(d))["mode"].startswith("audit"))


class FetchDocsTests(unittest.TestCase):
    def test_page_table_has_the_load_bearing_pages(self):
        aio = fetch_docs.PAGES["aio"]
        for pid in (2856, 2864, 2902, 2878, 2881, 2890, 45919, 45948, 10092):
            self.assertIn(pid, aio)
        self.assertIn(10127, fetch_docs.PAGES["logistics"])

    def test_is_markdown(self):
        self.assertTrue(fetch_docs.is_markdown("# title\n\ntext"))
        self.assertFalse(fetch_docs.is_markdown("<!DOCTYPE html><html>"))

    @unittest.skipUnless(os.environ.get("ECPAY_LIVE") == "1", "set ECPAY_LIVE=1")
    def test_live_checkmac_page_is_markdown(self):
        text = fetch_docs.get(f"{fetch_docs.BASE}2902.md").decode("utf-8", "replace")
        self.assertTrue(fetch_docs.is_markdown(text))
        self.assertIn("6C51C9E6888DE861FD62FB1DD17029FC742634498FD813DC43D4243B5685B840", text)


class ExplainErrorTests(unittest.TestCase):
    def test_known_codes_both_gateways(self):
        for code in ("MPG02003", "10200079", "1106", "TRA10071", "10100073"):
            out = explain_error.explain(code)
            self.assertIn("Do this", out, code)
            self.assertIn("Source", out, code)

    def test_unknown_code_points_to_the_manual(self):
        self.assertIn("not in this table", explain_error.explain("MPG99999"))
        self.assertIn("newebpay.com", explain_error.explain("MPG99999"))
        self.assertIn("ecpay", explain_error.explain("10999999").lower())

    def test_scan_text_mode(self):
        r = run([sys.executable, str(ROOT / "tools" / "explain_error.py"), "-"], input="<b>10200073</b> CheckMacValue Error and MPG02003")
        self.assertEqual(r.returncode, 0)
        self.assertIn("10200073", r.stdout)
        self.assertIn("MPG02003", r.stdout)


@unittest.skipUnless(PHP, "php not on PATH")
class PhpToolTests(unittest.TestCase):
    def test_checkmac_known_answer(self):
        r = run([PHP, str(TOOLS / "callback.php"), "selftest"])
        self.assertIn("SELFTEST PASS", r.stdout, r.stdout + r.stderr)

    def test_sign_matches_worked_example_and_make_verify_roundtrip(self):
        env = {**os.environ, "ECPAY_HASH_KEY": "pwFHCqoQZGmho4w6", "ECPAY_HASH_IV": "EkRm7iFT261dpevs"}
        sample = {"ChoosePayment": "ALL", "EncryptType": "1", "ItemName": "Apple iphone 15", "MerchantID": "3002607", "MerchantTradeDate": "2023/03/12 15:30:23", "MerchantTradeNo": "ecpay20230312153023", "PaymentType": "aio", "ReturnURL": "https://www.ecpay.com.tw/receive.php", "TotalAmount": "30000", "TradeDesc": "促銷方案"}
        with tempfile.TemporaryDirectory() as d:
            s = run([PHP, str(TOOLS / "callback.php"), "sign"], env=env, cwd=d, input=json.dumps(sample, ensure_ascii=False))
            self.assertEqual(s.stdout.strip(), "6C51C9E6888DE861FD62FB1DD17029FC742634498FD813DC43D4243B5685B840", s.stderr)
            body = run([PHP, str(TOOLS / "callback.php"), "make"], env=env, cwd=d, input=json.dumps({"MerchantID": "3002607", "MerchantTradeNo": "X1", "RtnCode": "1", "TradeAmt": "100", "SimulatePaid": "1"}))
            v = run([PHP, str(TOOLS / "callback.php"), "verify"], env=env, cwd=d, input=body.stdout)
            self.assertEqual(v.returncode, 0, v.stderr)
            out = json.loads(v.stdout)
            self.assertEqual(out["reply_with"], "1|OK")
            self.assertTrue(any("SimulatePaid" in n for n in out["notes"]))
            bad = run([PHP, str(TOOLS / "callback.php"), "verify"], env={**env, "ECPAY_HASH_IV": "wrongwrongwrong1"}, cwd=d, input=body.stdout)
            self.assertEqual(bad.returncode, 2)

    def test_probe_dry_run_and_production_refusal(self):
        with tempfile.TemporaryDirectory() as d:
            r = run([PHP, str(TOOLS / "probe_aio.php"), "ATM", "--dry-run"], env={**os.environ, **STAGE_ENV}, cwd=d)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("method=ATM", r.stdout)
            self.assertNotIn("3002607", r.stdout)
            self.assertNotIn("pwFHCqoQZGmho4w6", r.stdout)
            p = run([PHP, str(TOOLS / "probe_aio.php"), "--dry-run"], env={**os.environ, **STAGE_ENV, "ECPAY_ENV": "production"}, cwd=d)
            self.assertEqual(p.returncode, 1)
            self.assertIn("REFUSED", p.stderr)

    @unittest.skipUnless(os.environ.get("ECPAY_LIVE") == "1", "set ECPAY_LIVE=1")
    def test_probe_live_pass_and_wrong_keys(self):
        with tempfile.TemporaryDirectory() as d:
            ok = run([PHP, str(TOOLS / "probe_aio.php"), "Credit"], env={**os.environ, **STAGE_ENV}, cwd=d)
            self.assertEqual(ok.returncode, 0, ok.stdout)
            bad = run([PHP, str(TOOLS / "probe_aio.php"), "Credit"], env={**os.environ, **STAGE_ENV, "ECPAY_HASH_IV": "wrongwrongwrong1"}, cwd=d)
            self.assertEqual(bad.returncode, 2)
            self.assertIn("10200073", bad.stdout)


if __name__ == "__main__":
    unittest.main()
