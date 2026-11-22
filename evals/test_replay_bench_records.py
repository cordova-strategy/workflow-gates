"""Tests for the on-disk run record and diff a block's runs leave under a campaign directory."""
from __future__ import annotations

import json

import pytest
from replay_bench import records
from review_bench.runner import HarnessInvalidatedError
from test_replay_bench_summary import metrics, record


class TestWriteRun:
    def test_a_rerun_with_no_diff_removes_the_earlier_diff(self, tmp_path):
        first_attempt = record("t1", "toolkit")
        records.write_run(tmp_path, first_attempt, "diff --git a/x b/x\n")
        stale_diff = records.diff_path(tmp_path, "t1", "toolkit", 0)
        assert stale_diff.exists()

        records.write_run(tmp_path, record("t1", "toolkit", ok=False, reason="launch-error"), None)

        assert not stale_diff.exists()
        assert records.record_path(tmp_path, "t1", "toolkit", 0).exists()

    def test_a_rerun_with_no_diff_keeps_the_diff_of_a_sibling_run(self, tmp_path):
        records.write_run(tmp_path, record("t1", "bare"), "diff --git a/y b/y\n")

        records.write_run(tmp_path, record("t1", "toolkit"), None)

        assert records.diff_path(tmp_path, "t1", "bare", 0).exists()

    def test_a_run_with_a_diff_writes_both_files(self, tmp_path):
        records.write_run(tmp_path, record("t1", "toolkit"), "diff --git a/x b/x\n")

        assert records.diff_path(tmp_path, "t1", "toolkit", 0).read_text(encoding="utf-8") == "diff --git a/x b/x\n"
        assert records.read_block_records(tmp_path, "t1") == [record("t1", "toolkit")]


class TestReadingARecordThatLacksOptionalKeys:
    def test_a_record_without_the_optional_keys_reads_with_their_defaults(self, tmp_path):
        records.write_run(tmp_path, record("t1", "toolkit"), None)
        path = records.record_path(tmp_path, "t1", "toolkit", 0)
        stored = json.loads(path.read_text(encoding="utf-8"))
        for key in ("runner_commit", "runner_dirty", "empty_final_text", "denied_tool_calls"):
            del stored[key]
        path.write_text(json.dumps(stored), encoding="utf-8")

        (read_back,) = records.read_block_records(tmp_path, "t1")

        assert (read_back.runner_commit, read_back.runner_dirty) == (None, None)
        assert read_back.empty_final_text is False
        assert read_back.denied_tool_calls == []


class TestEndedWithoutTextOrChange:
    @pytest.mark.parametrize(
        ("ok", "empty_final_text", "changed_paths", "expected"),
        [
            pytest.param(True, True, [], True, id="no-text-and-no-changed-path"),
            pytest.param(True, True, ["src/a.py"], False, id="no-text-but-a-changed-path"),
            pytest.param(True, False, [], False, id="text-and-no-changed-path"),
            pytest.param(False, True, [], False, id="a-missing-run"),
        ],
    )
    def test_it_holds_only_for_an_ok_run_with_neither_text_nor_a_changed_path(
        self, ok, empty_final_text, changed_paths, expected,
    ):
        run_metrics = {**metrics(), "changed_paths": changed_paths}

        run = record(
            "t1", "toolkit", ok=ok, reason=None if ok else "timeout", run_metrics=run_metrics,
            empty_final_text=empty_final_text,
        )

        assert run.ended_without_text_or_change is expected


class TestReadingARecordWithInvalidRunnerProvenance:
    @pytest.mark.parametrize(
        ("key", "bad_value"),
        [
            pytest.param("runner_commit", ["a" * 40], id="commit-a-list"),
            pytest.param("runner_commit", "abc", id="commit-abbreviated"),
            pytest.param("runner_commit", "a" * 40 + "\nforged line", id="commit-with-a-newline"),
            pytest.param("runner_dirty", "yes", id="dirty-text"),
            pytest.param("runner_dirty", 1, id="dirty-integer"),
        ],
    )
    def test_the_record_is_refused_as_unreadable(self, tmp_path, key, bad_value):
        records.write_run(tmp_path, record("t1", "toolkit"), None)
        path = records.record_path(tmp_path, "t1", "toolkit", 0)
        stored = json.loads(path.read_text(encoding="utf-8"))
        stored[key] = bad_value
        path.write_text(json.dumps(stored), encoding="utf-8")

        with pytest.raises(HarnessInvalidatedError, match="cannot read the run record"):
            records.read_block_records(tmp_path, "t1")

    def test_a_full_object_name_and_a_bool_are_read_back_beside_the_other_later_added_fields(self, tmp_path):
        stored = record("t1", "toolkit", runner_commit="a" * 40, runner_dirty=True, empty_final_text=True)
        stored.denied_tool_calls = [{"tool": "Bash", "command": "pytest -q"}, {"tool": "Edit", "command": None}]
        records.write_run(tmp_path, stored, None)

        assert records.read_block_records(tmp_path, "t1") == [stored]


class TestReadBlockRecords:
    def test_denied_tool_calls_survive_a_write_and_read(self, tmp_path):
        written = record("t1", "toolkit")
        written.denied_tool_calls = [{"tool": "Bash", "command": "pytest -q"}, {"tool": "Edit", "command": None}]
        records.write_run(tmp_path, written, None)

        assert records.read_block_records(tmp_path, "t1") == [written]

    def test_a_record_stored_without_denied_tool_calls_reads_as_an_empty_list(self, tmp_path):
        records.write_run(tmp_path, record("t1", "toolkit"), None)
        path = records.record_path(tmp_path, "t1", "toolkit", 0)
        stored = json.loads(path.read_text(encoding="utf-8"))
        del stored["denied_tool_calls"]
        path.write_text(json.dumps(stored), encoding="utf-8")

        assert records.read_block_records(tmp_path, "t1")[0].denied_tool_calls == []
