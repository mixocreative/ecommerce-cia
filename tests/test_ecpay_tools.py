"""Tests for tools/ecpay and tools/explain_error.py. Run from the repo root:  python tests/test_ecpay_tools.py

Offline except the live tests, which run only with ECPAY_LIVE=1 (they use ECPay's public stage
merchant 3002607 - published test credentials, stage host only).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import urllib.parse
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


class CheckMacValueRuleTests(unittest.TestCase):
    """ECPay's published worked example (developers.ecpay.com.tw/2902.md) recomputed with the stdlib, independently of
    the PHP tool, so the algorithm - not just the tool - is pinned: sort A-Z case-insensitive, HashKey=..&k=v..&HashIV=..,
    urlencode with the .NET replacements, lowercase, SHA-256, uppercase."""

    KEY, IV = "pwFHCqoQZGmho4w6", "EkRm7iFT261dpevs"
    SAMPLE = {"ChoosePayment": "ALL", "EncryptType": "1", "ItemName": "Apple iphone 15", "MerchantID": "3002607", "MerchantTradeDate": "2023/03/12 15:30:23", "MerchantTradeNo": "ecpay20230312153023", "PaymentType": "aio", "ReturnURL": "https://www.ecpay.com.tw/receive.php", "TotalAmount": "30000", "TradeDesc": "促銷方案"}
    EXPECT = "6C51C9E6888DE861FD62FB1DD17029FC742634498FD813DC43D4243B5685B840"

    @classmethod
    def mac(cls, fields: dict, key: str, iv: str) -> str:
        items = sorted(((k, v) for k, v in fields.items() if k != "CheckMacValue"), key=lambda kv: kv[0].lower())
        raw = f"HashKey={key}&" + "&".join(f"{k}={v}" for k, v in items) + f"&HashIV={iv}"
        enc = urllib.parse.quote_plus(raw, safe="")
        for a, b in (("%2D", "-"), ("%5F", "_"), ("%2E", "."), ("%21", "!"), ("%2A", "*"), ("%28", "("), ("%29", ")")):
            enc = enc.replace(a, b)
        return hashlib.sha256(enc.lower().encode()).hexdigest().upper()

    def test_worked_example_reproduces(self):
        self.assertEqual(self.mac(self.SAMPLE, self.KEY, self.IV), self.EXPECT)

    def test_case_insensitive_sort_matters(self):
        # the worked example's keys all start uppercase, so it cannot tell ordinal from case-insensitive sorting
        # (a vacuous check, S21); this pair can - and the PHP tool must agree with the case-insensitive rule
        fields = {"Zeta": "1", "alpha": "2", "MerchantID": "3002607"}
        ordinal = f"HashKey={self.KEY}&" + "&".join(f"{k}={v}" for k, v in sorted(fields.items())) + f"&HashIV={self.IV}"
        ordinal_mac = hashlib.sha256(urllib.parse.quote_plus(ordinal, safe="").lower().encode()).hexdigest().upper()
        self.assertNotEqual(self.mac(fields, self.KEY, self.IV), ordinal_mac)
        if PHP:
            with tempfile.TemporaryDirectory() as d:
                r = run([PHP, str(TOOLS / "callback.php"), "sign"], env={**os.environ, "ECPAY_HASH_KEY": self.KEY, "ECPAY_HASH_IV": self.IV}, cwd=d, input=json.dumps(fields))
            self.assertEqual(r.stdout.strip(), self.mac(fields, self.KEY, self.IV), r.stderr)

    def test_wrong_iv_gives_the_10200073_case(self):
        self.assertNotEqual(self.mac(self.SAMPLE, self.KEY, "wrongwrongwrong1"), self.EXPECT)

    def test_urlencoding_space_and_slash_follow_dotnet(self):
        # "Apple iphone 15" -> "apple+iphone+15", "https://" -> "https%3a%2f%2f" after lowercasing
        items = sorted(self.SAMPLE.items(), key=lambda kv: kv[0].lower())
        raw = f"HashKey={self.KEY}&" + "&".join(f"{k}={v}" for k, v in items) + f"&HashIV={self.IV}"
        enc = urllib.parse.quote_plus(raw, safe="").lower()
        self.assertIn("apple+iphone+15", enc)
        self.assertIn("https%3a%2f%2fwww.ecpay.com.tw%2freceive.php", enc.replace("%2e", "."))


class ExplainErrorECPayTests(unittest.TestCase):
    def test_result_codes_that_are_not_payments(self):
        for code in ("10100073", "2"):
            t = explain_error.explain(code)
            self.assertIn("[ECPay]", t)
            self.assertIn("NOT a payment", t)
        self.assertIn("do NOT ship", explain_error.explain("10300066"))

    def test_live_verified_refusals(self):
        self.assertIn("CheckMacValue", explain_error.explain("10200073"))
        self.assertIn("not activated", explain_error.explain("10200079"))
        self.assertIn("MerchantID", explain_error.explain("10100251"))

    def test_unknown_ecpay_code_points_to_the_result_page(self):
        t = explain_error.explain("10999999")
        self.assertIn("not in this table", t)
        self.assertIn("2878", t)


@unittest.skipUnless(PHP, "php not on PATH")
class PhpToolDepthTests(unittest.TestCase):
    ENV = {"ECPAY_HASH_KEY": "pwFHCqoQZGmho4w6", "ECPAY_HASH_IV": "EkRm7iFT261dpevs"}

    def _verify(self, body: str, env=None):
        with tempfile.TemporaryDirectory() as d:
            return run([PHP, str(TOOLS / "callback.php"), "verify"], env={**os.environ, **self.ENV, **(env or {})}, cwd=d, input=body)

    def _make(self, fields: dict) -> str:
        with tempfile.TemporaryDirectory() as d:
            r = run([PHP, str(TOOLS / "callback.php"), "make"], env={**os.environ, **self.ENV}, cwd=d, input=json.dumps(fields, ensure_ascii=False))
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def test_paid_callback_has_no_notes_and_acks_1_ok(self):
        out = json.loads(self._verify(self._make({"MerchantID": "3002607", "MerchantTradeNo": "P1", "RtnCode": "1", "RtnMsg": "交易成功", "TradeAmt": "100", "PaymentType": "Credit_CreditCard"})).stdout)
        self.assertEqual(out["notes"], [])
        self.assertEqual(out["reply_with"], "1|OK")
        self.assertEqual(out["fields"]["MerchantTradeNo"], "P1")

    def test_code_issued_callback_is_flagged_not_paid(self):
        # RtnCode 2 (ATM 取號) and 10100073 (CVS/BARCODE 取號) arrive on PaymentInfoURL and must not fulfil anything
        for code in ("2", "10100073"):
            out = json.loads(self._verify(self._make({"MerchantID": "3002607", "MerchantTradeNo": "A1", "RtnCode": code, "TradeAmt": "100", "PaymentType": "ATM_LAND"})).stdout)
            self.assertTrue(any("NOT a successful payment" in n for n in out["notes"]), code)

    def test_tampered_amount_is_refused(self):
        body = self._make({"MerchantID": "3002607", "MerchantTradeNo": "T1", "RtnCode": "1", "TradeAmt": "100"})
        r = self._verify(body.replace("TradeAmt=100", "TradeAmt=1"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("SIGNATURE MISMATCH", r.stderr)
        self.assertEqual(r.stdout.strip(), "")

    def test_lowercase_checkmac_accepted_md5_length_detected(self):
        body = self._make({"MerchantID": "3002607", "MerchantTradeNo": "L1", "RtnCode": "1", "TradeAmt": "5"})
        mac = body.split("CheckMacValue=")[1].split("&")[0]
        self.assertEqual(self._verify(body.replace(mac, mac.lower())).returncode, 0)

    def test_non_aio_body_is_named_not_guessed(self):
        r = self._verify("Data=abcdef&TransCode=1&TransMsg=x")
        self.assertEqual(r.returncode, 1)
        self.assertIn("not an AIO callback", r.stderr)

    def test_probe_selftest_and_all_methods_dry_run(self):
        r = run([PHP, str(TOOLS / "probe_aio.php"), "--selftest"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        with tempfile.TemporaryDirectory() as d:
            for m in ("Credit", "WebATM", "ATM", "CVS", "BARCODE", "BNPL"):
                p = run([PHP, str(TOOLS / "probe_aio.php"), m, "--dry-run"], env={**os.environ, **STAGE_ENV}, cwd=d)
                self.assertEqual(p.returncode, 0, m + p.stderr)
                self.assertIn(f"method={m}", p.stdout)
                self.assertIn("payment-stage.ecpay.com.tw", p.stdout)

    def test_probe_names_stage_refusals_in_source(self):
        src = (TOOLS / "probe_aio.php").read_text(encoding="utf-8")
        for code in ("10200073", "10200079", "10100251"):
            self.assertIn(code, src)


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
