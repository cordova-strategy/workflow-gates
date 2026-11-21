"""Tests for transcript_analysis/sessions.py's cmd_sessions, reached through the real parser."""
import pytest
from transcript_analysis import cli, corpus

from .conftest import _asst, _write_jsonl, _write_subagent_dispatch, _write_subagent_jsonl


def test_sessions_without_paths_exits_2_and_emits_no_path(fake_projects, capsys):
    """The seeded transcript would reach stdout if the refusal ran after the emission loop."""
    _write_jsonl(fake_projects / "sess.jsonl", [_asst("claude-sonnet-5")])
    args = cli.build_parser().parse_args(["sessions"])

    with pytest.raises(SystemExit) as exit_info:
        args.func(args)

    captured = capsys.readouterr()
    assert exit_info.value.code == 2
    assert "--paths is required" in captured.err
    assert captured.out == ""


@pytest.mark.parametrize(
    ("argv", "expected_relative_paths"),
    [
        (["sessions", "--paths"], ["sess.jsonl", "tail.jsonl"]),
        (
            ["sessions", "--paths", "--include-subagents"],
            ["sess.jsonl", "sess/subagents/agent-probe.jsonl", "tail.jsonl"],
        ),
    ],
    ids=["paths", "paths-include-subagents"],
)
def test_sessions_paths_emits_subagent_paths_only_under_include_subagents(
    fake_projects, capsys, argv, expected_relative_paths
):
    """--include-subagents prints direct subagent transcripts only, not their sidecars or workflow-nested files.

    That case shows the seeded subagent file would print, so the plain case cannot pass vacuously.
    The orphan subagent directory has no main transcript, so it must not print in either case.
    The tail session sorts after the session with subagents.
    It has no subagents directory, so it prints only its own transcript.
    """
    _write_jsonl(fake_projects / "sess.jsonl", [_asst("claude-sonnet-5")])
    _write_jsonl(fake_projects / "tail.jsonl", [_asst("claude-sonnet-5")])
    _write_subagent_dispatch(
        fake_projects, "sess", "agent-probe", "toolu_probe", [_asst("claude-sonnet-5", sidechain=True)]
    )
    _write_subagent_jsonl(fake_projects, "orphan", "agent-orphan", [_asst("claude-sonnet-5", sidechain=True)])
    workflow_dir = fake_projects / "sess" / corpus.SUBAGENT_SUBDIR / "workflows" / "wf_probe"
    workflow_dir.mkdir(parents=True)
    _write_jsonl(workflow_dir / "agent-nested.jsonl", [_asst("claude-sonnet-5", sidechain=True)])
    args = cli.build_parser().parse_args(argv)

    args.func(args)

    captured = capsys.readouterr()
    assert captured.out.splitlines() == [str(fake_projects / path) for path in expected_relative_paths]
    assert "SESSIONS SOURCES (*; " in captured.err


def test_sessions_paths_include_subagents_prints_main_then_subagent_files_in_sorted_order(fake_projects, capsys):
    """Subagent files written out of sorted order print sorted, and an empty one still prints.

    The reader drops an empty subagent file from its merge, so printing it is the documented difference.
    """
    _write_jsonl(fake_projects / "sess.jsonl", [_asst("claude-sonnet-5")])
    _write_subagent_jsonl(fake_projects, "sess", "agent-beta", [_asst("claude-sonnet-5", sidechain=True)])
    _write_subagent_jsonl(fake_projects, "sess", "agent-alpha", [_asst("claude-sonnet-5", sidechain=True)])
    (fake_projects / "sess" / corpus.SUBAGENT_SUBDIR / "agent-gamma-empty.jsonl").touch()
    args = cli.build_parser().parse_args(["sessions", "--paths", "--include-subagents"])

    args.func(args)

    captured = capsys.readouterr()
    assert captured.out.splitlines() == [
        str(fake_projects / relative_path)
        for relative_path in (
            "sess.jsonl",
            "sess/subagents/agent-alpha.jsonl",
            "sess/subagents/agent-beta.jsonl",
            "sess/subagents/agent-gamma-empty.jsonl",
        )
    ]
