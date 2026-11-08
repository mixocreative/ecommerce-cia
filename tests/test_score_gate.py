"""Guard tests for tools/score.py's per-commit gate (ported from cia on 2026-11-09).

Run: python -m unittest discover -s tests -p "test_score_gate.py"   (from the repo root; tests/ is not a package)
"""
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import score  # noqa: E402

HDR = "| Date | Skill commit | Runtime | Tier | Hits | Near | Miss | False+ | Minutes | Note |"


def row(date, hits, near=0, miss=0, commit="aaaaaaa"):
    return f"| {date} | `{commit}` | Claude Sonnet | Screen on fixture-shop-node | {hits} | {near} | {miss} | 0 | 5 | n |"


class GateTests(unittest.TestCase):
    def gate(self, rows):
        # The runtime-row gate (every scored run since 2026-09-24 also records what it ran) is a separate
        # rule; give each date a clean runtime row so these tests isolate the per-commit gate.
        dates = sorted({r.split("|")[1].strip() for r in rows})
        runtime = ["## Runtime evidence, per run", "",
                   "| Date | Fixture | Ladders | Adversarial rows | Probes | Ledger rows P / F / U | PASS without artefact | Note |",
                   *[f"| {d} | fixture-shop-node | 1 | 1 | 1 | 1/0/0 | 0 | n |" for d in dates]]
        text = "\n".join(["# RUNS", "", HDR, *rows, "", *runtime, ""])
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "RUNS.md"
            p.write_text(text, encoding="utf-8")
            old_runs, old_argv = score.RUNS, sys.argv
            score.RUNS, sys.argv = p, ["score.py", "--gate"]
            try:
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    return score.main()
            finally:
                score.RUNS, sys.argv = old_runs, old_argv

    def test_two_runs_at_the_floor_pass(self):
        self.assertEqual(self.gate([row("2026-09-25", 4), row("2026-10-21", 4, commit="bbbbbbb"),
                                    row("2026-11-09", 4, commit="ccccccc"), row("2026-11-09", 3, near=1, commit="ccccccc")]), 0)

    def test_one_run_is_a_sample(self):
        self.assertEqual(self.gate([row("2026-09-25", 4), row("2026-11-09", 4, commit="ccccccc")]), 1)

    def test_a_miss_fails_even_with_a_good_mean(self):
        self.assertEqual(self.gate([row("2026-09-25", 4), row("2026-11-09", 4, commit="ccccccc"),
                                    row("2026-11-09", 4, miss=1, commit="ccccccc")]), 1)

    def test_mean_below_the_floor_fails(self):
        self.assertEqual(self.gate([row("2026-09-25", 4), row("2026-11-09", 3, commit="ccccccc"),
                                    row("2026-11-09", 3, commit="ccccccc")]), 1)

    def test_reverted_rows_are_never_under_test(self):
        self.assertEqual(self.gate([row("2026-09-25", 4), row("2026-10-21", 4, commit="bbbbbbb"),
                                    row("2026-11-01", 4, commit="bbbbbbb"),
                                    row("2026-11-09", 1, commit="ccccccc` (reverted in `ddddddd")]), 0)


if __name__ == "__main__":
    unittest.main()
