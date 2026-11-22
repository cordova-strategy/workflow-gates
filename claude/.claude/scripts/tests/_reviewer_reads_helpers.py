"""Constants and builders shared by the test_transcript_reviewer_reads* files."""
import argparse
from pathlib import Path

from transcript_analysis import corpus, reviewer_reads, scope

from ._read_cost_helpers import _HUNDRED_TOKEN_TEXT, _TRACKED_AGENT_TYPE, _file_record
from .conftest import (
    _asst,
    _read_result,
    _read_use,
    _skill_block,
    _user_msg,
    _write_subagent_dispatch,
)

_WORKTREE_PATH = "/home/user/testrepo"
_SESSION_ID = "session-main"
# The window `--since 2026-08-10 --until 2026-08-12` selects, and a timestamp inside it.
_SINCE = "2026-08-10"
_UNTIL = "2026-08-12"
_IN_WINDOW = "2026-08-11T10:00:00.000Z"
_BEFORE_WINDOW = "2026-08-09T10:00:00.000Z"
_SINCE_TS = corpus._parse_ts("2026-08-10T00:00:00Z")
_UNTIL_EPOCH = corpus._parse_ts("2026-08-13T00:00:00Z")
_WITHHELD = "(withheld — untracked agent type)"
# Distinguishes a `version` key holding None from no key at all.
_NO_VERSION = object()


def _reviewer_turn(
    message_id: str, content: list | None = None, *, ts: str | None = _IN_WINDOW, version: object = _NO_VERSION,
    model: object = "claude-sonnet-5", usage: dict | None = None, request_id: str | None = None,
) -> dict:
    """An assistant record carrying an id, a timestamp and usage, and a `version` key only when one is given."""
    rec = _asst("claude-sonnet-5", ts=ts, content=content, request_id=request_id)
    rec["message"]["id"] = message_id
    rec["message"]["model"] = model
    rec["message"]["usage"] = {"output_tokens": 10} if usage is None else usage
    if version is not _NO_VERSION:
        rec["version"] = version
    return rec


def _file_result(
    tool_id: str, path: str, *, num_lines: int, total_lines: int, start_line: int = 1,
    truncated: bool | None = None, text: str = _HUNDRED_TOKEN_TEXT,
) -> dict:
    """A Read result record carrying the structured `toolUseResult.file` fields. The flag is absent unless given."""
    file_record = _file_record(
        path, start_line=start_line, num_lines=num_lines, total_lines=total_lines, truncated_by_token_cap=truncated,
    )
    return _read_result(tool_id, text, tool_use_result=file_record)


def _structured_read_exchange(
    message_id: str, tool_id: str, path: str, *, num_lines: int, total_lines: int, start_line: int = 1,
    truncated: bool | None = None, offset: int | None = None, limit: int | None = None,
    allow_large: bool | None = None, text: str = _HUNDRED_TOKEN_TEXT, ts: str | None = _IN_WINDOW,
) -> list[dict]:
    """A turn holding one Read call and the record carrying its structured result."""
    use = _read_use(tool_id, path, offset=offset, limit=limit, allow_large=allow_large)
    return [
        _reviewer_turn(message_id, [use], ts=ts),
        _file_result(
            tool_id, path, num_lines=num_lines, total_lines=total_lines, start_line=start_line, truncated=truncated,
            text=text,
        ),
    ]


def _failed_read_exchange(
    message_id: str, tool_id: str, path: str, error_text: object, *, offset: int | None = None,
    limit: int | None = None, ts: str | None = _IN_WINDOW,
) -> list[dict]:
    """A turn holding one Read call and its error result, `toolUseResult` an `Error:` string as the review bench models it."""
    return [
        _reviewer_turn(message_id, [_read_use(tool_id, path, offset=offset, limit=limit)], ts=ts),
        _read_result(tool_id, error_text, is_error=True, tool_use_result=f"Error: {error_text}"),
    ]


def _reviewer_window(
    proj: Path, agent_id: str, records: list[dict], *, agent_type: str = _TRACKED_AGENT_TYPE, spawn_depth: int = 1,
    session_id: str = _SESSION_ID,
) -> None:
    """A subagent transcript and its `.meta.json`. Every record is a sidechain record, as on disk."""
    _write_subagent_dispatch(
        proj, session_id, agent_id, f"dispatch-{agent_id}", [{**rec, "isSidechain": True} for rec in records],
        agent_type=agent_type, spawn_depth=spawn_depth,
    )


def _access_recording_read_facts(read_facts_class: type, accesses: list) -> type:
    """A subclass of the follow-up facts class that appends to `accesses` on every read of a fact.

    A named field appends its name. Indexing and iteration, which unpacking uses, append "positional".
    """

    def recording_field(name: str, index: int) -> property:
        def read_field(read):
            accesses.append(name)
            return tuple.__getitem__(read, index)

        return property(read_field)

    class AccessRecordingReadFacts(read_facts_class):
        __slots__ = ()
        call_order, has_offset, interval = (recording_field(name, index) for index, name in enumerate(read_facts_class._fields))

        def __getitem__(self, index):
            accesses.append("positional")
            return tuple.__getitem__(self, index)

        def __iter__(self):
            accesses.append("positional")
            return tuple.__iter__(self)

    return AccessRecordingReadFacts


def _round_records(
    skill: str, message_id: str, *, ts: str | None = _IN_WINDOW, reads: tuple[dict, ...] = (),
) -> list[dict]:
    """A main-thread round window: the record opening it with a `Skill` block, then one turn holding the Read blocks.

    The window closes at the next fresh user prompt or round-opening record, which the caller appends.
    """
    return [
        _reviewer_turn(f"{message_id}-open", [_skill_block(f"{message_id}-skill", skill)], ts=ts),
        _reviewer_turn(f"{message_id}-reads", list(reads), ts=ts),
    ]


def _next_prompt(ts: str | None = _IN_WINDOW) -> dict:
    return _user_msg("next prompt", ts=ts)


class _WorktreeListCalls(list):
    """Each command label `scope._repo_worktree_paths` was called with."""


def _reviewer_reads_args(
    monkeypatch, *, since: object = _SINCE, until: object = _UNTIL, this_repo: bool = True, projects: str = "*",
    worktree_paths: tuple[str, ...] = (_WORKTREE_PATH,),
) -> tuple[argparse.Namespace, _WorktreeListCalls]:
    """Args for the report, with `scope._repo_worktree_paths` stubbed to return `worktree_paths` and record its calls."""
    calls = _WorktreeListCalls()

    def stub_worktree_paths(command_label: str) -> list[str]:
        calls.append(command_label)
        return list(worktree_paths)

    monkeypatch.setattr(scope, "_repo_worktree_paths", stub_worktree_paths)
    args = argparse.Namespace(this_repo=this_repo, projects=projects, since=since, until=until)
    return args, calls


def _report_text(args: argparse.Namespace, fake_projects: Path, capsys) -> str:
    """Runs the report over the fixture's one root and returns stdout."""
    reviewer_reads._reviewer_reads_report(args, [fake_projects.parent])
    return capsys.readouterr().out


def _printed_line(report: str, prefix: str) -> str:
    """The one report line starting with `prefix`."""
    matches = [line for line in report.splitlines() if line.startswith(prefix)]
    assert len(matches) == 1, (prefix, matches)
    return matches[0]
