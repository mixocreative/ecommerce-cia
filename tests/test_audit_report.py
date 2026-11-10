"""Guard tests for tools/audit_report.py and the receipt leak rule in tools/receipts.py.

Why: the checker is what makes a run read its references; a checker that passes a report with no
receipts, or a SKILL.md that quotes a receipt, puts the reading collapse back.
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import audit_report  # noqa: E402
import receipts  # noqa: E402


def full_report():
    found, _ = receipts.scan()
    by_key = {("sweeps/" if k.startswith("sweeps/") else k): v for k, v in found.items()}
    quoted = " | ".join(f'{k} "{by_key[k]}"' for k in audit_report.ALWAYS)
    sweeps = "\n".join(f"- S{n}: swept, 0 findings, sites: a.php:1" for n in range(1, 25))
    lines = "\n".join(f"{n}. line {n}" for n in range(1, 16))
    return f"Owner paragraph: not safe.\n{sweeps}\n{lines}\nReference receipts: {quoted}\n"


class AuditReportTests(unittest.TestCase):
    def test_a_complete_report_passes(self):
        self.assertTrue(all(ok for _, ok, _ in audit_report.checks(full_report())))

    def test_every_always_file_has_a_receipt(self):
        found, _ = receipts.scan()
        keys = {("sweeps/" if k.startswith("sweeps/") else k) for k in found}
        self.assertEqual([f for f in audit_report.ALWAYS if f not in keys], [])

    def test_a_missing_receipt_names_the_file(self):
        found, _ = receipts.scan()
        report = full_report().replace(found["evidence.md"], "something else")
        self.assertEqual(audit_report.receipts_missing(report), ["evidence.md"])

    def test_missing_sweep_and_line_are_named(self):
        report = full_report().replace("- S13:", "- S99:").replace("\n7. line 7", "")
        missing = {name: ok for name, ok, _ in audit_report.checks(report)}
        self.assertFalse(missing["sweep lines S1-S24"])
        self.assertFalse(missing["Step 7 lines 1-15"])

    def test_an_unreadable_path_is_exit_2(self):
        self.assertEqual(audit_report.main(["check", "no/such/report.md"]), 2)

    def test_an_undecodable_report_is_exit_2(self):
        with tempfile.TemporaryDirectory() as d:
            report = Path(d) / "report.md"
            report.write_text(full_report(), encoding="utf-16")   # what PowerShell's `>` writes
            self.assertEqual(audit_report.main(["check", str(report)]), 2)

    def test_skill_quotes_no_real_receipt(self):
        found, _ = receipts.scan()
        skill = (receipts.HERE / "SKILL.md").read_text(encoding="utf-8")
        self.assertEqual(receipts.leaked(found, skill), [])


if __name__ == "__main__":
    unittest.main()
