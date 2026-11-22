"""cmd_correction_candidates and its subparser: wiring, refusals, preview, the written file, and what reaches the terminal."""
import json
import os
import stat
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from helpers import init_git_repo_with_commit
from transcript_analysis import cli, correction_candidates, ledger_common, scope

from ._compaction_context_helpers import slash_invocation
from ._correction_candidates_helpers import (
    ask_answer_record,
    ask_record,
    assistant_text,
    prompt,
    question_spec,
    record_streams,
    run_main,
    seed,
    stub_git_check,
    ts,
    with_fields,
    written_lines,
)
from .conftest import _two_declared_roots

_SCOPE_ERROR = "correction-candidates: pass --projects GLOB or --this-repo (--projects '*' reads every project on this machine)\n"
_OUT_ERROR = "correction-candidates: pass --out PATH (a new file outside any git work tree) or --preview\n"
_ZERO_PADDED = "must be a zero-padded YYYY-MM-DD date\n"
_HEADER_PREFIX = "CORRECTION CANDIDATES SOURCES ("
_FAMILIES_PREFIX = "correction-candidates: families "
_COUNTS_PREFIX = "correction-candidates: counts "
_REPO_FAMILY = "-home-example-src-workflow-gates"
_ABORT_LINE = "correction-candidates: the transcript scan aborted ({name}); no file was written\n"
_SUBAGENT_CANARY = "CANARY-SUBAGENT-DISPATCH-PROMPT"
_UNPADDED_SINCE = ["--since", "2026-5-09"]
_UNPADDED_SINCE_ERROR = f"correction-candidates: --since {_ZERO_PADDED}"


@pytest.fixture()
def real_git_check():
    """Requesting this fixture keeps the real out-path git check, which every other test here stubs."""


@pytest.fixture(autouse=True)
def stubbed_git_check(request, monkeypatch):
    if "real_git_check" not in request.fixturenames:
        stub_git_check(monkeypatch)


@pytest.fixture()
def out_dir(tmp_path) -> Path:
    directory = tmp_path / "out"
    directory.mkdir()
    return directory


def families_of(stderr: str) -> dict:
    (families_line,) = [line for line in stderr.splitlines() if line.startswith(_FAMILIES_PREFIX)]
    return json.loads(families_line.removeprefix(_FAMILIES_PREFIX))


def question_session(*, minute: int = 1) -> list[dict]:
    return [
        prompt("please fix the thing", minute),
        ask_record([question_spec("Which one?", ("Alpha", "Beta"))], minute=minute + 1),
        ask_answer_record(answers={"Which one?": "Alpha"}, timestamp=ts(minute + 2)),
        assistant_text("done", timestamp=ts(minute + 3)),
    ]


class TestCliWiring:
    def test_defaults_and_bound_function(self):
        args = cli.build_parser().parse_args(["correction-candidates", "--this-repo"])

        assert args.truncate_chars == 2000
        assert args.projects is None
        assert args.preview is False
        assert args.out is None
        assert args.func is correction_candidates.cmd_correction_candidates

    def test_projects_defaults_to_none_without_either_scope_flag(self):
        assert cli.build_parser().parse_args(["correction-candidates", "--preview"]).projects is None

    def test_explicit_projects_star_parses_to_star(self):
        assert cli.build_parser().parse_args(["correction-candidates", "--projects", "*"]).projects == "*"

    def test_this_repo_and_projects_are_mutually_exclusive(self):
        with pytest.raises(SystemExit):
            cli.build_parser().parse_args(["correction-candidates", "--this-repo", "--projects", "x"])

    def test_zero_truncate_chars_parses(self):
        assert cli.build_parser().parse_args(["correction-candidates", "--truncate-chars", "0"]).truncate_chars == 0


class TestAllowPaths:
    def test_this_repo_alone_runs_and_reads_the_seeded_family(self, fake_projects, out_dir, monkeypatch, capsys):
        monkeypatch.setattr(scope, "_repo_scoped_project_slugs", lambda *args, **kwargs: [fake_projects.name])
        seed(fake_projects, question_session())
        out = out_dir / "run.jsonl"

        status, stdout, _stderr = run_main(monkeypatch, capsys, "--this-repo", "--out", str(out))

        assert status == 0
        assert stdout == f"{out}\n"
        lines = written_lines(out)
        assert lines[0]["families"] == {"-home-user-testrepo": 1}
        assert [line["kind"] for line in lines] == ["scope", "prompt", "question"]

    def test_explicit_projects_star_runs(self, fake_projects, out_dir, monkeypatch, capsys):
        seed(fake_projects, question_session())
        out = out_dir / "run.jsonl"

        status, _stdout, _stderr = run_main(monkeypatch, capsys, "--projects", "*", "--out", str(out))

        assert status == 0
        assert [line["kind"] for line in written_lines(out)] == ["scope", "prompt", "question"]

    @pytest.mark.parametrize(
        ("flag", "date"), [("--since", "0001-01-01"), ("--until", "9999-12-31")], ids=["earliest-since", "latest-until"],
    )
    def test_the_extreme_dates_run_and_the_scope_record_names_them(
        self, fake_projects, out_dir, monkeypatch, capsys, flag, date,
    ):
        seed(fake_projects, question_session())
        out = out_dir / "run.jsonl"

        status, _stdout, _stderr = run_main(monkeypatch, capsys, "--projects", "*", flag, date, "--out", str(out))

        scope_record = written_lines(out)[0]
        assert status == 0
        assert scope_record[flag.removeprefix("--")] == date
        assert scope_record["counts"]["prompts"] == 1


class TestRefusals:
    @pytest.fixture(params=[(), ("--preview",)], ids=["run", "preview"])
    def mode_flags(self, request) -> tuple[str, ...]:
        return request.param

    def _assert_refused(self, status, stdout, stderr, *, expected_stderr=None, expected_status=2):
        assert status == expected_status
        assert stdout == ""
        assert _HEADER_PREFIX not in stderr
        assert _FAMILIES_PREFIX not in stderr
        if expected_stderr is not None:
            assert stderr == expected_stderr

    @pytest.mark.parametrize(
        "scope_args",
        [pytest.param([], id="neither-scope-flag"), pytest.param(["--projects", ""], id="empty-projects"),
         pytest.param(["--projects="], id="empty-projects-equals-form")],
    )
    def test_a_run_without_an_effective_scope_exits_2_with_one_line(
        self, fake_projects, out_dir, monkeypatch, capsys, scope_args, mode_flags,
    ):
        out = out_dir / "run.jsonl"

        result = run_main(monkeypatch, capsys, *scope_args, "--out", str(out), *mode_flags)

        self._assert_refused(*result, expected_stderr=_SCOPE_ERROR)
        assert not out.exists()

    def test_neither_scope_flag_nor_out_prints_the_scope_line_only(self, fake_projects, monkeypatch, capsys):
        result = run_main(monkeypatch, capsys)

        self._assert_refused(*result, expected_stderr=_SCOPE_ERROR)

    def test_a_negative_truncate_chars_exits_2_with_argparses_usage_and_error(
        self, fake_projects, out_dir, monkeypatch, capsys, mode_flags,
    ):
        out = out_dir / "run.jsonl"

        status, stdout, stderr = run_main(
            monkeypatch, capsys, "--projects", "*", "--truncate-chars", "-1", "--out", str(out), *mode_flags,
        )

        self._assert_refused(status, stdout, stderr)
        assert "usage:" in stderr
        assert "argument --truncate-chars: must be 0 or more: '-1'" in stderr
        assert not out.exists()

    def test_a_date_that_does_not_exist_exits_2_with_argparses_usage_and_error(
        self, fake_projects, out_dir, monkeypatch, capsys, mode_flags,
    ):
        out = out_dir / "run.jsonl"

        status, stdout, stderr = run_main(
            monkeypatch, capsys, "--projects", "*", "--since", "2026-02-30", "--out", str(out), *mode_flags,
        )

        self._assert_refused(status, stdout, stderr)
        assert "usage:" in stderr
        assert "argument --since: not a valid YYYY-MM-DD date: '2026-02-30'" in stderr
        assert not out.exists()

    @pytest.mark.parametrize(
        ("window_args", "expected_flags"),
        [
            pytest.param(["--since", "2026-5-09"], "--since", id="unpadded-since"),
            pytest.param(["--until", "2026-05-9"], "--until", id="unpadded-until"),
            pytest.param(["--since", "2026-5-09", "--until", "2026-05-9"], "--since and --until", id="both-unpadded"),
        ],
    )
    def test_a_bound_that_yields_no_window_exits_2_naming_the_flag_and_never_echoing_the_value(
        self, fake_projects, out_dir, monkeypatch, capsys, window_args, expected_flags, mode_flags,
    ):
        seed(fake_projects, question_session())
        out = out_dir / "run.jsonl"

        result = run_main(monkeypatch, capsys, "--projects", "*", *window_args, "--out", str(out), *mode_flags)

        self._assert_refused(*result, expected_stderr=f"correction-candidates: {expected_flags} {_ZERO_PADDED}")
        assert not out.exists()

    def test_an_argparse_error_prints_instead_of_the_scope_refusal(self, fake_projects, monkeypatch, capsys, mode_flags):
        status, stdout, stderr = run_main(monkeypatch, capsys, "--truncate-chars", "-1", *mode_flags)

        self._assert_refused(status, stdout, stderr)
        assert "argument --truncate-chars" in stderr
        assert _SCOPE_ERROR not in stderr

    @pytest.mark.parametrize(
        ("scope_args", "supplies_existing_out", "window_args", "expected_stderr"),
        [
            # Pins the documented refusal order (scope, then window), not a privacy invariant.
            pytest.param([], False, _UNPADDED_SINCE, _SCOPE_ERROR, id="no-scope-before-an-unapplied-window"),
            pytest.param([], True, [], _SCOPE_ERROR, id="no-scope-before-an-existing-out"),
            pytest.param(
                ["--projects", "*"], False, _UNPADDED_SINCE, _UNPADDED_SINCE_ERROR,
                id="unapplied-window-before-neither-out-nor-preview",
            ),
            pytest.param(
                ["--projects", "*"], True, _UNPADDED_SINCE, _UNPADDED_SINCE_ERROR, id="unapplied-window-before-an-existing-out",
            ),
        ],
    )
    def test_two_refusals_that_apply_print_only_the_earlier_ones_line(
        self, fake_projects, out_dir, monkeypatch, capsys, scope_args, supplies_existing_out, window_args, expected_stderr,
    ):
        out_args = []
        if supplies_existing_out:
            existing_out = out_dir / "run.jsonl"
            existing_out.write_text("precious\n")
            out_args = ["--out", str(existing_out)]

        result = run_main(monkeypatch, capsys, *scope_args, *window_args, *out_args)

        self._assert_refused(*result, expected_stderr=expected_stderr)

    def test_neither_out_nor_preview_exits_2_with_one_line(self, fake_projects, monkeypatch, capsys):
        result = run_main(monkeypatch, capsys, "--projects", "*")

        self._assert_refused(*result, expected_stderr=_OUT_ERROR)

    def test_an_existing_out_exits_2_and_is_left_unchanged(self, fake_projects, out_dir, monkeypatch, capsys, mode_flags):
        out = out_dir / "run.jsonl"
        out.write_text("precious\n")

        result = run_main(monkeypatch, capsys, "--projects", "*", "--out", str(out), *mode_flags)

        self._assert_refused(
            *result,
            expected_stderr=(
                f"correction-candidates: --out {str(out)!r} already exists -- refusing to overwrite; pass a new path\n"
            ),
        )
        assert out.read_text() == "precious\n"

    def test_an_out_inside_a_real_git_work_tree_exits_2(
        self, fake_projects, tmp_path, monkeypatch, capsys, real_git_check, mode_flags,
    ):
        repo = init_git_repo_with_commit(tmp_path / "repo")
        out = repo / "run.jsonl"

        status, stdout, stderr = run_main(monkeypatch, capsys, "--projects", "*", "--out", str(out), *mode_flags)

        self._assert_refused(status, stdout, stderr)
        assert stderr.startswith(f"correction-candidates: --out {str(out)!r} is inside a git working tree")
        assert not out.exists()

    def test_an_out_in_a_missing_directory_exits_2(self, fake_projects, tmp_path, monkeypatch, capsys, mode_flags):
        out = tmp_path / "no-such-directory" / "run.jsonl"

        result = run_main(monkeypatch, capsys, "--projects", "*", "--out", str(out), *mode_flags)

        self._assert_refused(
            *result,
            expected_stderr=(
                f"correction-candidates: --out {str(out)!r} is not in an existing directory"
                " -- create the directory first\n"
            ),
        )
        assert not out.parent.exists()

    def test_this_repo_outside_a_checkout_exits_1_with_scopes_own_line(
        self, fake_projects, tmp_path, out_dir, monkeypatch, capsys, mode_flags,
    ):
        monkeypatch.chdir(tmp_path)
        out = out_dir / "run.jsonl"

        status, stdout, stderr = run_main(monkeypatch, capsys, "--this-repo", "--out", str(out), *mode_flags)

        self._assert_refused(status, stdout, stderr, expected_status=1)
        assert stderr.startswith("correction-candidates: cannot determine repo scope")
        assert not out.exists()

    def test_this_repo_with_a_config_dir_holding_none_of_its_directories_exits_1_with_scopes_own_line(
        self, tmp_path, out_dir, monkeypatch, capsys, mode_flags,
    ):
        config_dir = tmp_path / "other-account"
        (config_dir / "projects").mkdir(parents=True)
        monkeypatch.setattr(scope, "_repo_scoped_project_slugs", lambda *args, **kwargs: ["-no-such-slug"])
        out = out_dir / "run.jsonl"

        status, stdout, stderr = run_main(
            monkeypatch, capsys, "--this-repo", "--out", str(out), *mode_flags, top_level=("--config-dir", str(config_dir)),
        )

        self._assert_refused(status, stdout, stderr, expected_status=1)
        assert stderr.startswith("correction-candidates: --this-repo matched zero project directories under --config-dir")
        assert not out.exists()

    def test_a_multi_level_projects_glob_under_two_roots_exits_2_with_scopes_own_line(
        self, tmp_path, out_dir, monkeypatch, capsys, mode_flags,
    ):
        _two_declared_roots(tmp_path, monkeypatch)
        out = out_dir / "run.jsonl"

        status, stdout, stderr = run_main(monkeypatch, capsys, "--projects", "a/b", "--out", str(out), *mode_flags)

        self._assert_refused(status, stdout, stderr)
        assert stderr.startswith("correction-candidates: --projects: ")
        assert not out.exists()


class TestPublishFailure:
    def test_a_link_failure_after_the_scan_exits_2_and_leaves_no_file(self, fake_projects, out_dir, monkeypatch, capsys):
        seed(fake_projects, question_session())
        out = out_dir / "run.jsonl"

        def failing_link(*args, **kwargs):
            raise OSError("link refused")

        monkeypatch.setattr(os, "link", failing_link)

        status, stdout, stderr = run_main(monkeypatch, capsys, "--projects", "*", "--out", str(out))

        assert status == 2
        assert stdout == ""
        assert len(stderr.splitlines()) == 2
        assert stderr.splitlines()[0].startswith(_HEADER_PREFIX)
        assert "could not be published" in stderr.splitlines()[1]
        assert list(out_dir.iterdir()) == []

    def test_a_destination_that_appears_mid_scan_exits_2_and_is_left_unchanged(
        self, fake_projects, out_dir, monkeypatch, capsys,
    ):
        seed(fake_projects, question_session())
        out = out_dir / "run.jsonl"
        real_resolve = scope._resolve_project_scope

        def resolve_then_squat(*args, **kwargs):
            sessions, label = real_resolve(*args, **kwargs)

            def squatting_sessions():
                yield from sessions
                out.write_text("squatter\n")

            return squatting_sessions(), label

        monkeypatch.setattr(scope, "_resolve_project_scope", resolve_then_squat)

        status, stdout, stderr = run_main(monkeypatch, capsys, "--projects", "*", "--out", str(out))

        assert status == 2
        assert stdout == ""
        assert len(stderr.splitlines()) == 2
        assert stderr.splitlines()[0].startswith(_HEADER_PREFIX)
        assert out.read_text() == "squatter\n"
        assert [path.name for path in out_dir.iterdir()] == ["run.jsonl"]


class TestPreview:
    def test_preview_prints_the_header_and_families_on_stderr_and_creates_nothing(
        self, fake_projects, tmp_path, monkeypatch, capsys,
    ):
        seed(fake_projects, question_session())
        before = sorted(tmp_path.rglob("*"))

        status, stdout, stderr = run_main(monkeypatch, capsys, "--projects", "*", "--preview")

        assert status == 0
        assert stdout == ""
        header, families_line = stderr.splitlines()
        assert header.startswith(_HEADER_PREFIX)
        assert families_line.startswith(_FAMILIES_PREFIX)
        assert families_of(stderr) == {"-home-user-testrepo": 1}
        assert sorted(tmp_path.rglob("*")) == before

    def test_preview_families_equal_the_scope_records_even_when_a_window_excludes_every_record(
        self, fake_projects, out_dir, monkeypatch, capsys,
    ):
        seed(fake_projects, question_session(), "one.jsonl")
        seed(fake_projects, question_session(minute=10), "two.jsonl")
        seed(fake_projects.parent / "-home-user-other", question_session())
        seed(fake_projects.parent / "-home-user-quiet", [assistant_text("only agent text", timestamp=ts(1))])
        out = out_dir / "run.jsonl"
        expected_families = {"-home-user-other": 1, "-home-user-quiet": 1, "-home-user-testrepo": 2}

        _status, _stdout, preview_stderr = run_main(monkeypatch, capsys, "--projects", "*", "--preview")
        _status, _stdout, windowed_preview_stderr = run_main(
            monkeypatch, capsys, "--projects", "*", "--since", "2030-01-01", "--truncate-chars", "5", "--preview",
        )
        run_main(monkeypatch, capsys, "--projects", "*", "--since", "2030-01-01", "--out", str(out))

        scope_record = written_lines(out)[0]
        assert families_of(preview_stderr) == families_of(windowed_preview_stderr) == expected_families
        assert scope_record["families"] == expected_families
        assert scope_record["counts"]["prompts"] == scope_record["counts"]["questions"] == 0

    def test_a_zero_session_preview_warns_once(self, fake_projects, monkeypatch, capsys):
        status, stdout, stderr = run_main(monkeypatch, capsys, "--projects", "*-no-such-repo*", "--preview")

        assert status == 0
        assert stdout == ""
        assert [line for line in stderr.splitlines() if "warning" in line] == [
            "correction-candidates: warning: no session matched this scope;"
            " check that the checkout's directory name holds the repo name",
        ]


class TestRun:
    def test_run_prints_only_the_path_on_stdout_and_writes_a_private_file(self, fake_projects, out_dir, monkeypatch, capsys):
        seed(fake_projects, question_session())
        out = out_dir / "run.jsonl"

        status, stdout, _stderr = run_main(monkeypatch, capsys, "--projects", "*", "--out", str(out))

        assert status == 0
        assert stdout == f"{out}\n"
        assert stat.S_IMODE(out.stat().st_mode) == 0o600

    def test_the_path_prints_after_the_publish_and_before_the_families_and_counts_lines(
        self, fake_projects, out_dir, monkeypatch,
    ):
        seed(fake_projects, question_session())
        out = out_dir / "run.jsonl"
        writes = record_streams(monkeypatch)
        real_publish = ledger_common._publish_new_owner_file

        def recording_publish(*args, **kwargs):
            writes.append(("publish", ""))
            return real_publish(*args, **kwargs)

        monkeypatch.setattr(ledger_common, "_publish_new_owner_file", recording_publish)
        monkeypatch.setattr(
            sys, "argv", ["transcript-analysis.py", "correction-candidates", "--projects", "*", "--out", str(out)],
        )

        cli.main()

        def label(stream: str, text: str) -> str:
            prefixes = {"stderr": ((_HEADER_PREFIX, "header"), (_FAMILIES_PREFIX, "families"), (_COUNTS_PREFIX, "counts"))}
            return next((name for prefix, name in prefixes.get(stream, ()) if text.startswith(prefix)), stream)

        events = [label(stream, text) for stream, text in writes if text != "\n"]
        assert events == ["header", "publish", "stdout", "families", "counts"]

    def test_stderr_holds_the_header_the_families_line_and_the_counts_line_at_one_root(
        self, fake_projects, out_dir, monkeypatch, capsys,
    ):
        seed(fake_projects, question_session())
        out = out_dir / "run.jsonl"

        _status, _stdout, stderr = run_main(monkeypatch, capsys, "--projects", "*", "--out", str(out))

        header, families_line, counts_line = stderr.splitlines()
        assert header.startswith(_HEADER_PREFIX)
        assert stderr.isascii()
        assert families_line.startswith(_FAMILIES_PREFIX)
        record = written_lines(out)[0]
        assert record["header"] == header
        counts_payload = json.loads(counts_line.removeprefix(_COUNTS_PREFIX))
        assert counts_payload == {"counts": record["counts"], "checks": record["checks"]}

    def test_stderr_at_two_roots_holds_the_header_a_scanning_line_per_root_then_families_and_counts(
        self, tmp_path, out_dir, monkeypatch, capsys,
    ):
        _first_root, second_root = _two_declared_roots(tmp_path, monkeypatch)
        seed(second_root / _REPO_FAMILY, question_session())
        out = out_dir / "run.jsonl"

        status, _stdout, stderr = run_main(monkeypatch, capsys, "--projects", "*-workflow-gates*", "--out", str(out))

        assert status == 0
        header, first_root_line, second_root_line, families_line, counts_line = stderr.splitlines()
        assert "2 roots" in header
        assert (first_root_line, second_root_line) == ("scanning root 1/2...", "scanning root 2/2...")
        assert families_line.startswith(_FAMILIES_PREFIX)
        assert counts_line.startswith(_COUNTS_PREFIX)
        lines = written_lines(out)
        assert lines[0]["families"] == {_REPO_FAMILY: 1}
        assert [line["kind"] for line in lines] == ["scope", "prompt", "question"]

    def test_cross_session_duplicates_do_not_inflate_the_emitted_line_count_per_kind(
        self, fake_projects, out_dir, monkeypatch, capsys,
    ):
        seed(fake_projects, question_session(), "sess-a.jsonl")
        seed(fake_projects, question_session(), "sess-b.jsonl")
        out = out_dir / "run.jsonl"

        run_main(monkeypatch, capsys, "--projects", "*", "--out", str(out))

        lines = written_lines(out)
        scope_record = lines[0]
        assert sum(1 for line in lines if line["kind"] == "prompt") == scope_record["counts"]["prompts"] == 1
        assert sum(1 for line in lines if line["kind"] == "question") == scope_record["counts"]["questions"] == 1
        assert scope_record["counts"]["skipped"]["duplicate_prompt"] == 1
        assert scope_record["counts"]["skipped"]["duplicate_question"] == 1

    def test_the_window_flags_reach_the_scope_record_and_filter_by_day(self, fake_projects, out_dir, monkeypatch, capsys):
        seed(fake_projects, [*question_session(), prompt("a later day", 1, day=21)])
        out = out_dir / "run.jsonl"

        run_main(monkeypatch, capsys, "--projects", "*", "--until", "2026-05-19", "--since", "2026-05-01", "--out", str(out))

        lines = written_lines(out)
        assert (lines[0]["since"], lines[0]["until"], lines[0]["truncate_chars"]) == ("2026-05-01", "2026-05-19", 2000)
        assert [line["text"] for line in lines if line["kind"] == "prompt"] == ["please fix the thing"]

    def test_a_record_at_the_start_of_the_since_day_is_emitted_and_one_a_millisecond_earlier_is_not(
        self, fake_projects, out_dir, monkeypatch, capsys,
    ):
        seed(fake_projects, [
            with_fields(prompt("just in", 0), timestamp="2026-05-15T00:00:00.000Z", uuid="in"),
            with_fields(prompt("just out", 0), timestamp="2026-05-14T23:59:59.999Z", uuid="out"),
        ])
        out = out_dir / "run.jsonl"

        run_main(monkeypatch, capsys, "--projects", "*", "--since", "2026-05-15", "--out", str(out))

        assert [line["text"] for line in written_lines(out) if line["kind"] == "prompt"] == ["just in"]

    def test_until_alone_counts_an_undated_record_as_undated(self, fake_projects, out_dir, monkeypatch, capsys):
        seed(fake_projects, [with_fields(prompt("no clock", 0), timestamp=None, uuid="u")])
        out = out_dir / "run.jsonl"

        run_main(monkeypatch, capsys, "--projects", "*", "--until", "2026-05-19", "--out", str(out))

        scope_record = written_lines(out)[0]
        assert scope_record["counts"]["skipped"]["undated"] == 1
        assert scope_record["counts"]["prompts"] == 0

    def test_a_timestamp_past_the_utc_range_is_emitted_with_a_null_timestamp_and_the_run_exits_0(
        self, fake_projects, out_dir, monkeypatch, capsys,
    ):
        seed(fake_projects, [with_fields(prompt("far away", 0), timestamp="9999-12-31T23:59:59-14:00", uuid="u")])
        out = out_dir / "run.jsonl"

        status, _stdout, _stderr = run_main(monkeypatch, capsys, "--projects", "*", "--out", str(out))

        assert status == 0
        assert [line["timestamp"] for line in written_lines(out) if line["kind"] == "prompt"] == [None]

    def test_truncate_chars_cuts_a_long_prompt_text_and_leaves_its_id_whole(self, fake_projects, out_dir, monkeypatch, capsys):
        seed(fake_projects, [prompt("abcdefghijklmnop", 1)], "a-long-session-file-name.jsonl")
        out = out_dir / "run.jsonl"

        run_main(monkeypatch, capsys, "--projects", "*", "--truncate-chars", "5", "--out", str(out))

        scope_record, prompt_line = written_lines(out)
        assert prompt_line["text"] == "abcde… (truncated, 16 chars total)"
        assert prompt_line["id"] == "a-long-session-file-name:0"
        assert scope_record["truncate_chars"] == 5
        assert scope_record["checks"]["truncated_fields"] == {"text": 1}

    def test_a_slash_prompt_is_written_with_its_args_and_command(self, fake_projects, out_dir, monkeypatch, capsys):
        seed(fake_projects, [with_fields(slash_invocation("plan-it", "draft the plan"), timestamp=ts(1), uuid="s1")])
        out = out_dir / "run.jsonl"

        run_main(monkeypatch, capsys, "--projects", "*", "--out", str(out))

        scope_record, prompt_line = written_lines(out)
        assert (prompt_line["text"], prompt_line["command"]) == ("draft the plan", "/plan-it")
        assert scope_record["counts"]["slash_prompts"] == 1

    def test_non_ascii_directory_prompt_and_answer_text_round_trip_through_an_ascii_file_and_ascii_stderr(
        self, tmp_path, out_dir, monkeypatch, capsys,
    ):
        projects = tmp_path / "projects"
        monkeypatch.setattr(scope, "PROJECTS_DIR", projects)
        seed(projects / "-home-user-café", [
            prompt("café ☕ please", 1),
            ask_record([question_spec("Quelle?", ("Oui", "Non"))], minute=2),
            ask_answer_record(answers={"Quelle?": "Ünïcode answer"}, timestamp=ts(3)),
        ])
        out = out_dir / "run.jsonl"

        _status, _stdout, stderr = run_main(monkeypatch, capsys, "--projects", "*", "--out", str(out))

        assert out.read_bytes().isascii()
        assert stderr.isascii()
        scope_record, prompt_line, question_line = written_lines(out)
        assert prompt_line["text"] == "café ☕ please"
        assert question_line["questions"][0]["answer"] == "Ünïcode answer"
        assert families_of(stderr) == scope_record["families"]
        assert any("caf" in family for family in scope_record["families"])

    def test_a_zero_session_run_exits_0_warns_once_and_writes_only_the_scope_record(
        self, fake_projects, out_dir, monkeypatch, capsys,
    ):
        out = out_dir / "run.jsonl"

        status, _stdout, stderr = run_main(monkeypatch, capsys, "--projects", "*-no-such-repo*", "--out", str(out))

        assert status == 0
        assert len([line for line in stderr.splitlines() if "warning" in line]) == 1
        lines = written_lines(out)
        assert [line["kind"] for line in lines] == ["scope"]
        assert lines[0]["checks"]["failed_relations"] == []

    def test_a_main_and_a_worktree_directory_share_one_family(self, tmp_path, out_dir, monkeypatch, capsys):
        projects = tmp_path / "projects"
        monkeypatch.setattr(scope, "PROJECTS_DIR", projects)
        seed(projects / _REPO_FAMILY, question_session())
        seed(projects / f"{_REPO_FAMILY}--claude-worktrees-feature", question_session(minute=10))
        out = out_dir / "run.jsonl"

        run_main(monkeypatch, capsys, "--projects", "*workflow-gates*", "--out", str(out))

        assert written_lines(out)[0]["families"] == {_REPO_FAMILY: 2}

    def test_generated_at_is_the_time_of_the_run_in_utc(self, fake_projects, out_dir, monkeypatch, capsys):
        seed(fake_projects, question_session())
        out = out_dir / "run.jsonl"

        run_main(monkeypatch, capsys, "--projects", "*", "--out", str(out))

        generated_at = datetime.fromisoformat(written_lines(out)[0]["generated_at"])
        assert generated_at.utcoffset() == timedelta(0)
        assert abs(datetime.now(UTC) - generated_at) < timedelta(minutes=5)


class TestSubagentFiles:
    def test_a_subagent_file_beside_a_main_session_adds_no_line_and_no_count(
        self, fake_projects, out_dir, monkeypatch, capsys,
    ):
        seed(fake_projects, question_session())
        seed(fake_projects / "sess" / "subagents", [prompt(_SUBAGENT_CANARY, 9, uuid="subagent-uuid")], "agent-1.jsonl")
        out = out_dir / "run.jsonl"

        run_main(monkeypatch, capsys, "--projects", "*", "--out", str(out))

        assert _SUBAGENT_CANARY not in out.read_text(encoding="ascii")
        scope_record, prompt_line, question_line = written_lines(out)
        assert prompt_line["text"] == "please fix the thing"
        assert question_line["questions"][0]["answer"] == "Alpha"
        assert (scope_record["counts"]["prompts"], scope_record["counts"]["questions"]) == (1, 1)
        assert scope_record["families"] == {"-home-user-testrepo": 1}


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
        assert all(
            canary in file_text for name, canary in _CANARIES.items() if name not in _CANARIES_IN_KEYS_NO_OUTPUT_READS
        )
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
        assert stderr.isascii()
        assert "\x1b" not in stderr
        assert [line.startswith(_FAMILIES_PREFIX) for line in stderr.splitlines()].count(True) == 1
        assert len(stderr.splitlines()) == 2


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
        assert header.startswith(_HEADER_PREFIX)
        assert abort_line == _ABORT_LINE.format(name=aborting_scan)
        _assert_no_canary_outside_the_file(stderr)
        assert list(out_dir.iterdir()) == []

    def test_a_preview_exits_1_with_no_families_line(self, aborting_scan, monkeypatch, capsys):
        status, stdout, stderr = run_main(monkeypatch, capsys, "--projects", "*", "--preview")

        assert status == 1
        assert stdout == ""
        assert _FAMILIES_PREFIX not in stderr
        assert stderr.splitlines(keepends=True)[1] == _ABORT_LINE.format(name=aborting_scan)
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
        assert stderr.splitlines(keepends=True)[-1] == _ABORT_LINE.format(name="RecursionError")
        assert "Traceback" not in stderr
        assert _FAMILIES_PREFIX not in stderr
        assert list(out_dir.iterdir()) == []

    def test_a_preview_exits_1_with_no_families_line(self, nested_line_project, monkeypatch, capsys):
        status, stdout, stderr = run_main(monkeypatch, capsys, "--projects", "*", "--preview")

        assert status == 1
        assert stdout == ""
        assert stderr.splitlines(keepends=True)[-1] == _ABORT_LINE.format(name="RecursionError")
        assert "Traceback" not in stderr
        assert _FAMILIES_PREFIX not in stderr
