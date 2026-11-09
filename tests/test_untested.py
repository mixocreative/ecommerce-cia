"""Guard tests for tools/untested.py: doctrine with no scored run cannot be pushed."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import untested  # noqa: E402

RUNS = "\n".join([
    "| 2026-11-01 | `aaaaaaa` | Claude | Screen | 12 | 0 | 0 | 0 | 5 | n |",
    "| 2026-11-02 | `bbbbbbb` (reverted in `ccccccc`) | Claude | Screen | 9 | 0 | 1 | 0 | 5 | n |",
    "| - | - | - | - | - | - | - | - | - | none yet |",
])


class UntestedTests(unittest.TestCase):
    def test_live_rows_only(self):
        self.assertEqual(untested.live_tokens(RUNS), {"aaaaaaa"})

    def test_a_measured_commit_passes(self):
        self.assertTrue(untested.verdict("aaaaaaa1234", "feat: x", untested.live_tokens(RUNS))[0])

    def test_an_unmeasured_doctrine_commit_blocks(self):
        ok, why = untested.verdict("ddddddd1234", "feat(skill): new rule", untested.live_tokens(RUNS))
        self.assertFalse(ok)
        self.assertIn("no live scored run", why)

    def test_a_reverted_commit_is_not_measured_doctrine(self):
        self.assertFalse(untested.verdict("bbbbbbb1234", "feat: y", untested.live_tokens(RUNS))[0])

    def test_a_revert_returns_to_measured_doctrine(self):
        msg = 'Revert "feat: y"\n\nThis reverts commit bbbbbbb.'
        self.assertTrue(untested.verdict("eeeeeee1234", msg, untested.live_tokens(RUNS))[0])


if __name__ == "__main__":
    unittest.main()
