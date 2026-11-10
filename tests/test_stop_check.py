"""Guard tests for tools/stop_check.py, the Stop hook that will not let an audit end on a failing report.

Why: the hook is the only thing that makes the report step's 'check again until it exits 0' hold, and a
hook that blocks wrongly (an old report, a retry, a later turn) traps a session, while one that never
fires (an install folder named by version, a POSIX st_ctime) is a guard nobody sees fail; each is pinned.
"""
import datetime
import json
import os
import shutil
import subprocess
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

    def test_a_report_written_outside_the_working_directory_this_turn_blocks(self):
        # SKILL lets the owner put the report elsewhere; the turn's own Write names where.
        other = self.dir / "elsewhere"
        other.mkdir()
        report = other / stop_check.REPORT
        report.write_text("draft", encoding="utf-8")
        self.write_transcript({"type": "assistant", "timestamp": stamp(time.time()), "message": {"content": [
            {"type": "tool_use", "name": "Write", "input": {"file_path": str(report), "content": "draft"}}]}}, append=True)
        answer = stop_check.decide(self.payload(), failing)
        self.assertIn(str(report), answer["reason"])

    def test_a_write_from_an_earlier_turn_is_not_this_turns(self):
        other = self.dir / "elsewhere"
        other.mkdir()
        report = other / stop_check.REPORT
        report.write_text("draft", encoding="utf-8")
        earlier = {"type": "assistant", "timestamp": stamp(self.prompt_at - 30), "message": {"content": [
            {"type": "tool_use", "name": "Write", "input": {"file_path": str(report), "content": "draft"}}]}}
        prompt = {"type": "user", "timestamp": stamp(self.prompt_at), "message": {"content": "thanks"}}
        self.write_transcript(earlier, prompt)
        self.assertIsNone(stop_check.decide(self.payload(), failing))   # only this turn's writes are looked up

    def run_shipped(self, shell, path_dirs, only=False):
        """The shipped hooks.json command, with ${CLAUDE_PLUGIN_ROOT} filled in the way Claude Code does
        (textually, a native path), run through `shell` with this payload; returns its stdout."""
        self.write_report()
        hooks = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        command = hooks["hooks"]["Stop"][0]["hooks"][0]["command"].replace("${CLAUDE_PLUGIN_ROOT}", str(ROOT))
        env = {**os.environ, "PATH": os.pathsep.join([*path_dirs, *([] if only else [os.environ.get("PATH", "")])])}
        done = subprocess.run([*shell, command], input=json.dumps(self.payload()), capture_output=True,
                              text=True, env=env, timeout=60)
        # Exit 0 or Claude Code discards the JSON: `python` missing after a working python3 left 127 (Fable).
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout

    @unittest.skipUnless(shutil.which("sh"), "needs a POSIX shell, as Claude Code uses when bash is there")
    def test_the_shipped_command_survives_a_python3_that_is_not_python(self):
        # Windows' "python3" can be the Store stub: it prints to stderr and exits 9009. The command then runs
        # `python`, and whichever interpreter runs first reads the payload; the second reads nothing and is silent.
        # Not covered: a stub that READ stdin would leave `python` an empty payload, and the hook would allow.
        stub_dir = self.dir / "bin"
        stub_dir.mkdir()
        stub = stub_dir / "python3"
        stub.write_text("#!/bin/sh" + chr(10) + "echo not found >&2; exit 9009" + chr(10), encoding="utf-8")
        stub.chmod(0o755)
        out = self.run_shipped(["sh", "-c"], [stub_dir.as_posix(), Path(sys.executable).parent.as_posix()])
        self.assertEqual(json.loads(out)["decision"], "block")

    @unittest.skipUnless(shutil.which("sh"), "needs a POSIX shell")
    def test_the_shipped_command_exits_0_with_python3_and_no_python(self):
        # Stock macOS and many Linux installs: a working python3, no `python`. PATH holds nothing else.
        bin_dir = self.dir / "only"
        bin_dir.mkdir()
        shim = bin_dir / "python3"
        shim.write_text("#!/bin/sh" + chr(10) + f'exec "{Path(sys.executable).as_posix()}" "$@"' + chr(10), encoding="utf-8")
        shim.chmod(0o755)
        out = self.run_shipped([shutil.which("sh"), "-c"], [bin_dir.as_posix()], only=True)
        self.assertEqual(json.loads(out)["decision"], "block")

    @unittest.skipUnless(shutil.which("pwsh") or shutil.which("powershell"), "needs PowerShell")
    def test_the_shipped_command_parses_in_powershell(self):
        # Claude Code runs hook commands in PowerShell on Windows without Git Bash (hooks docs, `shell` field);
        # an `if ...; then ...; fi` command was a syntax error there on every Stop.
        shell = [shutil.which("pwsh") or shutil.which("powershell"), "-NoProfile", "-Command"]
        out = self.run_shipped(shell, [str(Path(sys.executable).parent)])
        self.assertEqual(json.loads(out)["decision"], "block")

    def test_a_report_a_bash_command_wrote_outside_the_working_directory_blocks(self):
        other = self.dir / "out"
        other.mkdir()
        report = other / stop_check.REPORT
        report.write_text("draft", encoding="utf-8")
        self.write_transcript({"type": "assistant", "timestamp": stamp(time.time()), "message": {"content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": f"cat draft.md > {report.as_posix()}"}}]}}, append=True)
        self.assertIn(report.as_posix(), stop_check.decide(self.payload(), failing)["reason"].replace(chr(92), "/"))

    def test_a_malformed_tool_input_never_raises(self):
        self.write_report()
        self.write_transcript({"type": "assistant", "timestamp": stamp(time.time()), "message": {"content": [
            {"type": "tool_use", "name": "Write", "input": ["not", {"file_path": 7}]}, "junk"]}}, append=True)
        self.assertIsNotNone(stop_check.decide(self.payload(), failing))   # still finds the cwd report

    def test_a_file_whose_name_only_ends_in_the_report_name_is_not_this_skills(self):
        # "ecommerce-cia-audit-report.md" ends in "cia-audit-report.md"; with both plugins installed, cia's hook
        # graded the other skill's report against its own checker (Fable, 2026-11-10).
        other = self.dir / "shop"
        other.mkdir()
        report = other / ("ecommerce-" + stop_check.REPORT)
        report.write_text("draft", encoding="utf-8")
        self.write_transcript({"type": "assistant", "timestamp": stamp(time.time()), "message": {"content": [
            {"type": "tool_use", "name": "Write", "input": {"file_path": str(report), "content": "draft"}}]}}, append=True)
        self.assertIsNone(stop_check.decide(self.payload(), failing))

    def test_a_crash_inside_the_hook_is_said_not_swallowed(self):
        # The command ends `exit 0`, so a crash would otherwise turn the guard off silently.
        import io
        from unittest import mock
        out = io.StringIO()
        with mock.patch.object(stop_check, "decide", side_effect=RuntimeError("boom")),                 mock.patch.object(sys, "stdin", io.StringIO(json.dumps(self.payload()))),                 mock.patch.object(sys, "stdout", out):
            self.assertEqual(stop_check.main(), 0)
        message = json.loads(out.getvalue())
        self.assertNotIn("decision", message)                 # never a block on our own bug
        self.assertIn("boom", message["systemMessage"])

    def test_a_broken_checker_speaks_only_where_a_report_was_written(self):
        import io
        from unittest import mock

        def run():
            out = io.StringIO()
            with mock.patch.dict(sys.modules, {"audit_report": None}),                     mock.patch.object(sys, "stdin", io.StringIO(json.dumps(self.payload()))),                     mock.patch.object(sys, "stdout", out):
                self.assertEqual(stop_check.main(), 0)
            return out.getvalue()
        self.assertEqual(run(), "")                            # no report this turn: silent, whatever is broken
        self.write_report()
        self.assertIn("could not run", json.loads(run())["systemMessage"])

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
