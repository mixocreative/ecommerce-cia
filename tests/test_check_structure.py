"""Guard tests for tools/check_structure.py: green on the repo as it is, and each rule fails when broken.

Why: a guard nobody has seen fail is a guard nobody knows works. The size rule is the one that
mattered (a 1,919-line sweeps.md sat here with no check), so it is the one proven to bite.
"""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import check_structure as cs  # noqa: E402


class StructureTests(unittest.TestCase):
    def test_repo_is_green(self):
        self.assertEqual(cs.main(), 0, cs.failures)

    def test_size_rule_fails_over_the_hard_limit(self):
        with mock.patch.object(cs, "HARD_LIMIT", 100):
            cs.main()
        self.assertTrue(any("the cut is taken" in f for f in cs.failures), cs.failures)

    def test_unnamed_debt_fails(self):
        # Nothing is over 600 since the 2026-11-10 cuts, so lower the line to prove the rule still bites.
        with mock.patch.object(cs, "DEBT", {}), mock.patch.object(cs, "DEBT_LIMIT", 100):
            cs.main()
        self.assertTrue(any("must be named in DEBT" in f for f in cs.failures), cs.failures)

    def test_paid_off_debt_fails(self):
        with mock.patch.object(cs, "DEBT", {**cs.DEBT, "references/theory.md": "a cut"}):
            cs.main()
        self.assertTrue(any("no longer over" in f for f in cs.failures), cs.failures)

    def test_every_sweep_once(self):
        cs.failures.clear()
        cs.check_sweeps()
        self.assertEqual(cs.failures, [])


    def test_a_line_the_read_tool_would_cut_fails(self):
        import check_structure as cs_mod
        from unittest import mock as _mock
        with _mock.patch.object(cs_mod, "READ_LIMIT", 50):
            cs_mod.failures.clear()
            cs_mod.check_line_length()
        self.assertTrue(any("the Read tool cuts it" in m for m in cs_mod.failures), cs_mod.failures)
        cs_mod.failures.clear()
        cs_mod.check_line_length()
        self.assertEqual(cs_mod.failures, [])

if __name__ == "__main__":
    unittest.main()
