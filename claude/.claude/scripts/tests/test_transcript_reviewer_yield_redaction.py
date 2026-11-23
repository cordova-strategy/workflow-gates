"""Tests for `reviewer-yield --redact`: untracked agent types print as agent-type-<N> in both tables."""
import sys

import pytest
from transcript_analysis import cli, redaction, reviewer_yield

from .conftest import (
    _agent_use,
    _asst,
    _reviewer_yield_args,
    _two_declared_roots,
    _write_jsonl,
    _write_subagent_dispatch,
)

TRACKED_AGENT_TYPE = "ciso-reviewer"
UNTRACKED_AGENT_TYPE = "staff-synthetic-widget"
# These two untracked names sort before and after TRACKED_AGENT_TYPE_BETWEEN, so each one's label depends on sorted position.
UNTRACKED_AGENT_TYPE_BEFORE = "staff-alpha-widget"
UNTRACKED_AGENT_TYPE_AFTER = "staff-zeta-widget"
TRACKED_AGENT_TYPE_BETWEEN = "staff-middle-tracked"


def _seed_zero_finding_dispatches(project_dir, agent_types) -> None:
    """One session dispatching each agent type once, each with a zero-finding verdict, so every type has one row per table."""
    _write_jsonl(project_dir / "sess.jsonl", [
        _asst("claude-opus-4-7", ts="2026-05-19T10:00:00.000Z", content=[
            _agent_use(f"a{position}", agent_type) for position, agent_type in enumerate(agent_types)
        ]),
    ])
    for position, agent_type in enumerate(agent_types):
        _write_subagent_dispatch(
            project_dir, "sess", f"agent-a{position}", f"a{position}",
            [_asst("claude-sonnet-4-6", sidechain=True, content=[{"type": "text", "text": "**No concerns**"}])],
            agent_type=agent_type,
        )


def _agent_type_column(out: str, printed_names: set[str]) -> list[str]:
    """The first-column value of every table row whose first token is one of `printed_names`, in print order."""
    return [line.split()[0] for line in out.splitlines() if line.split() and line.split()[0] in printed_names]


@pytest.fixture
def tracked_and_untracked_dispatches(fake_projects, stub_repo_tracked_agent_types):
    """One session that dispatches one tracked and one untracked reviewer type, each with a zero-finding verdict."""
    stub_repo_tracked_agent_types(TRACKED_AGENT_TYPE)
    _seed_zero_finding_dispatches(fake_projects, [TRACKED_AGENT_TYPE, UNTRACKED_AGENT_TYPE])


class TestReviewerYieldRedact:
    def test_redact_prints_a_tracked_type_raw_and_an_untracked_type_as_a_label_in_both_tables(
        self, tracked_and_untracked_dispatches, capsys,
    ):
        reviewer_yield.cmd_reviewer_yield(_reviewer_yield_args(redact=True))

        out = capsys.readouterr().out
        # Each type prints one row per table, so a type appears twice only if both tables carry it.
        assert out.count(TRACKED_AGENT_TYPE) == 2
        assert out.count("agent-type-1") == 2
        assert UNTRACKED_AGENT_TYPE not in out

    def test_without_redact_both_types_print_raw_in_both_tables(self, tracked_and_untracked_dispatches, capsys):
        reviewer_yield.cmd_reviewer_yield(_reviewer_yield_args(redact=False))

        out = capsys.readouterr().out
        assert out.count(TRACKED_AGENT_TYPE) == 2
        assert out.count(UNTRACKED_AGENT_TYPE) == 2
        assert "agent-type-" not in out


class TestReviewerYieldRedactThroughMain:
    def test_redact_flag_parsed_by_the_cli_hides_an_untracked_type_from_stdout(
        self, tracked_and_untracked_dispatches, monkeypatch, capsys,
    ):
        monkeypatch.setattr(sys, "argv", ["transcript-analysis.py", "reviewer-yield", "--redact"])

        cli.main()

        captured = capsys.readouterr()
        # Each type prints one row per table, so the counts show capture works and both tables carry the type.
        assert captured.out.count(TRACKED_AGENT_TYPE) == 2
        assert captured.out.count("agent-type-1") == 2
        assert UNTRACKED_AGENT_TYPE not in captured.out

    def test_without_the_flag_the_cli_prints_the_untracked_type_raw(
        self, tracked_and_untracked_dispatches, monkeypatch, capsys,
    ):
        monkeypatch.setattr(sys, "argv", ["transcript-analysis.py", "reviewer-yield"])

        cli.main()

        assert capsys.readouterr().out.count(UNTRACKED_AGENT_TYPE) == 2


class TestReviewerYieldRedactLabelIdentity:
    def test_two_untracked_types_around_a_tracked_one_keep_one_label_each_across_both_tables(
        self, fake_projects, stub_repo_tracked_agent_types, capsys,
    ):
        stub_repo_tracked_agent_types(TRACKED_AGENT_TYPE_BETWEEN)
        _seed_zero_finding_dispatches(
            fake_projects, [UNTRACKED_AGENT_TYPE_AFTER, TRACKED_AGENT_TYPE_BETWEEN, UNTRACKED_AGENT_TYPE_BEFORE],
        )

        reviewer_yield.cmd_reviewer_yield(_reviewer_yield_args(redact=True))

        out = capsys.readouterr().out
        printed_names = {"agent-type-1", "agent-type-2", TRACKED_AGENT_TYPE_BETWEEN}
        # Rows follow raw sort order: untracked-before, tracked, untracked-after, in each of the two tables.
        assert _agent_type_column(out, printed_names) == ["agent-type-1", TRACKED_AGENT_TYPE_BETWEEN, "agent-type-2"] * 2
        assert UNTRACKED_AGENT_TYPE_BEFORE not in out
        assert UNTRACKED_AGENT_TYPE_AFTER not in out

    def test_a_failed_tracked_set_lookup_labels_every_reviewer_type(
        self, fake_projects, tmp_path, monkeypatch, capsys,
    ):
        """Every reviewer type name is outside the built-in set, so an unavailable git lookup must hide all of them."""
        _seed_zero_finding_dispatches(fake_projects, [TRACKED_AGENT_TYPE, UNTRACKED_AGENT_TYPE])
        with monkeypatch.context() as patched:
            patched.setattr(redaction, "_REPO_AGENT_DEFINITIONS_DIR", tmp_path / "missing-agents-dir")
            redaction._repo_tracked_agent_type_names.cache_clear()
            try:
                reviewer_yield.cmd_reviewer_yield(_reviewer_yield_args(redact=True))
            finally:
                # Clear while the patch is still live, then again after it is undone, so no entry computed
                # under the missing directory outlives this test.
                redaction._repo_tracked_agent_type_names.cache_clear()
        redaction._repo_tracked_agent_type_names.cache_clear()

        out = capsys.readouterr().out
        assert _agent_type_column(out, {"agent-type-1", "agent-type-2"}) == ["agent-type-1", "agent-type-2"] * 2
        assert TRACKED_AGENT_TYPE not in out
        assert UNTRACKED_AGENT_TYPE not in out

    def test_an_untracked_type_found_only_under_a_declared_root_is_labelled(
        self, tmp_path, monkeypatch, stub_repo_tracked_agent_types, capsys,
    ):
        active_projects, declared_projects = _two_declared_roots(tmp_path, monkeypatch)
        stub_repo_tracked_agent_types(TRACKED_AGENT_TYPE)
        active_project = active_projects / "-home-user-testrepo"
        declared_project = declared_projects / "-home-user-otherrepo"
        active_project.mkdir()
        declared_project.mkdir()
        _seed_zero_finding_dispatches(active_project, [TRACKED_AGENT_TYPE])
        _seed_zero_finding_dispatches(declared_project, [UNTRACKED_AGENT_TYPE])

        reviewer_yield.cmd_reviewer_yield(_reviewer_yield_args(redact=False))
        raw_out = capsys.readouterr().out
        reviewer_yield.cmd_reviewer_yield(_reviewer_yield_args(redact=True))
        redacted_out = capsys.readouterr().out

        # The raw run shows the declared root was scanned, so the redacted run's absence is not vacuous.
        assert raw_out.count(UNTRACKED_AGENT_TYPE) == 2
        assert redacted_out.count("agent-type-1") == 2
        assert redacted_out.count(TRACKED_AGENT_TYPE) == 2
        assert UNTRACKED_AGENT_TYPE not in redacted_out
