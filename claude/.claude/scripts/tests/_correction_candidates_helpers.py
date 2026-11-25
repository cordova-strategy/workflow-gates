"""Builders and fixtures shared by the test_transcript_correction_candidates*.py files.

The record builders come from _compaction_context_helpers, whose shapes follow docs/precompact-hook-behavior.md.
Importing that module executes compaction-context.py, so test_transcript_analysis_multi_root_scope.py must not import this one.
The args-namespace builder lives in conftest.py for that reason.
"""
import copy
import json
import sys
from collections import Counter
from collections.abc import Iterator
from pathlib import Path

import pytest
from transcript_analysis import cli, correction_candidates, ledger_common, scope

from ._compaction_context_helpers import (
    ABSENT,
    _apply_overrides,
    answer_record,
    bash_input,
    bash_stdout,
    interrupt_marker,
    local_command_stdout,
    sidechain,
    skill_load,
    slash_invocation,
    user_prompt,
)
from .conftest import _correction_candidates_args, _write_jsonl

HEADER_PREFIX = "CORRECTION CANDIDATES SOURCES ("
FAMILIES_PREFIX = "correction-candidates: families "
BANNER = scope._DO_NOT_PUBLISH_BANNER
ABORT_LINE = "correction-candidates: the transcript scan aborted ({name}); no file was written\n"
DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_TIMESTAMP = "2026-05-19T10:00:00.000Z"


def with_fields(record: dict, **fields) -> dict:
    """A deep copy of record with top-level keys set, ABSENT removing one, so a shared builder's own dicts are never mutated."""
    return _apply_overrides(copy.deepcopy(record), fields)


def text_block(text: str) -> dict:
    return {"type": "text", "text": text}


def thinking_block(text: str = "private reasoning") -> dict:
    return {"type": "thinking", "thinking": text}


def tool_use_block(name: str = "Bash", tool_use_id: str = "toolu_1", tool_input: dict | None = None) -> dict:
    return {"type": "tool_use", "id": tool_use_id, "name": name, "input": {} if tool_input is None else tool_input}


def assistant_record(
    content: list,
    *,
    uuid=ABSENT,
    timestamp=DEFAULT_TIMESTAMP,
    model=DEFAULT_MODEL,
    attribution_skill=ABSENT,
) -> dict:
    """A main-thread assistant record; pass ABSENT for uuid, timestamp, model or attribution_skill to leave it off."""
    message = {"role": "assistant", "content": content}
    rec = {"type": "assistant", "message": message}
    if model is not ABSENT:
        message["model"] = model
    return _apply_overrides(rec, {"uuid": uuid, "timestamp": timestamp, "attributionSkill": attribution_skill})


def assistant_text(text: str, **overrides) -> dict:
    return assistant_record([text_block(text)], **overrides)


def question_spec(
    question: str,
    labels: tuple[str, ...] = ("Yes", "No"),
    *,
    header: str | None = "Choice",
    multi_select: bool = False,
) -> dict:
    """One entry of an AskUserQuestion call's `input.questions`."""
    spec = {
        "question": question,
        "multiSelect": multi_select,
        "options": [{"label": label, "description": f"{label} description"} for label in labels],
    }
    if header is not None:
        spec["header"] = header
    return spec


def ask_user_question_block(questions: list, *, tool_use_id: str = "toolu_q1", raw_input=ABSENT) -> dict:
    """One AskUserQuestion tool_use block. raw_input replaces the whole `input`, so a malformed one can be built."""
    return {
        "type": "tool_use",
        "id": tool_use_id,
        "name": "AskUserQuestion",
        "input": {"questions": questions} if raw_input is ABSENT else raw_input,
    }


def ask_answer_record(
    *,
    tool_use_id: str = "toolu_q1",
    answers=ABSENT,
    annotations=ABSENT,
    tool_use_result=ABSENT,
    content="User has answered your questions.",
    **overrides,
) -> dict:
    """The user record that answers an AskUserQuestion call, built on the docs-grounded `answer_record`.

    tool_use_result replaces the whole top-level `toolUseResult`. While it is ABSENT, `toolUseResult` is built from
    answers and annotations, each left out when ABSENT. `with_fields(record, toolUseResult=ABSENT)` drops the key.
    """
    if tool_use_result is ABSENT:
        tool_use_result = {"questions": []}
        if answers is not ABSENT:
            tool_use_result["answers"] = answers
        if annotations is not ABSENT:
            tool_use_result["annotations"] = annotations
    rec = answer_record(content)
    rec["message"]["content"][0]["tool_use_id"] = tool_use_id
    return _apply_overrides(rec, {"toolUseResult": tool_use_result, "timestamp": DEFAULT_TIMESTAMP, **overrides})


def _paths_in(value, prefix: tuple = ()) -> Iterator[tuple]:
    if isinstance(value, dict):
        children = value.items()
    elif isinstance(value, list):
        children = enumerate(value)
    else:
        return
    for key, child in children:
        path = (*prefix, key)
        yield path
        yield from _paths_in(child, path)


def _set_at(root, path: tuple, replacement) -> None:
    target = root
    for step in path[:-1]:
        target = target[step]
    target[path[-1]] = replacement


_MUTATION_REPLACEMENTS = (None, "mutated", "", 7, [], {})


def field_mutations(record: dict) -> Iterator[tuple[tuple, dict]]:
    """Each path in the record, nested ones included, with a deep copy holding None, a string, an int, a list or a dict there."""
    for path in list(_paths_in(record)):
        for replacement in _MUTATION_REPLACEMENTS:
            mutated = copy.deepcopy(record)
            _set_at(mutated, path, copy.deepcopy(replacement))
            yield path, mutated


FAMILY = "-home-example-src-workflow-gates"
SESSION = "sess-a"
SONNET = "claude-sonnet-4-6"
OPUS = "claude-opus-4-7"


def ts(minute: int, second: int = 0, *, day: int = 19) -> str:
    return f"2026-05-{day:02d}T10:{minute:02d}:{second:02d}.000Z"


def iso(minute: int, second: int = 0, *, day: int = 19) -> str:
    return f"2026-05-{day:02d}T10:{minute:02d}:{second:02d}+00:00"


def prompt(text: str, minute: int, *, uuid: str | None = None, day: int = 19, **overrides) -> dict:
    """A typed prompt stamped at `minute` of the day, with a uuid unique to that minute unless one is given."""
    return with_fields(user_prompt(text), timestamp=ts(minute, day=day), uuid=uuid or f"uuid-{day}-{minute}", **overrides)


def ask_record(questions, *, tool_use_id="toolu_q1", minute=5, **overrides) -> dict:
    return assistant_record(
        [text_block("asking now"), ask_user_question_block(questions, tool_use_id=tool_use_id)],
        timestamp=ts(minute), **overrides,
    )


def scripted_session() -> list:
    """Session one. An uninterpretable record leads, so no record index is 0 or 1 by accident."""
    return [
        "not a record",
        with_fields(slash_invocation("scratch", None), timestamp=ts(0)),
        prompt("first ask", 1, uuid="u1"),
        assistant_text("reply one", timestamp=ts(2), model=SONNET, attribution_skill="claude:plan-it"),
        sidechain(assistant_text("SIDECHAIN TEXT", timestamp=ts(2, 10), model=SONNET)),
        assistant_record([thinking_block(), tool_use_block()], timestamp=ts(2, 30), model=OPUS),
        with_fields(interrupt_marker(), timestamp=ts(3)),
        with_fields(local_command_stdout(), timestamp=ts(3, 10)),
        with_fields(bash_input(), timestamp=ts(3, 20)),
        with_fields(bash_stdout(), timestamp=ts(3, 30)),
        prompt("after interrupt", 4, uuid="u2"),
        ask_record([question_spec("Which?")], model=OPUS, attribution_skill="some/dir/skill-x"),
        ask_answer_record(answers={"Which?": "Yes"}, timestamp=ts(6)),
        assistant_text("thanks, proceeding", timestamp=ts(7), model=SONNET, attribution_skill="claude:plan-it"),
        prompt("last one", 8, uuid="u3"),
    ]


def slash_prompt_session() -> list:
    """Session two: a slash prompt with args, its skill-load record, assistant text, then a typed prompt."""
    return [
        "not a record",
        with_fields(slash_invocation("plan-it", "  draft the plan  "), timestamp=ts(0), uuid="s1"),
        with_fields(skill_load(), timestamp=ts(1)),
        assistant_text("working on it", timestamp=ts(2), model=SONNET),
        prompt("a correction", 3, uuid="s2"),
    ]


def window_bounds(since=None, until=None) -> tuple[float | None, float | None]:
    return scope._parse_absolute_window_args(_correction_candidates_args(since=since, until=until), "correction-candidates")


def scan(records, *, session=SESSION, family=FAMILY, truncate_chars=2000, since=None, until=None):
    since_ts, until_epoch = window_bounds(since, until)
    return correction_candidates._session_candidates(
        records, session, family, truncate_chars=truncate_chars, since_ts=since_ts, until_epoch=until_epoch,
    )


def emitted(records, **kwargs) -> list[dict]:
    """The file's output lines in file order."""
    kept, _duplicates = correction_candidates._dedup_and_order(scan(records, **kwargs)[0])
    return [candidate.record for candidate in kept]


def only_line(records, **kwargs) -> dict:
    (line,) = emitted(records, **kwargs)
    return line


def run_files(files: dict[str, list], **kwargs):
    """Every file through scan, dedup and counting, as cmd_correction_candidates runs them."""
    candidates, scan_counts = [], Counter()
    for session, records in files.items():
        file_candidates, file_counts = scan(records, session=session, **kwargs)
        candidates.extend(file_candidates)
        scan_counts.update(file_counts)
    kept, duplicate_counts = correction_candidates._dedup_and_order(candidates)
    scan_counts.update(duplicate_counts)
    counts, checks = correction_candidates._counts_and_checks(kept, scan_counts)
    return kept, counts, checks


def question_session(*, minute: int = 1) -> list[dict]:
    return [
        prompt("please fix the thing", minute),
        ask_record([question_spec("Which one?", ("Alpha", "Beta"))], minute=minute + 1),
        ask_answer_record(answers={"Which one?": "Alpha"}, timestamp=ts(minute + 2)),
        assistant_text("done", timestamp=ts(minute + 3)),
    ]


def stub_git_check(monkeypatch) -> None:
    """Replace the out-path git check with one that finds no work tree, so allow-path and preview tests never run `git`."""
    monkeypatch.setattr(ledger_common, "_ledger_path_is_git_tracked", lambda *args, **kwargs: False)


@pytest.fixture()
def real_git_check():
    """Requesting this fixture keeps the real out-path git check, which `stubbed_git_check` otherwise replaces."""


@pytest.fixture(autouse=True)
def stubbed_git_check(request, monkeypatch):
    if "real_git_check" not in request.fixturenames:
        stub_git_check(monkeypatch)


@pytest.fixture()
def out_dir(tmp_path) -> Path:
    directory = tmp_path / "out"
    directory.mkdir()
    return directory


class _TaggedStream:
    def __init__(self, tag: str, writes: list[tuple[str, str]]) -> None:
        self._tag = tag
        self._writes = writes

    def write(self, text: str) -> int:
        self._writes.append((self._tag, text))
        return len(text)

    def flush(self) -> None:
        pass


def record_streams(monkeypatch) -> list[tuple[str, str]]:
    """Replace sys.stdout and sys.stderr with streams that append `(stream name, text)` to one shared list."""
    writes: list[tuple[str, str]] = []
    monkeypatch.setattr(sys, "stdout", _TaggedStream("stdout", writes))
    monkeypatch.setattr(sys, "stderr", _TaggedStream("stderr", writes))
    return writes


def run_main(monkeypatch, capsys, *argv: str, top_level: tuple[str, ...] = ()) -> tuple[int, str, str]:
    """Drive the real parser and main(), returning the exit status, stdout and stderr."""
    monkeypatch.setattr(sys, "argv", ["transcript-analysis.py", *top_level, "correction-candidates", *argv])
    status = 0
    try:
        cli.main()
    except SystemExit as exit_signal:
        status = exit_signal.code
    captured = capsys.readouterr()
    return status, captured.out, captured.err


def written_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="ascii").splitlines()]


def seed(project_dir: Path, records: list, name: str = "sess.jsonl") -> None:
    project_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(project_dir / name, records)
