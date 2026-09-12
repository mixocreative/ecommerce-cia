"""Tests for tools/newebpay. Run from the repo root:  python -m unittest tests.test_newebpay_tools

Offline except test_fetch_manuals_live, which is skipped unless NEWEBPAY_LIVE=1.
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
TOOLS = ROOT / "tools" / "newebpay"
PHP = shutil.which("php")
sys.path.insert(0, str(TOOLS))

import detect  # noqa: E402
import fetch_manuals  # noqa: E402
import readiness  # noqa: E402


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", **kw)


class DetectTests(unittest.TestCase):
    def test_fixture_shop_is_not_newebpay(self) -> None:
        r = detect.scan(ROOT / "tests" / "fixture-shop")
        self.assertFalse(r["detected"])
        self.assertEqual(r["mode"], "not-newebpay")

    def test_env_keys_and_host_trigger_setup_mode(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / ".env").write_text("NEWEBPAY_MERCHANT_ID=MS1\nNEWEBPAY_HASH_KEY=x\n", encoding="utf-8")
            (p / "pay.php").write_text("$url = 'https://ccore.newebpay.com/MPG/mpg_gateway';", encoding="utf-8")
            r = detect.scan(p)
            self.assertTrue(r["detected"])
            self.assertTrue(r["mode"].startswith("setup"))
            self.assertEqual(r["env_files_with_keys"][".env"], ["NEWEBPAY_HASH_KEY", "NEWEBPAY_MERCHANT_ID"])
            # names only, never values
            self.assertNotIn("MS1", json.dumps(r))

    def test_callback_endpoint_plus_host_means_audit(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "src").mkdir()
            (p / "src" / "NotifyEndpoint.php").write_text("verify($post['TradeSha'], $post['TradeInfo']); // core.newebpay.com", encoding="utf-8")
            r = detect.scan(p)
            self.assertTrue(r["mode"].startswith("audit"))
            self.assertEqual(r["callback_files"], ["src/NotifyEndpoint.php"])


class FetchManualsParserTests(unittest.TestCase):
    PAGE = (
        'var x = [{"WDI_Document_Name":"線上交易─幕前支付技術串接手冊_NDNF-9.9.9","WDI_Document_Number":"NDNF-9.9.9",'
        '"WDI_File_Name":"線上交易─幕前支付技術串接手冊_NDNF-9.9.9.pdf","WDI_Latest_Date":"2030-01-02 00:00:00","WDI_Program_Number":"3.0","WDI_Content":"x"},'
        '{"WDI_Document_Name":null,"WDI_File_Name":"藍新科技_藍新金流_行動支付機制申請表.pdf","WDI_Latest_Date":"2025-09-05 00:00:00"},'
        '{"WDI_Model_Name":"WooCommerce","WDI_File_Name":"newebpay-payment-1.0.12.zip","WDI_CMS_Number":"WordPress 6.4.3"}];'
    )

    def test_parse_embedded_json(self) -> None:
        docs = fetch_manuals.parse(self.PAGE)
        kinds = {d["file"]: d["kind"] for d in docs}
        self.assertEqual(kinds["線上交易─幕前支付技術串接手冊_NDNF-9.9.9.pdf"], "manual")
        self.assertEqual(kinds["藍新科技_藍新金流_行動支付機制申請表.pdf"], "form")
        self.assertEqual(kinds["newebpay-payment-1.0.12.zip"], "module-or-sample")
        m = next(d for d in docs if d["kind"] == "manual")
        self.assertEqual(m["document_version"], "NDNF-9.9.9")
        self.assertEqual(m["dated"], "2030-01-02")
        self.assertIn("download_file?name=", m["url"])
        self.assertEqual(docs[0]["kind"], "manual")  # manuals sort first

    @unittest.skipUnless(os.environ.get("NEWEBPAY_LIVE") == "1", "set NEWEBPAY_LIVE=1 to hit newebpay.com")
    def test_fetch_manuals_live(self) -> None:
        page = fetch_manuals.get(fetch_manuals.PAGE).decode("utf-8", "replace")
        docs = fetch_manuals.parse(page)
        families = {d["family"] for d in docs if d["kind"] == "manual"}
        self.assertTrue(any("MPG" in f for f in families), families)


class ReadinessTests(unittest.TestCase):
    def test_init_then_render_reports_missing(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "r.yaml"
            self.assertEqual(readiness.main(["--init", str(p)]), 0)
            self.assertEqual(readiness.main([str(p)]), 1)  # template has missing rows
            p.write_text("shop: ok | demo\nmethods.credit: ok | probe PASS 2026-09-12\nwaits: wait | LINE Pay, NewebPay, since 2026-09-01\n", encoding="utf-8")
            self.assertEqual(readiness.main([str(p)]), 0)


@unittest.skipUnless(PHP, "php not on PATH")
class PhpToolTests(unittest.TestCase):
    def test_probe_selftest(self) -> None:
        r = run([PHP, str(TOOLS / "probe_mpg.php"), "--selftest"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("SELFTEST PASS", r.stdout)

    def test_probe_refuses_bad_config_without_posting(self) -> None:
        env = {**os.environ, "NEWEBPAY_MERCHANT_ID": "MS1", "NEWEBPAY_HASH_KEY": "short", "NEWEBPAY_HASH_IV": "x" * 16, "NEWEBPAY_CALLBACK_BASE": "http://nope"}
        with tempfile.TemporaryDirectory() as d:
            r = run([PHP, str(TOOLS / "probe_mpg.php"), "--dry-run"], env=env, cwd=d)
        self.assertEqual(r.returncode, 1)
        self.assertIn("32 chars", r.stderr)
        self.assertIn("https", r.stderr)

    def test_probe_dry_run_redacts(self) -> None:
        env = {**os.environ, "NEWEBPAY_MERCHANT_ID": "MS123456", "NEWEBPAY_HASH_KEY": "k" * 32, "NEWEBPAY_HASH_IV": "i" * 16, "NEWEBPAY_CALLBACK_BASE": "https://example.test"}
        with tempfile.TemporaryDirectory() as d:
            r = run([PHP, str(TOOLS / "probe_mpg.php"), "--dry-run", "VACC"], env=env, cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("DRY RUN", r.stdout)
        self.assertIn("method=VACC", r.stdout)
        self.assertNotIn("MS123456", r.stdout)
        self.assertNotIn("k" * 32, r.stdout)

    def test_probe_refuses_production_by_default(self) -> None:
        env = {**os.environ, "NEWEBPAY_MERCHANT_ID": "MS1", "NEWEBPAY_HASH_KEY": "k" * 32, "NEWEBPAY_HASH_IV": "i" * 16, "NEWEBPAY_CALLBACK_BASE": "https://example.test", "NEWEBPAY_ENV": "production"}
        with tempfile.TemporaryDirectory() as d:
            r = run([PHP, str(TOOLS / "probe_mpg.php"), "--dry-run"], env=env, cwd=d)
        self.assertEqual(r.returncode, 1)
        self.assertIn("REFUSED", r.stderr)

    def test_callback_selftest_and_make_verify_roundtrip(self) -> None:
        r = run([PHP, str(TOOLS / "callback.php"), "selftest"])
        self.assertIn("SELFTEST PASS", r.stdout, r.stderr)
        env = {**os.environ, "NEWEBPAY_HASH_KEY": "a" * 32, "NEWEBPAY_HASH_IV": "b" * 16, "NEWEBPAY_MERCHANT_ID": "MS9"}
        payload = json.dumps({"Status": "SUCCESS", "Result": {"MerchantOrderNo": "ORDER_7", "Amt": 100, "PaymentType": "CREDIT", "TradeNo": "T1"}})
        with tempfile.TemporaryDirectory() as d:
            made = run([PHP, str(TOOLS / "callback.php"), "make"], env=env, cwd=d, input=payload)
            self.assertEqual(made.returncode, 0, made.stderr)
            self.assertIn("TradeSha=", made.stdout)
            ver = run([PHP, str(TOOLS / "callback.php"), "verify"], env=env, cwd=d, input=made.stdout)
            self.assertEqual(ver.returncode, 0, ver.stderr)
            out = json.loads(ver.stdout)
            self.assertEqual(out["payload"]["Result"]["MerchantOrderNo"], "ORDER_7")
            # wrong keys must be refused, not decoded into garbage
            bad = run([PHP, str(TOOLS / "callback.php"), "verify"], env={**env, "NEWEBPAY_HASH_KEY": "c" * 32}, cwd=d, input=made.stdout)
            self.assertEqual(bad.returncode, 2)
            self.assertIn("SIGNATURE MISMATCH", bad.stderr)


if __name__ == "__main__":
    unittest.main()
