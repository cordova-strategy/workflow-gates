"""Which accounts each narrowed command reads: the active account by default, every declared account under
--all-accounts or --this-repo, and the pooled modes that keep reading every declared account."""
import json
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest
from transcript_analysis import (
    audit_routing,
    buckets,
    duration,
    handoff_signal_response,
    judgment_pair,
    review_trace,
    scope,
    sessions,
    skill_invocation,
    struggle,
    turn_shape,
)

from ._account_scope_helpers import (
    ACTIVE_ACCOUNT_CLAUSE,
    ACTIVE_ROOT_SENTINEL,
    DECLARED_ROOT_SENTINEL,
    NAMED_ACCOUNT_SENTINEL,
    SESSION_TS,
    SHARED_PROJECT_SLUG,
    _sessions_args,
    seed_one_session_per_root,
    write_judgment_pair_session,
    write_skill_name_session,
)
from ._audit_routing_helpers import _audit_routing_samples_args
from ._handoff_nudge_helpers import (
    _handoff_cards,
    _handoff_signal_response_args,
    _write_signal_with_excerpt_session,
)
from ._session_signal_helpers import _branch_args
from ._skill_helpers import _judgment_pair_args, _skill_inv_args
from ._turn_shape_helpers import _turn_shape_holdout_samples_args, _turn_shape_samples_args
from .conftest import (
    _asst,
    _audit_routing_args,
    _bash_use,
    _hook_deny_current,
    _opus,
    _priced,
    _read_use,
    _review_trace_args,
    _skill_use_rec,
    _table_cols,
    _two_declared_roots,
    _user_msg,
    _write_jsonl,
    _write_subagent_jsonl,
)

_LATER_SESSION_TS = "2026-05-20T10:10:00.000Z"
_STDOUT = "out"
_STDERR = "err"


class _NarrowedRow(NamedTuple):
    """One narrowed command: how to seed one root's session, build its args, run it, and where its header prints."""
    name: str
    header_stream: str
    args_factory: Callable[[], object]
    write_session: Callable[[Path, str], None]
    run: Callable[[object], None]
    # skill-invocation reads this repo's slugs only while --projects is unset.
    unsets_projects_under_this_repo: bool = False


def _write_review_trace_session(project_dir: Path, sentinel: str) -> None:
    _write_jsonl(project_dir / f"{sentinel}.jsonl", [_skill_use_rec("code-review", SESSION_TS)])


def _write_review_trace_denial_session(project_dir: Path, sentinel: str) -> None:
    _write_jsonl(project_dir / f"{sentinel}.jsonl", [_hook_deny_current("Commit blocked by code-review gate.")])


def _write_sessions_session(project_dir: Path, sentinel: str) -> None:
    _write_jsonl(project_dir / f"{sentinel}.jsonl", [_asst("claude-sonnet-4-6")])


def _write_opus_read_session(project_dir: Path, sentinel: str) -> None:
    _write_jsonl(project_dir / f"{sentinel}.jsonl", [_opus([_read_use("r1", "/a.py")], out=100)])


def _write_two_commit_turns_session(project_dir: Path, sentinel: str) -> None:
    _write_jsonl(project_dir / f"{sentinel}.jsonl", [
        _priced("claude-sonnet-5", input=10, output=5, content=[_bash_use("b1", "git commit -m a")], request_id="r1"),
        _priced("claude-sonnet-5", input=10, output=5, content=[_bash_use("b2", "git commit -m b")], request_id="r2"),
    ])


def _write_one_commit_turn_session(project_dir: Path, sentinel: str) -> None:
    _write_jsonl(project_dir / f"{sentinel}.jsonl", [
        _priced("claude-sonnet-5", input=10, output=5, content=[_bash_use("b1", "git commit -m a")], request_id="r1"),
    ])


def _write_branch_session(project_dir: Path, sentinel: str) -> None:
    _write_jsonl(project_dir / "sess.jsonl", [_asst("claude-sonnet-4-6", branch=sentinel, ts=SESSION_TS)])


def _write_two_timestamp_branch_session(project_dir: Path, sentinel: str) -> None:
    _write_jsonl(project_dir / "sess.jsonl", [
        _asst("claude-sonnet-4-6", branch=sentinel, ts=SESSION_TS),
        _asst("claude-sonnet-4-6", branch=sentinel, ts=_LATER_SESSION_TS),
    ])


def _write_struggle_branch_session(project_dir: Path, sentinel: str) -> None:
    _write_jsonl(project_dir / "sess.jsonl", [
        _asst("claude-sonnet-4-6", branch=sentinel, ts=SESSION_TS),
        _user_msg("are you saying the build passes?", branch=sentinel, ts=_LATER_SESSION_TS),
    ])


_NARROWED_ROWS = [
    _NarrowedRow(
        "review-trace", _STDOUT, _review_trace_args,
        _write_review_trace_session, review_trace.cmd_review_trace,
    ),
    _NarrowedRow(
        "review-trace --deny-only", _STDOUT, lambda: _review_trace_args(deny_only=True),
        _write_review_trace_denial_session, review_trace.cmd_review_trace,
    ),
    _NarrowedRow(
        "judgment-pair", _STDOUT, _judgment_pair_args,
        write_judgment_pair_session, judgment_pair.cmd_judgment_pair,
    ),
    _NarrowedRow(
        "sessions", _STDERR, _sessions_args,
        _write_sessions_session, sessions.cmd_sessions,
    ),
    _NarrowedRow(
        "skill-invocation --projects", _STDOUT, _skill_inv_args,
        write_skill_name_session, skill_invocation.cmd_skill_invocation,
        unsets_projects_under_this_repo=True,
    ),
    _NarrowedRow(
        "buckets", _STDOUT, _branch_args,
        _write_branch_session, buckets.cmd_buckets,
    ),
    _NarrowedRow(
        "duration", _STDOUT, _branch_args,
        _write_two_timestamp_branch_session, duration.cmd_duration,
    ),
    _NarrowedRow(
        "struggle", _STDOUT, _branch_args,
        _write_struggle_branch_session, struggle.cmd_struggle,
    ),
    _NarrowedRow(
        "audit-routing", _STDOUT, _audit_routing_args,
        _write_opus_read_session, audit_routing.cmd_audit_routing,
    ),
    _NarrowedRow(
        "audit-routing-samples", _STDERR, _audit_routing_samples_args,
        _write_opus_read_session, audit_routing.cmd_audit_routing_samples,
    ),
    _NarrowedRow(
        "turn-shape-samples", _STDERR, _turn_shape_samples_args,
        _write_two_commit_turns_session, turn_shape.cmd_turn_shape_samples,
    ),
    _NarrowedRow(
        "turn-shape-holdout-samples", _STDERR, _turn_shape_holdout_samples_args,
        _write_one_commit_turn_session, turn_shape.cmd_turn_shape_holdout_samples,
    ),
    _NarrowedRow(
        "handoff-signal-response --sample", _STDOUT, lambda: _handoff_signal_response_args(sample=5, seed=1),
        _write_signal_with_excerpt_session, handoff_signal_response.cmd_handoff_signal_response,
    ),
]
_ROW_IDS = [row.name for row in _NARROWED_ROWS]


def _seed_two_roots(row: _NarrowedRow, tmp_path, monkeypatch) -> object:
    """Seed both declared roots with one session each under one shared project slug and return the row's args."""
    seed_one_session_per_root(_two_declared_roots(tmp_path, monkeypatch), row.write_session)
    return row.args_factory()


def _bound_to_this_repo(args: object, monkeypatch, *, unset_projects: bool = False) -> object:
    """Set --this-repo on `args` with the shared slug standing in for this repo's own worktree slug."""
    args.this_repo = True
    args._this_repo_slugs = [SHARED_PROJECT_SLUG]
    # skill-invocation's default scope reads the slugs through this helper, not through `args`.
    monkeypatch.setattr(scope, "_repo_scoped_project_slugs", lambda *_a, **_k: [SHARED_PROJECT_SLUG])
    if unset_projects:
        args.projects = None
    return args


def _streams(capsys) -> dict[str, str]:
    captured = capsys.readouterr()
    return {_STDOUT: captured.out, _STDERR: captured.err}


@pytest.mark.parametrize("row", _NARROWED_ROWS, ids=_ROW_IDS)
class TestNarrowedCommandsReadScope:
    def test_default_run_prints_the_active_root_only_and_says_so_in_the_header(
        self, row, tmp_path, monkeypatch, capsys,
    ):
        args = _seed_two_roots(row, tmp_path, monkeypatch)

        row.run(args)

        streams = _streams(capsys)
        everything = streams[_STDOUT] + streams[_STDERR]
        assert ACTIVE_ROOT_SENTINEL in everything  # positive control: the run printed the active root's row
        assert DECLARED_ROOT_SENTINEL not in everything
        assert ACTIVE_ACCOUNT_CLAUSE in streams[row.header_stream]

    def test_all_accounts_run_prints_both_roots(self, row, tmp_path, monkeypatch, capsys):
        args = _seed_two_roots(row, tmp_path, monkeypatch)
        args.all_accounts = True

        row.run(args)

        streams = _streams(capsys)
        everything = streams[_STDOUT] + streams[_STDERR]
        assert ACTIVE_ROOT_SENTINEL in everything
        assert DECLARED_ROOT_SENTINEL in everything
        assert "2 roots" in streams[row.header_stream]

    def test_this_repo_run_prints_both_roots(self, row, tmp_path, monkeypatch, capsys):
        args = _bound_to_this_repo(
            _seed_two_roots(row, tmp_path, monkeypatch), monkeypatch,
            unset_projects=row.unsets_projects_under_this_repo,
        )

        row.run(args)

        streams = _streams(capsys)
        everything = streams[_STDOUT] + streams[_STDERR]
        assert ACTIVE_ROOT_SENTINEL in everything
        assert DECLARED_ROOT_SENTINEL in everything
        assert "2 roots" in streams[row.header_stream]

    def test_top_level_config_dir_run_prints_the_named_account_alone_without_the_active_account_clause(
        self, row, tmp_path, monkeypatch, fake_config_dir_factory, capsys,
    ):
        roots = _two_declared_roots(tmp_path, monkeypatch)
        named_account = fake_config_dir_factory("named-account")
        seed_one_session_per_root(
            [*roots, named_account / "projects"], row.write_session,
            markers=(ACTIVE_ROOT_SENTINEL, DECLARED_ROOT_SENTINEL, NAMED_ACCOUNT_SENTINEL),
        )
        args = row.args_factory()
        args.config_dir = str(named_account)

        row.run(args)

        streams = _streams(capsys)
        everything = streams[_STDOUT] + streams[_STDERR]
        assert NAMED_ACCOUNT_SENTINEL in everything  # positive control: the run printed the named account's row
        assert ACTIVE_ROOT_SENTINEL not in everything
        assert DECLARED_ROOT_SENTINEL not in everything
        assert " SOURCES (" in streams[row.header_stream]  # positive control: a header printed on this stream
        assert ACTIVE_ACCOUNT_CLAUSE not in streams[row.header_stream]

    def test_this_repo_beside_a_top_level_config_dir_prints_the_named_account_alone(
        self, row, tmp_path, monkeypatch, fake_config_dir_factory, capsys,
    ):
        roots = _two_declared_roots(tmp_path, monkeypatch)
        named_account = fake_config_dir_factory("named-account")
        seed_one_session_per_root(
            [*roots, named_account / "projects"], row.write_session,
            markers=(ACTIVE_ROOT_SENTINEL, DECLARED_ROOT_SENTINEL, NAMED_ACCOUNT_SENTINEL),
        )
        args = _bound_to_this_repo(
            row.args_factory(), monkeypatch, unset_projects=row.unsets_projects_under_this_repo,
        )
        args.config_dir = str(named_account)

        row.run(args)

        streams = _streams(capsys)
        everything = streams[_STDOUT] + streams[_STDERR]
        assert NAMED_ACCOUNT_SENTINEL in everything  # positive control: the run printed the named account's row
        assert ACTIVE_ROOT_SENTINEL not in everything
        assert DECLARED_ROOT_SENTINEL not in everything
        assert " SOURCES (" in streams[row.header_stream]  # positive control: a header printed on this stream
        assert ACTIVE_ACCOUNT_CLAUSE not in streams[row.header_stream]


class TestBucketsCombinations:
    def test_both_widening_flags_print_what_this_repo_alone_prints(self, tmp_path, monkeypatch, capsys):
        buckets_row = next(row for row in _NARROWED_ROWS if row.name == "buckets")
        this_repo_args = _bound_to_this_repo(_seed_two_roots(buckets_row, tmp_path, monkeypatch), monkeypatch)
        buckets.cmd_buckets(this_repo_args)
        this_repo_only_out = capsys.readouterr().out

        both_flags_args = _bound_to_this_repo(buckets_row.args_factory(), monkeypatch)
        both_flags_args.all_accounts = True
        buckets.cmd_buckets(both_flags_args)
        both_flags_out = capsys.readouterr().out

        assert ACTIVE_ROOT_SENTINEL in this_repo_only_out  # positive control: rows printed
        assert both_flags_out == this_repo_only_out

    def test_a_branch_worked_from_two_accounts_pools_into_one_row_under_this_repo(
        self, tmp_path, monkeypatch, capsys,
    ):
        shared_branch = "shared-branch"
        roots = _two_declared_roots(tmp_path, monkeypatch)
        seed_one_session_per_root(roots, _write_branch_session, markers=(shared_branch, shared_branch))
        args = _bound_to_this_repo(_branch_args(), monkeypatch)

        buckets.cmd_buckets(args)

        out = capsys.readouterr().out
        branch_rows = [line for line in out.splitlines() if line.startswith(shared_branch)]
        assert len(branch_rows) == 1
        cols = _table_cols(out, header_contains="Branch", row_contains=shared_branch, max_labels=8)
        assert cols["Sess"] == "2"


class TestJudgmentPairHeaderWhenNothingMatches:
    def test_zero_match_run_prints_the_active_account_clause_above_the_empty_message(
        self, tmp_path, monkeypatch, capsys,
    ):
        _two_declared_roots(tmp_path, monkeypatch)

        judgment_pair.cmd_judgment_pair(_judgment_pair_args())

        lines = capsys.readouterr().out.splitlines()
        assert lines == [f"JUDGMENT PAIR SOURCES (*; {ACTIVE_ACCOUNT_CLAUSE})", "No judgment pairs found."]


class TestSessionsIncludeSubagentsReadsTheActiveRootByDefault:
    """--include-subagents lists each split subagent file beside its main session, so it must stay inside the
    roots the run resolved."""

    @staticmethod
    def _write_session_with_subagent(project_dir: Path, sentinel: str) -> None:
        _write_jsonl(project_dir / f"{sentinel}.jsonl", [_asst("claude-sonnet-4-6")])
        _write_subagent_jsonl(project_dir, sentinel, f"agent-{sentinel}", [_asst("claude-sonnet-4-6")])

    @staticmethod
    def _listed_paths(capsys) -> list[str]:
        return capsys.readouterr().out.splitlines()

    def test_default_run_lists_the_active_roots_session_and_subagent_only(self, tmp_path, monkeypatch, capsys):
        seed_one_session_per_root(_two_declared_roots(tmp_path, monkeypatch), self._write_session_with_subagent)
        args = _sessions_args()
        args.include_subagents = True

        sessions.cmd_sessions(args)

        listed = self._listed_paths(capsys)
        listed_names = {Path(path).name for path in listed}
        assert f"{ACTIVE_ROOT_SENTINEL}.jsonl" in listed_names
        assert f"agent-{ACTIVE_ROOT_SENTINEL}.jsonl" in listed_names
        assert not any(DECLARED_ROOT_SENTINEL in path for path in listed)

    def test_all_accounts_run_lists_both_roots_sessions_and_subagents(self, tmp_path, monkeypatch, capsys):
        seed_one_session_per_root(_two_declared_roots(tmp_path, monkeypatch), self._write_session_with_subagent)
        args = _sessions_args()
        args.include_subagents = True
        args.all_accounts = True

        sessions.cmd_sessions(args)

        listed = self._listed_paths(capsys)
        listed_names = {Path(path).name for path in listed}
        for sentinel in (ACTIVE_ROOT_SENTINEL, DECLARED_ROOT_SENTINEL):
            assert f"{sentinel}.jsonl" in listed_names
            assert f"agent-{sentinel}.jsonl" in listed_names


class TestPooledModesKeepReadingEveryDeclaredRoot:
    def test_review_trace_deny_summary_reads_both_roots(self, tmp_path, monkeypatch, capsys):
        row = next(row for row in _NARROWED_ROWS if row.name == "review-trace")
        args = _seed_two_roots(row, tmp_path, monkeypatch)
        args.deny_summary = True

        review_trace.cmd_review_trace(args)

        captured = capsys.readouterr()
        assert "2 roots" in captured.out
        assert "scanning root 2/2..." in captured.err

    def test_handoff_signal_response_aggregate_run_reads_both_roots_and_prints_no_banner(
        self, tmp_path, monkeypatch, capsys,
    ):
        row = next(row for row in _NARROWED_ROWS if row.name == "handoff-signal-response --sample")
        _seed_two_roots(row, tmp_path, monkeypatch)

        handoff_signal_response.cmd_handoff_signal_response(_handoff_signal_response_args())

        captured = capsys.readouterr()
        assert "2 roots" in captured.out
        assert "scanning root 2/2..." in captured.err
        assert scope._DO_NOT_PUBLISH_BANNER not in captured.out + captured.err

    def test_skill_invocation_without_projects_reads_both_roots(self, tmp_path, monkeypatch, capsys):
        row = next(row for row in _NARROWED_ROWS if row.name == "skill-invocation --projects")
        _seed_two_roots(row, tmp_path, monkeypatch)
        monkeypatch.setattr(scope, "_repo_scoped_project_slugs", lambda *_a, **_k: [SHARED_PROJECT_SLUG])

        skill_invocation.cmd_skill_invocation(_skill_inv_args(projects=None))

        out = capsys.readouterr().out
        assert "2 roots" in out
        assert ACTIVE_ROOT_SENTINEL in out
        assert DECLARED_ROOT_SENTINEL in out


class TestSampleCommandsBannerAboveOneRoot:
    """audit-routing-samples and handoff-signal-response --sample print the DO NOT PUBLISH line on stderr above one
    root, and keep it off their stdout."""

    @staticmethod
    def _audit_routing_samples_session_ids(stdout: str) -> set[str]:
        return {record["session_id"] for record in json.loads(stdout)}

    @staticmethod
    def _handoff_card_excerpts(stdout: str) -> set[str]:
        return {card["excerpt"] for card in _handoff_cards(stdout)}

    def test_audit_routing_samples_default_run_prints_no_banner(self, tmp_path, monkeypatch, capsys):
        row = next(row for row in _NARROWED_ROWS if row.name == "audit-routing-samples")
        args = _seed_two_roots(row, tmp_path, monkeypatch)

        audit_routing.cmd_audit_routing_samples(args)

        captured = capsys.readouterr()
        assert ACTIVE_ROOT_SENTINEL in self._audit_routing_samples_session_ids(captured.out)
        assert scope._DO_NOT_PUBLISH_BANNER not in captured.err

    @pytest.mark.parametrize("widening", ["all_accounts", "this_repo"])
    def test_audit_routing_samples_widened_run_prints_the_banner_on_stderr_only(
        self, widening, tmp_path, monkeypatch, capsys,
    ):
        row = next(row for row in _NARROWED_ROWS if row.name == "audit-routing-samples")
        args = _seed_two_roots(row, tmp_path, monkeypatch)
        if widening == "all_accounts":
            args.all_accounts = True
        else:
            _bound_to_this_repo(args, monkeypatch)

        audit_routing.cmd_audit_routing_samples(args)

        captured = capsys.readouterr()
        assert scope._DO_NOT_PUBLISH_BANNER in captured.err
        assert scope._DO_NOT_PUBLISH_BANNER not in captured.out
        assert self._audit_routing_samples_session_ids(captured.out) == {
            ACTIVE_ROOT_SENTINEL, DECLARED_ROOT_SENTINEL,
        }

    def test_handoff_sample_default_run_prints_no_banner(self, tmp_path, monkeypatch, capsys):
        row = next(row for row in _NARROWED_ROWS if row.name == "handoff-signal-response --sample")
        args = _seed_two_roots(row, tmp_path, monkeypatch)

        handoff_signal_response.cmd_handoff_signal_response(args)

        captured = capsys.readouterr()
        assert ACTIVE_ROOT_SENTINEL in self._handoff_card_excerpts(captured.out)
        assert scope._DO_NOT_PUBLISH_BANNER not in captured.err

    @pytest.mark.parametrize("widening", ["all_accounts", "this_repo"])
    def test_handoff_sample_widened_run_prints_the_banner_on_stderr_only(
        self, widening, tmp_path, monkeypatch, capsys,
    ):
        row = next(row for row in _NARROWED_ROWS if row.name == "handoff-signal-response --sample")
        args = _seed_two_roots(row, tmp_path, monkeypatch)
        if widening == "all_accounts":
            args.all_accounts = True
        else:
            _bound_to_this_repo(args, monkeypatch)

        handoff_signal_response.cmd_handoff_signal_response(args)

        captured = capsys.readouterr()
        assert scope._DO_NOT_PUBLISH_BANNER in captured.err
        assert scope._DO_NOT_PUBLISH_BANNER not in captured.out
        assert self._handoff_card_excerpts(captured.out) == {ACTIVE_ROOT_SENTINEL, DECLARED_ROOT_SENTINEL}
