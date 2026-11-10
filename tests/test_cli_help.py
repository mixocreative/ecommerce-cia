"""Guard test: every runnable tool answers --help with what it is for, and exits 0 without doing its job.

Why: ported from cia (tests/tools/test_cli_help.py) on 2026-11-10. Here `--help` ran the job in every
hand-parsed tool: score.py printed the score, fetch_docs.py took it as a folder to download into, and
social_preview.py rendered two PNGs into a folder named `--help`. A stranger's first command is --help.
"""
import ast
import os
import subprocess
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
RUNNABLE = sorted(p for p in TOOLS.rglob("*.py") if '__name__ == "__main__"' in p.read_text(encoding="utf-8"))


class HelpTests(unittest.TestCase):
    def test_every_tool_is_found(self):
        self.assertGreaterEqual(len(RUNNABLE), 20)   # a glob that matches nothing would pass the loop below

    def test_help_exits_zero_and_says_what_the_tool_is(self):
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        for tool in RUNNABLE:
            for flag in ("--help", "-h"):
                with self.subTest(tool=tool.name, flag=flag):
                    r = subprocess.run([sys.executable, str(tool), flag], capture_output=True,
                                       encoding="utf-8", env=env, timeout=30, cwd=TOOLS.parent)
                    self.assertEqual(r.returncode, 0, r.stderr)
                    first = ast.get_docstring(ast.parse(tool.read_text(encoding="utf-8"))).splitlines()[0]
                    # argparse tools print their own usage; the hand-parsed ones print the docstring
                    self.assertTrue(first in r.stdout or r.stdout.lower().startswith("usage:"), r.stdout[:200])
        self.assertFalse((TOOLS.parent / "--help").exists(), "a tool took --help as an output folder")


if __name__ == "__main__":
    unittest.main()
