"""Tests for the reviewer-reads command: argparse wiring, scope and date refusals, the header, single-root reading,
this repository's ledger files, the output invariant and the fresh-interpreter refusal."""
import argparse
import logging
import os
import subprocess
import sys
import warnings

import pytest
from helpers import REPO_ROOT
from transcript_analysis import cli, pricing, publication_scope, reviewer_reads, scope

from ._read_cost_helpers import _PROJECT_SLUG, _TRACKED_AGENT_TYPE
from ._review_round_corpus_helpers import _LEAK_SENTINEL_PREFIX, _leak_sentinel
from ._reviewer_reads_helpers import (
    _IN_WINDOW,
    _SESSION_ID,
    _WORKTREE_PATH,
    _failed_read_exchange,
    _file_result,
    _next_prompt,
    _printed_line,
    _report_text,
    _reviewer_reads_args,
    _reviewer_turn,
    _reviewer_window,
    _round_records,
    _structured_read_exchange,
)
from .conftest import (
    _agent_use,
    _ledger_row,
    _read_truncation_notice,
    _read_use,
    _skill_block,
    _user_msg,
    _write_jsonl,
    _write_named_ledger_file,
    _write_this_repo_ledger_file,
    _write_use,
)

_SCRIPT = REPO_ROOT / "claude" / ".claude" / "scripts" / "transcript-analysis.py"
_REFUSAL_LINE = "reviewer-reads: requires --this-repo and refuses any --projects scope -- see docs/transcript-analysis.md\n"
_REAL_ARGV = ["reviewer-reads", "--this-repo", "--since", "2026-08-10", "--until", "2026-08-12"]


def _address_row(row_id: str, *, session_id: str = _SESSION_ID) -> dict:
    return _ledger_row(
        round=1, disposition="ADDRESS", id=row_id, ref="", decided_by="", reviewers=[_TRACKED_AGENT_TYPE],
        session_id=session_id, event_time="2026-08-11T10:00:00Z", schema_version=3,
    )


class TestArgparseWiring:
    def _parse(self, *flags: str) -> argparse.Namespace:
        parser = argparse.ArgumentParser()
        reviewer_reads._add_reviewer_reads_subparser(parser.add_subparsers())
        return parser.parse_args(["reviewer-reads", *flags])

    def test_wires_to_cmd_reviewer_reads_with_the_scope_flag_and_both_dates(self):
        parsed = self._parse("--this-repo", "--since", "2026-08-10", "--until", "2026-08-12")

        assert parsed.func is reviewer_reads.cmd_reviewer_reads
        assert (parsed.this_repo, parsed.since, parsed.until) == (True, "2026-08-10", "2026-08-12")

    @pytest.mark.parametrize(
        "flags",
        [
            pytest.param(("--this-repo", "--since", "August", "--until", "2026-08-12"), id="since_not_a_date"),
            pytest.param(("--this-repo", "--since", "2026-08-10", "--until", "99d"), id="until_not_a_date"),
        ],
    )
    def test_a_malformed_date_exits_2_at_parse_time(self, flags, capsys):
        with pytest.raises(SystemExit) as raised:
            self._parse(*flags)

        assert raised.value.code == 2
        assert capsys.readouterr().out == ""

    def test_a_missing_date_parses_to_none_and_the_command_refuses_it_before_any_scan(self):
        parsed = self._parse("--this-repo")

        assert (parsed.since, parsed.until) == (None, None)


class TestRefusalsBeforeAnyScan:
    @pytest.fixture(autouse=True)
    def _no_scan_may_start(self, monkeypatch):
        def fail(*_args, **_kwargs):
            raise AssertionError("a scan started")

        monkeypatch.setattr(scope, "_resolve_project_scope", fail)

    def _refused(self, args, fake_projects, capsys, calls) -> str:
        with pytest.raises(SystemExit) as raised:
            reviewer_reads._reviewer_reads_report(args, [fake_projects.parent])
        captured = capsys.readouterr()
        assert (raised.value.code, captured.out, calls) == (2, "", [])
        return captured.err

    def test_without_this_repo_under_its_own_label(self, fake_projects, monkeypatch, capsys):
        args, calls = _reviewer_reads_args(monkeypatch, this_repo=False)

        assert self._refused(args, fake_projects, capsys, calls) == _REFUSAL_LINE

    def test_the_scope_refusal_comes_before_the_date_checks(self, fake_projects, monkeypatch, capsys):
        args, calls = _reviewer_reads_args(monkeypatch, this_repo=False, since=None, until=None)

        assert self._refused(args, fake_projects, capsys, calls) == _REFUSAL_LINE

    @pytest.mark.parametrize(
        ("since", "until", "expected_message"),
        [
            pytest.param(None, "2026-08-12", "--since is required and must be a zero-padded YYYY-MM-DD date", id="no_since"),
            pytest.param("2026-08-10", None, "--until is required and must be a zero-padded YYYY-MM-DD date", id="no_until"),
            pytest.param(
                "2026-1-5", "2026-08-12", "--since is required and must be a zero-padded YYYY-MM-DD date",
                id="unpadded_since",
            ),
            pytest.param(
                "2026-08-10", "2026-1-5", "--until is required and must be a zero-padded YYYY-MM-DD date",
                id="unpadded_until",
            ),
            pytest.param("2026-08-13", "2026-08-12", "--since must not be after --until", id="since_after_until"),
        ],
    )
    def test_a_missing_unpadded_or_reversed_date_exits_2(
        self, since, until, expected_message, fake_projects, monkeypatch, capsys,
    ):
        args, calls = _reviewer_reads_args(monkeypatch, since=since, until=until)

        assert self._refused(args, fake_projects, capsys, calls) == f"reviewer-reads: {expected_message}\n"


class TestReport:
    def test_since_equal_to_until_is_accepted_and_covers_that_one_day(
        self, fake_projects, stub_repo_tracked_agent_types, monkeypatch, capsys,
    ):
        stub_repo_tracked_agent_types()
        args, _calls = _reviewer_reads_args(monkeypatch, since="2026-08-11", until="2026-08-11")

        report = _report_text(args, fake_projects, capsys)

        assert "window: 2026-08-11 to 2026-08-11 (UTC, both days included)" in report.splitlines()

    def test_header_names_the_command_and_states_the_scope(
        self, fake_projects, stub_repo_tracked_agent_types, monkeypatch, capsys,
    ):
        stub_repo_tracked_agent_types()
        args, _calls = _reviewer_reads_args(monkeypatch)

        assert _report_text(args, fake_projects, capsys).splitlines()[0] == (
            "REVIEWER READS SOURCES (this repo (1 project dirs: 1 live, 0 unlisted); reads one account (the active account),"
            " the working directory's repository only; ~/.claude/transcript-config-dirs not consulted)"
        )

    def test_unresolvable_config_dir_exits_2_with_one_reviewer_reads_stderr_line_and_no_stdout(
        self, monkeypatch, capsys,
    ):
        def unresolvable_config_dir():
            raise ValueError("CLAUDE_CONFIG_DIR is not absolute")

        monkeypatch.setattr(scope, "config_dir", unresolvable_config_dir)
        args, _calls = _reviewer_reads_args(monkeypatch)

        with pytest.raises(SystemExit) as raised:
            reviewer_reads.cmd_reviewer_reads(args)

        captured = capsys.readouterr()
        assert (raised.value.code, captured.err, captured.out) == (
            2, "reviewer-reads: CLAUDE_CONFIG_DIR is not absolute\n", "",
        )

    def test_a_declared_second_root_is_seen_by_no_reader(
        self, fake_projects, stub_repo_tracked_agent_types, tmp_path, monkeypatch, capsys,
    ):
        stub_repo_tracked_agent_types(_TRACKED_AGENT_TYPE)
        args, _calls = _reviewer_reads_args(monkeypatch)
        declared = tmp_path / "declared-account"
        declared_project = declared / "projects" / _PROJECT_SLUG
        declared_project.mkdir(parents=True)
        roots_file = tmp_path / "roots"
        roots_file.write_text(f"{declared}\n")
        monkeypatch.setenv("TRANSCRIPT_CONFIG_DIRS_FILE", str(roots_file))
        for project, session in ((fake_projects, "session-main"), (declared_project, "session-other")):
            dispatch = _agent_use(f"dispatch-agent-{session}", _TRACKED_AGENT_TYPE)
            _write_jsonl(project / f"{session}.jsonl", [_reviewer_turn("m0", [dispatch])])
            _reviewer_window(project, f"agent-{session}", [_reviewer_turn(f"a-{session}", [])], session_id=session)
        _write_this_repo_ledger_file(declared, _WORKTREE_PATH, "slot", [_address_row("a1", session_id="session-other")])
        roots_seen = []
        resolve_project_scope = scope._resolve_project_scope

        def recording_resolve(args_, subcommand, include_subagents=False, roots=None, **kwargs):
            roots_seen.append((include_subagents, list(roots)))
            return resolve_project_scope(args_, subcommand, include_subagents, roots, **kwargs)

        monkeypatch.setattr(scope, "_resolve_project_scope", recording_resolve)
        monkeypatch.setattr(scope, "resolve_scan_roots", lambda *_a, **_k: pytest.fail("resolve_scan_roots called"))

        report = _report_text(args, fake_projects, capsys)

        assert roots_seen == [(False, [fake_projects.parent]), (True, [fake_projects.parent])]
        assert "sessions=1 reviewer_windows=1" in report
        assert _printed_line(report, "TOTAL: dispatches=") == (
            "TOTAL: dispatches=1 findings_found=0 zero_finding=0 unclassified=1 findings=0"
        )
        assert "terminal rows: ADDRESS=0 DEFER=0 SETTLED=0 total=0" in report
        assert "ledger files: directory=absent read=0 unreadable=0" in report

    def test_the_ledger_counts_this_checkouts_file_not_a_foreign_one_and_resolves_the_worktrees_once(
        self, fake_projects, stub_repo_tracked_agent_types, tmp_path, monkeypatch, capsys,
    ):
        stub_repo_tracked_agent_types()
        args, calls = _reviewer_reads_args(monkeypatch)
        _write_jsonl(fake_projects / f"{_SESSION_ID}.jsonl", [_reviewer_turn("m0")])
        _write_this_repo_ledger_file(tmp_path, _WORKTREE_PATH, "branch-slot", [_address_row("in-scope")])
        _write_named_ledger_file(tmp_path, "f" * 64, _SESSION_ID, [_address_row("foreign-1"), _address_row("foreign-2")])

        report = _report_text(args, fake_projects, capsys)

        assert "terminal rows: ADDRESS=1 DEFER=0 SETTLED=0 total=1" in report
        assert "ledger files: directory=present read=1 unreadable=0" in report
        assert "sessions with a disposition row=1 covered by the transcript scan=1" in report
        assert calls == ["reviewer-reads"]

    def test_the_scope_is_the_worktree_paths_the_one_call_returned(
        self, fake_projects, stub_repo_tracked_agent_types, monkeypatch, capsys,
    ):
        stub_repo_tracked_agent_types()
        second_worktree_path = f"{_WORKTREE_PATH}/.claude/worktrees/b"
        (fake_projects.parent / scope._path_to_project_slug(second_worktree_path)).mkdir()
        args, _calls = _reviewer_reads_args(monkeypatch, worktree_paths=(_WORKTREE_PATH, second_worktree_path))

        assert _report_text(args, fake_projects, capsys).splitlines()[0].startswith(
            "REVIEWER READS SOURCES (this repo (2 project dirs: 2 live, 0 unlisted);"
        )

    def test_a_removed_worktrees_window_is_counted_and_only_the_listed_paths_ledger_file_is_read(
        self, fake_projects, stub_repo_tracked_agent_types, tmp_path, monkeypatch, capsys,
    ):
        stub_repo_tracked_agent_types(_TRACKED_AGENT_TYPE)
        removed_worktree_path = f"{_WORKTREE_PATH}/.claude/worktrees/gone"
        removed_project = fake_projects.parent / scope._path_to_project_slug(removed_worktree_path)
        removed_project.mkdir()
        args, _calls = _reviewer_reads_args(monkeypatch)
        dispatch = _agent_use("dispatch-agent-removed", _TRACKED_AGENT_TYPE)
        _write_jsonl(removed_project / f"{_SESSION_ID}.jsonl", [_reviewer_turn("m0", [dispatch])])
        _reviewer_window(removed_project, "agent-removed", [_reviewer_turn("a-removed", [])])
        _write_this_repo_ledger_file(tmp_path, _WORKTREE_PATH, "listed-slot", [_address_row("listed")])
        _write_this_repo_ledger_file(
            tmp_path, removed_worktree_path, "removed-slot", [_address_row("removed-1"), _address_row("removed-2")],
        )

        report = _report_text(args, fake_projects, capsys)

        assert report.splitlines()[0].startswith("REVIEWER READS SOURCES (this repo (2 project dirs: 1 live, 1 unlisted);")
        assert "sessions=1 reviewer_windows=1" in report
        assert "ledger files: directory=present read=1 unreadable=0" in report
        assert "terminal rows: ADDRESS=1 DEFER=0 SETTLED=0 total=1" in report
        assert "sessions with a disposition row=1 covered by the transcript scan=1" in report


def _structured_result_leaking_text(tool_id: str, path: str, *, num_lines: int, total_lines: int) -> dict:
    """A successful Read result whose text and `toolUseResult.file.content` both carry a sentinel."""
    result = _file_result(
        tool_id, path, num_lines=num_lines, total_lines=total_lines, text=_leak_sentinel("result-text"),
    )
    result["toolUseResult"]["file"]["content"] = _leak_sentinel("result-file-content")
    return result


class TestOutputInvariant:
    """A sentinel in every input channel never reaches stdout or stderr, and each channel's record moved a printed count."""

    _SLUG_SENTINEL = _leak_sentinel("project-slug")
    _SESSION_SENTINEL = _leak_sentinel("session")

    def _seed(self, fake_projects, tmp_path):
        project = fake_projects.parent / f"-home-user-{self._SLUG_SENTINEL}"
        project.mkdir()
        read_path = f"/repo/{_leak_sentinel('read-path')}/module.py"
        reviewer_read_id = _leak_sentinel("reviewer-tool-use-id")
        reviewer_records = [
            _reviewer_turn(
                "m1", [_read_use(reviewer_read_id, read_path)], version=_leak_sentinel("version"),
                model=_leak_sentinel("model"),
            ),
            _structured_result_leaking_text(reviewer_read_id, read_path, num_lines=5, total_lines=9),
            *_structured_read_exchange(
                "m2", "r2", f"/x/{_leak_sentinel('diff-dir')}/code-review-diff-markers/review.diff", num_lines=3,
                total_lines=3,
            ),
            *_failed_read_exchange(
                "m3", "r3", f"/repo/{_leak_sentinel('failed-read-path')}/a.py",
                f"ENOENT /home/{_leak_sentinel('error-string-path')}/a.py",
            ),
            *_failed_read_exchange(
                "m4", "r4", f"/repo/{_leak_sentinel('failed-read-path-2')}/b.py",
                [{"type": "text", "text": f"EIO /home/{_leak_sentinel('error-blocks-path')}/b.py"}],
            ),
        ]
        _write_jsonl(project / f"{self._SESSION_SENTINEL}.jsonl", [
            _reviewer_turn("m0", [_agent_use("dispatch-agent-leak", f"staff-{_leak_sentinel('subagent-type')}")]),
            *self._round_window_leaking_every_main_thread_channel(),
        ])
        _reviewer_window(
            project, "agent-leak", reviewer_records, agent_type=f"staff-{_leak_sentinel('agent-type')}",
            session_id=self._SESSION_SENTINEL,
        )
        ledger_rows = [
            {**_address_row(_leak_sentinel("ledger-id"), session_id=self._SESSION_SENTINEL),
             "finding": _leak_sentinel("finding")},
            {**_address_row(_leak_sentinel("ledger-id-2"), session_id=self._SESSION_SENTINEL),
             "ref": _leak_sentinel("ledger-ref-unmatched")},
        ]
        _write_this_repo_ledger_file(
            tmp_path, f"/home/user/{self._SLUG_SENTINEL}", _leak_sentinel("slot"), ledger_rows,
        )
        dangling = tmp_path / "review-narrative-ledger" / (
            f"{publication_scope._ledger_repo_hash(f'/home/user/{self._SLUG_SENTINEL}')}.{_leak_sentinel('dangling-slot')}.jsonl"
        )
        dangling.symlink_to(tmp_path / "does-not-exist")

    @staticmethod
    def _round_window_leaking_every_main_thread_channel() -> list[dict]:
        """A review-round window whose Skill input, Read inputs, Read result text and ids each carry a sentinel."""
        whole_file_id = _leak_sentinel("round-whole-file-tool-use-id")
        targeted_id = _leak_sentinel("round-targeted-tool-use-id")
        whole_file_path = f"/repo/{_leak_sentinel('round-read-path')}/module.py"
        skill_open = _skill_block("round-skill-id", "code-review")
        skill_open["input"]["args"] = _leak_sentinel("skill-args")
        return [
            _reviewer_turn("m-round-open", [skill_open]),
            _reviewer_turn("m-round-reads", [
                _read_use(whole_file_id, whole_file_path),
                _read_use(targeted_id, f"/repo/{_leak_sentinel('round-targeted-path')}/b.py", offset=5, limit=10),
            ]),
            _structured_result_leaking_text(whole_file_id, whole_file_path, num_lines=3, total_lines=3),
            _next_prompt(),
        ]

    def test_no_sentinel_reaches_either_stream_and_every_channel_moved_a_printed_count(
        self, fake_projects, stub_repo_tracked_agent_types, tmp_path, monkeypatch, capfd, caplog, recwarn,
    ):
        stub_repo_tracked_agent_types()
        worktree_path = f"/home/user/{self._SLUG_SENTINEL}"
        _reviewer_reads_args(monkeypatch, worktree_paths=(worktree_path,))
        self._seed(fake_projects, tmp_path)
        monkeypatch.setattr(sys, "argv", ["transcript-analysis.py", *_REAL_ARGV])
        caplog.set_level(logging.DEBUG)

        cli.main()

        captured = capfd.readouterr()
        out = captured.out
        assert _LEAK_SENTINEL_PREFIX not in out + captured.err
        assert [record.getMessage() for record in caplog.records if _LEAK_SENTINEL_PREFIX in record.getMessage()] == []
        assert [str(warning.message) for warning in recwarn if _LEAK_SENTINEL_PREFIX in str(warning.message)] == []
        # Positive controls: each channel's record moved a printed count.
        assert "sessions=1 reviewer_windows=1" in out  # the project slug and the transcript name
        assert "code-review: round_windows=1 read_calls=2 whole_file=1 targeted=1" in out  # the round's Skill and Read inputs
        round_lines = out.splitlines()
        round_block = round_lines[round_lines.index("code-review: round_windows=1 read_calls=2 whole_file=1 targeted=1"):]
        # The round's result record paired with its call through the sentinel id.
        assert "complete=1" in round_block[1].split() and "up_to_1000=1" in round_block[2].split()
        outcome_tables = out.split("## Whole-file calls in reviewer windows")[1].split("## After a partial")[0]
        code_table = outcome_tables.split("\nprose (")[0]
        diff_handoff_table = outcome_tables.split("\ndiff handoff")[1]
        assert "  complete: total=1 up_to_1000=1" in diff_handoff_table  # the diff-handoff directory name
        assert "  other_error: total=2" in code_table  # both failed-call paths and both error shapes
        assert "  partial_unflagged: total=1 up_to_1000=1" in code_table  # the reviewed file's path
        assert "code/other: calls=1 later_offset_read insufficient (0/1)" in out  # the same call, followed up
        assert "harness version: other=1" in out and "model: other=1" in out  # a version and a model
        assert "TOTAL: windows=1 partial=1 refused=0 larger_than_one_call=1" in out  # the agent type, folded
        assert _printed_line(out, "(withheld — untracked agent type): windows=1")
        assert _printed_line(out, "(withheld — untracked agent type): dispatches=1")  # the dispatch subagent_type
        assert "terminal rows: ADDRESS=2 DEFER=0 SETTLED=0 total=2" in out  # a ledger id, ref and finding
        assert "sessions with a disposition row=1 covered by the transcript scan=1" in out  # the session id
        assert "ledger files: directory=present read=1 unreadable=1" in out  # the dangling symlink

    @pytest.mark.parametrize("field", ["version", "model"])
    def test_a_hostile_value_prints_nowhere_in_the_report(
        self, field, fake_projects, stub_repo_tracked_agent_types, monkeypatch, capsys,
    ):
        stub_repo_tracked_agent_types(_TRACKED_AGENT_TYPE)
        args, _calls = _reviewer_reads_args(monkeypatch)
        hostile = _reviewer_turn("m1", **{field: "/home/user/HOSTILE-value"})
        _reviewer_window(fake_projects, "agent-a", [hostile])
        _write_jsonl(fake_projects / "session-main.jsonl", [_reviewer_turn("m0")])

        report = _report_text(args, fake_projects, capsys)

        assert "HOSTILE" not in report
        assert f"{'harness version' if field == 'version' else 'model'}: other=1" in report

    @pytest.mark.parametrize(
        "hostile_model",
        [
            pytest.param(lambda priced: f"{priced}-20260101/HOSTILE-corpus-text", id="priced key extended with hostile text"),
            pytest.param(str.upper, id="case variant of a priced key"),
        ],
    )
    @pytest.mark.parametrize("priced_model", sorted(pricing._MODEL_BASE_INPUT_RATES))
    def test_a_model_near_a_priced_key_prints_as_other(
        self, priced_model, hostile_model, fake_projects, stub_repo_tracked_agent_types, monkeypatch, capsys,
    ):
        stub_repo_tracked_agent_types(_TRACKED_AGENT_TYPE)
        args, _calls = _reviewer_reads_args(monkeypatch)
        _reviewer_window(fake_projects, "agent-a", [_reviewer_turn("m1", model=hostile_model(priced_model))])
        _write_jsonl(fake_projects / "session-main.jsonl", [_reviewer_turn("m0")])

        report = _report_text(args, fake_projects, capsys)

        assert "HOSTILE" not in report and priced_model.upper() not in report
        assert "model: other=1" in report

    def test_the_capture_mechanism_sees_each_channel_a_sentinel_could_leak_through(self, capfd, caplog, recwarn):
        print(_leak_sentinel("control-out"))
        print(_leak_sentinel("control-err"), file=sys.stderr)
        os.write(1, _leak_sentinel("control-fd").encode())
        logging.warning(_leak_sentinel("control-log"))
        warnings.warn(_leak_sentinel("control-warning"), stacklevel=1)

        captured = capfd.readouterr()
        assert _leak_sentinel("control-out") in captured.out and _leak_sentinel("control-fd") in captured.out
        assert _leak_sentinel("control-err") in captured.err
        assert [record.getMessage() for record in caplog.records] == [_leak_sentinel("control-log")]
        assert [str(warning.message) for warning in recwarn] == [_leak_sentinel("control-warning")]


class TestNestedDispatch:
    def test_a_nested_reviewer_is_in_the_read_figures_and_not_in_the_yield_figures(
        self, fake_projects, stub_repo_tracked_agent_types, monkeypatch, capsys,
    ):
        stub_repo_tracked_agent_types(_TRACKED_AGENT_TYPE)
        args, _calls = _reviewer_reads_args(monkeypatch)
        main_dispatch = _reviewer_turn("md", [_agent_use("dispatch-agent-main", _TRACKED_AGENT_TYPE)])
        _write_jsonl(fake_projects / "session-main.jsonl", [main_dispatch])
        _reviewer_window(fake_projects, "agent-main", [_reviewer_turn("a1", [])])
        _reviewer_window(fake_projects, "agent-nested", [_reviewer_turn("n1", [])], spawn_depth=2)

        report = _report_text(args, fake_projects, capsys)

        assert "sessions=1 reviewer_windows=2" in report
        assert _printed_line(report, "TOTAL: dispatches=") == (
            "TOTAL: dispatches=1 findings_found=0 zero_finding=0 unclassified=1 findings=0"
        )


class TestRequestIdNotice:
    def test_a_non_contiguous_request_id_run_prints_its_id_only_in_pricings_stderr_notice(
        self, fake_projects, stub_repo_tracked_agent_types, monkeypatch, capfd,
    ):
        stub_repo_tracked_agent_types()
        args, _calls = _reviewer_reads_args(monkeypatch)
        monkeypatch.setattr(pricing, "_non_contiguous_merge_notices_logged", set())
        _write_jsonl(fake_projects / f"{_SESSION_ID}.jsonl", [
            *_round_records("code-review", "a"),
            _reviewer_turn("n1", [], request_id="req-noncontiguous", usage={"output_tokens": 7}),
            _structured_read_exchange("n2", "rx", "/repo/a.py", num_lines=1, total_lines=1)[1],
            _reviewer_turn("n3", [], request_id="req-noncontiguous", usage={"output_tokens": 7}),
            _next_prompt(),
        ])

        reviewer_reads._reviewer_reads_report(args, [fake_projects.parent])

        captured = capfd.readouterr()
        assert "req-noncontiguous" not in captured.out
        assert captured.err == (
            "NOTICE: non-contiguous requestId run merged -- requestId 'req-noncontiguous' has 2 non-contiguous"
            " assistant records, merged into one turn (usage matched on every compared record) (further merged occurrences"
            " this run of the CLI are suppressed).\n"
        )


_YIELD_NOT_COMPLETED = (
    "reviewer-yield pass: not completed, because the shared reviewer-yield code raised an AttributeError, TypeError,"
    " ValueError or RecursionError, so no yield rows are printed"
)
_HOSTILE_SENTINEL = _leak_sentinel("hostile-field")
_TRACKED_DISPATCH = _agent_use("dispatch-agent-a", _TRACKED_AGENT_TYPE)


def _hostile(record: dict, **message_changes) -> dict:
    return {**record, "message": {**record["message"], **message_changes}}


class TestMainThreadPassOverHostileInput:
    @pytest.mark.parametrize(
        "hostile_records",
        [
            pytest.param([_hostile(_reviewer_turn("h1", []), content=5)], id="assistant_content_int"),
            pytest.param([_user_msg([{"type": "text", "text": 5}], ts=_IN_WINDOW)], id="user_text_block_int_text"),
            pytest.param(
                [_hostile(_reviewer_turn(f"p{n}", [], request_id="req-pair"), usage=_HOSTILE_SENTINEL) for n in (1, 2)],
                id="same_request_id_pair_with_string_usage",
            ),
            pytest.param(
                [_hostile(_reviewer_turn(f"p{n}", [], request_id="req-pair"), content=5) for n in (1, 2)],
                id="same_request_id_pair_with_int_content",
            ),
        ],
    )
    def test_a_shape_the_round_pass_would_choke_on_is_reduced_and_the_report_completes(
        self, hostile_records, fake_projects, stub_repo_tracked_agent_types, monkeypatch, capfd,
    ):
        stub_repo_tracked_agent_types()
        args, _calls = _reviewer_reads_args(monkeypatch)
        _write_jsonl(
            fake_projects / f"{_SESSION_ID}.jsonl", [*_round_records("code-review", "a"), *hostile_records, _next_prompt()],
        )

        reviewer_reads._reviewer_reads_report(args, [fake_projects.parent])

        captured = capfd.readouterr()
        assert "code-review: round_windows=1 read_calls=0 whole_file=0 targeted=0" in captured.out
        assert "sessions=1 reviewer_windows=0" in captured.out
        assert _HOSTILE_SENTINEL not in captured.out + captured.err


@pytest.mark.usefixtures("default_int_str_digit_limit")
class TestYieldPassOverHostileInput:
    def _seed_dispatch(self, fake_projects, dispatch_block, main_lines=(), window_records=None):
        _write_jsonl(fake_projects / f"{_SESSION_ID}.jsonl", [*main_lines, _reviewer_turn("m0", [dispatch_block])])
        _reviewer_window(fake_projects, "agent-a", window_records or [_reviewer_turn("a1", [])])

    def _seed_oversized_sidecar_integer(self, fake_projects):
        self._seed_dispatch(fake_projects, _TRACKED_DISPATCH)
        sidecar = fake_projects / _SESSION_ID / "subagents" / "agent-a.meta.json"
        sidecar.write_text(f'{{"agentType": "{_HOSTILE_SENTINEL}", "toolUseId": {"1" * 5000}}}')
        return "unreadable_subagent_meta=1"

    def _seed_deeply_nested_sidecar(self, fake_projects):
        self._seed_dispatch(fake_projects, _TRACKED_DISPATCH)
        sidecar = fake_projects / _SESSION_ID / "subagents" / "agent-a.meta.json"
        sidecar.write_text("[" * 3_000_000 + "]" * 3_000_000)
        return "unreadable_subagent_meta=1"

    def _seed_verdict_count_over_the_digit_limit(self, fake_projects):
        verdict = {"type": "text", "text": f"Found {'1' * 4301} issues. {_HOSTILE_SENTINEL}"}
        self._seed_dispatch(fake_projects, _TRACKED_DISPATCH, window_records=[_reviewer_turn("a1", [verdict])])
        return "sessions=1 reviewer_windows=1"

    def _seed_surrogate_write_target(self, fake_projects):
        write = _write_use("w1", "x", path=f"/repo/{_HOSTILE_SENTINEL}/\ud800.py")
        self._seed_dispatch(
            fake_projects, _TRACKED_DISPATCH, main_lines=[_reviewer_turn("m1", [write])],
        )
        return "sessions=1 reviewer_windows=1"

    @pytest.mark.parametrize(
        "seed",
        [
            pytest.param(_seed_oversized_sidecar_integer, id="sidecar_integer_over_the_digit_limit"),
            pytest.param(_seed_deeply_nested_sidecar, id="sidecar_nested_past_the_decoders_stack"),
            pytest.param(_seed_verdict_count_over_the_digit_limit, id="verdict_count_over_the_digit_limit"),
            pytest.param(_seed_surrogate_write_target, id="lone_surrogate_in_a_write_target_path"),
        ],
    )
    def test_a_decode_failure_in_the_yield_pass_prints_the_fixed_notice_and_leaves_the_rest_of_the_report(
        self, seed, fake_projects, stub_repo_tracked_agent_types, monkeypatch, capfd,
    ):
        stub_repo_tracked_agent_types(_TRACKED_AGENT_TYPE)
        args, _calls = _reviewer_reads_args(monkeypatch)
        expected_figure = seed(self, fake_projects)

        reviewer_reads._reviewer_reads_report(args, [fake_projects.parent])

        captured = capfd.readouterr()
        assert _printed_line(captured.out, "reviewer-yield pass:") == _YIELD_NOT_COMPLETED
        assert expected_figure in captured.out
        assert "## Diagnostics" in captured.out
        assert "1" * 50 not in captured.out + captured.err
        assert _HOSTILE_SENTINEL not in captured.out + captured.err

    def test_a_verdict_count_of_4000_digits_prints_the_ceiling_and_none_of_its_digits(
        self, fake_projects, stub_repo_tracked_agent_types, monkeypatch, capfd,
    ):
        stub_repo_tracked_agent_types(_TRACKED_AGENT_TYPE)
        args, _calls = _reviewer_reads_args(monkeypatch)
        verdict = {"type": "text", "text": f"Found {'1' * 4000} issues."}
        self._seed_dispatch(fake_projects, _TRACKED_DISPATCH, window_records=[_reviewer_turn("a1", [verdict])])

        reviewer_reads._reviewer_reads_report(args, [fake_projects.parent])

        captured = capfd.readouterr()
        assert "TOTAL: dispatches=1 findings_found=1 zero_finding=0 unclassified=0 findings=over 1,000,000" in captured.out
        assert "1" * 50 not in captured.out + captured.err

    def test_a_non_object_line_and_a_non_object_message_leave_the_yield_pass_complete(
        self, fake_projects, stub_repo_tracked_agent_types, monkeypatch, capsys,
    ):
        stub_repo_tracked_agent_types(_TRACKED_AGENT_TYPE)
        args, _calls = _reviewer_reads_args(monkeypatch)
        self._seed_dispatch(
            fake_projects, _agent_use("dispatch-agent-a", _TRACKED_AGENT_TYPE),
            main_lines=[5, "text", {"type": "assistant", "timestamp": _IN_WINDOW, "message": "text"}],
        )

        report = _report_text(args, fake_projects, capsys)

        assert "reviewer-yield pass: skipped_input_total=0" in report
        assert "TOTAL: dispatches=1 findings_found=0 zero_finding=0 unclassified=1 findings=0" in report

    @pytest.mark.parametrize(
        "dispatch_block",
        [
            pytest.param(_agent_use("dispatch-agent-a", ["staff-x"]), id="subagent_type_list_raises_attribute_error"),
            pytest.param(_agent_use(["dispatch-agent-a"], _TRACKED_AGENT_TYPE), id="tool_use_id_list_raises_type_error"),
        ],
    )
    def test_a_field_shape_the_shared_yield_code_cannot_take_ends_the_pass_with_a_fixed_notice(
        self, dispatch_block, fake_projects, stub_repo_tracked_agent_types, monkeypatch, capsys,
    ):
        stub_repo_tracked_agent_types(_TRACKED_AGENT_TYPE)
        args, _calls = _reviewer_reads_args(monkeypatch)
        self._seed_dispatch(fake_projects, dispatch_block)

        report = _report_text(args, fake_projects, capsys)

        assert "reviewer-yield pass: not completed" in report
        assert "sessions=1 reviewer_windows=1" in report


def test_the_ledger_window_includes_the_whole_until_day(
    fake_projects, stub_repo_tracked_agent_types, tmp_path, monkeypatch, capsys,
):
    stub_repo_tracked_agent_types()
    args, _calls = _reviewer_reads_args(monkeypatch)
    last_second_of_until_day = {**_address_row("late"), "event_time": "2026-08-12T23:59:59Z"}
    _write_this_repo_ledger_file(tmp_path, _WORKTREE_PATH, "slot", [last_second_of_until_day])

    assert "terminal rows: ADDRESS=1 DEFER=0 SETTLED=0 total=1" in _report_text(args, fake_projects, capsys)


def test_a_dispatch_with_no_subagent_files_prints_pricings_fixed_format_drift_warning_on_stderr(
    fake_projects, stub_repo_tracked_agent_types, monkeypatch, capfd,
):
    stub_repo_tracked_agent_types(_TRACKED_AGENT_TYPE)
    args, _calls = _reviewer_reads_args(monkeypatch)
    _write_jsonl(fake_projects / f"{_SESSION_ID}.jsonl", [_reviewer_turn("m0", [_agent_use("d1", _TRACKED_AGENT_TYPE)])])

    reviewer_reads._reviewer_reads_report(args, [fake_projects.parent])

    assert capfd.readouterr().err == (
        "WARNING: subagent spawns detected in main thread but zero isSidechain assistant turns were read from"
        " 'subagents/' subdirectories. The Claude Code transcript format may have drifted \u2014 check that subagent"
        " files still live under <session>/subagents/*.jsonl and that records still carry 'isSidechain': true.\n"
    )


def test_a_refusal_in_a_fresh_interpreter_exits_2_with_the_command_label(tmp_path):
    environment = {name: value for name, value in os.environ.items() if name != "PYTHONPATH"}
    environment.update(HOME=str(tmp_path), CLAUDE_CONFIG_DIR=str(tmp_path / "account"))

    result = subprocess.run(
        [sys.executable, str(_SCRIPT), "reviewer-reads", "--since", "2026-08-10", "--until", "2026-08-12"],
        cwd=_SCRIPT.parent, capture_output=True, text=True, timeout=30, env=environment,
    )

    assert (result.returncode, result.stdout, result.stderr) == (2, "", _REFUSAL_LINE)


def test_a_reviewer_window_timestamp_outside_the_window_is_not_counted_through_the_whole_command(
    fake_projects, stub_repo_tracked_agent_types, monkeypatch, capsys,
):
    stub_repo_tracked_agent_types(_TRACKED_AGENT_TYPE)
    args, _calls = _reviewer_reads_args(monkeypatch)
    _write_jsonl(fake_projects / f"{_SESSION_ID}.jsonl", [_reviewer_turn("m0")])
    _reviewer_window(fake_projects, "agent-in", [_reviewer_turn("a1", ts=_IN_WINDOW)])
    _reviewer_window(fake_projects, "agent-out", [_reviewer_turn("b1", ts="2026-08-13T00:00:00.000Z")])

    assert "sessions=1 reviewer_windows=1" in _report_text(args, fake_projects, capsys)


@pytest.mark.parametrize(
    ("later_read", "expected_covered_after", "expected_neither"),
    [
        pytest.param(False, 0, 1, id="flagged_call_reporting_the_last_line_is_not_covered_by_itself"),
        pytest.param(True, 1, 0, id="flagged_call_short_of_the_last_line_is_covered_by_a_later_paged_read"),
    ],
)
def test_a_token_cap_flagged_call_reaching_the_last_line_adds_no_coverage_to_the_printed_follow_up(
    later_read, expected_covered_after, expected_neither,
    fake_projects, stub_repo_tracked_agent_types, monkeypatch, capsys,
):
    stub_repo_tracked_agent_types(_TRACKED_AGENT_TYPE)
    args, _calls = _reviewer_reads_args(monkeypatch)
    big_path = "/repo/src/big.py"
    flagged_lines = 40 if later_read else 100
    reviewer_records = _structured_read_exchange("m1", "r1", big_path, num_lines=flagged_lines, total_lines=100, truncated=True)
    if later_read:
        reviewer_records += _structured_read_exchange(
            "m2", "r2", big_path, num_lines=60, total_lines=100, start_line=41, offset=40, limit=60,
        )
    main_dispatch = _reviewer_turn("m0", [_agent_use("dispatch-agent-main", _TRACKED_AGENT_TYPE)])
    _write_jsonl(fake_projects / f"{_SESSION_ID}.jsonl", [main_dispatch])
    _reviewer_window(fake_projects, "agent-main", reviewer_records)

    follow_up_line = _printed_line(_report_text(args, fake_projects, capsys), "code/other: calls=")

    assert f"covered_after insufficient ({expected_covered_after}/1);" in follow_up_line
    assert follow_up_line.endswith(f"insufficient ({expected_neither}/1)")


@pytest.mark.parametrize(
    ("notice_present", "expected_partial_calls_without_notice"),
    [
        pytest.param(True, 0, id="notice_naming_the_call_inside_its_attachment_object_is_paired"),
        pytest.param(False, 1, id="no_notice_record_leaves_the_partial_token_cap_call_unpaired"),
    ],
)
def test_a_truncated_whole_file_read_is_paired_with_its_notice_through_the_report(
    notice_present, expected_partial_calls_without_notice,
    fake_projects, stub_repo_tracked_agent_types, monkeypatch, capsys,
):
    # Pins the on-disk path: a real-shaped notice in a subagent transcript file reaches the notice-agreement line.
    stub_repo_tracked_agent_types(_TRACKED_AGENT_TYPE)
    args, _calls = _reviewer_reads_args(monkeypatch)
    truncated_call = _structured_read_exchange("m1", "r1", "/repo/src/big.py", num_lines=40, total_lines=100, truncated=True)
    notice = [_read_truncation_notice("r1")] if notice_present else []
    main_dispatch = _reviewer_turn("m0", [_agent_use("dispatch-agent-main", _TRACKED_AGENT_TYPE)])
    _write_jsonl(fake_projects / f"{_SESSION_ID}.jsonl", [main_dispatch])
    _reviewer_window(fake_projects, "agent-main", [*truncated_call, *notice])

    notice_agreement_line = _printed_line(_report_text(args, fake_projects, capsys), "notice agreement:")

    assert notice_agreement_line == (
        f"notice agreement: partial_token_cap calls with no read_truncation_notice={expected_partial_calls_without_notice};"
        " notices naming neither a partial_token_cap nor a size_unknown call=0;"
        " notices naming a size_unknown call=0"
    )
