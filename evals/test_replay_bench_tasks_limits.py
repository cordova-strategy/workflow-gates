"""Tests for `build_task_fixture`'s optional settings file, for `SelectionLimits`' range checks, and for the selection
limits `test_replay_bench_tasks.py` has no room for. Kept apart from that file, which is already past 1,000 lines. No
test launches `claude`.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from replay_bench import tasks
from replay_bench.comment_metrics import LineClass
from replay_bench.tasks import SkipReason
from test_replay_bench_tasks import (
    BARE_WRITER_MARKDOWN,
    FIXTURE_TIMEOUT_S,
    _app_with,
    _assert_only_skipped_as,
    _change,
    _git,
    _git_text,
    _make_repo,
    _make_source_repo,
    _mine,
    _mine_one_task,
)

SETTINGS_TEXT = '{"claudeMdExcludes": ["/synthetic/rules/a.md"]}'


def build_fixture_with(tmp_path: Path, settings_text: str | None) -> Path:
    repo = _make_source_repo(tmp_path)
    _change(repo)
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    tasks.build_task_fixture(
        _mine_one_task(repo), fixture, tmp_path / "attempt" / "baseline.git", bare_writer_markdown=BARE_WRITER_MARKDOWN,
        timeout_s=FIXTURE_TIMEOUT_S, settings_text=settings_text,
    )
    return fixture


class TestFixtureSettingsFile:
    def test_settings_text_lands_as_an_excluded_file(self, tmp_path):
        fixture = build_fixture_with(tmp_path, SETTINGS_TEXT)

        assert (fixture / ".claude" / "settings.json").read_bytes() == SETTINGS_TEXT.encode()
        assert _git_text(fixture, "status", "--porcelain") == ""

    def test_no_settings_text_writes_no_settings_file(self, tmp_path):
        fixture = build_fixture_with(tmp_path, None)

        assert not (fixture / ".claude" / "settings.json").exists()


class TestSelectionLimitsRanges:
    INTEGER_FIELDS = (
        "max_count", "max_tasks", "max_files", "min_code_lines", "max_code_lines", "max_test_code_lines", "max_prompt_chars",
        "max_base_mb", "max_base_entries",
    )

    @pytest.mark.parametrize("bad_value", [0, -1])
    @pytest.mark.parametrize("field_name", INTEGER_FIELDS)
    def test_an_integer_limit_below_one_is_refused(self, field_name, bad_value):
        with pytest.raises(tasks.TaskSourceError, match="--" + field_name.replace("_", "-")):
            tasks.SelectionLimits(**{field_name: bad_value})

    def test_equal_code_line_bounds_are_accepted(self):
        assert tasks.SelectionLimits(min_code_lines=7, max_code_lines=7).min_code_lines == 7

    def test_a_minimum_one_above_the_maximum_is_refused(self):
        with pytest.raises(tasks.TaskSourceError, match=r"--min-code-lines.*--max-code-lines"):
            tasks.SelectionLimits(min_code_lines=11, max_code_lines=10)

    def test_a_maximum_below_the_default_minimum_is_refused(self):
        with pytest.raises(tasks.TaskSourceError, match="--max-code-lines"):
            tasks.SelectionLimits(max_code_lines=5)


class TestTestCodeLineCeiling:
    @staticmethod
    def change_with_test_code_lines(repo: Path, test_code_lines: int) -> None:
        _change(repo, {
            "src/app.py": _app_with(12),
            "tests/test_app.py": "".join(f"value_{n} = {n}\n" for n in range(test_code_lines)),
        })

    @pytest.mark.parametrize(("test_code_lines", "kept"), [(20, True), (21, False)])
    def test_max_test_code_lines_is_inclusive(self, tmp_path, test_code_lines, kept):
        repo = _make_repo(tmp_path)
        self.change_with_test_code_lines(repo, test_code_lines)

        report = _mine(repo, max_test_code_lines=20)

        assert bool(report.tasks) is kept
        if not kept:
            _assert_only_skipped_as(report, SkipReason.TOO_MANY_TEST_CODE_LINES)

    @pytest.mark.parametrize(("test_code_lines", "kept"), [(300, True), (301, False)])
    def test_the_default_ceiling_is_three_hundred_test_code_lines(self, tmp_path, test_code_lines, kept):
        repo = _make_repo(tmp_path)
        self.change_with_test_code_lines(repo, test_code_lines)

        report = _mine(repo)

        assert bool(report.tasks) is kept
        if not kept:
            _assert_only_skipped_as(report, SkipReason.TOO_MANY_TEST_CODE_LINES)

    def test_the_skip_shows_in_the_mining_summary_by_its_reason(self, tmp_path):
        repo = _make_repo(tmp_path)
        self.change_with_test_code_lines(repo, 21)

        summary = tasks.format_mining_summary(_mine(repo, max_test_code_lines=20))

        assert "  skipped too-many-test-code-lines: 1" in summary


    def test_a_test_file_at_the_ceiling_plus_comment_and_blank_lines_is_kept_and_a_deleted_test_line_is_not_counted(
        self, tmp_path,
    ):
        repo = _make_repo(tmp_path, {"tests/test_old.py": "".join(f"old_{n} = {n}\n" for n in range(10))})
        added_test_code = "".join(f"value_{n} = {n}\n" for n in range(20))
        _change(repo, {
            "src/app.py": _app_with(12),
            "tests/test_app.py": f"# a comment\n\n{added_test_code}\n# another comment\n",
            "tests/test_old.py": None,
        })

        task = _mine_one_task(repo, max_test_code_lines=20)

        assert task.reference_metrics.line_counts["test"][LineClass.CODE.value] == 20


class TestSubjectOnlyBriefs:
    def test_a_commit_whose_message_is_only_a_subject_line_is_skipped(self, tmp_path):
        repo = _make_repo(tmp_path)
        _change(repo, message="Add helpers")

        _assert_only_skipped_as(_mine(repo), SkipReason.SUBJECT_ONLY_BRIEF)

    def test_a_subject_holding_a_unicode_line_separator_is_still_one_line(self, tmp_path):
        repo = _make_repo(tmp_path)
        _change(repo, message="Add\u2028helpers")

        _assert_only_skipped_as(_mine(repo), SkipReason.SUBJECT_ONLY_BRIEF)

    @pytest.mark.parametrize(("files", "limit_overrides", "reason"), [
        ({"src/app.py": _app_with(3)}, {}, SkipReason.TOO_FEW_CODE_LINES),
        (
            {"src/app.py": _app_with(12), "tests/test_app.py": "".join(f"value_{n} = {n}\n" for n in range(21))},
            {"max_test_code_lines": 20}, SkipReason.TOO_MANY_TEST_CODE_LINES,
        ),
    ])
    def test_a_subject_only_commit_skipped_for_its_line_counts_keeps_that_reason(
        self, tmp_path, files, limit_overrides, reason,
    ):
        repo = _make_repo(tmp_path)
        _change(repo, files, message="Add helpers")

        _assert_only_skipped_as(_mine(repo, **limit_overrides), reason)

    def test_a_commit_with_a_body_after_its_subject_is_kept(self, tmp_path):
        repo = _make_repo(tmp_path)
        _change(repo, message="Add helpers\n\nThey compute values.")

        assert _mine_one_task(repo).brief == "Add helpers\n\nThey compute values."

    def test_a_body_made_only_of_a_co_authored_by_trailer_counts_as_a_body(self, tmp_path):
        repo = _make_repo(tmp_path)
        message = "Add helpers\n\nCo-Authored-By: Pair Author <pair@example.com>"
        _change(repo, message=message)

        assert _mine_one_task(repo).brief == message

    def test_a_merge_commit_that_merged_nothing_and_has_only_a_subject_is_skipped(self, tmp_path):
        repo = _make_repo(tmp_path)
        base_commit = _git_text(repo, "rev-parse", "HEAD").strip()
        parent_commit = _change(repo, {"src/other.py": "other = 1\n"})
        final_commit = _change(repo)
        final_tree = _git_text(repo, "rev-parse", f"{final_commit}^{{tree}}").strip()
        # The second parent is already an ancestor of the first, so `git log <second> ^<first>` lists nothing.
        merge_commit = _git_text(
            repo, "commit-tree", final_tree, "-p", parent_commit, "-p", base_commit, "-m", "Merge nothing",
        ).strip()
        _git(repo, "update-ref", "HEAD", merge_commit)

        report = _mine(repo)

        assert report.tasks == []
        assert dict(report.skip_counts) == {
            SkipReason.NO_PARENT: 1, SkipReason.TOO_FEW_CODE_LINES: 1, SkipReason.SUBJECT_ONLY_BRIEF: 1,
        }
