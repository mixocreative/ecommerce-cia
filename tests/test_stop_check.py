"""Guard tests for tools/stop_check.py, the Stop hook that will not let an audit end on a failing report.

Why: the hook is the only thing that makes Step 6's 'check again until it exits 0' hold, and a hook that
blocks wrongly (an old report, a retry) traps a session; each branch is pinned here.
"""
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import stop_check  # noqa: E402


def failing(_text):
    return [("receipts", False, "the receipt of theory.md"), ("sweep lines S1-S24", True, "")]


def passing(_text):
    return [("receipts", True, "")]


class StopCheckTests(unittest.TestCase):
    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.addCleanup(self._d.cleanup)
        self.dir = Path(self._d.name)
        self.transcript = self.dir / "t.jsonl"
        self.transcript.write_text("{}", encoding="utf-8")
        self.report = self.dir / stop_check.REPORT

    def payload(self, active=False):
        return {"cwd": str(self.dir), "transcript_path": str(self.transcript), "stop_hook_active": active}

    def write_report(self, age=0):
        self.report.write_text("draft", encoding="utf-8")
        if age:
            t = time.time() - age
            os.utime(self.report, (t, t))

    def test_a_failing_report_written_this_session_blocks_with_the_missing_lines(self):
        self.write_report()
        answer = stop_check.decide(self.payload(), failing)
        self.assertEqual(answer["decision"], "block")
        self.assertIn("the receipt of theory.md", answer["reason"])
        self.assertIn("filed as a numbered finding", answer["reason"])   # backfilled sweep lines carry no prose defects

    def test_a_retry_is_never_blocked(self):
        self.write_report()
        self.assertIsNone(stop_check.decide(self.payload(active=True), failing))

    def test_a_passing_report_is_allowed(self):
        self.write_report()
        self.assertIsNone(stop_check.decide(self.payload(), passing))

    def test_no_report_is_allowed(self):
        self.assertIsNone(stop_check.decide(self.payload(), failing))

    def test_a_report_from_an_earlier_session_is_allowed(self):
        self.write_report(age=3600)
        self.assertIsNone(stop_check.decide(self.payload(), failing))

    def test_the_report_name_is_this_skills(self):
        self.assertEqual(stop_check.REPORT, f"{Path(stop_check.__file__).resolve().parent.parent.name}-audit-report.md")


if __name__ == "__main__":
    unittest.main()
