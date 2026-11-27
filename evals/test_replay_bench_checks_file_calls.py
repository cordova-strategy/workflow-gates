"""Tests for the evals/replay_bench/checks readers behind a smoke run's report: file tool calls, whether a write ran and
transcript incompleteness. Shared helpers live in test_replay_bench_checks_support.
"""
from __future__ import annotations

import pytest
from replay_bench import checks
from test_replay_bench_checks_support import (
    PRINTED_SKIPPED_LINES_SIGNAL_SUFFIX,
    PRINTED_STATUS_DENIED,
    PRINTED_STATUS_RAN,
    PRINTED_STATUS_UNANSWERED,
    PRINTED_TORN_LINE_SIGNAL,
    PRINTED_UNREADABLE_SIGNAL_PREFIX,
    _assistant,
    _call_and_result,
    _tool_use,
    _transcript,
)


class TestFileToolCalls:
    def test_a_call_with_a_result_is_ran_a_denied_one_is_denied_and_one_without_a_result_is_unanswered(self, tmp_path):
        transcript = _transcript(tmp_path, [
            *_call_and_result("toolu_1", "Read", {"file_path": "src/app.py"}),
            *_call_and_result("toolu_2", "Edit", {"file_path": "src/app.py"}, denied=True),
            _assistant([_tool_use("toolu_3", "Write", {"file_path": "src/new.py"})]),
        ])

        assert checks.file_tool_calls(transcript) == [
            {"tool": "Read", "path": "src/app.py", "status": PRINTED_STATUS_RAN},
            {"tool": "Edit", "path": "src/app.py", "status": PRINTED_STATUS_DENIED},
            {"tool": "Write", "path": "src/new.py", "status": PRINTED_STATUS_UNANSWERED},
        ]

    def test_a_denied_read_is_denied_though_the_denial_is_also_a_result(self, tmp_path):
        transcript = _transcript(tmp_path, _call_and_result("toolu_1", "Read", {"file_path": "a.py"}, denied=True))

        assert [call["status"] for call in checks.file_tool_calls(transcript)] == [PRINTED_STATUS_DENIED]

    def test_only_read_and_the_write_tools_are_listed_in_transcript_order(self, tmp_path):
        transcript = _transcript(tmp_path, [
            *_call_and_result("toolu_1", "Bash", {"command": "cat a.py"}),
            *_call_and_result("toolu_2", "MultiEdit", {"file_path": "b.py"}),
            *_call_and_result("toolu_3", "Grep", {"pattern": "x", "file_path": "c.py"}),
            *_call_and_result("toolu_4", "Read", {"file_path": "d.py"}),
        ])

        assert [(call["tool"], call["path"]) for call in checks.file_tool_calls(transcript)] == [
            ("MultiEdit", "b.py"), ("Read", "d.py"),
        ]

    def test_a_notebook_edit_names_its_notebook_path(self, tmp_path):
        notebook_edit = {"notebook_path": "n.ipynb", "file_path": "ignored.py"}
        transcript = _transcript(tmp_path, _call_and_result("toolu_1", "NotebookEdit", notebook_edit))

        assert [call["path"] for call in checks.file_tool_calls(transcript)] == ["n.ipynb"]

    @pytest.mark.parametrize("tool_input", [{}, {"file_path": 7}, {"file_path": None}], ids=["missing", "number", "null"])
    def test_a_missing_or_non_string_path_is_none(self, tmp_path, tool_input):
        transcript = _transcript(tmp_path, _call_and_result("toolu_1", "Read", tool_input))

        assert checks.file_tool_calls(transcript) == [{"tool": "Read", "path": None, "status": PRINTED_STATUS_RAN}]

    def test_a_transcript_with_no_calls_lists_none(self, tmp_path):
        assert checks.file_tool_calls(_transcript(tmp_path, [])) == []


class TestMadeWriteCallThatRan:
    @pytest.mark.parametrize(
        ("tool_name", "tool_input"),
        [
            ("Edit", {"file_path": "src/app.py"}),
            ("MultiEdit", {"file_path": "src/app.py"}),
            ("Write", {"file_path": "src/app.py"}),
            ("NotebookEdit", {"notebook_path": "n.ipynb"}),
        ],
    )
    def test_each_write_tool_that_ran_counts(self, tmp_path, tool_name, tool_input):
        transcript = _transcript(tmp_path, [
            *_call_and_result("toolu_1", "Read", {"file_path": "src/app.py"}),
            *_call_and_result("toolu_2", tool_name, tool_input),
        ])

        assert checks.made_write_call_that_ran(transcript) is True

    def test_a_denied_write_does_not_count(self, tmp_path):
        transcript = _transcript(tmp_path, _call_and_result("toolu_1", "Edit", {"file_path": "src/app.py"}, denied=True))

        assert checks.made_write_call_that_ran(transcript) is False

    def test_an_unanswered_write_does_not_count(self, tmp_path):
        transcript = _transcript(tmp_path, [_assistant([_tool_use("toolu_1", "Write", {"file_path": "src/app.py"})])])

        assert checks.made_write_call_that_ran(transcript) is False

    @pytest.mark.parametrize(
        ("tool_name", "tool_input"), [("Read", {"file_path": "src/app.py"}), ("Bash", {"command": "ls"})],
    )
    def test_a_call_of_another_tool_does_not_count(self, tmp_path, tool_name, tool_input):
        transcript = _transcript(tmp_path, _call_and_result("toolu_1", tool_name, tool_input))

        assert checks.made_write_call_that_ran(transcript) is False

    def test_a_transcript_with_no_calls_does_not_count(self, tmp_path):
        assert checks.made_write_call_that_ran(_transcript(tmp_path, [])) is False


class TestTranscriptIncompletenessSignals:
    def test_a_clean_transcript_has_none(self, tmp_path):
        transcript = _transcript(tmp_path, _call_and_result("toolu_1", "Bash", {"command": "ls"}))

        assert checks.transcript_incompleteness_signals(transcript) == []

    def test_an_unreadable_transcript_names_its_detail(self, tmp_path):
        transcript = checks.read_subagent_transcript(tmp_path / "absent.jsonl")

        expected = f"{PRINTED_UNREADABLE_SIGNAL_PREFIX}{transcript.unreadable_detail}"
        assert checks.transcript_incompleteness_signals(transcript) == [expected]

    def test_a_torn_last_line_is_named_with_the_skipped_line_it_also_counts_as(self, tmp_path):
        transcript = _transcript(tmp_path, [*_call_and_result("toolu_1", "Bash", {"command": "ls"}), '{"type": "assis'])

        assert checks.transcript_incompleteness_signals(transcript) == [
            PRINTED_TORN_LINE_SIGNAL, f"1{PRINTED_SKIPPED_LINES_SIGNAL_SUFFIX}",
        ]

    def test_bad_lines_mid_file_are_counted_without_a_torn_tail(self, tmp_path):
        bad_lines = ["not json", "also not json"]
        transcript = _transcript(tmp_path, [*bad_lines, *_call_and_result("toolu_1", "Bash", {"command": "ls"})])

        assert checks.transcript_incompleteness_signals(transcript) == [f"2{PRINTED_SKIPPED_LINES_SIGNAL_SUFFIX}"]
