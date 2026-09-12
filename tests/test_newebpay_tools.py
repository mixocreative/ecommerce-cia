"""Tests for tools/newebpay. Run from the repo root:  python -m unittest tests.test_newebpay_tools

Offline except test_fetch_manuals_live, which is skipped unless NEWEBPAY_LIVE=1.
"""
from __future__ import annotations

import hashlib
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

sys.path.insert(0, str(ROOT / "tools"))
import explain_error  # noqa: E402

KAT = json.loads((TOOLS / "manual-example.json").read_text(encoding="utf-8"))


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


class VendorKnownAnswerTests(unittest.TestCase):
    """The NDNF-1.2.5 manual (§4.1) prints key, IV, plaintext, TradeInfo and TradeSha for one request, and a complete
    signed NotifyURL body. Those are the vendor's own numbers; reproducing them is the only proof that the codec is
    NewebPay's codec and not merely self-consistent."""

    def test_vector_is_the_manual_example(self):
        self.assertEqual(KAT["merchant_id"], "MS127874575")
        self.assertEqual(len(KAT["hash_key"]), 32)
        self.assertEqual(len(KAT["hash_iv"]), 16)
        self.assertEqual(len(KAT["trade_info"]), 448)
        self.assertTrue(KAT["plain"].startswith("MerchantID=MS127874575&RespondType=String&TimeStamp=1695795410&Version=2.0"))
        self.assertIn("NDNF-1.2.5", KAT["_source"])

    def test_tradesha_rule_reproduces_manual_with_stdlib(self):
        # TradeSha = SHA-256 upper of "HashKey={key}&{TradeInfo}&HashIV={iv}" - no PHP needed for this half
        msg = f"HashKey={KAT['hash_key']}&{KAT['trade_info']}&HashIV={KAT['hash_iv']}".encode()
        self.assertEqual(hashlib.sha256(msg).hexdigest().upper(), KAT["trade_sha"])
        # the classic mistake - signing the plaintext - must NOT reproduce it
        wrong = f"HashKey={KAT['hash_key']}&{KAT['plain']}&HashIV={KAT['hash_iv']}".encode()
        self.assertNotEqual(hashlib.sha256(wrong).hexdigest().upper(), KAT["trade_sha"])

    def test_callback_body_signature_reproduces_with_stdlib(self):
        import urllib.parse
        f = dict(urllib.parse.parse_qsl(KAT["callback_body"]))
        self.assertEqual(f["Status"], "SUCCESS")
        self.assertEqual(f["MerchantID"], KAT["merchant_id"])
        msg = f"HashKey={KAT['hash_key']}&{f['TradeInfo']}&HashIV={KAT['hash_iv']}".encode()
        self.assertEqual(hashlib.sha256(msg).hexdigest().upper(), f["TradeSha"])

    def test_wrong_iv_changes_tradesha_the_mpg03009_case(self):
        bad_iv = KAT["hash_iv"][:-1] + ("X" if KAT["hash_iv"][-1] != "X" else "Y")
        msg = f"HashKey={KAT['hash_key']}&{KAT['trade_info']}&HashIV={bad_iv}".encode()
        self.assertNotEqual(hashlib.sha256(msg).hexdigest().upper(), KAT["trade_sha"])

    @unittest.skipUnless(PHP, "php not on PATH")
    def test_php_encrypt_reproduces_manual_tradeinfo(self):
        r = run([PHP, str(TOOLS / "probe_mpg.php"), "--selftest"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("vendor known-answer NDNF-1.2.5", r.stdout)
        self.assertIn("TradeInfo 448 hex", r.stdout)
        self.assertIn(KAT["trade_sha"][:8], r.stdout)

    @unittest.skipUnless(PHP, "php not on PATH")
    def test_php_verify_accepts_manual_callback_and_decodes_it(self):
        env = {**os.environ, "NEWEBPAY_HASH_KEY": KAT["hash_key"], "NEWEBPAY_HASH_IV": KAT["hash_iv"]}
        with tempfile.TemporaryDirectory() as d:
            r = run([PHP, str(TOOLS / "callback.php"), "verify"], env=env, cwd=d, input=KAT["callback_body"])
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertTrue(out["verified"])
        for k, v in KAT["callback_expect"].items():
            self.assertEqual(str(out["payload"][k]), str(v), k)
        self.assertEqual(out["outer"]["MerchantID"], KAT["merchant_id"])

    @unittest.skipUnless(PHP, "php not on PATH")
    def test_selftest_fails_when_the_vector_is_tampered(self):
        # the test of the test: copy the tool dir, flip one hex digit of the expected TradeInfo, selftest must go red
        with tempfile.TemporaryDirectory() as d:
            dst = Path(d) / "newebpay"
            shutil.copytree(TOOLS, dst)
            k = dict(KAT)
            k["trade_info"] = k["trade_info"][:-1] + ("0" if k["trade_info"][-1] != "0" else "1")
            (dst / "manual-example.json").write_text(json.dumps(k), encoding="utf-8")
            r = run([PHP, str(dst / "probe_mpg.php"), "--selftest"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("DIFFERS", r.stdout)

    @unittest.skipUnless(PHP, "php not on PATH")
    def test_verify_with_wrong_iv_is_refused_before_decrypt(self):
        env = {**os.environ, "NEWEBPAY_HASH_KEY": KAT["hash_key"], "NEWEBPAY_HASH_IV": "0123456789abcdef"}
        with tempfile.TemporaryDirectory() as d:
            r = run([PHP, str(TOOLS / "callback.php"), "verify"], env=env, cwd=d, input=KAT["callback_body"])
        self.assertEqual(r.returncode, 2)
        self.assertIn("SIGNATURE MISMATCH", r.stderr)
        self.assertEqual(r.stdout.strip(), "")  # nothing decoded, nothing leaked

    @unittest.skipUnless(PHP, "php not on PATH")
    def test_verify_accepts_lowercase_tradesha_and_rejects_logistics_body(self):
        env = {**os.environ, "NEWEBPAY_HASH_KEY": KAT["hash_key"], "NEWEBPAY_HASH_IV": KAT["hash_iv"]}
        low = KAT["callback_body"].replace("TradeSha=" + KAT["callback_body"].split("TradeSha=")[1], "TradeSha=" + KAT["callback_body"].split("TradeSha=")[1].lower())
        with tempfile.TemporaryDirectory() as d:
            r = run([PHP, str(TOOLS / "callback.php"), "verify"], env=env, cwd=d, input=low)
            self.assertEqual(r.returncode, 0, r.stderr)
            r2 = run([PHP, str(TOOLS / "callback.php"), "verify"], env=env, cwd=d, input="EncryptData_=abcd&HashData_=ef01&UID_=x")
        self.assertEqual(r2.returncode, 1)
        self.assertIn("logistics", r2.stderr)


class ExplainErrorNewebPayTests(unittest.TestCase):
    def test_live_verified_codes_have_actions(self):
        for code, must in (("MPG02003", "not enabled"), ("MPG03009", "SHA 256"), ("TRA10071", "LOCKED"), ("TRA10702", "LOCKED"), ("CHK00007", "TradeSha")):
            t = explain_error.explain(code)
            self.assertIn("[NewebPay]", t, code)
            self.assertIn(must, t, code)
            self.assertIn("Do this", t)

    def test_logistics_codes_are_newebpay_logistics(self):
        self.assertIn("[NewebPay 物流]", explain_error.explain("1106"))
        self.assertIn("IP", explain_error.explain("1106"))
        self.assertIn("idempotency", explain_error.explain("1103"))

    def test_unknown_mpg_code_points_to_the_manual_not_memory(self):
        t = explain_error.explain("MPG99999")
        self.assertIn("not in this table", t)
        self.assertIn("download_api", t)

    def test_scan_mode_finds_codes_in_a_gateway_page(self):
        import io
        import unittest.mock
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf), unittest.mock.patch("sys.stdin", io.StringIO('<div class="error">MPG02003 該商店未開啟此付款方式</div>')):
            explain_error.main(["-"])
        self.assertIn("MPG02003 [NewebPay]", buf.getvalue())


class FetchManualsEdgeTests(unittest.TestCase):
    def test_empty_page_yields_no_docs(self):
        self.assertEqual(fetch_manuals.parse("<html>no json here</html>"), [])

    def test_newer_manual_version_sorts_first(self):
        page = ('[{"WDI_Document_Name":"線上交易─幕前支付技術串接手冊_NDNF-1.2.4","WDI_Document_Number":"NDNF-1.2.4","WDI_File_Name":"a_NDNF-1.2.4.pdf","WDI_Latest_Date":"2025-01-01 00:00:00"},'
                '{"WDI_Document_Name":"線上交易─幕前支付技術串接手冊_NDNF-1.2.5","WDI_Document_Number":"NDNF-1.2.5","WDI_File_Name":"a_NDNF-1.2.5.pdf","WDI_Latest_Date":"2026-09-01 00:00:00"}]')
        docs = [d for d in fetch_manuals.parse(page) if d["kind"] == "manual"]
        self.assertEqual(docs[0]["document_version"], "NDNF-1.2.5")


class ReadinessEdgeTests(unittest.TestCase):
    def test_wait_without_owner_or_date_is_a_finding(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "r.yaml"
            p.write_text("shop: ok | demo\nmethods.linepay: wait | applied\n", encoding="utf-8")
            self.assertEqual(readiness.main([str(p)]), 1)
            p.write_text("shop: ok | demo\nmethods.linepay: wait | LINE Pay, NewebPay 客服, since 2026-09-01\n", encoding="utf-8")
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

    def test_probe_names_both_live_refusals(self) -> None:
        src = (TOOLS / "probe_mpg.php").read_text(encoding="utf-8")
        for code in ("MPG02003", "MPG03009"):
            self.assertIn(code, src)
        self.assertIn('"payType"', src)

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
