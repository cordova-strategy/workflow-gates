"""Tests for `summarize`, over synthetic run records under `tmp_path`."""
from __future__ import annotations

import json
import math
import re
import statistics
from pathlib import Path

import pytest
from replay_bench import records, summary, tasks
from replay_bench.campaign import task_set_hash
from replay_bench.comment_metrics import CommentMetrics, PythonDefinitionCounts
from replay_bench.spend import SpendFile, SpendLine
from review_bench import analysis
from review_bench.runner import HarnessInvalidatedError, RunStore
from test_replay_bench_comment_metrics import _measure_change

ACCOUNT = "/synthetic/account"
CAP = 3.0


def metrics(
    *, words=None, code=10, docstring=None, unclassified=0, ast_rejected=0, non_file=0, undecodable=0,
    test_words=None, test_code=0, test_docstring=None, definitions=None,
) -> dict:
    """With `definitions`, each scope's comment words default to cover its new docstring words and its docstring lines
    to cover one line per new docstring. An explicit value below that fails the helper."""
    def new_docstring_totals(scope) -> tuple[int, int]:
        return (definitions[scope]["new_docstrings"], definitions[scope]["new_docstring_words"]) if definitions else (0, 0)

    new_docstrings, new_docstring_words = new_docstring_totals("non_test")
    test_new_docstrings, test_new_docstring_words = new_docstring_totals("test")
    words = max(10, new_docstring_words) if words is None else words
    docstring = new_docstrings if docstring is None else docstring
    test_words = test_new_docstring_words if test_words is None else test_words
    test_docstring = test_new_docstrings if test_docstring is None else test_docstring
    assert words >= new_docstring_words and docstring >= new_docstrings, "the fixture's totals cannot hold its new docstrings"
    assert test_words >= test_new_docstring_words and test_docstring >= test_new_docstrings, (
        "the fixture's test-scope totals cannot hold its new docstrings"
    )
    synthetic = CommentMetrics()
    synthetic.comment_words["non_test"] = words
    synthetic.line_counts["non_test"].update(code=code, docstring=docstring, unclassified=unclassified)
    synthetic.comment_words["test"] = test_words
    synthetic.line_counts["test"].update(code=test_code, docstring=test_docstring)
    synthetic.python_files_ast_rejected = ast_rejected
    synthetic.non_file_entries = non_file
    synthetic.undecodable_files = undecodable
    synthetic.python_definition_counts = definitions
    return synthetic.to_dict()


def definition_counts(new_docstrings, new_docstring_words, new_definitions, documented_new_definitions) -> dict:
    """The non-test counts as given. The test-scope counts are nonzero and differ from them, so a read of the test scope fails."""
    return {
        "non_test": {
            "new_docstrings": new_docstrings, "new_docstring_words": new_docstring_words,
            "new_definitions": new_definitions, "documented_new_definitions": documented_new_definitions,
        },
        "test": {
            "new_docstrings": 61, "new_docstring_words": 977, "new_definitions": 53, "documented_new_definitions": 47,
        },
    }


def record(
    task_id, arm, *, run_index=0, ok=True, reason=None, run_metrics=None, denials=0, cli="2.1.322", ignored=0,
    empty_final_text=False, runner_commit=None, runner_dirty=None,
):
    return records.ReplayRunRecord(
        campaign_id="c1", task_id=task_id, arm=arm, run_index=run_index, status="ok" if ok else "missing",
        missing_reason=None if ok else reason, missing_detail=None, attempts=1, account_key=ACCOUNT, session_id="s",
        cli_version=cli, ambient_config_commit="commit", wall_clock_s=1.0, total_cost_usd=1.0,
        metrics=(run_metrics or metrics()) if ok else None, permission_denials=denials, ignored_paths_count=ignored,
        empty_final_text=empty_final_text, runner_commit=runner_commit, runner_dirty=runner_dirty,
    )


class Campaign:
    def __init__(self, tmp_path: Path) -> None:
        self.local_dir = tmp_path / ".local"
        self.dir = self.local_dir / "campaigns" / "c1"
        self.store = RunStore(self.dir / "store")

    def add_block(self, task_id, *run_records, complete=True) -> None:
        for run in run_records:
            records.write_run(self.dir, run, None)
        if complete:
            self.store.mark_block_complete(task_id)

    def summarize(self) -> list[str]:
        return summary.summarize(self.dir, local_dir=self.local_dir, budget_cap_usd=CAP)


@pytest.fixture
def campaign(tmp_path):
    return Campaign(tmp_path)


def number_after(lines: list[str], prefix: str) -> float:
    line = next(line for line in lines if line.startswith(prefix))
    return float(re.search(r"-?\d+\.\d+|-?\d+", line[len(prefix):]).group())


class TestThePrimaryOutcome:
    def test_it_is_a_ratio_of_sums_over_a_tasks_runs(self, campaign):
        campaign.add_block(
            "t1",
            record("t1", "toolkit", run_metrics=metrics(words=10, code=10)),
            record("t1", "toolkit", run_index=1, run_metrics=metrics(words=30, code=90)),
            record("t1", "bare", run_metrics=metrics(words=0, code=10)),
        )

        lines = campaign.summarize()

        assert number_after(lines, "paired difference toolkit - bare:") == pytest.approx(40 / 100)

    def test_one_paired_task_prints_no_interval(self, campaign):
        campaign.add_block("t1", record("t1", "toolkit"), record("t1", "bare"))

        line = next(line for line in campaign.summarize() if line.startswith("paired difference"))

        assert "no interval for fewer than two paired tasks" in line

    def test_two_paired_tasks_print_an_interval(self, campaign):
        for task_id, words in (("t1", 20), ("t2", 30)):
            campaign.add_block(task_id, record(task_id, "toolkit", run_metrics=metrics(words=words)), record(task_id, "bare"))

        line = next(line for line in campaign.summarize() if line.startswith("paired difference"))

        assert re.fullmatch(r"paired difference toolkit - bare: -?\d+\.\d{4}, 95% interval \[-?\d+\.\d{4}, -?\d+\.\d{4}\]", line)

    def test_each_arms_pooled_ratio_the_sensitivity_mean_and_the_run_spread_are_printed(self, campaign):
        campaign.add_block(
            "small",
            record("small", "toolkit", run_metrics=metrics(words=40, code=2)),
            record("small", "bare", run_metrics=metrics(words=0, code=2)),
        )
        campaign.add_block(
            "large",
            record("large", "toolkit", run_metrics=metrics(words=5, code=98)),
            record("large", "toolkit", run_index=1, run_metrics=metrics(words=15, code=98)),
            record("large", "bare", run_metrics=metrics(words=0, code=98)),
        )

        lines = campaign.summarize()

        assert number_after(lines, "  toolkit words per code line:") == pytest.approx(0.5)
        assert number_after(lines, "  bare words per code line:") == pytest.approx(0.0)
        assert number_after(lines, "paired difference toolkit - bare:") == pytest.approx(0.5)
        assert number_after(lines, "  sensitivity, unweighted mean of per-task differences:") == pytest.approx(
            (40 / 2 + 10 / 98) / 2, abs=1e-4,
        )
        assert number_after(lines, "    toolkit:") == pytest.approx(statistics.stdev([5 / 98, 15 / 98]), abs=1e-4)
        toolkit_spread_line = next(line for line in lines if line.startswith("    toolkit: "))
        assert toolkit_spread_line.endswith(" over 1 paired tasks with two or more runs that added code")
        assert "    bare: n/a over 0 paired tasks with two or more runs that added code" in lines

    def test_an_arms_runs_of_equal_ratio_print_a_spread_of_zero(self, campaign):
        """Kills: printing a measured spread of zero as n/a, from run_spread returning none or from formatting a falsy 0.0."""
        campaign.add_block(
            "t1",
            record("t1", "toolkit", run_metrics=metrics(words=20, code=10)),
            record("t1", "toolkit", run_index=1, run_metrics=metrics(words=20, code=10)),
            record("t1", "bare"),
        )

        lines = campaign.summarize()

        assert "    toolkit: 0.0000 over 1 paired tasks with two or more runs that added code" in lines

    def test_each_difference_line_prints_its_own_interval(self, campaign):
        """Only tasks of unequal code lines give the two lines different intervals."""
        blocks = {"small": [
            record("small", "toolkit", run_metrics=metrics(words=40, code=2)),
            record("small", "bare", run_metrics=metrics(words=0, code=2)),
        ]}
        for task_id in ("large-1", "large-2", "large-3"):
            blocks[task_id] = [
                record(task_id, "toolkit", run_metrics=metrics(words=10, code=98)),
                record(task_id, "bare", run_metrics=metrics(words=0, code=98)),
            ]
        for task_id, task_records in blocks.items():
            campaign.add_block(task_id, *task_records)
        outcome = summary.paired_outcome(blocks)
        assert outcome.pooled_interval != outcome.unweighted_interval, "the fixture tells the two intervals apart"

        lines = campaign.summarize()

        def printed_interval(prefix: str) -> tuple[float, float]:
            line = next(line for line in lines if line.startswith(prefix))
            low, high = re.search(r"95% interval \[(-?\d+\.\d{4}), (-?\d+\.\d{4})\]", line).groups()
            return float(low), float(high)

        assert printed_interval("paired difference toolkit - bare:") == pytest.approx(outcome.pooled_interval, abs=1e-4)
        assert printed_interval("  sensitivity, unweighted mean of per-task differences:") == pytest.approx(
            outcome.unweighted_interval, abs=1e-4,
        )

    def test_a_campaign_with_no_paired_task_prints_each_figure_as_not_available(self, campaign):
        campaign.add_block("t1", record("t1", "toolkit"), record("t1", "bare", ok=False, reason="timeout"))

        lines = campaign.summarize()

        assert "  toolkit words per code line: n/a" in lines
        assert "  bare words per code line: n/a" in lines
        assert "paired difference toolkit - bare: n/a" in lines
        assert "  sensitivity, unweighted mean of per-task differences: n/a" in lines
        assert "    toolkit: n/a over 0 paired tasks with two or more runs that added code" in lines
        assert "    bare: n/a over 0 paired tasks with two or more runs that added code" in lines


class TestThePairedOutcomeAsValues:
    def blocks(self, *differences_in_words):
        """The bare arm writes no words, so a test over these blocks passes whether or not the bare ratio is subtracted."""
        return {
            f"t{index}": [
                record(f"t{index}", "toolkit", run_metrics=metrics(words=words, code=10)),
                record(f"t{index}", "bare", run_metrics=metrics(words=0, code=10)),
            ]
            for index, words in enumerate(differences_in_words)
        }

    def test_each_tasks_difference_is_its_toolkit_ratio_less_its_bare_ratio(self):
        outcome = summary.paired_outcome(self.blocks(20, 30, 70))

        assert outcome.differences == {"t0": pytest.approx(2.0), "t1": pytest.approx(3.0), "t2": pytest.approx(7.0)}
        assert outcome.unweighted_mean == pytest.approx(4.0)

    def test_a_nonzero_bare_ratio_is_subtracted_and_a_two_run_bare_arm_is_a_ratio_of_sums(self):
        """Kills: dropping or adding the bare term, and averaging a two-run arm's per-run ratios."""
        outcome = summary.paired_outcome({
            "two-run-bare": [
                record("two-run-bare", "toolkit", run_metrics=metrics(words=20, code=10)),
                record("two-run-bare", "bare", run_metrics=metrics(words=6, code=10)),
                record("two-run-bare", "bare", run_index=1, run_metrics=metrics(words=4, code=30)),
            ],
            "one-run-bare": [
                record("one-run-bare", "toolkit", run_metrics=metrics(words=30, code=10)),
                record("one-run-bare", "bare", run_metrics=metrics(words=9, code=6)),
            ],
        })

        toolkit_ratio, bare_ratio = 20 / 10, (6 + 4) / (10 + 30)
        assert bare_ratio != pytest.approx((6 / 10 + 4 / 30) / 2), "the fixture tells a ratio of sums from a mean of ratios"
        assert outcome.differences == {
            "two-run-bare": pytest.approx(toolkit_ratio - bare_ratio),
            "one-run-bare": pytest.approx(30 / 10 - 9 / 6),
        }
        assert outcome.unweighted_mean == pytest.approx(((toolkit_ratio - bare_ratio) + (30 / 10 - 9 / 6)) / 2)

    def test_the_interval_of_two_paired_tasks_spans_exactly_their_two_differences(self):
        """Kills: a bootstrap statistic that ignores the resampled IDs, which would collapse the interval to the mean."""
        outcome = summary.paired_outcome(self.blocks(20, 30))

        assert outcome.unweighted_interval == (pytest.approx(2.0), pytest.approx(3.0))
        assert outcome.pooled_interval == (pytest.approx(2.0), pytest.approx(3.0))

    def test_the_interval_of_several_tasks_lies_within_their_differences(self):
        outcome = summary.paired_outcome(self.blocks(20, 30, 70, 10))

        for low, high in (outcome.unweighted_interval, outcome.pooled_interval):
            assert min(outcome.differences.values()) <= low < high <= max(outcome.differences.values())

    def test_one_paired_task_has_no_interval(self):
        single = summary.paired_outcome(self.blocks(20))
        nothing = summary.paired_outcome({})

        assert single.unweighted_mean == pytest.approx(2.0) and single.unweighted_interval is None
        assert single.pooled_difference == pytest.approx(2.0) and single.pooled_interval is None
        assert nothing.unweighted_mean is None and nothing.unweighted_interval is None and nothing.differences == {}
        assert nothing.pooled_difference is None and nothing.pooled_interval is None and nothing.pooled_ratios == {}

    def test_the_pooled_difference_gives_a_task_the_weight_of_its_code_lines(self):
        """Kills: pooling as the mean of per-task differences, which the two-line task would dominate."""
        outcome = summary.paired_outcome({
            "small": [
                record("small", "toolkit", run_metrics=metrics(words=40, code=2)),
                record("small", "bare", run_metrics=metrics(words=1, code=2)),
            ],
            "large": [
                record("large", "toolkit", run_metrics=metrics(words=10, code=98)),
                record("large", "bare", run_metrics=metrics(words=4, code=48)),
            ],
        })

        assert outcome.pooled_ratios == {"toolkit": pytest.approx(50 / 100), "bare": pytest.approx(5 / 50)}
        assert outcome.pooled_difference == pytest.approx(50 / 100 - 5 / 50)
        assert outcome.unweighted_mean == pytest.approx(((40 / 2 - 1 / 2) + (10 / 98 - 4 / 48)) / 2)

    def test_a_task_with_more_valid_runs_has_no_more_weight_in_the_pooled_ratio(self):
        """Kills: pooling a task's run sums instead of its run means."""
        outcome = summary.paired_outcome({
            "three-runs": [
                *(record("three-runs", "toolkit", run_index=index, run_metrics=metrics(words=10, code=10)) for index in range(3)),
                record("three-runs", "bare", run_metrics=metrics(words=0, code=10)),
            ],
            "one-run": [
                record("one-run", "toolkit", run_metrics=metrics(words=0, code=10)),
                record("one-run", "bare", run_metrics=metrics(words=0, code=10)),
            ],
        })

        assert outcome.pooled_ratios["toolkit"] == pytest.approx(10 / 20)

    def test_a_tasks_counts_are_the_means_of_its_runs(self):
        """Kills: a median over the runs, which three skewed runs tell from the mean."""
        outcome = summary.paired_outcome({
            "skewed": [
                record("skewed", "toolkit", run_metrics=metrics(words=0, code=10)),
                record("skewed", "toolkit", run_index=1, run_metrics=metrics(words=3, code=10)),
                record("skewed", "toolkit", run_index=2, run_metrics=metrics(words=27, code=40)),
                record("skewed", "bare", run_metrics=metrics(words=0, code=10)),
            ],
        })

        assert outcome.pooled_ratios["toolkit"] == pytest.approx(10 / 20)

    def test_a_missing_run_stays_out_of_its_tasks_mean_counts(self):
        """Kills: dividing a task's counts by all of its runs, which would shrink its weight in the pooled ratio."""
        outcome = summary.paired_outcome({
            "one-missing": [
                record("one-missing", "toolkit", run_metrics=metrics(words=10, code=10)),
                record("one-missing", "toolkit", run_index=1, run_metrics=metrics(words=30, code=10)),
                record("one-missing", "toolkit", run_index=2, ok=False, reason="timeout"),
                record("one-missing", "bare", run_metrics=metrics(words=0, code=10)),
            ],
            "one-run": [
                record("one-run", "toolkit", run_metrics=metrics(words=0, code=20)),
                record("one-run", "bare", run_metrics=metrics(words=0, code=20)),
            ],
        })

        assert outcome.pooled_ratios["toolkit"] == pytest.approx(20 / 30)

    def test_each_interval_resamples_its_own_statistic(self):
        """Kills: swapping the two bootstrap statistics, which only tasks of unequal code lines tell apart."""
        blocks = {
            "small": [
                record("small", "toolkit", run_metrics=metrics(words=40, code=2)),
                record("small", "bare", run_metrics=metrics(words=0, code=2)),
            ],
        }
        for task_id in ("large-1", "large-2", "large-3"):
            blocks[task_id] = [
                record(task_id, "toolkit", run_metrics=metrics(words=10, code=98)),
                record(task_id, "bare", run_metrics=metrics(words=0, code=98)),
            ]

        outcome = summary.paired_outcome(blocks)

        assert outcome.pooled_interval[1] < 2 < outcome.unweighted_interval[1]

    def test_test_scope_counts_stay_out_of_every_figure(self):
        """Kills: reading a run's words or code lines as the sum of its test and non-test scopes."""
        outcome = summary.paired_outcome({
            "two-toolkit-runs": [
                record("two-toolkit-runs", "toolkit", run_metrics=metrics(words=10, code=10, test_words=500, test_code=300)),
                record(
                    "two-toolkit-runs", "toolkit", run_index=1,
                    run_metrics=metrics(words=30, code=10, test_words=700, test_code=100),
                ),
                record("two-toolkit-runs", "bare", run_metrics=metrics(words=2, code=10, test_words=40, test_code=60)),
            ],
            "one-run-each": [
                record("one-run-each", "toolkit", run_metrics=metrics(words=6, code=20, test_words=90, test_code=50)),
                record("one-run-each", "bare", run_metrics=metrics(words=4, code=20, test_words=30, test_code=5)),
            ],
        })

        assert outcome.pooled_ratios == {
            "toolkit": pytest.approx((20 + 6) / (10 + 20)), "bare": pytest.approx((2 + 4) / (10 + 20)),
        }
        assert outcome.pooled_difference == pytest.approx((20 + 6) / (10 + 20) - (2 + 4) / (10 + 20))
        assert outcome.differences == {
            "two-toolkit-runs": pytest.approx(20 / 10 - 2 / 10), "one-run-each": pytest.approx(6 / 20 - 4 / 20),
        }
        assert outcome.unweighted_mean == pytest.approx(((20 / 10 - 2 / 10) + (6 / 20 - 4 / 20)) / 2)
        assert outcome.run_spreads["toolkit"] == summary.RunSpread(pytest.approx(statistics.stdev([10 / 10, 30 / 10])), 1)

    def test_each_exclusion_is_tallied_with_its_records(self):
        blocks = {
            "paired": [record("paired", "toolkit"), record("paired", "bare")],
            "no-toolkit": [record("no-toolkit", "toolkit", ok=False, reason="timeout"), record("no-toolkit", "bare")],
            "no-bare": [record("no-bare", "toolkit"), record("no-bare", "bare", ok=False, reason="arm-leak")],
            "neither": [
                record("neither", "toolkit", ok=False, reason="timeout"),
                record("neither", "bare", ok=False, reason="result-error"),
            ],
            "no-code": [record("no-code", "toolkit"), record("no-code", "bare", run_metrics=metrics(words=5, code=0))],
        }

        outcome = summary.paired_outcome(blocks)

        assert list(outcome.differences) == ["paired"]
        assert outcome.excluded_counts == {"toolkit": 1, "bare": 1, "both": 1, "code": 1}
        assert [run.missing_reason for run in outcome.excluded_records["toolkit"]] == ["timeout"]
        assert [run.missing_reason for run in outcome.excluded_records["bare"]] == ["arm-leak"]
        assert sorted(run.missing_reason for run in outcome.excluded_records["both"]) == ["result-error", "timeout"]


class TestTheRunSpread:
    def runs(self, task_id, *words_and_code, arm="toolkit"):
        return [
            record(task_id, arm, run_index=index, run_metrics=metrics(words=words, code=code))
            for index, (words, code) in enumerate(words_and_code)
        ]

    def test_it_pools_each_tasks_variance_by_its_degrees_of_freedom(self):
        spread = summary.run_spread([
            self.runs("t1", (10, 10), (30, 10)),
            self.runs("t2", (10, 10), (20, 10), (60, 10)),
        ])

        assert spread.task_count == 2
        assert spread.standard_deviation == pytest.approx(math.sqrt((2.0 * 1 + 7.0 * 2) / 3))

    def test_a_task_with_fewer_than_two_runs_holding_code_adds_nothing(self):
        spread = summary.run_spread([
            self.runs("one-run", (10, 10)),
            self.runs("one-run-with-code", (10, 10), (30, 0)),
        ])

        assert spread == summary.RunSpread(None, 0)

    def test_a_missing_run_is_left_out(self):
        runs = [*self.runs("t1", (10, 10), (30, 10)), record("t1", "toolkit", run_index=2, ok=False, reason="timeout")]

        assert summary.run_spread([runs]).standard_deviation == pytest.approx(math.sqrt(2.0))

    @pytest.mark.parametrize(("arm_with_runs", "other_arm"), [("toolkit", "bare"), ("bare", "toolkit")])
    @pytest.mark.parametrize(
        "other_arm_run",
        [{"ok": False, "reason": "timeout"}, {"run_metrics": metrics(words=0, code=0)}],
        ids=["no-valid-run", "no-code-line"],
    )
    def test_the_paired_outcome_reports_it_per_arm_over_the_paired_tasks_only(self, arm_with_runs, other_arm, other_arm_run):
        outcome = summary.paired_outcome({
            "paired": [*self.runs("paired", (10, 10), (30, 10), arm=arm_with_runs), record("paired", other_arm)],
            "unpaired": [
                *self.runs("unpaired", (0, 10), (90, 10), arm=arm_with_runs),
                record("unpaired", other_arm, **other_arm_run),
            ],
        })

        assert list(outcome.differences) == ["paired"]
        assert outcome.run_spreads[arm_with_runs] == summary.RunSpread(pytest.approx(math.sqrt(2.0)), 1)
        assert outcome.run_spreads[other_arm] == summary.RunSpread(None, 0)

    def test_it_is_the_spread_of_each_runs_own_ratio(self):
        """Kills: dividing the spread of a task's words by the task's mean code lines."""
        spread = summary.run_spread([self.runs("t1", (10, 10), (30, 20))])

        assert spread.standard_deviation == pytest.approx(statistics.stdev([10 / 10, 30 / 20]))

    def test_runs_of_equal_ratio_give_a_spread_of_zero_not_an_unavailable_one(self):
        """Kills: guarding the unavailable spread on the summed squared deviations, not the degrees of freedom."""
        spread = summary.run_spread([self.runs("t1", (20, 10), (20, 10))])

        assert spread == summary.RunSpread(pytest.approx(0.0), 1)

    def test_a_run_with_no_code_line_adds_no_degree_of_freedom(self):
        spread = summary.run_spread([
            self.runs("one-run-without-code", (10, 10), (30, 10), (5, 0)),
            self.runs("t2", (20, 10), (20, 10), (20, 10)),
        ])

        assert spread.task_count == 2
        assert spread.standard_deviation == pytest.approx(math.sqrt((2.0 * 1 + 0.0 * 2) / 3))


class TestTheExclusionLine:
    def test_it_counts_each_exclusion_with_its_missing_reasons(self, campaign):
        campaign.add_block("paired", record("paired", "toolkit"), record("paired", "bare"))
        campaign.add_block(
            "no-toolkit", record("no-toolkit", "toolkit", ok=False, reason="timeout"), record("no-toolkit", "bare"),
        )
        for task_id in ("no-bare-1", "no-bare-2"):
            campaign.add_block(task_id, record(task_id, "toolkit"), record(task_id, "bare", ok=False, reason="arm-leak"))
        campaign.add_block(
            "neither", record("neither", "toolkit", ok=False, reason="timeout"),
            record("neither", "bare", ok=False, reason="result-error"),
        )
        campaign.add_block(
            "no-code", record("no-code", "toolkit"), record("no-code", "bare", run_metrics=metrics(words=5, code=0)),
        )

        lines = campaign.summarize()

        assert "paired 1 of 6 complete tasks" in lines
        excluded = {
            label: int(count)
            for label, count in (
                re.fullmatch(r"  excluded, (.+?): (\d+).*", line).groups() for line in lines if line.startswith("  excluded")
            )
        }
        assert excluded == {
            "toolkit with no valid run": 1, "bare with no valid run": 2, "both arms with no valid run": 1,
            "no non-test code line in an arm": 1,
        }
        by_label = {line.split(": ")[0]: line for line in lines if line.startswith("  excluded")}
        assert "timeout x1" in by_label["  excluded, toolkit with no valid run"]
        assert "arm-leak x2" in by_label["  excluded, bare with no valid run"]
        assert "result-error x1" in by_label["  excluded, both arms with no valid run"]
        assert "result-error" not in by_label["  excluded, toolkit with no valid run"]


class TestCompleteAndIncompleteBlocks:
    def test_an_incomplete_blocks_records_are_left_out(self, campaign):
        campaign.add_block("done", record("done", "toolkit"), record("done", "bare"))
        campaign.add_block("partial", record("partial", "toolkit", run_metrics=metrics(words=999)), complete=False)

        lines = campaign.summarize()

        assert "1 complete blocks, 1 incomplete blocks" in lines[0]
        assert "paired 1 of 1 complete tasks" in lines
        assert "toolkit: 1 ok" in "\n".join(lines)

    def test_a_campaign_that_does_not_exist_is_refused(self, tmp_path):
        with pytest.raises(HarnessInvalidatedError, match="holds no campaign"):
            summary.summarize(tmp_path / "absent", local_dir=tmp_path, budget_cap_usd=CAP)

    def test_records_from_two_environment_readings_of_one_account_are_refused(self, campaign):
        campaign.add_block("t1", record("t1", "toolkit"), record("t1", "bare", cli="2.9.9"))

        with pytest.raises(HarnessInvalidatedError, match="readings"):
            campaign.summarize()


def unparseable_record_texts() -> dict[str, str]:
    complete = record("t1", "toolkit").to_dict()
    without_arm = {key: value for key, value in complete.items() if key != "arm"}
    return {
        "invalid-json": "{not json",
        "null": "null",
        "a-list": "[]",
        "an-unknown-key": json.dumps({**complete, "unknown_key": 1}),
        "a-missing-required-key": json.dumps(without_arm),
    }


class TestARecordThatDoesNotParse:
    @pytest.fixture(params=sorted(unparseable_record_texts()))
    def unparseable_record_path(self, request, campaign) -> Path:
        path = records.record_path(campaign.dir, "t1", "toolkit", 0)
        path.parent.mkdir(parents=True)
        path.write_text(unparseable_record_texts()[request.param], encoding="utf-8")
        return path

    def test_reading_the_block_raises(self, campaign, unparseable_record_path):
        with pytest.raises(HarnessInvalidatedError) as raised:
            records.read_block_records(campaign.dir, "t1")

        assert str(unparseable_record_path) in str(raised.value)
        assert "cannot read the run record" in str(raised.value)

    def test_summarize_refuses_a_complete_block_holding_it(self, campaign, unparseable_record_path):
        campaign.store.mark_block_complete("t1")

        with pytest.raises(HarnessInvalidatedError) as raised:
            campaign.summarize()

        assert str(unparseable_record_path) in str(raised.value)

    def test_a_well_formed_record_in_the_same_place_reads_back(self, campaign):
        campaign.add_block("t1", record("t1", "toolkit"))

        assert [run.arm for run in records.read_block_records(campaign.dir, "t1")] == ["toolkit"]


def tree_snapshot(directory: Path) -> dict[str, tuple[int, bytes | None]]:
    """The bytes join the mtime so a rewrite within one timestamp tick still differs."""
    return {
        str(path.relative_to(directory)): (path.stat().st_mtime_ns, path.read_bytes() if path.is_file() else None)
        for path in [directory, *directory.rglob("*")]
    }


class TestSummarizeCreatesNothing:
    def test_a_campaign_directory_is_left_exactly_as_it_was(self, campaign):
        campaign.add_block("t1", record("t1", "toolkit"), record("t1", "bare"))
        campaign.add_block("t2", record("t2", "toolkit"), complete=False)
        spend = SpendFile(campaign.dir / "spend.jsonl", budget_cap_usd=CAP)
        spend.append(SpendLine("t1", "bare", 0, 1, ACCOUNT, "s", 2.0, False))
        (campaign.dir / "manifest.json").write_text(json.dumps({"budget_cap_usd": CAP}))
        before = tree_snapshot(campaign.dir)
        assert {"manifest.json", "spend.jsonl", "store", "runs"} <= set(before), "the snapshot sees each kind of file"

        lines = campaign.summarize()

        assert "1 complete blocks, 1 incomplete blocks" in lines[0]
        assert tree_snapshot(campaign.dir) == before

    def test_a_campaign_with_no_store_directory_gets_none(self, tmp_path):
        campaign_dir = tmp_path / ".local" / "campaigns" / "c1"
        campaign_dir.mkdir(parents=True)
        (campaign_dir / "manifest.json").write_text(json.dumps({"budget_cap_usd": CAP}))
        before = tree_snapshot(campaign_dir)

        lines = summary.summarize(campaign_dir, local_dir=tmp_path / ".local", budget_cap_usd=CAP)

        assert "0 complete blocks, 0 incomplete blocks" in lines[0]
        assert set(before) == {".", "manifest.json"}
        assert tree_snapshot(campaign_dir) == before


class TestSecondaryAndDiagnostics:
    def test_each_arm_prints_its_secondary_outcome_lines(self, campaign):
        campaign.add_block(
            "t1",
            record(
                "t1", "toolkit", run_metrics=metrics(code=50, docstring=10, unclassified=5, ast_rejected=2, non_file=1),
                denials=3,
            ),
            record("t1", "bare", run_metrics=metrics(code=100, docstring=5, unclassified=3, undecodable=4), ignored=7),
        )

        lines = campaign.summarize()
        text = "\n".join(lines)

        assert number_after(lines, "  toolkit, paired tasks pooled:") == pytest.approx(20.0)
        assert number_after(lines, "  bare, paired tasks pooled:") == pytest.approx(5.0)
        assert "runs with a permission-rule denial 1" in text
        assert "python files ast.parse rejected 2" in text
        assert "toolkit: unclassified-line share 0.0769," in text, "5 of 65 lines"
        assert "bare: unclassified-line share 0.0278," in text, "3 of 108 lines"
        assert "non_file_entries 1" in text and "undecodable_files 4" in text and "ignored_paths 7" in text

    def test_an_arms_docstring_rate_pools_each_paired_tasks_mean_counts_over_its_valid_runs(self, campaign):
        """Kills: summing runs across tasks and a mean of task rates."""
        campaign.add_block(
            "varied-runs",
            record("varied-runs", "toolkit", run_metrics=metrics(code=10, docstring=2)),
            record("varied-runs", "toolkit", run_index=1, run_metrics=metrics(code=30, docstring=18)),
            record("varied-runs", "toolkit", run_index=2, run_metrics=metrics(code=80, docstring=40)),
            record("varied-runs", "bare"),
        )
        campaign.add_block(
            "one-run",
            record("one-run", "toolkit", run_metrics=metrics(code=60, docstring=6)),
            record("one-run", "bare"),
        )

        lines = campaign.summarize()

        assert number_after(lines, "  toolkit, paired tasks pooled:") == pytest.approx(100 * (20 + 6) / (40 + 60))
        assert "  bare, paired tasks pooled: 0.0000" in lines

    def test_test_scope_counts_stay_out_of_an_arms_docstring_rate(self, campaign):
        """Kills: reading a run's docstring or code lines as the sum of its test and non-test scopes."""
        campaign.add_block(
            "t1",
            record("t1", "toolkit", run_metrics=metrics(code=10, docstring=2, test_code=100, test_docstring=50)),
            record("t1", "toolkit", run_index=1, run_metrics=metrics(code=30, docstring=18, test_code=20, test_docstring=30)),
            record("t1", "bare", run_metrics=metrics(code=100, docstring=5, test_code=900, test_docstring=400)),
        )

        lines = campaign.summarize()

        assert number_after(lines, "  toolkit, paired tasks pooled:") == pytest.approx(100 * (2 + 18) / (10 + 30))
        assert number_after(lines, "  bare, paired tasks pooled:") == pytest.approx(100 * 5 / 100)

    def test_a_run_with_an_empty_final_text_is_counted_per_arm_and_still_measured(self, campaign):
        campaign.add_block(
            "t1",
            record("t1", "toolkit", run_metrics=metrics(words=10, code=10), empty_final_text=True),
            record("t1", "bare", run_metrics=metrics(words=0, code=10)),
        )

        lines = campaign.summarize()

        assert any(line.startswith("  toolkit: ") and "runs with an empty final text 1," in line for line in lines)
        assert any(line.startswith("  bare: ") and "runs with an empty final text 0," in line for line in lines)
        assert number_after(lines, "paired difference toolkit - bare:") == pytest.approx(1.0)

    def test_a_missing_run_with_an_empty_final_text_stays_out_of_the_empty_final_text_count(self, campaign):
        """The count covers the valid runs, as the neighbouring `runs with no non-test code line` does."""
        campaign.add_block(
            "t1",
            record("t1", "toolkit"),
            record("t1", "bare"),
            record("t1", "bare", run_index=1, ok=False, reason="out-of-fixture-write", empty_final_text=True),
        )

        lines = campaign.summarize()

        assert any(line.startswith("  bare: ") and "runs with an empty final text 0," in line for line in lines)

    def test_a_missing_run_still_counts_its_denials_and_ignored_paths(self, campaign):
        """The two counts are diagnostics of a run that went wrong, which a missing run is the likeliest to be."""
        campaign.add_block(
            "t1",
            record("t1", "toolkit"),
            record("t1", "bare"),
            record("t1", "bare", run_index=1, ok=False, reason="timeout", denials=2, ignored=3),
        )

        lines = campaign.summarize()

        bare_line = next(line for line in lines if line.startswith("  bare: unclassified-line share"))
        assert "runs with a permission-rule denial 1," in bare_line
        assert "ignored_paths 3," in bare_line

    def test_a_run_with_no_non_test_code_line_enters_its_tasks_counts(self, campaign):
        campaign.add_block(
            "t1",
            record("t1", "toolkit", run_metrics=metrics(words=10, code=10)),
            record("t1", "toolkit", run_index=1, run_metrics=metrics(words=5, code=0)),
            record("t1", "bare", run_metrics=metrics(words=0, code=10)),
        )

        lines = campaign.summarize()

        assert number_after(lines, "paired difference toolkit - bare:") == pytest.approx(15 / 10)
        assert "runs with no non-test code line 1" in "\n".join(lines)


def reference_task(
    *, code, docstring=None, words=None, commit_digit="a", test_words=None, test_code=0, test_docstring=None, definitions=None,
) -> tasks.ReplayTask:
    source_repo, commit = "/synthetic/source-repo", commit_digit * 40
    return tasks.ReplayTask(
        id=tasks.make_task_id(Path(source_repo), commit), source_repo=source_repo, base_commit="b" * 40, commit=commit,
        brief="synthetic brief", changed_paths=("src/app.py",), author_email="author@example.invalid",
        committer_email="committer@example.invalid",
        reference_metrics=CommentMetrics.from_dict(
            metrics(
                words=words, code=code, docstring=docstring,
                test_words=test_words, test_code=test_code, test_docstring=test_docstring, definitions=definitions,
            ),
        ),
        base_density=None, base_tree_bytes=0, base_tree_entries=0,
    )


class TestThePairedSecondaryOutcome:
    def add_paired_and_unpaired_tasks(self, campaign) -> None:
        """`paired` has a valid run in each arm. `toolkit-only` has none in the bare arm."""
        campaign.add_block(
            "paired",
            record("paired", "toolkit", run_metrics=metrics(code=100, docstring=10)),
            record("paired", "bare", run_metrics=metrics(code=100, docstring=20)),
        )
        campaign.add_block(
            "toolkit-only",
            record("toolkit-only", "toolkit", run_metrics=metrics(code=100, docstring=50)),
            record("toolkit-only", "bare", ok=False, reason="timeout"),
        )

    def test_a_task_with_no_valid_run_in_one_arm_does_not_enter_either_arms_rate(self, campaign):
        """Kills: pooling every valid run, which would put the toolkit rate at 30 against the bare rate of 20."""
        self.add_paired_and_unpaired_tasks(campaign)

        lines = campaign.summarize()

        assert number_after(lines, "  toolkit, paired tasks pooled:") == pytest.approx(10.0)
        assert number_after(lines, "  bare, paired tasks pooled:") == pytest.approx(20.0)

    def test_each_paired_task_prints_both_arms_rates_and_an_unpaired_task_prints_none(self, campaign):
        self.add_paired_and_unpaired_tasks(campaign)

        lines = campaign.summarize()

        assert "  paired task 'paired': toolkit 10.0000, bare 20.0000" in lines
        assert not any(line.startswith("  paired task 'toolkit-only'") for line in lines)

    def test_a_tasks_rate_is_a_ratio_of_its_mean_counts_and_the_pool_weights_tasks_by_mean_code_lines(self, campaign):
        campaign.add_block(
            "small",
            record("small", "toolkit", run_metrics=metrics(code=10, docstring=5)),
            record("small", "toolkit", run_index=1, run_metrics=metrics(code=30, docstring=5)),
            record("small", "bare", run_metrics=metrics(code=10, docstring=0)),
        )
        campaign.add_block(
            "large",
            record("large", "toolkit", run_metrics=metrics(code=160, docstring=0)),
            record("large", "bare", run_metrics=metrics(code=90, docstring=9)),
        )

        lines = campaign.summarize()

        assert "  paired task 'small': toolkit 25.0000, bare 0.0000" in lines, "(5+5) / (10+30), not the mean of 50 and 16.7"
        assert number_after(lines, "  toolkit, paired tasks pooled:") == pytest.approx(100 * (5 + 0) / (20 + 160), abs=1e-4)
        assert number_after(lines, "  bare, paired tasks pooled:") == pytest.approx(100 * 9 / 100)

    def test_a_missing_run_beside_a_valid_run_in_a_paired_tasks_arm_enters_neither_the_pool_nor_the_task_line(self, campaign):
        """Kills: building an arm's counts from its raw records, which reads `metrics` off a missing run (None) or,
        if it zeroes that run, halves the task's mean code lines and shifts the pooled rate from 30 to about 36.7."""
        campaign.add_block(
            "with-a-missing-run",
            record("with-a-missing-run", "toolkit", run_metrics=metrics(code=100, docstring=10)),
            record("with-a-missing-run", "toolkit", run_index=1, ok=False, reason="timeout"),
            record("with-a-missing-run", "bare", run_metrics=metrics(code=100, docstring=20)),
        )
        campaign.add_block(
            "all-valid",
            record("all-valid", "toolkit", run_metrics=metrics(code=100, docstring=50)),
            record("all-valid", "bare", run_metrics=metrics(code=100, docstring=20)),
        )

        lines = campaign.summarize()

        assert number_after(lines, "  toolkit, paired tasks pooled:") == pytest.approx(100 * (10 + 50) / (100 + 100))
        assert "  paired task 'with-a-missing-run': toolkit 10.0000, bare 20.0000" in lines
        assert len([line for line in lines if line.startswith("  paired task ")]) == 2

    def test_a_task_with_no_non_test_code_line_in_one_arm_is_excluded_from_every_secondary_line(self, campaign):
        """Both arms have a valid run on `no-code`, but the toolkit arm wrote no code line, so the primary outcome
        drops the task and the secondary outcome must drop it from the pools, the per-task lines and the reference."""
        paired_task = reference_task(code=40, docstring=10)
        no_code_task = reference_task(code=40, docstring=30, commit_digit="c")
        tasks.write_task_set(campaign.local_dir / "tasks", "readable", [paired_task, no_code_task])
        (campaign.dir / "manifest.json").write_text(json.dumps({
            "tasks_name": "readable", "task_set_hash": task_set_hash((paired_task, no_code_task)),
        }))
        campaign.add_block(
            paired_task.id,
            record(paired_task.id, "toolkit", run_metrics=metrics(code=100, docstring=10)),
            record(paired_task.id, "bare", run_metrics=metrics(code=100, docstring=20)),
        )
        campaign.add_block(
            no_code_task.id,
            record(no_code_task.id, "toolkit", run_metrics=metrics(code=0, docstring=50)),
            record(no_code_task.id, "bare", run_metrics=metrics(code=100, docstring=90)),
        )

        lines = campaign.summarize()

        assert "  excluded, no non-test code line in an arm: 1" in lines
        assert "paired 1 of 2 complete tasks" in lines
        assert number_after(lines, "  toolkit, paired tasks pooled:") == pytest.approx(10.0)
        assert number_after(lines, "  bare, paired tasks pooled:") == pytest.approx(20.0)
        assert number_after(lines, "  reference (the merged commits), paired tasks pooled:") == pytest.approx(25.0)
        assert [line for line in lines if line.startswith("  paired task ")] == [
            f"  paired task {paired_task.id!r}: toolkit 10.0000, bare 20.0000",
        ]

    def test_a_campaign_with_no_paired_task_prints_n_a_for_each_arm(self, campaign):
        campaign.add_block("t1", record("t1", "toolkit"), record("t1", "bare", ok=False, reason="timeout"))

        lines = campaign.summarize()

        assert "  toolkit, paired tasks pooled: n/a" in lines and "  bare, paired tasks pooled: n/a" in lines
        assert not any(line.startswith("  paired task ") for line in lines)

    def test_a_toolkit_only_campaign_prints_n_a_for_every_rate_and_diagnoses_the_toolkit_arm_alone(self, campaign):
        toolkit_only_tasks = (reference_task(code=40, docstring=10), reference_task(code=40, docstring=30, commit_digit="c"))
        tasks.write_task_set(campaign.local_dir / "tasks", "readable", list(toolkit_only_tasks))
        (campaign.dir / "manifest.json").write_text(json.dumps({
            "tasks_name": "readable", "task_set_hash": task_set_hash(toolkit_only_tasks),
        }))
        for task in toolkit_only_tasks:
            campaign.add_block(task.id, record(task.id, "toolkit"))

        lines = campaign.summarize()

        assert "  toolkit, paired tasks pooled: n/a" in lines and "  bare, paired tasks pooled: n/a" in lines
        assert "  reference (the merged commits), paired tasks pooled: n/a" in lines, (
            "each task has a reference entry, so only the empty paired set makes the line read n/a"
        )
        assert not any(line.startswith("  paired task ") for line in lines)
        diagnostics = lines[lines.index("diagnostics per arm:") + 1:]
        arm_diagnostics = [line for line in diagnostics if line.startswith(("  toolkit: ", "  bare: "))]
        assert len(arm_diagnostics) == 1 and arm_diagnostics[0].startswith("  toolkit: ")

    def test_the_reference_rate_covers_the_paired_tasks_only(self, campaign):
        paired_task = reference_task(code=40, docstring=10)
        unpaired_task = reference_task(code=40, docstring=30, commit_digit="c")
        tasks.write_task_set(campaign.local_dir / "tasks", "readable", [paired_task, unpaired_task])
        (campaign.dir / "manifest.json").write_text(json.dumps({
            "tasks_name": "readable", "task_set_hash": task_set_hash((paired_task, unpaired_task)),
        }))
        campaign.add_block(paired_task.id, record(paired_task.id, "toolkit"), record(paired_task.id, "bare"))
        campaign.add_block(
            unpaired_task.id, record(unpaired_task.id, "toolkit"), record(unpaired_task.id, "bare", ok=False, reason="timeout"),
        )

        lines = campaign.summarize()

        assert number_after(lines, "  reference (the merged commits), paired tasks pooled:") == pytest.approx(25.0)


WORDS_FIGURE = "words per new docstring"
SHARE_FIGURE = "share of new definitions with a new docstring"
BOTH_FIGURES = [WORDS_FIGURE, SHARE_FIGURE]


def counted_runs(task_id, *, toolkit, bare) -> list[records.ReplayRunRecord]:
    """Each arm lists one entry per run: a `definition_counts` dict, or None for a run recorded without the counts."""
    return [
        record(task_id, arm_name, run_index=run_index, run_metrics=metrics(definitions=definitions))
        for arm_name, arm_runs in (("toolkit", toolkit), ("bare", bare))
        for run_index, definitions in enumerate(arm_runs)
    ]


def add_counted_block(campaign, task_id, *, toolkit, bare) -> None:
    campaign.add_block(task_id, *counted_runs(task_id, toolkit=toolkit, bare=bare))


def counted_blocks(runs_by_task: dict[str, tuple[list, list]]) -> dict[str, list[records.ReplayRunRecord]]:
    """One block per task from `{task_id: (toolkit_runs, bare_runs)}`, as `summary.docstring_figure_outcomes` reads them."""
    return {
        task_id: counted_runs(task_id, toolkit=toolkit, bare=bare) for task_id, (toolkit, bare) in runs_by_task.items()
    }


def figure_outcomes(blocks, reference=None) -> dict[str, summary.DocstringFigureOutcome]:
    """The outcomes of every block as paired tasks, keyed by figure stem. `reference` maps a task id to its entry.

    `summarize` feeds the paired ids in sorted order and the seeded bootstrap depends on that order, so the helper does too.
    """
    return {
        outcome.stem: outcome for outcome in summary.docstring_figure_outcomes(blocks, sorted(blocks), reference or {})
    }


def figure_section(lines: list[str]) -> list[str]:
    start = next(index for index, line in enumerate(lines) if line.startswith("additional secondary outcome:"))
    return lines[start:lines.index("diagnostics per arm:")]


def pin_reference_task_set(campaign, *reference_tasks) -> None:
    tasks.write_task_set(campaign.local_dir / "tasks", "readable", list(reference_tasks))
    (campaign.dir / "manifest.json").write_text(json.dumps({
        "tasks_name": "readable", "task_set_hash": task_set_hash(tuple(reference_tasks)),
    }))


class TestThePerDocstringFigures:
    def test_a_toolkit_figure_below_bare_prints_a_negative_difference(self, campaign):
        for task_id in ("a", "b"):
            add_counted_block(campaign, task_id, toolkit=[definition_counts(2, 10, 2, 1)], bare=[definition_counts(2, 30, 2, 2)])

        lines = campaign.summarize()

        resamples = analysis.BOOTSTRAP_RESAMPLES
        assert (
            f"  {WORDS_FIGURE}, toolkit - bare: -10.0000, 95% interval [-10.0000, -10.0000], 0 of {resamples} resamples dropped"
        ) in lines
        assert (
            f"  {SHARE_FIGURE}, toolkit - bare: -0.5000, 95% interval [-0.5000, -0.5000], 0 of {resamples} resamples dropped"
        ) in lines

    @pytest.mark.parametrize("figure", BOTH_FIGURES)
    def test_the_printed_difference_line_carries_the_difference_the_interval_bounds_and_the_dropped_count(
        self, campaign, figure,
    ):
        """Kills: printing the unmeasured count, a literal 0 or the kept count as the dropped count, swapping the
        interval bounds, and printing the difference where the interval goes."""
        runs_by_task = {
            "both-arms-high": ([definition_counts(3, 30, 3, 2)], [definition_counts(3, 12, 3, 1)]),
            "both-arms-low": ([definition_counts(2, 20, 2, 1)], [definition_counts(4, 40, 4, 3)]),
            "one-arm-empty": ([definition_counts(0, 0, 0, 0)], [definition_counts(2, 10, 2, 1)]),
        }
        for task_id, (toolkit, bare) in runs_by_task.items():
            add_counted_block(campaign, task_id, toolkit=toolkit, bare=bare)
        difference = figure_outcomes(counted_blocks(runs_by_task))[figure].difference
        low, high = difference.interval
        assert difference.dropped_resamples > 0, "the fixture must drop a resample so that a printed 0 is wrong"
        assert low < high and difference.difference not in (low, high), "the fixture's difference and bounds must differ"

        lines = campaign.summarize()

        assert (
            f"  {figure}, toolkit - bare: {difference.difference:.4f}, 95% interval [{low:.4f}, {high:.4f}], "
            f"{difference.dropped_resamples} of {analysis.BOOTSTRAP_RESAMPLES} resamples dropped"
        ) in lines

    def test_an_unpaired_task_and_a_no_code_task_stay_out_and_a_failed_run_is_not_an_unmeasured_one(self, campaign):
        campaign.add_block(
            "paired",
            record("paired", "toolkit", run_metrics=metrics(definitions=definition_counts(2, 20, 2, 1))),
            record("paired", "toolkit", run_index=1, ok=False, reason="timeout"),
            record("paired", "bare", run_metrics=metrics(definitions=definition_counts(1, 5, 1, 1))),
        )
        campaign.add_block(
            "unpaired",
            record("unpaired", "toolkit", run_metrics=metrics(definitions=definition_counts(50, 5000, 50, 50))),
            record("unpaired", "bare", ok=False, reason="timeout"),
        )
        campaign.add_block(
            "no-code",
            record("no-code", "toolkit", run_metrics=metrics(code=0)),
            record("no-code", "bare", run_metrics=metrics(definitions=definition_counts(60, 6000, 60, 60))),
        )

        lines = campaign.summarize()

        assert "paired 1 of 3 complete tasks" in lines
        assert f"  toolkit {WORDS_FIGURE}: 10.0000" in lines and f"  bare {WORDS_FIGURE}: 5.0000" in lines
        assert f"  toolkit {SHARE_FIGURE}: 0.5000" in lines and f"  bare {SHARE_FIGURE}: 1.0000" in lines
        assert not any("not measured" in line for line in figure_section(lines))

    @pytest.mark.parametrize(
        "runs_with_gaps",
        [
            pytest.param([definition_counts(2, 20, 2, 1), None], id="the counts first"),
            pytest.param([None, definition_counts(2, 20, 2, 1)], id="the counts last"),
        ],
    )
    @pytest.mark.parametrize("lacking_arm", ["toolkit", "bare"])
    @pytest.mark.parametrize("figure", BOTH_FIGURES)
    def test_one_run_without_the_counts_leaves_that_arm_and_the_difference_not_measured(
        self, campaign, figure, lacking_arm, runs_with_gaps,
    ):
        """Kills:
        - computing an arm over only the runs that carry the counts, which would change the tasks a figure covers
        - testing only one arm for missing counts in the difference

        The run order varies so that inspecting only the first or only the last valid run fails.
        """
        measured_arm = "bare" if lacking_arm == "toolkit" else "toolkit"
        arm_runs = {lacking_arm: runs_with_gaps, measured_arm: [definition_counts(1, 5, 1, 1)]}
        add_counted_block(campaign, "k2", toolkit=arm_runs["toolkit"], bare=arm_runs["bare"])

        lines = campaign.summarize()

        not_measured = "not measured (1 of 1 paired tasks lack the counts)"
        assert f"  {lacking_arm} {figure}: {not_measured}" in lines
        assert f"  {figure}, toolkit - bare: {not_measured}" in lines
        assert not any(line.startswith(f"  {measured_arm} {figure}: ") and "not measured" in line for line in lines)
        assert number_after(lines, f"  {measured_arm} {figure}:") > 0

    @pytest.mark.parametrize("figure", BOTH_FIGURES)
    def test_a_campaign_with_no_paired_task_prints_n_a_for_every_arm_the_reference_and_the_difference(self, campaign, figure):
        campaign.add_block(
            "unpaired",
            record("unpaired", "toolkit", run_metrics=metrics(definitions=definition_counts(2, 20, 2, 1))),
            record("unpaired", "bare", ok=False, reason="timeout"),
        )

        lines = campaign.summarize()

        assert f"  toolkit {figure}: n/a" in lines
        assert f"  bare {figure}: n/a" in lines
        assert f"  reference (the merged commits) {figure}: n/a" in lines
        assert f"  {figure}, toolkit - bare: n/a" in lines

    @pytest.mark.parametrize("figure", BOTH_FIGURES)
    def test_a_task_recorded_before_the_counts_leaves_each_arm_and_the_difference_not_measured_with_the_count_of_tasks(
        self, campaign, figure,
    ):
        """Kills: counting a task that both arms lack twice in the difference, and printing the unmeasured count as
        its own total."""
        add_counted_block(campaign, "old", toolkit=[None], bare=[None])
        add_counted_block(campaign, "new", toolkit=[definition_counts(2, 20, 2, 1)], bare=[definition_counts(1, 5, 1, 1)])

        lines = campaign.summarize()

        not_measured = "not measured (1 of 2 paired tasks lack the counts)"
        assert f"  toolkit {figure}: {not_measured}" in lines
        assert f"  bare {figure}: {not_measured}" in lines
        assert f"  {figure}, toolkit - bare: {not_measured}" in lines

    def test_the_reference_pools_the_paired_tasks_non_test_counts(self, campaign):
        paired = reference_task(code=40, definitions=definition_counts(3, 30, 2, 1))
        other_paired = reference_task(code=40, commit_digit="c", definitions=definition_counts(2, 40, 4, 1))
        unpaired = reference_task(code=40, commit_digit="d", definitions=definition_counts(40, 4000, 40, 40))
        pin_reference_task_set(campaign, paired, other_paired, unpaired)
        for task in (paired, other_paired):
            add_counted_block(
                campaign, task.id, toolkit=[definition_counts(2, 20, 2, 1)], bare=[definition_counts(1, 5, 1, 1)],
            )
        campaign.add_block(unpaired.id, record(unpaired.id, "toolkit"), record(unpaired.id, "bare", ok=False, reason="timeout"))

        lines = campaign.summarize()

        assert f"  reference (the merged commits) {WORDS_FIGURE}: {(30 + 40) / (3 + 2):.4f}" in lines
        assert f"  reference (the merged commits) {SHARE_FIGURE}: {(1 + 1) / (2 + 4):.4f}" in lines

    def test_a_reference_entry_without_the_counts_is_not_measured(self, campaign):
        task = reference_task(code=40, docstring=10)
        pin_reference_task_set(campaign, task)
        add_counted_block(campaign, task.id, toolkit=[definition_counts(2, 20, 2, 1)], bare=[definition_counts(1, 5, 1, 1)])

        lines = campaign.summarize()

        for figure in BOTH_FIGURES:
            assert (
                f"  reference (the merged commits) {figure}: "
                "not measured (1 of 1 paired tasks with a reference entry lack the counts)"
            ) in lines
        assert f"  toolkit {WORDS_FIGURE}: 10.0000" in lines

    def test_an_unavailable_reference_and_a_reference_lacking_the_task_print_n_a_and_never_say_unavailable(self, campaign):
        add_counted_block(campaign, "t1", toolkit=[definition_counts(2, 20, 2, 1)], bare=[definition_counts(1, 5, 1, 1)])
        unavailable = campaign.summarize()
        other_task = reference_task(code=40, definitions=definition_counts(3, 30, 2, 1))
        pin_reference_task_set(campaign, other_task)
        lacking_the_task = campaign.summarize()

        assert "  reference unavailable: the campaign has no manifest" in unavailable
        assert not any("reference unavailable" in line for line in lacking_the_task)
        for lines in (unavailable, lacking_the_task):
            for figure in BOTH_FIGURES:
                assert f"  reference (the merged commits) {figure}: n/a" in lines
            assert not any("reference unavailable" in line for line in figure_section(lines))

    def test_an_arm_with_no_new_docstring_prints_n_a_for_that_figure_and_its_difference(self, campaign):
        add_counted_block(campaign, "t1", toolkit=[definition_counts(0, 0, 2, 0)], bare=[definition_counts(2, 10, 2, 1)])

        lines = campaign.summarize()

        assert f"  toolkit {WORDS_FIGURE}: n/a" in lines
        assert f"  bare {WORDS_FIGURE}: 5.0000" in lines
        assert f"  {WORDS_FIGURE}, toolkit - bare: n/a" in lines
        assert f"  toolkit {SHARE_FIGURE}: 0.0000" in lines
        assert f"  {SHARE_FIGURE}, toolkit - bare: -0.5000, no interval for fewer than two paired tasks" in lines

    def test_the_figures_print_after_the_secondary_outcome_and_before_the_diagnostics(self, campaign):
        add_counted_block(campaign, "t1", toolkit=[definition_counts(2, 20, 2, 1)], bare=[definition_counts(1, 5, 1, 1)])

        lines = campaign.summarize()

        figure_headers = [index for index, line in enumerate(lines) if line.startswith("additional secondary outcome:")]
        assert len(figure_headers) == 2
        assert max(index for index, line in enumerate(lines) if line.startswith("  paired task ")) < figure_headers[0]
        assert figure_headers[-1] < lines.index("diagnostics per arm:")

    def test_the_primary_outcome_lines_are_the_same_with_and_without_the_counts(self, tmp_path):
        def primary_lines(campaign_name, definitions_by_task) -> list[str]:
            campaign = Campaign(tmp_path / campaign_name)
            for task_id, words in (("t1", 20), ("t2", 30)):
                campaign.add_block(
                    task_id,
                    record(task_id, "toolkit", run_metrics=metrics(words=words, definitions=definitions_by_task[task_id])),
                    record(task_id, "bare", run_metrics=metrics(words=5, definitions=definitions_by_task[task_id])),
                )
            lines = campaign.summarize()
            start = next(index for index, line in enumerate(lines) if line.startswith("primary outcome:"))
            end = max(index for index, line in enumerate(lines) if line.startswith("  excluded,"))
            return lines[start:end + 1]

        without_counts = primary_lines("without", {"t1": None, "t2": None})
        with_counts = primary_lines("with", {"t1": definition_counts(2, 4, 3, 1), "t2": definition_counts(5, 5, 4, 4)})

        assert without_counts and with_counts == without_counts

    def test_real_measure_diff_output_reaches_the_arms_and_the_reference(self, campaign, tmp_path):
        """Kills: a key or scope that the producer writes and the reader does not read, which a hand-built fixture hides."""
        toolkit_source = (
            'def documented():\n    """\n    Does a thing.\n\n    More words here.\n    """\n    return 1\n\n\n'
            "def undocumented():\n    return 2\n"
        )
        bare_source = 'def short():\n    """\n    Short.\n    """\n    return 1\n'
        reference_source = (
            'def long_one():\n    """\n    One two three four five.\n    """\n    return 1\n\n\n'
            'def second():\n    """\n    Six.\n    """\n    return 2\n'
        )
        measured = {}
        for name, source in (("toolkit", toolkit_source), ("bare", bare_source), ("reference", reference_source)):
            (tmp_path / name).mkdir()
            measured[name] = _measure_change(tmp_path / name, after={"mod.py": source}).to_dict()
        reference_template = reference_task(code=40, docstring=10).to_dict()
        task = tasks.ReplayTask.from_dict({**reference_template, "reference_metrics": measured["reference"]})
        pin_reference_task_set(campaign, task)
        campaign.add_block(
            task.id,
            record(task.id, "toolkit", run_metrics=measured["toolkit"]), record(task.id, "bare", run_metrics=measured["bare"]),
        )

        lines = campaign.summarize()

        def expected(name: str) -> tuple[float, float]:
            counts = PythonDefinitionCounts(**measured[name]["python_definition_counts"]["non_test"])
            assert counts.new_docstrings and counts.new_definitions, "the fixture's source adds a docstring and a definition"
            return (
                counts.new_docstring_words / counts.new_docstrings,
                counts.documented_new_definitions / counts.new_definitions,
            )

        assert expected("toolkit")[1] == 0.5 and expected("bare")[1] == 1.0 and expected("reference")[1] == 1.0
        for name, prefix in (
            ("toolkit", "  toolkit"), ("bare", "  bare"), ("reference", "  reference (the merged commits)"),
        ):
            words_per_docstring, documented_share = expected(name)
            assert number_after(lines, f"{prefix} {WORDS_FIGURE}:") == pytest.approx(words_per_docstring, abs=1e-4)
            assert number_after(lines, f"{prefix} {SHARE_FIGURE}:") == pytest.approx(documented_share, abs=1e-4)


class TestThePerDocstringFiguresAsValues:
    def test_each_figure_is_a_ratio_of_sums_over_a_tasks_per_run_means(self):
        """Kills:
        - pooling run sums
        - a mean of per-task ratios
        - a share numerator wired to new docstrings
        - a field swap
        - a read of the test scope

        Task `b` has 6 new docstrings and 2 new definitions, so a share numerator wired to new docstrings puts its share
        above 1.
        """
        outcomes = figure_outcomes(counted_blocks({
            "a": ([definition_counts(2, 20, 4, 1), definition_counts(4, 60, 2, 1)], [definition_counts(2, 8, 3, 2)]),
            "b": ([definition_counts(6, 12, 2, 1)], [definition_counts(2, 6, 4, 1)]),
        }))

        toolkit_words, bare_words = (20 + 60) / 2 + 12, 8 + 6
        toolkit_docstrings, bare_docstrings = (2 + 4) / 2 + 6, 2 + 2
        words = outcomes[WORDS_FIGURE]
        assert words.arms["toolkit"].ratio == pytest.approx(toolkit_words / toolkit_docstrings)
        assert words.arms["bare"].ratio == pytest.approx(bare_words / bare_docstrings)
        assert words.difference.difference == pytest.approx(toolkit_words / toolkit_docstrings - bare_words / bare_docstrings)
        toolkit_share, bare_share = ((1 + 1) / 2 + 1) / ((4 + 2) / 2 + 2), (2 + 1) / (3 + 4)
        share = outcomes[SHARE_FIGURE]
        assert share.arms["toolkit"].ratio == pytest.approx(toolkit_share)
        assert share.arms["bare"].ratio == pytest.approx(bare_share)
        assert share.difference.difference == pytest.approx(toolkit_share - bare_share)

    def test_the_reference_is_a_ratio_of_sums_over_the_paired_tasks_with_an_entry(self):
        """Kills: a mean of per-task ratios, and pooling a reference task that is not paired.

        The tasks' words per docstring are 10 and 20 and their shares 1/2 and 1/4, so a mean of ratios gives 15 and 3/8.
        """
        blocks = counted_blocks({
            task_id: ([definition_counts(2, 20, 2, 1)], [definition_counts(1, 5, 1, 1)]) for task_id in ("a", "b")
        })
        reference = {
            task_id: {"python_definition_counts": counts}
            for task_id, counts in {
                "a": definition_counts(3, 30, 2, 1),
                "b": definition_counts(2, 40, 4, 1),
                "unpaired": definition_counts(40, 4000, 40, 40),
            }.items()
        }

        outcomes = figure_outcomes(blocks, reference)

        assert outcomes[WORDS_FIGURE].reference.ratio == pytest.approx((30 + 40) / (3 + 2))
        assert outcomes[SHARE_FIGURE].reference.ratio == pytest.approx((1 + 1) / (2 + 4))

    @pytest.mark.parametrize(
        ("figure", "numerator_index", "denominator_index"),
        [pytest.param(WORDS_FIGURE, 1, 0, id="words per new docstring"), pytest.param(SHARE_FIGURE, 3, 2, id="share")],
    )
    def test_the_interval_is_bootstrapped_over_the_pooled_difference(self, figure, numerator_index, denominator_index):
        """Kills: an interval bootstrapped over an unweighted mean of per-task differences instead of the pooled
        difference."""
        toolkit_by_task = {"a": (3, 35, 4, 1), "b": (2, 16, 6, 2), "c": (6, 29, 6, 6)}
        bare_by_task = {"a": (4, 17, 5, 4), "b": (4, 30, 5, 0), "c": (4, 11, 3, 2)}
        blocks = counted_blocks({
            task_id: ([definition_counts(*toolkit_by_task[task_id])], [definition_counts(*bare_by_task[task_id])])
            for task_id in toolkit_by_task
        })

        def pooled_ratio(counts_by_task, resampled_ids) -> float:
            return (
                sum(counts_by_task[task_id][numerator_index] for task_id in resampled_ids)
                / sum(counts_by_task[task_id][denominator_index] for task_id in resampled_ids)
            )

        def pooled_difference(resampled_ids) -> float:
            return pooled_ratio(toolkit_by_task, resampled_ids) - pooled_ratio(bare_by_task, resampled_ids)

        def unweighted_mean_difference(resampled_ids) -> float:
            return statistics.fmean(pooled_difference([task_id]) for task_id in resampled_ids)

        task_ids = sorted(toolkit_by_task)
        clusters = {task_id: (task_id, "") for task_id in task_ids}
        (low, high), dropped = analysis.bootstrap_interval_with_drops(task_ids, pooled_difference, cluster_by_defect=clusters)
        unweighted_interval, _ = analysis.bootstrap_interval_with_drops(
            task_ids, unweighted_mean_difference, cluster_by_defect=clusters,
        )
        assert unweighted_interval != pytest.approx((low, high), abs=1e-4), (
            "the fixture's unweighted-mean interval equals the pooled one, so it cannot tell them apart"
        )

        difference = figure_outcomes(blocks)[figure].difference

        assert difference.difference == pytest.approx(pooled_difference(task_ids))
        assert difference.interval == pytest.approx((low, high))
        assert difference.dropped_resamples == dropped

    @pytest.mark.parametrize("empty_arm", ["toolkit", "bare"])
    @pytest.mark.parametrize("figure", BOTH_FIGURES)
    def test_resamples_that_leave_an_arm_with_no_denominator_are_dropped_and_counted(self, figure, empty_arm):
        """Two tasks, one of which leaves an arm empty: a resample drawing only that task drops, about a quarter of them."""
        populated, empty = [definition_counts(3, 30, 3, 2)], [definition_counts(0, 0, 0, 0)]
        blocks = counted_blocks({
            "both-arms": (populated, populated),
            "one-arm-empty": (empty if empty_arm == "toolkit" else populated, empty if empty_arm == "bare" else populated),
        })

        difference = figure_outcomes(blocks)[figure].difference

        assert 2000 < difference.dropped_resamples < 3000

    @pytest.mark.parametrize("figure", BOTH_FIGURES)
    def test_a_fixture_with_no_empty_arm_drops_no_resample(self, figure):
        blocks = counted_blocks({
            "t1": ([definition_counts(3, 30, 3, 2)], [definition_counts(2, 10, 3, 1)]),
            "t2": ([definition_counts(1, 9, 2, 1)], [definition_counts(4, 8, 2, 2)]),
        })

        difference = figure_outcomes(blocks)[figure].difference

        assert difference.interval is not None, "two paired tasks bootstrap an interval, so a zero drop count is a real count"
        assert difference.dropped_resamples == 0


class TestTheCampaignLineNamesTheRunner:
    def test_it_prints_the_commit_the_manifest_recorded(self, campaign):
        campaign.add_block(
            "t1", record("t1", "toolkit", runner_commit="a" * 40, runner_dirty=True),
            record("t1", "bare", runner_commit="a" * 40, runner_dirty=True),
        )
        (campaign.dir / "manifest.json").write_text(json.dumps({"runner_commit": "a" * 40, "runner_dirty": True}))

        first_line = campaign.summarize()[0]

        assert first_line == (
            f"campaign 'c1': 1 complete blocks, 0 incomplete blocks; runner commit {'a' * 40}, "
            "with uncommitted changes under evals/"
        )

    def test_records_with_no_reading_beside_the_manifests_reading_are_counted(self, campaign):
        campaign.add_block("t1", record("t1", "toolkit"), record("t1", "bare"))
        (campaign.dir / "manifest.json").write_text(json.dumps({"runner_commit": "a" * 40, "runner_dirty": False}))

        first_line = campaign.summarize()[0]

        assert first_line == (
            "campaign 'c1': 1 complete blocks, 0 incomplete blocks; runner readings differ across the campaign: "
            f"no runner reading (records: 2); runner commit {'a' * 40} (manifest)"
        )

    def test_a_campaign_resumed_at_another_commit_names_both_commits_and_their_record_counts(self, campaign):
        first_start, resumed = "a" * 40, "b" * 40
        campaign.add_block(
            "t1", record("t1", "toolkit", runner_commit=first_start, runner_dirty=False),
            record("t1", "bare", runner_commit=first_start, runner_dirty=False),
        )
        campaign.add_block(
            "t2", record("t2", "toolkit", runner_commit=resumed, runner_dirty=True),
            record("t2", "bare", runner_commit=resumed, runner_dirty=True),
        )
        (campaign.dir / "manifest.json").write_text(json.dumps({"runner_commit": first_start, "runner_dirty": False}))

        first_line = campaign.summarize()[0]

        assert first_line == (
            "campaign 'c1': 2 complete blocks, 0 incomplete blocks; runner readings differ across the campaign: "
            f"runner commit {first_start} (manifest, records: 2); "
            f"runner commit {resumed}, with uncommitted changes under evals/ (records: 2)"
        )

    def test_records_that_all_match_the_manifest_leave_the_clause_unchanged(self, campaign):
        campaign.add_block(
            "t1", record("t1", "toolkit", runner_commit="a" * 40, runner_dirty=False),
            record("t1", "bare", runner_commit="a" * 40, runner_dirty=False),
        )
        (campaign.dir / "manifest.json").write_text(json.dumps({"runner_commit": "a" * 40, "runner_dirty": False}))

        assert campaign.summarize()[0].endswith(f"; runner commit {'a' * 40}")

    def test_a_manifest_commit_that_is_no_object_name_reads_as_unreadable_and_is_not_printed(self, campaign):
        campaign.add_block(
            "t1", record("t1", "toolkit", runner_dirty=False), record("t1", "bare", runner_dirty=False),
        )
        forged_commit = "a" * 40 + "\nforged report line"
        (campaign.dir / "manifest.json").write_text(json.dumps({"runner_commit": forged_commit, "runner_dirty": False}))

        first_line = campaign.summarize()[0]

        assert first_line == (
            "campaign 'c1': 1 complete blocks, 0 incomplete blocks; "
            "runner commit unreadable, without uncommitted changes under evals/"
        )

    def test_the_runner_clause_and_the_reference_come_from_one_manifest_state(self, campaign, monkeypatch):
        """Kills: a second manifest read, which can answer from another state than the runner clause's. Each read
        of the manifest file returns the next state, so a second read would mix the two."""
        task_in_first_set = reference_task(code=40, docstring=10)
        task_in_second_set = reference_task(code=40, docstring=30)
        assert task_in_first_set.id == task_in_second_set.id
        tasks.write_task_set(campaign.local_dir / "tasks", "first-set", [task_in_first_set])
        tasks.write_task_set(campaign.local_dir / "tasks", "second-set", [task_in_second_set])
        manifest_states = [
            json.dumps({
                "runner_commit": "a" * 40, "runner_dirty": False, "tasks_name": "first-set",
                "task_set_hash": task_set_hash((task_in_first_set,)),
            }),
            json.dumps({
                "runner_commit": "b" * 40, "runner_dirty": False, "tasks_name": "second-set",
                "task_set_hash": task_set_hash((task_in_second_set,)),
            }),
        ]
        first_reading = {"runner_commit": "a" * 40, "runner_dirty": False}
        campaign.add_block(
            task_in_first_set.id,
            record(task_in_first_set.id, "toolkit", **first_reading), record(task_in_first_set.id, "bare", **first_reading),
        )
        manifest_path = campaign.dir / "manifest.json"
        manifest_path.write_text(manifest_states[0])
        real_read_text = Path.read_text
        manifest_reads = []

        def read_text_advancing_the_manifest(path, *args, **kwargs):
            if path == manifest_path:
                manifest_reads.append(path)
                return manifest_states[min(len(manifest_reads), len(manifest_states)) - 1]
            return real_read_text(path, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", read_text_advancing_the_manifest)

        lines = campaign.summarize()

        assert len(manifest_reads) == 1, "the interception saw the one read the summary takes"
        assert lines[0].endswith(f"; runner commit {'a' * 40}")
        assert number_after(lines, "  reference (the merged commits), paired tasks pooled:") == pytest.approx(25.0)

    def test_a_manifest_that_lacks_the_runner_fields_says_the_commit_is_not_recorded(self, campaign):
        campaign.add_block("t1", record("t1", "toolkit"), record("t1", "bare"))
        (campaign.dir / "manifest.json").write_text(json.dumps({"budget_cap_usd": CAP}))

        assert campaign.summarize()[0].endswith("; runner commit not recorded")


class TestAnUnavailableReferenceNamesItsCause:
    def reference_line(self, campaign):
        return next(line for line in campaign.summarize() if line.startswith("  reference unavailable"))

    def test_a_campaign_with_no_manifest_says_so(self, campaign):
        campaign.add_block("t1", record("t1", "toolkit"), record("t1", "bare"))

        assert self.reference_line(campaign) == "  reference unavailable: the campaign has no manifest"

    def test_an_unparseable_manifest_says_it_could_not_be_read(self, campaign):
        campaign.add_block("t1", record("t1", "toolkit"), record("t1", "bare"))
        (campaign.dir / "manifest.json").write_text("not json")

        assert "the manifest could not be read: JSONDecodeError" in self.reference_line(campaign)

    def test_a_manifest_that_is_not_a_json_object_says_so(self, campaign):
        campaign.add_block("t1", record("t1", "toolkit"), record("t1", "bare"))
        (campaign.dir / "manifest.json").write_text("[]")

        assert self.reference_line(campaign) == "  reference unavailable: the manifest is not a JSON object"

    @pytest.mark.parametrize("task_file_text", [None, "not json", '{"not": "a list"}'], ids=["gone", "unparseable", "not-a-list"])
    def test_a_task_set_that_cannot_be_read_gives_the_readers_cause(self, campaign, task_file_text):
        campaign.add_block("t1", record("t1", "toolkit"), record("t1", "bare"))
        (campaign.dir / "manifest.json").write_text(json.dumps({"tasks_name": "damaged"}))
        tasks_dir = campaign.local_dir / "tasks"
        if task_file_text is not None:
            tasks_dir.mkdir()
            (tasks_dir / "damaged.json").write_text(task_file_text)
        with pytest.raises(tasks.TaskFileError) as cause:
            tasks.read_task_set(tasks_dir, "damaged")

        line = self.reference_line(campaign)

        assert line == f"  reference unavailable: task set 'damaged' could not be read: {cause.value}"


class TestAReadableReferenceIsReportedWithoutAWarning:
    def test_the_reference_rate_is_the_task_sets_docstring_lines_per_100_code_lines(self, campaign):
        task = reference_task(code=40, docstring=10)
        tasks.write_task_set(campaign.local_dir / "tasks", "readable", [task])
        (campaign.dir / "manifest.json").write_text(
            json.dumps({"tasks_name": "readable", "task_set_hash": task_set_hash((task,))}),
        )
        campaign.add_block(task.id, record(task.id, "toolkit"), record(task.id, "bare"))

        lines = campaign.summarize()

        counts = task.reference_metrics.line_counts["non_test"]
        expected_rate = 100 * counts["docstring"] / counts["code"]
        assert expected_rate == pytest.approx(25.0), "the fixture's metrics reach the task as written"
        assert number_after(lines, "  reference (the merged commits), paired tasks pooled:") == pytest.approx(
            expected_rate,
        )
        assert not any("reference unavailable" in line for line in lines)

    def test_the_primary_outcome_prints_the_merged_commits_pooled_ratio_over_the_paired_tasks(self, campaign):
        """Kills: a docstring-line numerator, a mean of per-task ratios, and counting an unpaired task's commit."""
        small = reference_task(code=40, docstring=3, words=10)
        large = reference_task(code=160, docstring=5, words=90, commit_digit="c")
        unpaired = reference_task(code=10, docstring=1, words=500, commit_digit="d")
        task_set = (small, large, unpaired)
        tasks.write_task_set(campaign.local_dir / "tasks", "readable", list(task_set))
        (campaign.dir / "manifest.json").write_text(
            json.dumps({"tasks_name": "readable", "task_set_hash": task_set_hash(task_set)}),
        )
        for task in (small, large):
            campaign.add_block(task.id, record(task.id, "toolkit"), record(task.id, "bare"))
        campaign.add_block(
            unpaired.id, record(unpaired.id, "toolkit"), record(unpaired.id, "bare", ok=False, reason="timeout"),
        )

        lines = campaign.summarize()

        reference_ratio = number_after(lines, "  reference (the merged commits) words per code line:")
        assert reference_ratio == pytest.approx((10 + 90) / (40 + 160))
        assert not any("reference unavailable" in line for line in lines)

    def test_a_merged_commits_test_scope_counts_stay_out_of_both_reference_figures(self, campaign):
        """Kills: reading the reference's words, code lines or docstring lines as the sum of its test and non-test scopes."""
        task = reference_task(code=40, docstring=10, words=10, test_words=300, test_code=200, test_docstring=60)
        tasks.write_task_set(campaign.local_dir / "tasks", "readable", [task])
        (campaign.dir / "manifest.json").write_text(
            json.dumps({"tasks_name": "readable", "task_set_hash": task_set_hash((task,))}),
        )
        campaign.add_block(task.id, record(task.id, "toolkit"), record(task.id, "bare"))

        lines = campaign.summarize()

        assert number_after(lines, "  reference (the merged commits) words per code line:") == pytest.approx(10 / 40)
        assert number_after(lines, "  reference (the merged commits), paired tasks pooled:") == pytest.approx(100 * 10 / 40)

    def test_an_unpaired_tasks_merged_commit_stays_out_of_the_pooled_reference(self, campaign):
        task = reference_task(code=40, docstring=10)
        tasks.write_task_set(campaign.local_dir / "tasks", "readable", [task])
        (campaign.dir / "manifest.json").write_text(
            json.dumps({"tasks_name": "readable", "task_set_hash": task_set_hash((task,))}),
        )
        campaign.add_block(task.id, record(task.id, "toolkit"), record(task.id, "bare", ok=False, reason="timeout"))

        lines = campaign.summarize()

        assert "  reference (the merged commits) words per code line: n/a" in lines
        assert not any("reference unavailable" in line for line in lines)

    @pytest.mark.parametrize(
        ("pinned_hash", "reason"),
        [("0" * 64, "task set 'rewritten' is not the one this campaign pinned"), (None, "the manifest records no task set hash")],
        ids=["different-hash", "no-hash"],
    )
    def test_a_task_set_that_is_not_the_one_the_campaign_pinned_leaves_the_reference_unavailable(
        self, campaign, pinned_hash, reason,
    ):
        task = reference_task(code=40, docstring=10)
        tasks.write_task_set(campaign.local_dir / "tasks", "rewritten", [task])
        manifest = {"tasks_name": "rewritten"}
        if pinned_hash is not None:
            manifest["task_set_hash"] = pinned_hash
        (campaign.dir / "manifest.json").write_text(json.dumps(manifest))
        campaign.add_block(task.id, record(task.id, "toolkit"), record(task.id, "bare"))

        lines = campaign.summarize()

        assert f"  reference unavailable: {reason}" in lines
        assert "  reference (the merged commits), paired tasks pooled: n/a" in lines
        assert "  reference (the merged commits) words per code line: n/a" in lines
        assert any(line.startswith("paired difference toolkit - bare:") for line in lines)
        assert "paired 1 of 1 complete tasks" in lines


class TestSpendByAccount:
    def spend_with_one_unparsed_line(self, campaign) -> None:
        campaign.add_block("t1", record("t1", "toolkit"), record("t1", "bare"))
        spend = SpendFile(campaign.dir / "spend.jsonl", budget_cap_usd=CAP)
        spend.append(SpendLine("t1", "bare", 0, 1, ACCOUNT, "s", 2.0, False))
        spend.append(SpendLine("t1", "bare", 0, 1, "/other/account", "s", 1.0, False))
        with spend.path.open("a") as handle:
            handle.write("not json\n")

    def test_an_unparseable_spend_line_counts_at_the_flag_when_the_manifest_pins_no_cap(self, campaign):
        self.spend_with_one_unparsed_line(campaign)

        lines = campaign.summarize()

        assert f"  {ACCOUNT!r}: $5.00" in lines and "  '/other/account': $4.00" in lines
        assert any("did not parse" in line and "$3.00 each" in line and "manifest pins no usable cap" in line for line in lines)

    def test_an_unparseable_spend_line_counts_at_the_cap_the_campaign_pinned(self, campaign):
        self.spend_with_one_unparsed_line(campaign)
        (campaign.dir / "manifest.json").write_text(json.dumps({"budget_cap_usd": 2.0}))

        lines = campaign.summarize()

        assert f"  {ACCOUNT!r}: $4.00" in lines and "  '/other/account': $3.00" in lines
        assert any("did not parse" in line and "$2.00 each" in line and "campaign pinned" in line for line in lines)

    @pytest.mark.parametrize("unusable_cap", ["three", 0, -1.0, True], ids=["string", "zero", "negative", "bool"])
    def test_a_pinned_cap_that_is_not_a_positive_number_falls_back_to_the_flag(self, campaign, unusable_cap):
        self.spend_with_one_unparsed_line(campaign)
        (campaign.dir / "manifest.json").write_text(json.dumps({"budget_cap_usd": unusable_cap}))

        lines = campaign.summarize()

        assert any("did not parse" in line and "$3.00 each" in line and "manifest pins no usable cap" in line for line in lines)

