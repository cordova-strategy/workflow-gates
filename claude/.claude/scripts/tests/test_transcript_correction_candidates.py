"""cmd_correction_candidates and its subparser: wiring, refusals, preview and the written file.

The canary and abort tests are in test_transcript_correction_candidates_canaries_and_aborts.py."""
import json
import os
import stat
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from helpers import init_git_repo_with_commit
from transcript_analysis import cli, correction_candidates, ledger_common, scope

from . import _correction_candidates_helpers as candidates_helpers
from ._compaction_context_helpers import slash_invocation
from ._correction_candidates_helpers import (
    BANNER,
    FAMILIES_PREFIX,
    HEADER_PREFIX,
    ask_answer_record,
    ask_record,
    assistant_text,
    prompt,
    question_session,
    question_spec,
    record_streams,
    run_main,
    seed,
    ts,
    with_fields,
    written_lines,
)
from .conftest import _two_declared_roots

_SCOPE_ERROR = "correction-candidates: pass --projects GLOB or --this-repo (--projects '*' reads every project on this machine)\n"
_OUT_ERROR = "correction-candidates: pass --out PATH (a new file outside any git work tree) or --preview\n"
_ZERO_PADDED = "must be a zero-padded YYYY-MM-DD date\n"
_REVERSED_WINDOW_ARGS = ["--since", "2026-05-02", "--until", "2026-05-01"]
_FAR_REVERSED_WINDOW_ARGS = ["--since", "2026-05-10", "--until", "2026-05-01"]
_REVERSED_WINDOW_ERROR = "correction-candidates: --since must not be after --until\n"
_COUNTS_PREFIX = "correction-candidates: counts "
_REPO_FAMILY = "-home-example-src-workflow-gates"
_SUBAGENT_CANARY = "CANARY-SUBAGENT-DISPATCH-PROMPT"
_UNPADDED_SINCE = ["--since", "2026-5-09"]
_UNPADDED_SINCE_ERROR = f"correction-candidates: --since {_ZERO_PADDED}"


# The fixtures live once in the helper module. An import would trip F811 on every test parameter that names one.
real_git_check = candidates_helpers.real_git_check
stubbed_git_check = candidates_helpers.stubbed_git_check
out_dir = candidates_helpers.out_dir


def families_of(stderr: str) -> dict:
    (families_line,) = [line for line in stderr.splitlines() if line.startswith(FAMILIES_PREFIX)]
    return json.loads(families_line.removeprefix(FAMILIES_PREFIX))


class TestStderrLinePrefixes:
    """The abort tests assert these prefixes are absent, so a prefix that drifts from the command's output must fail here."""

    def test_the_command_prints_the_banner_then_a_line_starting_with_the_families_prefix(self, capsys):
        correction_candidates._stderr_families_line({"-home-example-src-repo": 1})

        banner, families_line = capsys.readouterr().err.splitlines()
        assert banner == BANNER
        assert families_line.startswith(FAMILIES_PREFIX)


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

    def test_help_states_that_a_scope_flag_is_required(self, monkeypatch, capsys):
        status, stdout, _stderr = run_main(monkeypatch, capsys, "--help")

        assert status == 0
        assert "Scope is required" in stdout

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

    def test_a_one_day_window_with_equal_since_and_until_runs(self, fake_projects, out_dir, monkeypatch, capsys):
        seed(fake_projects, question_session())
        out = out_dir / "run.jsonl"

        status, _stdout, _stderr = run_main(
            monkeypatch, capsys, "--projects", "*", "--since", "2026-05-19", "--until", "2026-05-19", "--out", str(out),
        )

        assert status == 0
        assert written_lines(out)[0]["counts"]["prompts"] == 1


class TestRefusals:
    @pytest.fixture(params=[(), ("--preview",)], ids=["run", "preview"])
    def mode_flags(self, request) -> tuple[str, ...]:
        return request.param

    def _assert_refused(self, status, stdout, stderr, *, expected_stderr=None, expected_status=2):
        assert status == expected_status
        assert stdout == ""
        assert HEADER_PREFIX not in stderr
        assert FAMILIES_PREFIX not in stderr
        assert BANNER not in stderr
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

    @pytest.mark.parametrize(
        "reversed_window_args", [_REVERSED_WINDOW_ARGS, _FAR_REVERSED_WINDOW_ARGS], ids=["adjacent-day", "multi-day"],
    )
    def test_a_since_after_until_exits_2_with_one_line_that_echoes_no_date(
        self, fake_projects, out_dir, monkeypatch, capsys, mode_flags, reversed_window_args,
    ):
        seed(fake_projects, question_session())
        out = out_dir / "run.jsonl"

        result = run_main(monkeypatch, capsys, "--projects", "*", *reversed_window_args, "--out", str(out), *mode_flags)

        self._assert_refused(*result, expected_stderr=_REVERSED_WINDOW_ERROR)
        assert not out.exists()

    def test_a_non_integer_truncate_chars_exits_2_with_argparses_usage_and_error(
        self, fake_projects, out_dir, monkeypatch, capsys, mode_flags,
    ):
        out = out_dir / "run.jsonl"

        status, stdout, stderr = run_main(
            monkeypatch, capsys, "--projects", "*", "--truncate-chars", "abc", "--out", str(out), *mode_flags,
        )

        self._assert_refused(status, stdout, stderr)
        assert "usage:" in stderr
        assert "argument --truncate-chars: not an integer: 'abc'" in stderr
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
            pytest.param(
                ["--projects", "*"], False, _REVERSED_WINDOW_ARGS, _REVERSED_WINDOW_ERROR,
                id="reversed-window-before-neither-out-nor-preview",
            ),
            pytest.param(
                ["--projects", "*"], True, _REVERSED_WINDOW_ARGS, _REVERSED_WINDOW_ERROR,
                id="reversed-window-before-an-existing-out",
            ),
            pytest.param([], False, _REVERSED_WINDOW_ARGS, _SCOPE_ERROR, id="no-scope-before-a-reversed-window"),
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
                " -- pass a new path in an existing directory outside any git working tree\n"
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
        assert stderr.splitlines()[0].startswith(HEADER_PREFIX)
        assert "could not be published" in stderr.splitlines()[1]
        assert list(out_dir.iterdir()) == []

    def test_the_publish_temp_name_keeps_the_destinations_jsonl_extension(
        self, fake_projects, out_dir, monkeypatch, capsys,
    ):
        seed(fake_projects, question_session())
        linked_sources: list[str] = []
        real_link = os.link

        def recording_link(src, dst):
            linked_sources.append(Path(src).name)
            real_link(src, dst)

        monkeypatch.setattr(os, "link", recording_link)

        status, _stdout, _stderr = run_main(monkeypatch, capsys, "--projects", "*", "--out", str(out_dir / "run.jsonl"))

        assert status == 0
        (temp_name,) = linked_sources
        assert temp_name.startswith(".correction-candidates-")
        assert temp_name.endswith(".jsonl")

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
        assert stderr.splitlines()[0].startswith(HEADER_PREFIX)
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
        header, banner, families_line = stderr.splitlines()
        assert header.startswith(HEADER_PREFIX)
        assert banner == BANNER
        assert families_line.startswith(FAMILIES_PREFIX)
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

    def test_a_zero_session_warning_names_the_directory_name_hint_only_for_a_projects_glob_that_names_a_repo(self, capsys):
        correction_candidates._warn_when_no_session_matched({}, None)
        correction_candidates._warn_when_no_session_matched({}, "*")
        correction_candidates._warn_when_no_session_matched({}, "*-no-such-repo*")

        assert capsys.readouterr().err.splitlines() == [
            "correction-candidates: warning: no session matched this scope",
            "correction-candidates: warning: no session matched this scope",
            "correction-candidates: warning: no session matched this scope;"
            " check that the checkout's directory name holds the repo name",
        ]


class TestZeroSessionHint:
    """The hint reaches stderr from both command call sites, and only for a `--projects` glob that names a repo."""

    @pytest.fixture(params=["run", "preview"])
    def mode_flags(self, request, out_dir) -> list[str]:
        return ["--out", str(out_dir / "run.jsonl")] if request.param == "run" else ["--preview"]

    @staticmethod
    def _warnings(stderr: str) -> list[str]:
        return [line for line in stderr.splitlines() if "warning" in line]

    def test_a_zero_session_this_repo_prints_no_directory_name_hint(self, fake_projects, monkeypatch, capsys, mode_flags):
        monkeypatch.setattr(scope, "_repo_scoped_project_slugs", lambda *args, **kwargs: [fake_projects.name])
        fake_projects.mkdir(parents=True, exist_ok=True)

        status, _stdout, stderr = run_main(monkeypatch, capsys, "--this-repo", *mode_flags)

        assert status == 0
        assert self._warnings(stderr) == ["correction-candidates: warning: no session matched this scope"]

    def test_a_zero_session_projects_glob_prints_the_directory_name_hint(self, fake_projects, monkeypatch, capsys, mode_flags):
        status, _stdout, stderr = run_main(monkeypatch, capsys, "--projects", "*-no-such-repo*", *mode_flags)

        assert status == 0
        assert self._warnings(stderr) == [
            "correction-candidates: warning: no session matched this scope;"
            " check that the checkout's directory name holds the repo name",
        ]

    def test_a_zero_session_projects_star_prints_no_directory_name_hint(self, fake_projects, monkeypatch, capsys, mode_flags):
        status, _stdout, stderr = run_main(monkeypatch, capsys, "--projects", "*", *mode_flags)

        assert status == 0
        assert self._warnings(stderr) == ["correction-candidates: warning: no session matched this scope"]


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
            prefixes = {
                "stderr": (
                    (HEADER_PREFIX, "header"), (BANNER, "banner"), (FAMILIES_PREFIX, "families"), (_COUNTS_PREFIX, "counts"),
                ),
            }
            return next((name for prefix, name in prefixes.get(stream, ()) if text.startswith(prefix)), stream)

        events = [label(stream, text) for stream, text in writes if text != "\n"]
        assert events == ["header", "publish", "stdout", "banner", "families", "counts"]

    def test_stderr_lines_and_the_scope_record_notice_at_one_root(
        self, fake_projects, out_dir, monkeypatch, capsys,
    ):
        seed(fake_projects, question_session())
        out = out_dir / "run.jsonl"

        _status, _stdout, stderr = run_main(monkeypatch, capsys, "--projects", "*", "--out", str(out))

        header, banner, families_line, counts_line = stderr.splitlines()
        assert header.startswith(HEADER_PREFIX)
        assert banner == BANNER
        assert families_line.startswith(FAMILIES_PREFIX)
        record = written_lines(out)[0]
        assert record["header"] == header
        assert "raw message text" in record["do_not_publish"]
        assert record["do_not_publish"].startswith("DO NOT PUBLISH")
        assert "credentials" in record["do_not_publish"]
        assert "project names" in record["do_not_publish"]
        counts_payload = json.loads(counts_line.removeprefix(_COUNTS_PREFIX))
        assert counts_payload == {"counts": record["counts"], "checks": record["checks"]}

    def test_stderr_at_two_roots_holds_the_header_a_scanning_line_per_root_then_banner_families_and_counts(
        self, tmp_path, out_dir, monkeypatch, capsys,
    ):
        _first_root, second_root = _two_declared_roots(tmp_path, monkeypatch)
        seed(second_root / _REPO_FAMILY, question_session())
        out = out_dir / "run.jsonl"

        status, _stdout, stderr = run_main(monkeypatch, capsys, "--projects", "*-workflow-gates*", "--out", str(out))

        assert status == 0
        header, first_root_line, second_root_line, banner, families_line, counts_line = stderr.splitlines()
        assert "2 roots" in header
        assert (first_root_line, second_root_line) == ("scanning root 1/2...", "scanning root 2/2...")
        assert banner == BANNER
        assert families_line.startswith(FAMILIES_PREFIX)
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
        assert stderr.replace(BANNER, "").isascii()
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

    @pytest.mark.parametrize(
        ("expected_failures", "answer_record"),
        [
            pytest.param([], ask_answer_record(answers={"Which one?": "Alpha"}, timestamp=ts(3)), id="healthy-selected-answer"),
            pytest.param(
                ["answers_read"], ask_answer_record(timestamp=ts(3)), id="answers_read-dict-result-without-answers",
            ),
            pytest.param(
                ["answers_keyed"], ask_answer_record(answers={"Choice": "Alpha"}, timestamp=ts(3)),
                id="answers_keyed-answers-keyed-by-header",
            ),
            pytest.param(
                ["labels_matched"], ask_answer_record(answers={"Which one?": "typed words"}, timestamp=ts(3)),
                id="labels_matched-every-answer-typed",
            ),
        ],
    )
    def test_the_scope_record_names_exactly_the_relations_an_answer_shape_fails(
        self, expected_failures, answer_record, fake_projects, out_dir, monkeypatch, capsys,
    ):
        seed(fake_projects, [
            prompt("please fix the thing", 1),
            ask_record([question_spec("Which one?", ("Alpha", "Beta"), header="Choice")], minute=2),
            answer_record,
        ])
        out = out_dir / "run.jsonl"

        run_main(monkeypatch, capsys, "--projects", "*", "--out", str(out))

        assert written_lines(out)[0]["checks"]["failed_relations"] == expected_failures

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


_OUT_OF_SCOPE_FAMILY = "-home-user-unrelated"
_OUT_OF_SCOPE_PROMPT = "CANARY-OUT-OF-SCOPE-PROMPT"


class TestScopeNarrowing:
    """A narrowed scope reads only its own families: the out-of-scope family stays out of the file and the counts."""

    @pytest.fixture(params=["this-repo", "narrow-glob"])
    def narrowed_scope_args(self, request, fake_projects, monkeypatch) -> list[str]:
        if request.param == "narrow-glob":
            return ["--projects", "*testrepo*"]
        monkeypatch.setattr(scope, "_repo_scoped_project_slugs", lambda *args, **kwargs: [fake_projects.name])
        return ["--this-repo"]

    @pytest.fixture()
    def in_and_out_of_scope_families(self, fake_projects):
        seed(fake_projects, question_session())
        seed(fake_projects.parent / _OUT_OF_SCOPE_FAMILY, [
            prompt(_OUT_OF_SCOPE_PROMPT, 1, uuid="unrelated-prompt"),
            ask_record([question_spec("Unrelated?")], tool_use_id="toolu_unrelated", minute=2),
            ask_answer_record(tool_use_id="toolu_unrelated", answers={"Unrelated?": "Yes"}, timestamp=ts(3)),
        ])

    def test_a_run_leaves_the_out_of_scope_family_out_of_the_families_the_lines_and_the_counts(
        self, in_and_out_of_scope_families, narrowed_scope_args, out_dir, monkeypatch, capsys,
    ):
        out = out_dir / "run.jsonl"

        status, _stdout, stderr = run_main(monkeypatch, capsys, *narrowed_scope_args, "--out", str(out))

        scope_record, *lines = written_lines(out)
        assert status == 0
        assert scope_record["families"] == families_of(stderr) == {"-home-user-testrepo": 1}
        assert {line["family"] for line in lines} == {"-home-user-testrepo"}
        assert _OUT_OF_SCOPE_PROMPT not in out.read_text(encoding="ascii")
        assert (scope_record["counts"]["prompts"], scope_record["counts"]["questions"]) == (1, 1)

    def test_a_preview_lists_only_the_in_scope_family(
        self, in_and_out_of_scope_families, narrowed_scope_args, monkeypatch, capsys,
    ):
        status, _stdout, stderr = run_main(monkeypatch, capsys, *narrowed_scope_args, "--preview")

        assert status == 0
        assert families_of(stderr) == {"-home-user-testrepo": 1}
        assert _OUT_OF_SCOPE_FAMILY not in stderr
