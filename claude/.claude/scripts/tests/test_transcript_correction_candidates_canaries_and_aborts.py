"""What reaches the terminal and the scope record from correction-candidates: transcript-text canaries, and corpus aborts."""
import json
import os
from pathlib import Path

import pytest
from transcript_analysis import scope

from . import _correction_candidates_helpers as candidates_helpers
from ._compaction_context_helpers import slash_invocation
from ._correction_candidates_helpers import (
    ABORT_LINE,
    FAMILIES_PREFIX,
    HEADER_PREFIX,
    ask_answer_record,
    ask_record,
    assistant_text,
    prompt,
    question_session,
    question_spec,
    run_main,
    seed,
    ts,
    with_fields,
)
from .conftest import _two_declared_roots

# The fixtures live once in the helper module. An import would trip F811 on every test parameter that names one.
stubbed_git_check = candidates_helpers.stubbed_git_check
out_dir = candidates_helpers.out_dir


_CANARIES = {
    "prompt": "CANARY-PROMPT-TEXT",
    "slash_args": "CANARY-SLASH-ARGS",
    "assistant": "CANARY-ASSISTANT-TEXT",
    "model": "CANARY-MODEL",
    "skill": "CANARY-SKILL",
    "question": "CANARY-QUESTION",
    "header": "CANARY-HEADER",
    "label": "CANARY-OPTION-LABEL",
    "description": "CANARY-OPTION-DESCRIPTION",
    "answer": "CANARY-ANSWER",
    "notes": "CANARY-NOTES",
    "result": "CANARY-DECLINE-CONTENT",
    "answers_key": "CANARY-ANSWERS-KEY",
    "annotations_key": "CANARY-ANNOTATIONS-KEY",
    "entry_key": "CANARY-ENTRY-KEY",
    "option_key": "CANARY-OPTION-KEY",
    "result_key": "CANARY-RESULT-KEY",
}
_CANARIES_IN_KEYS_NO_OUTPUT_READS = {"answers_key", "annotations_key", "entry_key", "option_key", "result_key"}


def _canary_session() -> list[dict]:
    spec = {
        **question_spec(_CANARIES["question"], (_CANARIES["label"], "Other"), header=_CANARIES["header"]),
        _CANARIES["entry_key"]: 1,
    }
    spec["options"][0]["description"] = _CANARIES["description"]
    spec["options"][1][_CANARIES["option_key"]] = 1
    answered = ask_answer_record(
        answers={_CANARIES["question"]: _CANARIES["answer"], _CANARIES["answers_key"]: "x"},
        annotations={_CANARIES["question"]: {"notes": _CANARIES["notes"]}, _CANARIES["annotations_key"]: {}},
        timestamp=ts(4),
    )
    answered["toolUseResult"][_CANARIES["result_key"]] = 1
    declined = ask_answer_record(
        tool_use_id="toolu_declined", tool_use_result="declined", content=_CANARIES["result"], timestamp=ts(7),
    )
    return [
        with_fields(slash_invocation("scratch", _CANARIES["slash_args"]), timestamp=ts(0), uuid="slash"),
        prompt(_CANARIES["prompt"], 1),
        assistant_text(_CANARIES["assistant"], timestamp=ts(2), model=_CANARIES["model"]),
        ask_record([spec], minute=3, model=_CANARIES["model"], attribution_skill=_CANARIES["skill"]),
        answered,
        ask_record([question_spec("Declined?")], tool_use_id="toolu_declined", minute=6),
        declined,
    ]


def _assert_no_canary_outside_the_file(*texts: str) -> None:
    for name, canary in _CANARIES.items():
        for text in texts:
            assert canary not in text, f"canary {name} reached the terminal or the scope record"


class TestCanaries:
    def test_a_run_prints_no_transcript_text_and_the_scope_record_holds_none(self, fake_projects, out_dir, monkeypatch, capsys):
        seed(fake_projects, _canary_session())
        out = out_dir / "run.jsonl"

        _status, stdout, stderr = run_main(monkeypatch, capsys, "--projects", "*", "--out", str(out))

        file_text = out.read_text(encoding="ascii")
        for name, canary in _CANARIES.items():
            if name in _CANARIES_IN_KEYS_NO_OUTPUT_READS:
                assert canary not in file_text, f"canary {name} reached the file, though the extractor never reads it"
            else:
                assert canary in file_text, f"canary {name} is missing from the file"
        _assert_no_canary_outside_the_file(stdout, stderr, file_text.splitlines()[0])

    def test_a_preview_prints_no_transcript_text(self, fake_projects, monkeypatch, capsys):
        seed(fake_projects, _canary_session())

        _status, stdout, stderr = run_main(monkeypatch, capsys, "--projects", "*", "--preview")

        _assert_no_canary_outside_the_file(stdout, stderr)

    def test_a_publish_failure_prints_no_transcript_text(self, fake_projects, out_dir, monkeypatch, capsys):
        seed(fake_projects, _canary_session())

        def failing_link(*args, **kwargs):
            raise OSError("link refused")

        monkeypatch.setattr(os, "link", failing_link)

        _status, stdout, stderr = run_main(monkeypatch, capsys, "--projects", "*", "--out", str(out_dir / "run.jsonl"))

        _assert_no_canary_outside_the_file(stdout, stderr)

    def test_a_project_directory_name_with_a_newline_and_an_escape_byte_gives_one_ascii_families_line(
        self, tmp_path, monkeypatch, capsys,
    ):
        projects = tmp_path / "projects"
        monkeypatch.setattr(scope, "PROJECTS_DIR", projects)
        seed(projects / "-home-user-odd\n\x1b[31mname", question_session())

        status, _stdout, stderr = run_main(monkeypatch, capsys, "--projects", "*", "--preview")

        assert status == 0
        assert stderr.replace(scope._DO_NOT_PUBLISH_BANNER, "").isascii()
        assert "\x1b" not in stderr
        assert [line.startswith(FAMILIES_PREFIX) for line in stderr.splitlines()].count(True) == 1
        assert len(stderr.splitlines()) == 3


class TestCorpusAbort:
    @pytest.fixture(params=[ValueError, RecursionError], ids=["value-error", "recursion-error"])
    def aborting_scan(self, request, fake_projects, monkeypatch):
        """Patch the session iterator to yield one session and then raise, the way the corpus reader aborts."""
        error_type = request.param

        def resolve_then_abort(*args, **kwargs):
            def sessions():
                yield fake_projects / "sess.jsonl", []
                raise error_type(f"aborted near {_CANARIES['prompt']}")

            return sessions(), "glob"

        monkeypatch.setattr(scope, "_resolve_project_scope", resolve_then_abort)
        return error_type.__name__

    def test_a_run_exits_1_without_echoing_the_exception_text_or_writing_a_file(
        self, aborting_scan, out_dir, monkeypatch, capsys,
    ):
        out = out_dir / "run.jsonl"

        status, stdout, stderr = run_main(monkeypatch, capsys, "--projects", "*", "--out", str(out))

        assert status == 1
        assert stdout == ""
        header, abort_line = stderr.splitlines(keepends=True)
        assert header.startswith(HEADER_PREFIX)
        assert abort_line == ABORT_LINE.format(name=aborting_scan)
        _assert_no_canary_outside_the_file(stderr)
        assert list(out_dir.iterdir()) == []

    def test_a_preview_exits_1_with_no_families_line(self, aborting_scan, monkeypatch, capsys):
        status, stdout, stderr = run_main(monkeypatch, capsys, "--projects", "*", "--preview")

        assert status == 1
        assert stdout == ""
        assert FAMILIES_PREFIX not in stderr
        assert stderr.splitlines(keepends=True)[1] == ABORT_LINE.format(name=aborting_scan)
        assert len(stderr.splitlines()) == 2


class TestCorpusAbortOnARealFile:
    """The reader's own exception contract: a line nested past the recursion limit reaches the command as an abort."""

    @pytest.fixture(params=["one-root", "two-roots"])
    def nested_line_project(self, request, tmp_path, monkeypatch) -> Path:
        deeply_nested_line = "[" * 200_000
        try:
            json.loads(deeply_nested_line)
        except RecursionError:
            pass
        else:
            pytest.skip("this interpreter parses a 200,000-deep array without raising")
        if request.param == "one-root":
            projects = tmp_path / "projects"
            monkeypatch.setattr(scope, "PROJECTS_DIR", projects)
        else:
            projects = _two_declared_roots(tmp_path, monkeypatch)[1]
        project_dir = projects / "-home-user-testrepo"
        project_dir.mkdir(parents=True)
        (project_dir / "sess.jsonl").write_text(f"{deeply_nested_line}\n")
        return project_dir

    def test_a_run_exits_1_with_the_one_line_abort_message_and_no_file(
        self, nested_line_project, out_dir, monkeypatch, capsys,
    ):
        status, stdout, stderr = run_main(monkeypatch, capsys, "--projects", "*", "--out", str(out_dir / "run.jsonl"))

        assert status == 1
        assert stdout == ""
        assert stderr.splitlines(keepends=True)[-1] == ABORT_LINE.format(name="RecursionError")
        assert "Traceback" not in stderr
        assert FAMILIES_PREFIX not in stderr
        assert list(out_dir.iterdir()) == []

    def test_a_preview_exits_1_with_no_families_line(self, nested_line_project, monkeypatch, capsys):
        status, stdout, stderr = run_main(monkeypatch, capsys, "--projects", "*", "--preview")

        assert status == 1
        assert stdout == ""
        assert stderr.splitlines(keepends=True)[-1] == ABORT_LINE.format(name="RecursionError")
        assert "Traceback" not in stderr
        assert FAMILIES_PREFIX not in stderr
