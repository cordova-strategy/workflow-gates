"""A `--branches` prefilter that skips a session unparsed never changes the stdout of a command that passes it,
except that `cost --summary`'s `PRICING INTEGRITY` banner can print less."""
from pathlib import Path

import pytest
from helpers import stub_git_worktree_listing, worktree_porcelain
from transcript_analysis import cli, corpus, pricing, review_rounds, review_trace, scope

from .conftest import (
    _agent_use,
    _asst,
    _attr_ts,
    _priced,
    _priced_sidechain_asst,
    _skill_use,
    _skill_use_rec,
    _user_msg,
    _write_jsonl,
    _write_subagent_jsonl,
)

_MODEL = "claude-sonnet-5"
_FILTERED_BRANCH = "feature-x"
_PRICING_BANNER = "PRICING INTEGRITY"

_COMMANDS_BY_CASE = {
    "cost-summary": ["cost", "--this-repo", "--branches", _FILTERED_BRANCH, "--summary"],
    "cost-counts": ["cost-counts", "--this-repo", "--branches", _FILTERED_BRANCH],
    "skill-invocation": ["skill-invocation", "--branches", _FILTERED_BRANCH, "--include-subagents"],
    "review-trace": ["review-trace", "--this-repo", "--branches", _FILTERED_BRANCH, "--omit-plan-review-spawns"],
}


def _write_session(project_dir: Path, session_id: str, records: list[dict]) -> None:
    project_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(project_dir / f"{session_id}.jsonl", records)


def _session_id_of(path: Path, root: Path) -> str:
    """The session id a main or subagent transcript path under `root` belongs to."""
    return path.relative_to(root).parts[1].removesuffix(".jsonl")


def _run_command(argv: list[str], capsys, monkeypatch) -> tuple[int | str | None, str]:
    """Run one subcommand through `build_parser()`; returns its exit status (0 on a normal return) and stdout.

    Both drift flags in pricing.py stay set within one test, so each run resets them first.
    """
    monkeypatch.setattr(pricing, "_usage_drift_warned", False)
    monkeypatch.setattr(pricing, "_subagent_format_drift_detected", False)
    args = cli.build_parser().parse_args(argv)
    exit_status: int | str | None = 0
    try:
        args.func(args)
    except SystemExit as exc:
        exit_status = exc.code
    return exit_status, capsys.readouterr().out


def _force_every_session_to_be_parsed(monkeypatch) -> None:
    """The prefilter-off oracle: every session `may_carry` is asked about is kept."""
    monkeypatch.setattr(corpus._BranchPrefilter, "may_carry", lambda self, jsonl, include_subagents: True)


class _ReadSpies:
    """`parsed` sees every `corpus._parse_jsonl_records` call. `read` sees only `_iter_project_dir_sessions`'
    reads, which `_build_redact_map`'s own parse of every directory cannot satisfy."""

    def __init__(self, monkeypatch) -> None:
        self.parsed: list[Path] = []
        self.read: list[Path] = []
        real_parse = corpus._parse_jsonl_records
        real_read = scope._read_session_file_partitioned

        def spy_parse(jsonl):
            self.parsed.append(jsonl)
            return real_parse(jsonl)

        def spy_read(jsonl, include_subagents):
            self.read.append(jsonl)
            return real_read(jsonl, include_subagents)

        monkeypatch.setattr(corpus, "_parse_jsonl_records", spy_parse)
        monkeypatch.setattr(scope, "_read_session_file_partitioned", spy_read)


@pytest.fixture()
def prefilter_corpus(fake_projects, stub_repo_tracked_agent_types, monkeypatch):
    """The root `fake_projects` patches in, holding four sessions that tell the prefilter's decisions apart."""
    stub_repo_tracked_agent_types()
    stub_git_worktree_listing(monkeypatch, worktree_porcelain("/repo/main"), "/repo/main", "/repo/main")
    root = fake_projects.parent
    main_dir = root / "-repo-main"
    removed_worktree_dir = root / "-repo-main--claude-worktrees-gone"

    _write_session(removed_worktree_dir, "s-feature", [
        _priced(_MODEL, input=1_000_000, branch=_FILTERED_BRANCH, ts=_attr_ts(0)),
        _skill_use_rec("code-review", _attr_ts(1), branch=_FILTERED_BRANCH, tool_id="skill-1"),
        _asst(
            _MODEL, branch=_FILTERED_BRANCH, ts=_attr_ts(2),
            content=[_agent_use("spawn-1", "general-purpose")],
        ),
    ])
    _write_subagent_jsonl(removed_worktree_dir, "s-feature", "agent-1", [
        _priced_sidechain_asst(_MODEL, input_tokens=400_000, ts=_attr_ts(3), branch=_FILTERED_BRANCH),
    ])

    # Its first gitBranch field is `main`, so only cost --summary's pre-branch credit makes it carry the filtered branch.
    _write_session(main_dir, "s-prefix", [
        _priced(_MODEL, input=500_000, branch="main", ts=_attr_ts(0)),
        _priced(_MODEL, input=600_000, branch=_FILTERED_BRANCH, ts=_attr_ts(5)),
    ])

    # The filtered branch sits only in a subagent file, in a record with no isSidechain flag.
    _write_session(main_dir, "s-subagent-only", [
        _priced(_MODEL, input=100_000, branch="main", ts=_attr_ts(0)),
    ])
    flagless_subagent_record = _priced(
        _MODEL, input=700_000, branch=_FILTERED_BRANCH, ts=_attr_ts(6),
        content=[_skill_use("skill-2", "code-review"), _agent_use("spawn-2", "general-purpose")],
    )
    flagless_subagent_record.pop("isSidechain")
    _write_subagent_jsonl(main_dir, "s-subagent-only", "agent-1", [flagless_subagent_record])

    # Names the filtered branch in message text and in a cwd, but in no gitBranch field.
    priced_record_in_worktree_cwd = _priced(_MODEL, input=300_000, branch="other-branch", ts=_attr_ts(1))
    priced_record_in_worktree_cwd["cwd"] = f"/repo/main/.claude/worktrees/{_FILTERED_BRANCH}"
    _write_session(main_dir, "s-other", [
        _user_msg(f"working on {_FILTERED_BRANCH}", branch="other-branch", ts=_attr_ts(0)),
        priced_record_in_worktree_cwd,
        _skill_use_rec("code-review", _attr_ts(2), branch="other-branch", tool_id="skill-3"),
        _asst(_MODEL, branch="other-branch", ts=_attr_ts(3), content=[_agent_use("spawn-3", "general-purpose")]),
    ])
    _write_subagent_jsonl(main_dir, "s-other", "agent-1", [
        _priced_sidechain_asst(_MODEL, input_tokens=200_000, ts=_attr_ts(4), branch="other-branch"),
    ])
    return root


@pytest.mark.parametrize("case", list(_COMMANDS_BY_CASE))
def test_prefiltered_output_equals_the_prefilter_off_output(prefilter_corpus, monkeypatch, capsys, case):
    spies = _ReadSpies(monkeypatch)

    shipped_status, shipped_stdout = _run_command(_COMMANDS_BY_CASE[case], capsys, monkeypatch)
    shipped_parsed = list(spies.parsed)
    shipped_read = list(spies.read)
    _force_every_session_to_be_parsed(monkeypatch)
    off_status, off_stdout = _run_command(_COMMANDS_BY_CASE[case], capsys, monkeypatch)

    assert (shipped_status, shipped_stdout) == (off_status, off_stdout), (
        f"{case}: the prefiltered run's exit status or stdout differs from the prefilter-off run's"
    )
    parsed_s_other_paths = [p for p in shipped_parsed if _session_id_of(p, prefilter_corpus) == "s-other"]
    assert parsed_s_other_paths == [], f"{case}: the prefiltered run parsed s-other through {parsed_s_other_paths}"
    assert shipped_status == 0, f"{case}: the prefiltered run exited {shipped_status}"
    assert any(_session_id_of(p, prefilter_corpus) == "s-feature" for p in shipped_read), (
        f"{case}: the prefiltered run never read s-feature, so equal outputs may both be empty"
    )


@pytest.mark.parametrize(
    "argv",
    [
        ["cost", "--this-repo", "--branches", _FILTERED_BRANCH],
        ["cost", "--this-repo", "--branches", _FILTERED_BRANCH, "--summary", "--since", "3650d"],
    ],
    ids=["full-report", "summary-since"],
)
def test_cost_parses_every_session_outside_summary_or_under_since(prefilter_corpus, monkeypatch, capsys, argv):
    spies = _ReadSpies(monkeypatch)

    status, _stdout = _run_command(argv, capsys, monkeypatch)

    assert status == 0
    assert any(_session_id_of(p, prefilter_corpus) == "s-other" for p in spies.read), (
        f"{argv}: the run skipped s-other, whose branches the exclusions table or --since coverage warning read"
    )


@pytest.mark.parametrize(
    ("case", "branch", "banner_expected"),
    [
        ("denied-dispatch", "other-branch", False),
        ("branch-own-drift", _FILTERED_BRANCH, True),
        ("kept-usage-drift", _FILTERED_BRANCH, True),
    ],
)
def test_summary_banner_prints_only_where_the_prefilter_off_run_prints_it(
    fake_projects, stub_repo_tracked_agent_types, monkeypatch, capsys, case, branch, banner_expected,
):
    stub_repo_tracked_agent_types()
    stub_git_worktree_listing(monkeypatch, worktree_porcelain("/repo/main"), "/repo/main", "/repo/main")
    root = fake_projects.parent
    main_dir = root / "-repo-main"
    removed_worktree_dir = root / "-repo-main--claude-worktrees-gone"
    spawn = [_agent_use("spawn-1", "general-purpose")]
    if case == "denied-dispatch":
        # A spawn on one branch whose dispatch a hook denied, so no subagent turn exists, and a sidechain turn on another.
        # The sidechain turn sits in a subagent file under a skipped session, as real ones do.
        # The prefilter-off arm still carries the banner suppression (it derives from the filter, not from `may_carry`),
        # so the hardcoded `banner_expected` is what pins the re-read.
        _write_session(main_dir, "s-other", [
            _priced(_MODEL, input=1_000_000, branch="other-branch", ts=_attr_ts(0), content=spawn),
        ])
        _write_session(removed_worktree_dir, "s-feature", [
            _priced(_MODEL, input=1_000, branch=_FILTERED_BRANCH, ts=_attr_ts(1)),
        ])
        _write_subagent_jsonl(removed_worktree_dir, "s-feature", "agent-1", [
            _priced_sidechain_asst(_MODEL, input_tokens=1_000, ts=_attr_ts(2), branch=_FILTERED_BRANCH),
        ])
    elif case == "branch-own-drift":
        _write_session(removed_worktree_dir, "s-feature", [
            _priced(_MODEL, input=1_000_000, branch=_FILTERED_BRANCH, ts=_attr_ts(0), content=spawn),
        ])
        _write_session(main_dir, "s-other", [
            _priced(_MODEL, input=1_000, branch="other-branch", ts=_attr_ts(1)),
        ])
    else:
        # A kept session whose one requestId run disagrees with itself on input_tokens, with no spawn,
        # so the usage-drift canary is the only thing that can raise the banner.
        _write_session(removed_worktree_dir, "s-feature", [
            _priced(_MODEL, input=1_000, branch=_FILTERED_BRANCH, ts=_attr_ts(0), request_id="req-1"),
            _priced(_MODEL, input=2_000, branch=_FILTERED_BRANCH, ts=_attr_ts(1), request_id="req-1"),
        ])
        _write_session(main_dir, "s-other", [
            _priced(_MODEL, input=1_000, branch="other-branch", ts=_attr_ts(2)),
        ])
    argv = ["cost", "--this-repo", "--branches", branch, "--summary"]

    shipped_status, shipped_stdout = _run_command(argv, capsys, monkeypatch)
    _force_every_session_to_be_parsed(monkeypatch)
    off_status, off_stdout = _run_command(argv, capsys, monkeypatch)

    assert (shipped_status, off_status) == (0, 0)
    assert (_PRICING_BANNER in off_stdout) is banner_expected, f"{case}: the prefilter-off run's banner"
    assert (_PRICING_BANNER in shipped_stdout) is banner_expected, f"{case}: the prefiltered run's banner"


def test_summary_banner_ignores_usage_drift_in_a_session_the_spawn_re_read_passes_over(
    fake_projects, stub_repo_tracked_agent_types, monkeypatch, capsys,
):
    """The re-read tests raw records, so it never dedups the skipped session whose requestId run disagrees with itself."""
    stub_repo_tracked_agent_types()
    stub_git_worktree_listing(monkeypatch, worktree_porcelain("/repo/main"), "/repo/main", "/repo/main")
    root = fake_projects.parent
    main_dir = root / "-repo-main"
    removed_worktree_dir = root / "-repo-main--claude-worktrees-gone"
    kept_branch = "other-branch"
    # The kept session holds a spawn and no subagent turn, so the re-read runs; the skipped one carries the sidechain turn.
    _write_session(main_dir, "s-other", [
        _priced(_MODEL, input=1_000_000, branch=kept_branch, ts=_attr_ts(0), content=[_agent_use("spawn-1", "general-purpose")]),
    ])
    _write_session(removed_worktree_dir, "s-feature", [
        _priced(_MODEL, input=1_000, branch=_FILTERED_BRANCH, ts=_attr_ts(1), request_id="req-1"),
        _priced(_MODEL, input=2_000, branch=_FILTERED_BRANCH, ts=_attr_ts(2), request_id="req-1"),
    ])
    _write_subagent_jsonl(removed_worktree_dir, "s-feature", "agent-1", [
        _priced_sidechain_asst(_MODEL, input_tokens=1_000, ts=_attr_ts(3), branch=_FILTERED_BRANCH),
    ])
    argv = ["cost", "--this-repo", "--branches", kept_branch, "--summary"]

    shipped_status, shipped_stdout = _run_command(argv, capsys, monkeypatch)
    _force_every_session_to_be_parsed(monkeypatch)
    off_status, off_stdout = _run_command(argv, capsys, monkeypatch)

    assert (shipped_status, off_status) == (0, 0)
    assert _PRICING_BANNER in off_stdout, "the prefilter-off run parses s-feature, so its usage drift must raise the banner"
    assert _PRICING_BANNER not in shipped_stdout, "the shipped run's re-read dedups s-feature, a session the filter skipped"


def _write_attribution_session(project_dir: Path, shape: str) -> Path:
    """One session per shape, each tagged record carrying a `code-review` Skill call so review-trace yields an event."""
    jsonl = project_dir / "s.jsonl"
    project_dir.mkdir(parents=True, exist_ok=True)
    if shape == "default-run-with-successor":
        _write_jsonl(jsonl, [
            _skill_use_rec("code-review", _attr_ts(0), branch="main", tool_id="skill-1"),
            _skill_use_rec("code-review", _attr_ts(1), branch=_FILTERED_BRANCH, tool_id="skill-2"),
        ])
    elif shape == "sidechain-own-tag":
        _write_jsonl(jsonl, [_skill_use_rec("code-review", _attr_ts(0), branch=_FILTERED_BRANCH, tool_id="skill-1")])
        _write_subagent_jsonl(project_dir, "s", "agent-1", [
            _skill_use_rec("code-review", _attr_ts(1), branch="worktree-agent-x", tool_id="skill-2", sidechain=True),
        ])
    elif shape == "subagent-file-without-sidechain-flag":
        _write_jsonl(jsonl, [_skill_use_rec("code-review", _attr_ts(0), branch="main", tool_id="skill-1")])
        flagless_subagent_record = _skill_use_rec("code-review", _attr_ts(1), branch="feat-sub", tool_id="skill-2")
        flagless_subagent_record.pop("isSidechain")
        _write_subagent_jsonl(project_dir, "s", "agent-1", [flagless_subagent_record])
    else:
        _write_jsonl(jsonl, [{"type": "user", "message": {"content": "no branch tag"}}])
        _write_subagent_jsonl(project_dir, "s", "agent-1", [
            _asst(_MODEL, branch="worktree-agent-x", sidechain=True, ts=_attr_ts(1)),
        ])
    return jsonl


@pytest.mark.parametrize(
    "shape",
    ["default-run-with-successor", "sidechain-own-tag", "subagent-file-without-sidechain-flag", "no-main-tag"],
)
def test_attributed_branches_are_tags_from_the_sessions_own_records(tmp_path, shape):
    """The prefilter is sound only while every branch a `--branches` filter can match is a `gitBranch` string
    from the session's own records."""
    jsonl = _write_attribution_session(tmp_path / "-repo-main", shape)
    records, group_boundaries = review_trace._fresh_records_and_group_boundaries(jsonl, [], include_subagents=True)
    branch_context = scope._session_branch_context(records)
    own_tags = {rec["gitBranch"] for rec in records if rec.get("gitBranch")}
    events, _tool_use_commands, _pre_regime = review_trace._review_trace_session_events(
        records, None, None, None, group_boundaries=group_boundaries,
    )
    if shape != "no-main-tag":
        assert events, f"{shape}: review-trace yielded no event, so its branch leg would pass empty"

    record_level_branches = {scope._attributed_branch(rec, branch_context) for rec in records}
    record_level_branches |= set(review_rounds._session_record_branches(records, []))
    for branch in sorted(b for b in record_level_branches if b):
        assert branch in own_tags, f"{shape}: {branch!r} is no record's gitBranch"
        assert corpus._branch_prefilter({branch}).may_carry(jsonl, True) is True, f"{shape}: {branch!r} skipped"

    event_branches = {event["branch"] for event in events if event["branch"] != corpus.UNTAGGED_BRANCH_LABEL}
    for branch in sorted(event_branches):
        assert branch in own_tags, f"{shape}: event branch {branch!r} is no record's gitBranch"
        assert corpus._branch_prefilter({branch}).may_carry(jsonl, True) is True, f"{shape}: {branch!r} skipped"
