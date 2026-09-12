"""Tests for tools/payuni and tools/tappay. Run from the repo root:  python tests/test_payuni_tappay_tools.py
Offline except the live PAYUNi refusal check (PAYUNI_LIVE=1) which posts fake credentials to the sandbox.
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
PHP = shutil.which("php")
sys.path.insert(0, str(ROOT / "tools" / "payuni"))
sys.path.insert(0, str(ROOT / "tools"))
import detect  # noqa: E402
import explain_error  # noqa: E402
import fetch_docs  # noqa: E402

FAKE = {"PAYUNI_MER_ID": "PROBE000", "PAYUNI_AES_KEY": "k" * 32, "PAYUNI_AES_IV": "1234567890123456", "PAYUNI_CALLBACK_BASE": "https://example.test", "PAYUNI_ENV": "sandbox"}


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", **kw)


class PayuniDetectTests(unittest.TestCase):
    def test_fixture_shop_not_payuni(self):
        self.assertEqual(detect.scan(ROOT / "tests" / "fixture-shop")["mode"], "not-payuni")

    def test_upp_host_and_env_mean_setup(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / ".env").write_text("PAYUNI_MER_ID=x\n", encoding="utf-8")
            (p / "pay.php").write_text("post('https://sandbox-api.payuni.com.tw/api/upp', $EncryptInfo)", encoding="utf-8")
            r = detect.scan(p)
            self.assertTrue(r["mode"].startswith("setup"))
            self.assertIn("host_sandbox", r["signals"])
            self.assertIn("upp", r["signals"])

    def test_fetch_docs_core_ids(self):
        for pid in (34, 374, 170, 29, 156, 245):
            self.assertIn(pid, fetch_docs.CORE)


class ExplainTests(unittest.TestCase):
    def test_payuni_and_tappay_codes(self):
        for c in ("DEF01007", "DEF01005", "API00009", "915", "10006"):
            self.assertIn("Do this", explain_error.explain(c), c)
        self.assertIn("payuni", explain_error.explain("DEF99999").lower())
        self.assertIn("tappaysdk", explain_error.explain("10009").lower())


@unittest.skipUnless(PHP, "php not on PATH")
class PhpTests(unittest.TestCase):
    def test_crypto_selftest_and_roundtrip(self):
        r = run([PHP, str(ROOT / "tools/payuni/crypto.php"), "selftest"])
        self.assertIn("SELFTEST PASS", r.stdout, r.stdout + r.stderr)
        env = {**os.environ, **FAKE}
        with tempfile.TemporaryDirectory() as d:
            e = run([PHP, str(ROOT / "tools/payuni/crypto.php"), "encrypt"], env=env, cwd=d, input=json.dumps({"MerID": "AAA", "MerTradeNo": "B_1", "Status": "SUCCESS", "TradeStatus": "0"}))
            self.assertEqual(e.returncode, 0, e.stderr)
            j = json.loads(e.stdout)
            body = f"EncryptInfo={j['EncryptInfo']}&HashInfo={j['HashInfo']}"
            dcr = run([PHP, str(ROOT / "tools/payuni/crypto.php"), "decrypt"], env=env, cwd=d, input=body)
            self.assertEqual(dcr.returncode, 0, dcr.stderr)
            out = json.loads(dcr.stdout)
            self.assertEqual(out["payload"]["MerTradeNo"], "B_1")
            self.assertTrue(any("NOT paid" in n for n in out["notes"]))
            bad = run([PHP, str(ROOT / "tools/payuni/crypto.php"), "decrypt"], env={**env, "PAYUNI_AES_IV": "6543210987654321"}, cwd=d, input=body)
            self.assertEqual(bad.returncode, 2)

    def test_probe_dry_run_redacts_and_checks_port(self):
        with tempfile.TemporaryDirectory() as d:
            r = run([PHP, str(ROOT / "tools/payuni/probe_upp.php"), "CVS", "--dry-run"], env={**os.environ, **FAKE}, cwd=d)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("flag=CVS", r.stdout)
            self.assertNotIn("PROBE000", r.stdout)
            bad = run([PHP, str(ROOT / "tools/payuni/probe_upp.php"), "--dry-run"], env={**os.environ, **FAKE, "PAYUNI_CALLBACK_BASE": "https://example.test:8443"}, cwd=d)
            self.assertEqual(bad.returncode, 1)
            self.assertIn("80 or 443", bad.stderr)

    @unittest.skipUnless(os.environ.get("PAYUNI_LIVE") == "1", "set PAYUNI_LIVE=1")
    def test_probe_live_refusal_on_fake_credentials(self):
        with tempfile.TemporaryDirectory() as d:
            r = run([PHP, str(ROOT / "tools/payuni/probe_upp.php"), "Credit"], env={**os.environ, **FAKE}, cwd=d)
            self.assertEqual(r.returncode, 2, r.stdout)
            self.assertIn("商店不存在", r.stdout)

    def test_tappay_dry_run(self):
        with tempfile.TemporaryDirectory() as d:
            r = run([PHP, str(ROOT / "tools/tappay/probe_prime.php"), "--dry-run"], env={**os.environ, "TAPPAY_PARTNER_KEY": "p" * 64, "TAPPAY_MERCHANT_ID": "demo"}, cwd=d)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("DRY RUN", r.stdout)
            self.assertNotIn("p" * 64, r.stdout)
            prod = run([PHP, str(ROOT / "tools/tappay/probe_prime.php"), "--dry-run"], env={**os.environ, "TAPPAY_PARTNER_KEY": "p" * 64, "TAPPAY_MERCHANT_ID": "demo", "TAPPAY_ENV": "production"}, cwd=d)
            self.assertEqual(prod.returncode, 1)


if __name__ == "__main__":
    unittest.main()
