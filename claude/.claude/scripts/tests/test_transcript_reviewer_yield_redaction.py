"""Tests for `reviewer-yield --redact`: untracked agent types print as agent-type-<N> in both tables."""
import sys

import pytest
from transcript_analysis import cli, redaction, reviewer_yield

from .conftest import (
    _agent_use,
    _asst,
    _reviewer_yield_args,
    _table_cols,
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
ZERO_FINDING_VERDICT = "**No concerns**"
FINDINGS_FOUND_VERDICT = "Found 1 issue in /synthetic/module.py needing a fix"
ZERO_FINDING_BUCKET = "zero-finding"
FINDINGS_FOUND_BUCKET = "findings-found"
FIRST_TABLE, SECOND_TABLE = 1, 2


def _seed_dispatches(project_dir, verdicts_by_agent_type: dict[str, list[str]]) -> None:
    """One session dispatching each agent type once per listed verdict text, each with its own subagent transcript."""
    dispatches = [
        (agent_type, verdict) for agent_type, verdicts in verdicts_by_agent_type.items() for verdict in verdicts
    ]
    _write_jsonl(project_dir / "sess.jsonl", [
        _asst("claude-opus-4-7", ts="2026-05-19T10:00:00.000Z", content=[
            _agent_use(f"a{position}", agent_type) for position, (agent_type, _verdict) in enumerate(dispatches)
        ]),
    ])
    for position, (agent_type, verdict) in enumerate(dispatches):
        _write_subagent_dispatch(
            project_dir, "sess", f"agent-a{position}", f"a{position}",
            [_asst("claude-sonnet-4-6", sidechain=True, content=[{"type": "text", "text": verdict}])],
            agent_type=agent_type,
        )


def _type_row_dispatches(out: str, label: str, *, table: int, bucket: str | None = None) -> str:
    """The Dispatches cell of `label`'s row in one `AgentType` table, so a label is bound to its type by dispatch count."""
    row_contains = label if bucket is None else [label, bucket]
    cols = _table_cols(
        out, header_contains="AgentType", row_contains=row_contains, row_startswith=True, occurrence=table,
    )
    return cols["Dispatches"]


@pytest.fixture
def tracked_and_untracked_dispatches(fake_projects, stub_repo_tracked_agent_types):
    """One tracked type with a single dispatch, and one untracked type with a dispatch in each of two verdict buckets."""
    stub_repo_tracked_agent_types(TRACKED_AGENT_TYPE)
    _seed_dispatches(fake_projects, {
        TRACKED_AGENT_TYPE: [ZERO_FINDING_VERDICT],
        UNTRACKED_AGENT_TYPE: [ZERO_FINDING_VERDICT, FINDINGS_FOUND_VERDICT],
    })


def _assert_redacted_output(out: str) -> None:
    """The tracked type keeps its name and the untracked type is `agent-type-1`, in both tables and both buckets."""
    assert _type_row_dispatches(out, TRACKED_AGENT_TYPE, table=FIRST_TABLE) == "1"
    assert _type_row_dispatches(out, "agent-type-1", table=FIRST_TABLE) == "2"
    assert _type_row_dispatches(out, TRACKED_AGENT_TYPE, table=SECOND_TABLE, bucket=ZERO_FINDING_BUCKET) == "1"
    assert _type_row_dispatches(out, "agent-type-1", table=SECOND_TABLE, bucket=ZERO_FINDING_BUCKET) == "1"
    assert _type_row_dispatches(out, "agent-type-1", table=SECOND_TABLE, bucket=FINDINGS_FOUND_BUCKET) == "1"
    assert UNTRACKED_AGENT_TYPE not in out


def _assert_raw_output(out: str) -> None:
    """Both types print under their own names in both tables and both buckets, with no label."""
    assert _type_row_dispatches(out, TRACKED_AGENT_TYPE, table=FIRST_TABLE) == "1"
    assert _type_row_dispatches(out, UNTRACKED_AGENT_TYPE, table=FIRST_TABLE) == "2"
    assert _type_row_dispatches(out, TRACKED_AGENT_TYPE, table=SECOND_TABLE, bucket=ZERO_FINDING_BUCKET) == "1"
    assert _type_row_dispatches(out, UNTRACKED_AGENT_TYPE, table=SECOND_TABLE, bucket=ZERO_FINDING_BUCKET) == "1"
    assert _type_row_dispatches(out, UNTRACKED_AGENT_TYPE, table=SECOND_TABLE, bucket=FINDINGS_FOUND_BUCKET) == "1"
    assert "agent-type-" not in out


class TestReviewerYieldRedact:
    def test_redact_prints_a_tracked_type_raw_and_an_untracked_type_as_a_label_in_both_tables(
        self, tracked_and_untracked_dispatches, capsys,
    ):
        reviewer_yield.cmd_reviewer_yield(_reviewer_yield_args(redact=True))

        _assert_redacted_output(capsys.readouterr().out)

    def test_without_redact_both_types_print_raw_in_both_tables(self, tracked_and_untracked_dispatches, capsys):
        reviewer_yield.cmd_reviewer_yield(_reviewer_yield_args(redact=False))

        _assert_raw_output(capsys.readouterr().out)


class TestReviewerYieldRedactThroughMain:
    def test_redact_flag_parsed_by_the_cli_hides_an_untracked_type_from_stdout(
        self, tracked_and_untracked_dispatches, monkeypatch, capsys,
    ):
        monkeypatch.setattr(sys, "argv", ["transcript-analysis.py", "reviewer-yield", "--redact"])

        cli.main()

        _assert_redacted_output(capsys.readouterr().out)

    def test_without_the_flag_the_cli_prints_the_untracked_type_raw(
        self, tracked_and_untracked_dispatches, monkeypatch, capsys,
    ):
        monkeypatch.setattr(sys, "argv", ["transcript-analysis.py", "reviewer-yield"])

        cli.main()

        _assert_raw_output(capsys.readouterr().out)


class TestReviewerYieldRedactLabelIdentity:
    def test_two_untracked_types_around_a_tracked_one_keep_one_label_each_across_both_tables(
        self, fake_projects, stub_repo_tracked_agent_types, capsys,
    ):
        stub_repo_tracked_agent_types(TRACKED_AGENT_TYPE_BETWEEN)
        # Distinct dispatch counts bind each printed label to its raw type: 1 before, 2 between, 3 after.
        _seed_dispatches(fake_projects, {
            UNTRACKED_AGENT_TYPE_AFTER: [ZERO_FINDING_VERDICT, ZERO_FINDING_VERDICT, FINDINGS_FOUND_VERDICT],
            TRACKED_AGENT_TYPE_BETWEEN: [ZERO_FINDING_VERDICT, ZERO_FINDING_VERDICT],
            UNTRACKED_AGENT_TYPE_BEFORE: [ZERO_FINDING_VERDICT],
        })

        reviewer_yield.cmd_reviewer_yield(_reviewer_yield_args(redact=True))

        out = capsys.readouterr().out
        assert _type_row_dispatches(out, "agent-type-1", table=FIRST_TABLE) == "1"
        assert _type_row_dispatches(out, TRACKED_AGENT_TYPE_BETWEEN, table=FIRST_TABLE) == "2"
        assert _type_row_dispatches(out, "agent-type-2", table=FIRST_TABLE) == "3"
        assert _type_row_dispatches(out, "agent-type-1", table=SECOND_TABLE, bucket=ZERO_FINDING_BUCKET) == "1"
        assert _type_row_dispatches(out, TRACKED_AGENT_TYPE_BETWEEN, table=SECOND_TABLE, bucket=ZERO_FINDING_BUCKET) == "2"
        assert _type_row_dispatches(out, "agent-type-2", table=SECOND_TABLE, bucket=ZERO_FINDING_BUCKET) == "2"
        assert _type_row_dispatches(out, "agent-type-2", table=SECOND_TABLE, bucket=FINDINGS_FOUND_BUCKET) == "1"
        assert UNTRACKED_AGENT_TYPE_BEFORE not in out
        assert UNTRACKED_AGENT_TYPE_AFTER not in out

    def test_a_failed_tracked_set_lookup_labels_every_reviewer_type(
        self, fake_projects, tmp_path, monkeypatch, capsys,
    ):
        """Every reviewer type name is outside the built-in set, so an unavailable git lookup must hide all of them."""
        _seed_dispatches(fake_projects, {
            TRACKED_AGENT_TYPE: [ZERO_FINDING_VERDICT],
            UNTRACKED_AGENT_TYPE: [ZERO_FINDING_VERDICT, FINDINGS_FOUND_VERDICT],
        })
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
        assert _type_row_dispatches(out, "agent-type-1", table=FIRST_TABLE) == "1"
        assert _type_row_dispatches(out, "agent-type-2", table=FIRST_TABLE) == "2"
        assert _type_row_dispatches(out, "agent-type-1", table=SECOND_TABLE, bucket=ZERO_FINDING_BUCKET) == "1"
        assert _type_row_dispatches(out, "agent-type-2", table=SECOND_TABLE, bucket=FINDINGS_FOUND_BUCKET) == "1"
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
        _seed_dispatches(active_project, {TRACKED_AGENT_TYPE: [ZERO_FINDING_VERDICT]})
        _seed_dispatches(declared_project, {UNTRACKED_AGENT_TYPE: [ZERO_FINDING_VERDICT]})

        reviewer_yield.cmd_reviewer_yield(_reviewer_yield_args(redact=False))
        raw_out = capsys.readouterr().out
        reviewer_yield.cmd_reviewer_yield(_reviewer_yield_args(redact=True))
        redacted_out = capsys.readouterr().out

        # The raw run shows the declared root was scanned, so the redacted run's absence is not vacuous.
        assert _type_row_dispatches(raw_out, UNTRACKED_AGENT_TYPE, table=FIRST_TABLE) == "1"
        assert _type_row_dispatches(redacted_out, "agent-type-1", table=FIRST_TABLE) == "1"
        assert _type_row_dispatches(redacted_out, "agent-type-1", table=SECOND_TABLE, bucket=ZERO_FINDING_BUCKET) == "1"
        assert _type_row_dispatches(redacted_out, TRACKED_AGENT_TYPE, table=FIRST_TABLE) == "1"
        assert UNTRACKED_AGENT_TYPE not in redacted_out


class TestReviewerYieldRawAgentTypeControlCharacters:
    def test_a_raw_agent_type_with_control_characters_cannot_forge_a_table_row(
        self, fake_projects, stub_repo_tracked_agent_types, capsys,
    ):
        stub_repo_tracked_agent_types(TRACKED_AGENT_TYPE)
        _seed_dispatches(fake_projects, {"staff-synthetic\nforged-row\x1b[31mwidget": [ZERO_FINDING_VERDICT]})

        reviewer_yield.cmd_reviewer_yield(_reviewer_yield_args(redact=False))

        out = capsys.readouterr().out
        sanitized_label = "staff-syntheticforged-row[31mwidget"
        assert _table_cols(
            out, header_contains="AgentType", row_contains=sanitized_label, row_startswith=True, occurrence=FIRST_TABLE,
        )["Dispatches"] == "1"
        assert _table_cols(
            out, header_contains="AgentType", row_contains=[sanitized_label, ZERO_FINDING_BUCKET],
            row_startswith=True, occurrence=SECOND_TABLE,
        )["Dispatches"] == "1"
        assert "\x1b" not in out

    def test_a_control_character_twin_of_a_real_type_prints_its_own_row_with_its_own_counts(
        self, fake_projects, stub_repo_tracked_agent_types, capsys,
    ):
        """Two raw types that sanitize to one label are not merged: each keeps its own counts under the shared label."""
        stub_repo_tracked_agent_types(TRACKED_AGENT_TYPE)
        _seed_dispatches(fake_projects, {
            UNTRACKED_AGENT_TYPE: [ZERO_FINDING_VERDICT],
            f"{UNTRACKED_AGENT_TYPE}\x00": [FINDINGS_FOUND_VERDICT, FINDINGS_FOUND_VERDICT],
        })

        reviewer_yield.cmd_reviewer_yield(_reviewer_yield_args(redact=False))

        out = capsys.readouterr().out
        yield_table = out.split("## Reviewer-agent cited-path edit overlap")[0]
        # _table_cols requires a unique row, so the shared-label rows of the first table are read directly.
        shared_label_rows = [line.split() for line in yield_table.splitlines() if line.startswith(UNTRACKED_AGENT_TYPE)]
        assert [row[1] for row in shared_label_rows] == ["1", "2"]
        assert _type_row_dispatches(
            out, UNTRACKED_AGENT_TYPE, table=SECOND_TABLE, bucket=ZERO_FINDING_BUCKET,
        ) == "1"
        assert _type_row_dispatches(
            out, UNTRACKED_AGENT_TYPE, table=SECOND_TABLE, bucket=FINDINGS_FOUND_BUCKET,
        ) == "2"
        assert "\x00" not in out
