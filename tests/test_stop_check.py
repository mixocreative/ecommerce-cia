"""Guard tests for tools/stop_check.py, the Stop hook that will not let an audit end on a failing report.

Why: the hook is the only thing that makes the report step's 'check again until it exits 0' hold, and a
hook that blocks wrongly (an old report, a retry, a later turn) traps a session, while one that never
fires (an install folder named by version, a POSIX st_ctime) is a guard nobody sees fail; each is pinned.
"""
import datetime
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import stop_check  # noqa: E402


def failing(_text):
    return [("receipts", False, "the receipt of theory.md"), ("sweep lines S1-S24", True, "")]


def passing(_text):
    return [("receipts", True, "")]


def stamp(epoch):
    return datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc).isoformat().replace("+00:00", "Z")


class StopCheckTests(unittest.TestCase):
    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.addCleanup(self._d.cleanup)
        self.dir = Path(self._d.name)
        self.transcript = self.dir / "t.jsonl"
        self.prompt_at = time.time() - 60
        self.write_transcript({"type": "user", "timestamp": stamp(self.prompt_at), "message": {"content": "audit this"}})
        self.report = self.dir / stop_check.REPORT

    def write_transcript(self, *entries, append=False):
        with open(self.transcript, "a" if append else "w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")

    def payload(self, active=False):
        return {"cwd": str(self.dir), "transcript_path": str(self.transcript), "stop_hook_active": active}

    def write_report(self, at=None):
        self.report.write_text("draft", encoding="utf-8")
        if at is not None:
            os.utime(self.report, (at, at))

    def test_a_failing_report_written_this_turn_blocks_with_the_missing_lines(self):
        self.write_report()
        answer = stop_check.decide(self.payload(), failing)
        self.assertEqual(answer["decision"], "block")
        self.assertIn("the receipt of theory.md", answer["reason"])
        self.assertIn("filed as a numbered finding", answer["reason"])   # backfilled sweep lines carry no prose defects

    def test_a_transcript_appended_after_the_report_still_blocks(self):
        # The POSIX trap: st_ctime moves on every append, and the old window made every report look stale.
        self.write_report()
        self.write_transcript({"type": "assistant", "timestamp": stamp(time.time()), "message": {"content": []}}, append=True)
        self.assertIsNotNone(stop_check.decide(self.payload(), failing))

    def test_a_tool_result_is_not_a_new_turn(self):
        self.write_report(at=time.time() - 30)
        self.write_transcript({"type": "user", "timestamp": stamp(time.time() - 10),
                                "message": {"content": [{"type": "tool_result", "content": "ok"}]}}, append=True)
        self.assertIsNotNone(stop_check.decide(self.payload(), failing))

    def test_an_injected_meta_entry_is_not_a_new_turn(self):
        # Hook feedback and notifications are logged as user entries with isMeta; one landing after the report
        # must not move the turn start past it.
        self.write_report(at=time.time() - 30)
        self.write_transcript({"type": "user", "isMeta": True, "timestamp": stamp(time.time() - 10),
                               "message": {"content": "a background task finished"}}, append=True)
        self.assertIsNotNone(stop_check.decide(self.payload(), failing))

    def test_a_report_from_before_this_turn_is_allowed(self):
        # An earlier turn, a resumed session, or another session in the same project: not this turn's report.
        self.write_report(at=self.prompt_at - 5)
        self.assertIsNone(stop_check.decide(self.payload(), failing))

    def test_a_retry_is_never_blocked(self):
        self.write_report()
        self.assertIsNone(stop_check.decide(self.payload(active=True), failing))

    def test_a_passing_report_is_allowed(self):
        self.write_report()
        self.assertIsNone(stop_check.decide(self.payload(), passing))

    def test_no_report_is_allowed(self):
        self.assertIsNone(stop_check.decide(self.payload(), failing))

    def test_an_unreadable_transcript_never_blocks(self):
        self.write_report()
        self.assertIsNone(stop_check.decide({"cwd": str(self.dir), "transcript_path": str(self.dir / "gone.jsonl")}, failing))

    def test_the_report_name_is_the_literal_the_skill_names(self):
        # Never derived from the folder: an installed plugin's folder is its version.
        self.assertEqual(stop_check.REPORT, "ecommerce-cia-audit-report.md")
        self.assertIn(stop_check.REPORT, (ROOT / "SKILL.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
