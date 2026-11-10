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


def row(date, hits, near=0, miss=0, commit="aaaaaaa", note="n"):
    return f"| {date} | `{commit}` | Claude Sonnet | Screen on fixture-shop-node | {hits} | {near} | {miss} | 0 | 5 | {note} |"


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

    def test_floor_is_the_recent_median_bounded_a_row_under_the_best(self):
        hist = [row("2026-11-10", 4, commit="aaaaaaa"), row("2026-11-10", 3, commit="aaaaaaa")]
        for i, c in enumerate("bcde"):
            hist += [row(f"2026-11-1{i + 1}", 3, commit=c * 7), row(f"2026-11-1{i + 1}", 3, commit=c * 7)]
        ok = hist + [row("2026-11-20", 3, commit="fffffff"), row("2026-11-20", 2, near=1, commit="fffffff")]
        self.assertEqual(self.gate(ok), 0)     # 2.75 >= median 3 - 0.5 and best 3.5 - 1
        low = hist + [row("2026-11-20", 2, commit="fffffff"), row("2026-11-20", 2, near=1, commit="fffffff")]
        self.assertEqual(self.gate(low), 1)    # 2.25 < 2.5

    def test_two_runs_at_the_floor_pass(self):
        self.assertEqual(self.gate([row("2026-09-25", 4), row("2026-10-21", 4, commit="bbbbbbb"),
                                    row("2026-11-09", 4, commit="ccccccc"), row("2026-11-09", 3, near=1, commit="ccccccc")]), 0)

    def test_a_later_clean_run_on_reverted_doctrine_does_not_block_the_shipped_commit(self):
        hist = [row("2026-11-10", 3, miss=1, commit="aaaaaaa"), row("2026-11-10", 3, miss=1, commit="aaaaaaa"),
                row("2026-11-11", 4, commit="bbbbbbb` (reverted in `ccccccc"),
                row("2026-11-11", 4, commit="bbbbbbb` (reverted in `ccccccc")]
        self.assertEqual(self.gate(hist), 0)
        later = hist + [row("2026-11-12", 4, commit="ddddddd"), row("2026-11-12", 4, miss=1, commit="ddddddd")]
        self.assertEqual(self.gate(later), 1)   # after a clean run, a miss blocks

    def test_one_run_is_a_sample(self):
        self.assertEqual(self.gate([row("2026-09-25", 4), row("2026-11-09", 4, commit="ccccccc")]), 1)

    def test_every_fixture_of_the_commit_is_gated_not_only_the_last_written(self):
        # Rows on the commit for two fixtures: a miss on the one written FIRST must still block.
        def shop(d, h, miss=0, c="aaaaaaa"):
            return row(d, h, miss=miss, commit=c).replace("fixture-shop-node", "fixture-shop")
        hist = [shop("2026-11-09", 14), shop("2026-11-09", 14),
                row("2026-11-09", 4), row("2026-11-09", 4)]
        new = [shop("2026-11-11", 14, miss=1, c="bbbbbbb"), shop("2026-11-11", 14, c="bbbbbbb"),
               row("2026-11-11", 4, commit="bbbbbbb"), row("2026-11-11", 4, commit="bbbbbbb")]
        self.assertEqual(self.gate(hist + new), 1)

    def test_a_row_one_run_missed_and_its_pair_found_does_not_block(self):
        base = [row("2026-11-09", 4), row("2026-11-09", 4)]
        pair = [row("2026-11-11", 4, miss=1, commit="bbbbbbb", note="missed: N3."), row("2026-11-11", 4, commit="bbbbbbb")]
        self.assertEqual(self.gate(base + pair), 0)    # mean 3.5, the floor holds, the pair found N3

    def test_a_row_every_run_missed_blocks(self):
        base = [row("2026-11-09", 4), row("2026-11-09", 4)]
        both = [row("2026-11-11", 4, miss=1, commit="bbbbbbb", note="missed: N3."),
                row("2026-11-11", 4, miss=1, commit="bbbbbbb", note="missed: N3, N4.")]
        self.assertEqual(self.gate(base + both), 1)

    def test_a_shared_miss_blocks_however_each_note_words_it(self):
        # Compared as whole strings, `N3 (not probed)` and `N3)` shared nothing and the pair passed.
        base = [row("2026-11-09", 4), row("2026-11-09", 4)]
        both = [row("2026-11-11", 4, miss=1, commit="bbbbbbb", note="missed: N3 (the catch was read, not probed). x"),
                row("2026-11-11", 4, miss=1, commit="bbbbbbb", note="(tracked: N5; missed: N3). y")]
        self.assertEqual(self.gate(base + both), 1)
        self.assertEqual(score.missed_of("missed: row 10, #15), E8 (noted but not filed)."), {"row 10", "#15", "e8"})

    def test_a_tag_that_names_no_row_blocks_like_no_tag(self):
        base = [row("2026-11-09", 4), row("2026-11-09", 4)]
        self.assertEqual(self.gate(base + [row("2026-11-11", 4, miss=1, commit="bbbbbbb", note="missed: ."),
                                           row("2026-11-11", 4, commit="bbbbbbb")]), 1)

    def test_an_untagged_miss_blocks(self):
        base = [row("2026-11-09", 4), row("2026-11-09", 4)]
        self.assertEqual(self.gate(base + [row("2026-11-11", 4, miss=1, commit="bbbbbbb"),
                                           row("2026-11-11", 4, commit="bbbbbbb")]), 1)

    def test_a_miss_fails_even_with_a_good_mean(self):
        self.assertEqual(self.gate([row("2026-09-25", 4), row("2026-11-09", 4, commit="ccccccc"),
                                    row("2026-11-09", 4, miss=1, commit="ccccccc")]), 1)

    def test_mean_below_the_floor_fails(self):
        self.assertEqual(self.gate([row("2026-09-25", 4), row("2026-11-09", 3, commit="ccccccc"),
                                    row("2026-11-09", 3, commit="ccccccc")]), 1)

    def test_launcher_rows_are_judged_against_launcher_rows(self):
        # Subagent floor 4; the launcher measures half a row lower on the same doctrine.
        def h(d, hits, near, c):
            return row(d, hits, near, commit=c).replace("Claude Sonnet", "Claude Sonnet (harness)")
        self.assertEqual(self.gate([row("2026-10-21", 4, commit="bbbbbbb"),
                                    h("2026-11-09", 3, 1, "ccccccc"), h("2026-11-09", 3, 1, "ccccccc"),
                                    h("2026-11-09", 3, 0, "ddddddd"), h("2026-11-09", 2, 2, "ddddddd"),
                                    h("2026-11-09", 3, 0, "ddddddd")]), 0)

    def test_single_runs_before_the_rule_are_history(self):
        # 2026-10-21 had one run, which the old rule allowed; it is the floor, never a failing sample.
        self.assertEqual(self.gate([row("2026-09-25", 4), row("2026-10-21", 4, commit="bbbbbbb")]), 0)

    def test_a_reverted_change_leaves_old_history_passing(self):
        self.assertEqual(self.gate([row("2026-09-25", 4), row("2026-10-21", 4, commit="bbbbbbb"),
                                    row("2026-11-09", 1, miss=1, commit="ccccccc` (reverted in `ddddddd")]), 0)

    def test_reverted_rows_are_never_under_test(self):
        self.assertEqual(self.gate([row("2026-09-25", 4), row("2026-10-21", 4, commit="bbbbbbb"),
                                    row("2026-11-01", 4, commit="bbbbbbb"),
                                    row("2026-11-09", 1, commit="ccccccc` (reverted in `ddddddd")]), 0)


if __name__ == "__main__":
    unittest.main()
