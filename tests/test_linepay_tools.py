"""Tests for tools/linepay. Run from the repo root:  python tests/test_linepay_tools.py

Offline except test_probe_live_refusal, which runs only with LINEPAY_LIVE=1 (it posts fake credentials to
LINE Pay's sandbox host and expects the documented 1104; nothing can be charged).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools" / "linepay"
PHP = shutil.which("php")
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(ROOT / "tools"))

import detect  # noqa: E402
import explain_error  # noqa: E402
import fetch_docs  # noqa: E402

FAKE_ENV = {"LINEPAY_CHANNEL_ID": "1234567890", "LINEPAY_CHANNEL_SECRET": "not-a-real-secret-0000000000", "LINEPAY_CALLBACK_BASE": "https://example.test"}


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", **kw)


class DetectTests(unittest.TestCase):
    def test_fixture_shop_is_not_linepay(self):
        r = detect.scan(ROOT / "tests" / "fixture-shop")
        self.assertFalse(r["detected"])
        self.assertEqual(r["mode"], "not-linepay")

    def test_direct_signals_mean_setup_direct_and_never_leak_values(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / ".env").write_text("LINEPAY_CHANNEL_ID=1234567890\nLINEPAY_CHANNEL_SECRET=sekrit\n", encoding="utf-8")
            (p / "pay.php").write_text("$h['X-LINE-Authorization'] = sign(); post('https://sandbox-api-pay.line.me/v3/payments/request');", encoding="utf-8")
            r = detect.scan(p)
            self.assertTrue(r["direct_online_api"])
            self.assertTrue(r["mode"].startswith("setup-direct"))
            self.assertEqual(r["env_files_with_keys"][".env"], ["LINEPAY_CHANNEL_ID", "LINEPAY_CHANNEL_SECRET"])
            self.assertNotIn("sekrit", json.dumps(r))
            self.assertNotIn("1234567890", json.dumps(r))

    def test_confirm_handler_means_audit(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "LinePayConfirmController.php").write_text("post('https://api-pay.line.me/v3/payments/' . $transactionId . '/confirm', ['amount' => $amt]);", encoding="utf-8")
            r = detect.scan(p)
            self.assertTrue(r["mode"].startswith("audit"))
            self.assertEqual(r["confirm_files"], ["LinePayConfirmController.php"])

    def test_via_newebpay_is_not_direct(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "Mpg.php").write_text("$fields = ['CREDIT' => 1, 'LINEPAY' => 1, 'VACC' => 0]; // ccore.newebpay.com", encoding="utf-8")
            r = detect.scan(p)
            self.assertFalse(r["direct_online_api"])
            self.assertEqual(r["via_aggregator"], ["newebpay"])
            self.assertTrue(r["mode"].startswith("via-aggregator (newebpay)"))

    def test_ecpay_claiming_linepay_is_suspect_not_via(self):
        # ECPay's AIO ChoosePayment has no LINE Pay value (developers.ecpay.com.tw/2864.md, 2026-09-13)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "Aio.php").write_text("$f['ChoosePayment'] = $wallet === 'linepay' ? 'LINEPay' : 'Credit';", encoding="utf-8")
            r = detect.scan(p)
            self.assertEqual(r["via_aggregator"], [])
            self.assertTrue(r["suspect_ecpay_linepay"])
            self.assertTrue(r["mode"].startswith("suspect"))
            self.assertIn("2864", r["mode"])

    def test_offline_api_is_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "pos.py").write_text("requests.post(HOST + '/v2/payments/oneTimeKeys/pay', ...)", encoding="utf-8")
            r = detect.scan(p)
            self.assertTrue(r["offline_api_present"])


class SignerTests(unittest.TestCase):
    """The PHP signer's fixed-input MAC must equal an independent stdlib computation of LINE Pay's rule:
    Base64(HMAC-SHA256(secret, secret + apiPath + body + nonce)) - developers-pay.line.me/online/prerequisites."""

    SECRET = b"selftest-secret-0123456789abcdef"

    def expected(self, path: bytes, payload: bytes, nonce: bytes) -> str:
        return base64.b64encode(hmac.new(self.SECRET, self.SECRET + path + payload + nonce, hashlib.sha256).digest()).decode()

    @unittest.skipUnless(PHP, "php not on PATH")
    def test_php_selftest_matches_python_hmac(self):
        r = run([PHP, str(TOOLS / "sign.php"), "selftest"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("SELFTEST PASS", r.stdout)
        kat = [l.split(" ", 1)[1] for l in r.stdout.splitlines() if l.startswith("KAT ")][0]
        self.assertEqual(kat, self.expected(b"/v3/payments/request", b'{"amount":1,"currency":"TWD"}', b"nonce-1"))

    @unittest.skipUnless(PHP, "php not on PATH")
    def test_headers_command_signs_exact_bytes_and_hides_secret(self):
        body = '{"amount":1,"currency":"TWD"}'
        env = {**os.environ, "LINEPAY_CHANNEL_ID": "123", "LINEPAY_CHANNEL_SECRET": self.SECRET.decode()}
        r = run([PHP, str(TOOLS / "sign.php"), "headers", "POST", "/v3/payments/request", body], env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        h = dict(l.split(": ", 1) for l in r.stdout.strip().splitlines())
        self.assertEqual(h["X-LINE-ChannelId"], "123")
        self.assertNotIn(self.SECRET.decode(), r.stdout)
        nonce = h["X-LINE-Authorization-Nonce"]
        self.assertRegex(nonce, r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
        self.assertEqual(h["X-LINE-Authorization"], self.expected(b"/v3/payments/request", body.encode(), nonce.encode()))
        # GET signs the query string
        r = run([PHP, str(TOOLS / "sign.php"), "headers", "GET", "/v3/payments", "orderId=X"], env=env)
        h = dict(l.split(": ", 1) for l in r.stdout.strip().splitlines())
        self.assertEqual(h["X-LINE-Authorization"], self.expected(b"/v3/payments", b"orderId=X", h["X-LINE-Authorization-Nonce"].encode()))

    @unittest.skipUnless(PHP, "php not on PATH")
    def test_headers_refuses_without_credentials(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("LINEPAY_")}
        with tempfile.TemporaryDirectory() as d:
            r = run([PHP, str(TOOLS / "sign.php"), "headers", "POST", "/v3/payments/request", "{}"], env=env, cwd=d)
        self.assertEqual(r.returncode, 1)
        self.assertIn("LINEPAY_CHANNEL_SECRET", r.stderr)


@unittest.skipUnless(PHP, "php not on PATH")
class ProbeTests(unittest.TestCase):
    def test_dry_run_builds_reference_shape_and_redacts(self):
        with tempfile.TemporaryDirectory() as d:
            r = run([PHP, str(TOOLS / "probe_request.php"), "--dry-run"], env={**os.environ, **FAKE_ENV}, cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("DRY RUN", r.stdout)
        self.assertIn("sandbox-api-pay.line.me/v3/payments/request", r.stdout)
        body = json.loads([l for l in r.stdout.splitlines() if "bytes: {" in l][0].split("bytes: ", 1)[1])
        self.assertEqual(body["currency"], "TWD")
        self.assertEqual(body["amount"], sum(p["amount"] for p in body["packages"]))
        self.assertTrue(body["redirectUrls"]["confirmUrl"].startswith("https://example.test/"))
        self.assertNotIn(FAKE_ENV["LINEPAY_CHANNEL_SECRET"], r.stdout)
        self.assertNotIn(FAKE_ENV["LINEPAY_CHANNEL_ID"], r.stdout)

    def test_v4_flag_switches_path(self):
        with tempfile.TemporaryDirectory() as d:
            r = run([PHP, str(TOOLS / "probe_request.php"), "--dry-run", "--v4"], env={**os.environ, **FAKE_ENV}, cwd=d)
        self.assertIn("/v4/payments/request", r.stdout)

    def test_config_errors_named(self):
        env = {**os.environ, **FAKE_ENV, "LINEPAY_CALLBACK_BASE": "http://plain"}
        with tempfile.TemporaryDirectory() as d:
            r = run([PHP, str(TOOLS / "probe_request.php"), "--dry-run"], env=env, cwd=d)
        self.assertEqual(r.returncode, 1)
        self.assertIn("https", r.stderr)

    def test_production_refused_by_default(self):
        env = {**os.environ, **FAKE_ENV, "LINEPAY_ENV": "production"}
        with tempfile.TemporaryDirectory() as d:
            r = run([PHP, str(TOOLS / "probe_request.php"), "--dry-run"], env=env, cwd=d)
        self.assertEqual(r.returncode, 1)
        self.assertIn("REFUSED", r.stderr)

    def test_walk_commands_dry_run_and_sign_the_right_payload(self):
        env = {**os.environ, **FAKE_ENV}
        with tempfile.TemporaryDirectory() as d:
            c = run([PHP, str(TOOLS / "probe_request.php"), "--confirm", "2026091302381764410", "--dry-run"], env=env, cwd=d)
            self.assertIn('/v3/payments/2026091302381764410/confirm  (env=sandbox, body/query {"amount":1,"currency":"TWD"})', c.stdout)
            r = run([PHP, str(TOOLS / "probe_request.php"), "--refund", "2026091302381764410", "--dry-run"], env=env, cwd=d)
            self.assertIn("/refund  (env=sandbox, body/query {})", r.stdout)  # omitted refundAmount = full refund
            r2 = run([PHP, str(TOOLS / "probe_request.php"), "--refund", "2026091302381764410", "--amount", "5", "--dry-run"], env=env, cwd=d)
            self.assertIn('{"refundAmount":5}', r2.stdout)
            g = run([PHP, str(TOOLS / "probe_request.php"), "--details", "2026091302381764410", "--dry-run"], env=env, cwd=d)
            self.assertIn("GET https://sandbox-api-pay.line.me/v3/payments  (env=sandbox, body/query transactionId=2026091302381764410)", g.stdout)
            for r_ in (c, r, r2, g):
                self.assertEqual(r_.returncode, 0, r_.stderr)
                self.assertNotIn(FAKE_ENV["LINEPAY_CHANNEL_SECRET"], r_.stdout)

    def test_no_capture_and_capture_void_dry_runs(self):
        env = {**os.environ, **FAKE_ENV}
        with tempfile.TemporaryDirectory() as d:
            r = run([PHP, str(TOOLS / "probe_request.php"), "--no-capture", "--dry-run"], env=env, cwd=d)
            self.assertIn('"options":{"payment":{"capture":false}}', r.stdout)
            c = run([PHP, str(TOOLS / "probe_request.php"), "--capture", "2026091302381765610", "--dry-run"], env=env, cwd=d)
            self.assertIn('/v3/payments/authorizations/2026091302381765610/capture  (env=sandbox, body/query {"amount":1,"currency":"TWD"})', c.stdout)
            v = run([PHP, str(TOOLS / "probe_request.php"), "--void", "2026091302381765610", "--dry-run"], env=env, cwd=d)
            self.assertIn("/authorizations/2026091302381765610/void", v.stdout)
        src = (TOOLS / "probe_request.php").read_text(encoding="utf-8")
        self.assertIn("'2103'", src)  # live: capture:false on a sandbox merchant

    def test_probe_source_carries_the_live_learned_codes(self):
        # 1169 (confirm before approval), 1172 (second confirm), 1165 (second refund), 1150 (details before confirm):
        # all observed live 2026-09-13 - see tests/RUNS.md
        src = (TOOLS / "probe_request.php").read_text(encoding="utf-8")
        for code in ("1169", "1172", "1165", "1150", "1145", "1152"):
            self.assertIn(f"'{code}'", src)
        self.assertIn("POP-UPS", src)

    def test_probe_source_names_the_documented_refusals(self):
        src = (TOOLS / "probe_request.php").read_text(encoding="utf-8")
        for code in ("1104", "1106", "1178", "1183", "1184", "2101", "2102"):
            self.assertIn(f"'{code}'", src)

    @unittest.skipUnless(os.environ.get("LINEPAY_LIVE") == "1", "set LINEPAY_LIVE=1 to hit sandbox-api-pay.line.me")
    def test_probe_live_refusal(self):
        with tempfile.TemporaryDirectory() as d:
            r = run([PHP, str(TOOLS / "probe_request.php")], env={**os.environ, **FAKE_ENV}, cwd=d)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("returnCode 1104", r.stdout)


class ExplainErrorTests(unittest.TestCase):
    def test_linepay_prefix_and_collision_with_newebpay_logistics(self):
        self.assertIn("HMAC", explain_error.explain("linepay:1106"))
        both = explain_error.explain("1104")
        self.assertIn("AMBIGUOUS", both)
        self.assertIn("[NewebPay 物流]", both)
        self.assertIn("[LINE Pay]", both)
        self.assertIn("[LINE Pay]", explain_error.explain("1172"))  # no collision -> straight answer

    def test_same_code_two_meanings_on_check(self):
        t = explain_error.explain("linepay:0000")
        self.assertIn("not completed", t)
        self.assertIn("0110", t)

    def test_scan_mode_detects_linepay_json(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf), unittest.mock.patch("sys.stdin", io.StringIO('{"returnCode":"1104","returnMessage":"Merchant not found."}')):
            explain_error.main(["-"])
        self.assertIn("[LINE Pay]", buf.getvalue())
        self.assertNotIn("AMBIGUOUS", buf.getvalue())


class FetchDocsParserTests(unittest.TestCase):
    NAV = '<a href=/online-api-v3>v3</a><a href=/online-api-v4>v4</a><a href=/offline-api-v4>x</a>'
    TEXT = "Request payment\nPOST /v3/payments/request\nConfirm payment\nPOST /v3/payments/{transactionId}/confirm\nRetrieve\nGET /v3/payments\n"

    def test_versions_from_nav(self):
        self.assertEqual(fetch_docs.versions(self.NAV), ["online-api-v3", "online-api-v4"])

    def test_endpoints_from_text(self):
        self.assertEqual(fetch_docs.endpoints(self.TEXT), ["POST /v3/payments/request", "POST /v3/payments/{transactionId}/confirm", "GET /v3/payments"])

    def test_to_text_strips_markup(self):
        t = fetch_docs.to_text("<html><script>x()</script><h1>Sandbox</h1><p>one<br>two</p><table><tr><td>a</td><td>b</td></tr></table></html>")
        self.assertIn("Sandbox", t)
        self.assertIn("a | b |", t)
        self.assertNotIn("x()", t)


if __name__ == "__main__":
    unittest.main()
