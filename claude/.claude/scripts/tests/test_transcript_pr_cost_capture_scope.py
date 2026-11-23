"""Tests for pr-cost's capture scope and branch-join guard (transcript_analysis/pr_cost.py): the repo-scope
default, the capture_scope a row records, the joinability filter on both entry paths, the --force re-scope
case, and the earliest-surviving-activity cell. Every other pr-cost behavior lives in test_transcript_pr_cost.py."""
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
from transcript_analysis import cli, pr_cost, pr_cost_ledger, review_rounds, scope

from ._pr_cost_helpers import (
    _EMPTY_SCOPE_RESCOPE_HINT,
    _GLOB_RESCOPE_HINT,
    _NOW,
    _SEEDED_MACHINE_IDENTITY,
    _already_captured_line,
    _arrange_record_run,
    _cell_of,
    _enable_pr_cost,
    _fake_pr_cost_subprocess_run,
    _force_refusal_line,
    _ledger_rows,
    _merged_pr,
    _pr_cost_args,
    _run_record,
    _sample_pr_cost_row,
    _spy_on_scans,
)
from .conftest import _priced, _skill_block, _two_declared_roots, _write_jsonl

# Slugs built through scope._path_to_project_slug, so none hand-types the worktree infix.
_MAIN_SLUG = scope._path_to_project_slug("/home/user/repo")
_LIVE_UNDER_PREFIX_SLUG = scope._path_to_project_slug("/home/user/repo/.claude/worktrees/live")
_LIVE_ELSEWHERE_SLUG = scope._path_to_project_slug("/home/user/elsewhere")
_REMOVED_SLUG = scope._path_to_project_slug("/home/user/repo/.claude/worktrees/gone")
_FOREIGN_SLUG = scope._path_to_project_slug("/home/user/foreign-repo")

_SONNET = "claude-sonnet-5"
_FOREIGN_FIRST_TURN_TS = "2026-05-01T08:00:00.000Z"
_IN_REPO_FIRST_TURN_TS = "2026-05-19T10:00:05.500Z"
_IN_REPO_FIRST_TURN_ISO = "2026-05-19T10:00:05Z"

_GUARDED_BRANCH_SKIP_LINE = (
    "pr-cost:   this branch is a default-branch candidate, a detached HEAD or a worktree-agent branch, which the"
    " ledger never joins -- skipped"
)
_FORK_BRANCH_SKIP_LINE = (
    "pr-cost:   every merged PR for this branch is cross-repository, which the ledger never records -- skipped"
)
_PAYLOAD_REFUSAL_LINE = (
    "pr-cost: gh pr list returned merged PRs this checkout cannot join (not a list of objects, each with a boolean"
    " isCrossRepository) -- refusing to join any PR; update gh, and report it if it repeats (see docs/pr-cost.md)"
)
_REASON_LESS_COMPLETE = "the re-capture is less complete under the same round rule"


def _empty_scope_line(for_account: str = "") -> str:
    return f"pr-cost: the repo scope found no priced turn{for_account} -- see docs/pr-cost.md"


def _guarded_head_refusal_line(pr_number: int) -> str:
    return (
        f"pr-cost: PR #{pr_number}'s head branch is a default-branch candidate, a detached HEAD or a worktree-agent"
        " branch, which the ledger never joins -- refusing; see docs/pr-cost.md"
    )


def _fork_refusal_line(pr_number: int) -> str:
    return (
        f"pr-cost: PR #{pr_number} is cross-repository, which the ledger never records -- refusing;"
        " see docs/pr-cost.md"
    )


def _fork_pr(number: int, branch: str, **overrides) -> dict:
    return {**_merged_pr(number, branch), "isCrossRepository": True, **overrides}


def _stub_repo_slugs(monkeypatch) -> None:
    """Resolve this checkout's live worktrees without git: the main worktree, one under .claude/worktrees/, and
    one elsewhere."""
    live_slugs = [_MAIN_SLUG, _LIVE_UNDER_PREFIX_SLUG, _LIVE_ELSEWHERE_SLUG]
    monkeypatch.setattr(scope, "_repo_scoped_project_slugs", lambda command_label="skill-invocation": list(live_slugs))


def _arrange_roots(tmp_path, monkeypatch, *, all_accounts: bool = False, stub_repo_scope: bool = True) -> list[Path]:
    """One or two opted-in account roots, a stubbed repo scope unless stub_repo_scope is false, and no
    PR_COST_LEDGER_PATH, so each account's ledger sits at <root>.parent / pr-cost-ledger.tsv."""
    if all_accounts:
        roots = _two_declared_roots(tmp_path, monkeypatch)
    else:
        single_root = tmp_path / "acct-a" / "projects"
        single_root.mkdir(parents=True)
        monkeypatch.setenv("TRANSCRIPT_CONFIG_DIRS_FILE", str(tmp_path / "no-declared-roots"))
        roots = [single_root]
    for root in roots:
        _enable_pr_cost(root.parent)
    if stub_repo_scope:
        _stub_repo_slugs(monkeypatch)
    return roots


def _write_session(root, slug: str, name: str, records: list[dict]) -> None:
    (root / slug).mkdir(parents=True, exist_ok=True)
    _write_jsonl(root / slug / f"{name}.jsonl", records)


def _branch_turn(branch: str, *, input_tokens: int = 1_000, ts: str = _IN_REPO_FIRST_TURN_TS, skill_id: str | None = None):
    content = [_skill_block(skill_id, "code-review")] if skill_id else None
    return _priced(_SONNET, input=input_tokens, branch=branch, ts=ts, content=content)


def _ledger_path_of(root: Path) -> Path:
    return root.parent / "pr-cost-ledger.tsv"


class TestReviewRoundsForceRescope:
    @pytest.mark.parametrize(
        "prior_cell,new_cell,new_absence,prior_scope,new_scope,is_refused",
        [
            pytest.param(
                _cell_of(1, code_review=[1]), None, "pass-failed", "", "repo", True,
                id="new-cell-empty-refused-even-moving-to-repo",
            ),
            pytest.param(
                _cell_of(2, code_review=[1]), _cell_of(1, code_review=[1]), None, "glob", "repo", True,
                id="lower-rule-refused-even-moving-to-repo",
            ),
            pytest.param(
                _cell_of(1, code_review=[1, 1]), _cell_of(1, code_review=[1]), None, "", "repo", False,
                id="shrink-from-empty-scope-to-repo-allowed",
            ),
            pytest.param(
                _cell_of(1, code_review=[1, 1]), _cell_of(1, code_review=[1]), None, "glob", "repo", False,
                id="shrink-from-glob-to-repo-allowed",
            ),
            pytest.param(
                _cell_of(1, code_review=[1, 1]), _cell_of(1, code_review=[1]), None, "repo", "repo", True,
                id="shrink-within-repo-refused",
            ),
            pytest.param(
                _cell_of(1, code_review=[1, 1]), _cell_of(1, code_review=[1]), None, "repo", "glob", True,
                id="shrink-from-repo-to-glob-refused",
            ),
            pytest.param(
                _cell_of(1, code_review=[1, 1]), _cell_of(1, code_review=[1]), None, "", "glob", True,
                id="shrink-from-empty-scope-to-glob-refused",
            ),
            pytest.param(
                _cell_of(1, code_review=[1]), _cell_of(1, code_review=[1, 1]), None, "repo", "glob", False,
                id="non-shrinking-glob-recapture-over-repo-allowed",
            ),
        ],
    )
    def test_only_a_move_into_the_repo_class_waives_the_same_rule_shrink_guard(
        self, prior_cell, new_cell, new_absence, prior_scope, new_scope, is_refused,
    ):
        reason = pr_cost._review_rounds_force_refusal(
            prior_cell, new_cell, new_absence, None, prior_capture_scope=prior_scope, new_capture_scope=new_scope,
        )

        assert (reason is not None) == is_refused


class TestEarliestSurvivingActivityAt:
    _FIRST_EPOCH = datetime(2026, 5, 19, 10, 0, 5, tzinfo=UTC).timestamp()
    _SECOND_EPOCH = datetime(2026, 6, 1, 0, 0, 0, tzinfo=UTC).timestamp()

    def test_the_smaller_of_two_epochs_in_utc_seconds(self):
        agg = {"session_starts": [(self._SECOND_EPOCH, "later-session"), (self._FIRST_EPOCH, "earlier-session")]}

        assert pr_cost._earliest_surviving_activity_at(agg) == "2026-05-19T10:00:05Z"

    def test_a_fractional_second_truncates_down_and_never_rounds_up(self):
        agg = {"session_starts": [(self._FIRST_EPOCH + 0.999, "only-session")]}

        assert pr_cost._earliest_surviving_activity_at(agg) == "2026-05-19T10:00:05Z"

    def test_an_empty_session_list_gives_an_empty_cell(self):
        assert pr_cost._earliest_surviving_activity_at({"session_starts": []}) == ""


class TestPrIsJoinable:
    @pytest.mark.parametrize("pr,expected", [
        pytest.param({"headRefName": "feature-a", "isCrossRepository": False}, True, id="same-repo-ordinary-head"),
        pytest.param({"headRefName": "feature-a", "isCrossRepository": True}, False, id="cross-repository"),
        pytest.param({"headRefName": "main", "isCrossRepository": False}, False, id="default-branch-head"),
        pytest.param({"headRefName": "worktree-agent-x", "isCrossRepository": False}, False, id="worktree-agent-head"),
    ])
    def test_joinable_only_for_a_same_repository_pr_with_an_ordinary_head(self, pr, expected):
        assert pr_cost._pr_is_joinable(pr) is expected


class TestRequireWellFormedMergedPrs:
    _GOOD_ENTRY = {"number": 1, "headRefName": "feature-a", "isCrossRepository": False}
    _FLAGLESS_ENTRY = {"number": 2, "headRefName": "feature-b"}

    @pytest.mark.parametrize("payload", [
        pytest.param([_GOOD_ENTRY, _FLAGLESS_ENTRY], id="missing-flag"),
        pytest.param([_GOOD_ENTRY, {**_FLAGLESS_ENTRY, "isCrossRepository": None}], id="none-flag"),
        pytest.param([_GOOD_ENTRY, {**_FLAGLESS_ENTRY, "isCrossRepository": "false"}], id="string-flag"),
        pytest.param([_GOOD_ENTRY, {**_FLAGLESS_ENTRY, "isCrossRepository": 0}], id="integer-flag"),
        pytest.param(None, id="none-payload"),
        pytest.param({"number": 1}, id="dict-payload"),
        pytest.param([_GOOD_ENTRY, "not-an-object"], id="entry-that-is-not-a-dict"),
    ])
    def test_a_payload_the_join_guard_cannot_read_exits_1_with_the_payload_line(self, payload, capsys):
        with pytest.raises(SystemExit) as exc_info:
            pr_cost._require_well_formed_merged_prs(payload)

        assert exc_info.value.code == 1
        assert capsys.readouterr().err.splitlines() == [_PAYLOAD_REFUSAL_LINE]

    @pytest.mark.parametrize("payload", [
        pytest.param([_GOOD_ENTRY, {**_GOOD_ENTRY, "number": 2, "isCrossRepository": True}], id="mixed-flags"),
        pytest.param([], id="empty-list"),
    ])
    def test_a_list_of_objects_with_boolean_flags_returns(self, payload, capsys):
        assert pr_cost._require_well_formed_merged_prs(payload) is None
        assert capsys.readouterr().err == ""


class TestPrCostSubparserScopeDefault:
    def test_a_bare_pr_cost_defaults_projects_to_none_and_an_explicit_glob_stays_a_glob(self):
        parser = cli.build_parser()

        bare = parser.parse_args(["pr-cost"])
        explicit_glob = parser.parse_args(["pr-cost", "--projects", "*"])

        assert bare.projects is None
        assert bare.this_repo is False
        assert explicit_glob.projects == "*"


class TestCaptureScopeOfARecordRun:
    @pytest.mark.parametrize("arg_overrides", [
        pytest.param({"projects": None}, id="bare-run"),
        pytest.param({"projects": None, "this_repo": True}, id="explicit-this-repo"),
    ])
    def test_a_repo_scoped_record_reads_live_and_removed_worktrees_skips_a_foreign_directory_and_records_repo(
        self, tmp_path, monkeypatch, capsys, arg_overrides,
    ):
        (root,) = _arrange_roots(tmp_path, monkeypatch)
        _write_session(root, _LIVE_UNDER_PREFIX_SLUG, "live", [
            _branch_turn("feature-a", input_tokens=1_000_000, skill_id="live-skill"),
        ])
        _write_session(root, _REMOVED_SLUG, "gone", [
            _branch_turn("feature-a", input_tokens=2_000_000, ts="2026-05-20T10:00:00.000Z", skill_id="gone-skill"),
        ])
        _write_session(root, _LIVE_ELSEWHERE_SLUG, "elsewhere", [
            _branch_turn("feature-a", input_tokens=4_000_000, ts="2026-05-21T10:00:00.000Z"),
        ])
        _write_session(root, _FOREIGN_SLUG, "foreign", [
            _branch_turn("feature-a", input_tokens=8_000_000, ts=_FOREIGN_FIRST_TURN_TS, skill_id="foreign-skill"),
        ])
        monkeypatch.setattr(subprocess, "run", _fake_pr_cost_subprocess_run(merged_prs=[_merged_pr(1, "feature-a")]))
        spy = _spy_on_scans(monkeypatch)

        pr_cost._pr_cost_report(_pr_cost_args(record=True, **arg_overrides), _NOW, [root])

        (row,) = _ledger_rows(_ledger_path_of(root))
        assert row["capture_scope"] == pr_cost_ledger._PR_COST_CAPTURE_SCOPE_REPO
        assert row["input_tokens"] == 7_000_000, "the foreign directory's 8M-token session must stay out"
        assert row["session_count"] == 3
        assert len(row["review_rounds"]["rounds"]["code-review"]) == 2
        assert row["earliest_surviving_activity_at"] == _IN_REPO_FIRST_TURN_ISO
        assert len(spy.scope_calls) == 2
        assert [call["this_repo"] for call in spy.scope_calls] == [True, True]
        assert [call["include_removed_worktrees"] for call in spy.scope_calls] == [True, True]
        assert _empty_scope_line() not in capsys.readouterr().err

    @pytest.mark.parametrize("projects_glob", [
        pytest.param("*", id="machine-wide-glob"),
        pytest.param(_LIVE_ELSEWHERE_SLUG, id="glob-matching-only-this-repositorys-directory"),
    ])
    def test_an_explicit_projects_glob_records_glob_and_resolves_both_scans_without_the_repo_arm(
        self, tmp_path, monkeypatch, projects_glob,
    ):
        (root,) = _arrange_roots(tmp_path, monkeypatch)
        _write_session(root, _LIVE_ELSEWHERE_SLUG, "elsewhere", [_branch_turn("feature-a")])
        monkeypatch.setattr(subprocess, "run", _fake_pr_cost_subprocess_run(merged_prs=[_merged_pr(1, "feature-a")]))
        spy = _spy_on_scans(monkeypatch)

        pr_cost._pr_cost_report(_pr_cost_args(record=True, projects=projects_glob), _NOW, [root])

        (row,) = _ledger_rows(_ledger_path_of(root))
        assert row["capture_scope"] == pr_cost_ledger._PR_COST_CAPTURE_SCOPE_GLOB
        assert [call["this_repo"] for call in spy.scope_calls] == [False, False]

    def test_a_bare_record_exits_1_before_any_write_when_git_cannot_list_the_worktrees(
        self, tmp_path, monkeypatch,
    ):
        (root,) = _arrange_roots(tmp_path, monkeypatch, stub_repo_scope=False)
        ledger_path = _ledger_path_of(root)
        pr_cost_ledger._write_pr_cost_ledger_file(ledger_path, [_sample_pr_cost_row(pr_number=50)])
        before_bytes = ledger_path.read_bytes()
        fake_run = _fake_pr_cost_subprocess_run(merged_prs=[_merged_pr(1, "feature-a")])

        def run_with_a_failing_worktree_list(cmd, *args, **kwargs):
            if cmd == ["git", "worktree", "list", "--porcelain"]:
                raise subprocess.CalledProcessError(128, cmd)
            return fake_run(cmd, *args, **kwargs)

        monkeypatch.setattr(subprocess, "run", run_with_a_failing_worktree_list)

        with pytest.raises(SystemExit) as exc_info:
            pr_cost._pr_cost_report(_pr_cost_args(record=True, projects=None), _NOW, [root])

        assert exc_info.value.code == 1
        assert ledger_path.read_bytes() == before_bytes

    @pytest.mark.parametrize("projects,expect_empty_scope_line,expected_scope", [
        pytest.param(None, True, "repo", id="bare-run"),
        pytest.param("-no-such-project-dir", False, "glob", id="glob-matching-nothing"),
    ])
    def test_a_single_account_pr_with_no_session_in_scope_writes_a_zero_valued_row_recording_its_scope(
        self, tmp_path, monkeypatch, capsys, projects, expect_empty_scope_line, expected_scope,
    ):
        (root,) = _arrange_roots(tmp_path, monkeypatch)
        _write_session(root, _FOREIGN_SLUG, "foreign", [_branch_turn("feature-a")])
        monkeypatch.setattr(subprocess, "run", _fake_pr_cost_subprocess_run(merged_prs=[_merged_pr(1, "feature-a")]))

        pr_cost._pr_cost_report(_pr_cost_args(record=True, pr=1, projects=projects), _NOW, [root])

        err = capsys.readouterr().err
        assert (_empty_scope_line() in err.splitlines()) is expect_empty_scope_line
        assert "has no matching local corpus activity" not in err
        (row,) = _ledger_rows(_ledger_path_of(root))
        assert row["capture_scope"] == expected_scope
        assert row["review_rounds_absence"] == "no-local-activity"
        assert row["earliest_surviving_activity_at"] == ""
        assert row["turn_count"] == 0

    def test_a_repo_scope_holding_only_unbranched_priced_turns_prints_no_empty_scope_line(
        self, tmp_path, monkeypatch, capsys,
    ):
        (root,) = _arrange_roots(tmp_path, monkeypatch)
        unbranched_turn = _branch_turn("unused")
        del unbranched_turn["gitBranch"]
        _write_session(root, _LIVE_UNDER_PREFIX_SLUG, "unbranched", [unbranched_turn])
        monkeypatch.setattr(subprocess, "run", _fake_pr_cost_subprocess_run(merged_prs=[]))

        pr_cost._pr_cost_report(_pr_cost_args(projects=None), _NOW, [root])

        err = capsys.readouterr().err
        assert "1 priced turns attributed to no branch at all" in err
        assert _empty_scope_line() not in err.splitlines()


class TestReadModeUnderTheRepoScope:
    def test_a_bare_listing_names_only_prs_a_record_run_can_capture(self, tmp_path, monkeypatch, capsys):
        (root,) = _arrange_roots(tmp_path, monkeypatch)
        for slug_branch in ("feature-a", "fork-only", "shared"):
            _write_session(root, _LIVE_UNDER_PREFIX_SLUG, slug_branch, [_branch_turn(slug_branch)])
        _write_session(root, _FOREIGN_SLUG, "foreign", [_branch_turn("out-of-scope")])
        monkeypatch.setattr(subprocess, "run", _fake_pr_cost_subprocess_run(merged_prs=[
            _merged_pr(1, "feature-a"), _fork_pr(2, "fork-only"),
            _merged_pr(3, "shared"), _fork_pr(4, "shared"), _merged_pr(5, "out-of-scope"),
        ]))

        pr_cost._pr_cost_report(_pr_cost_args(projects=None), _NOW, [root])

        listed_pr_numbers = [
            int(line.split("#", 1)[1].split()[0]) for line in capsys.readouterr().out.splitlines()
            if line.startswith("  PR #")
        ]
        assert listed_pr_numbers == [1, 3]


class TestJoinGuardInTheBranchWalk:
    def test_a_default_branch_and_a_fork_only_branch_are_skipped_with_their_own_lines_and_write_no_row(
        self, tmp_path, monkeypatch, capsys,
    ):
        (root,) = _arrange_roots(tmp_path, monkeypatch)
        _write_session(root, _LIVE_UNDER_PREFIX_SLUG, "main-session", [_branch_turn("main")])
        _write_session(root, _LIVE_UNDER_PREFIX_SLUG, "fork-session", [_branch_turn("fork-only")])
        monkeypatch.setattr(subprocess, "run", _fake_pr_cost_subprocess_run(
            merged_prs=[_merged_pr(1, "main"), _fork_pr(2, "fork-only")],
        ))

        pr_cost._pr_cost_report(_pr_cost_args(record=True, projects=None), _NOW, [root])

        err_lines = capsys.readouterr().err.splitlines()
        assert err_lines.count(_GUARDED_BRANCH_SKIP_LINE) == 1
        assert err_lines.count(_FORK_BRANCH_SKIP_LINE) == 1
        assert not _ledger_path_of(root).exists()

    def test_a_same_repository_pr_sharing_its_head_with_a_later_fork_pr_records_at_low_and_enriches_no_fork_pr(
        self, tmp_path, monkeypatch, capsys,
    ):
        (root,) = _arrange_roots(tmp_path, monkeypatch)
        _write_session(root, _LIVE_UNDER_PREFIX_SLUG, "shared-session", [_branch_turn("shared")])
        fork_commit_sha = "a" * 40
        call_log: list[list[str]] = []
        monkeypatch.setattr(subprocess, "run", _fake_pr_cost_subprocess_run(
            merged_prs=[_merged_pr(1, "shared"), _fork_pr(2, "shared", mergedAt="2026-01-05T00:00:00Z")],
            enrichment_by_pr={2: {"commits": [{"oid": fork_commit_sha}]}},
            local_git_shas={fork_commit_sha},
            call_log=call_log,
        ))

        pr_cost._pr_cost_report(_pr_cost_args(record=True, projects=None), _NOW, [root])

        (row,) = _ledger_rows(_ledger_path_of(root))
        assert (row["pr_number"], row["join_confidence"]) == (
            1, pr_cost_ledger._PR_COST_JOIN_CONFIDENCE_LOW,
        )
        assert "ambiguous branch-to-PR match" not in capsys.readouterr().err
        assert not any(cmd[:4] == ["gh", "pr", "view", "2"] for cmd in call_log)


class TestJoinGuardOnAPrTarget:
    @pytest.mark.parametrize("all_accounts", [False, True], ids=["single-account", "all-accounts"])
    @pytest.mark.parametrize("merged_prs,pr_number,refusal_line", [
        pytest.param(
            [_merged_pr(1, "shared"), _fork_pr(2, "shared")], 2, _fork_refusal_line(2),
            id="fork-pr-whose-head-a-same-repository-pr-shares",
        ),
        pytest.param([_merged_pr(1, "main")], 1, _guarded_head_refusal_line(1), id="guarded-head"),
    ])
    def test_a_refused_target_exits_1_with_its_line_after_the_empty_scope_line_and_leaves_the_ledger_unchanged(
        self, tmp_path, monkeypatch, capsys, all_accounts, merged_prs, pr_number, refusal_line,
    ):
        roots = _arrange_roots(tmp_path, monkeypatch, all_accounts=all_accounts)
        for root in roots:
            _write_session(root, _FOREIGN_SLUG, "foreign", [_branch_turn("shared")])
        ledger_path = _ledger_path_of(roots[0])
        pr_cost_ledger._write_pr_cost_ledger_file(ledger_path, [_sample_pr_cost_row(pr_number=50)])
        before_bytes = ledger_path.read_bytes()
        monkeypatch.setattr(subprocess, "run", _fake_pr_cost_subprocess_run(merged_prs=merged_prs))

        with pytest.raises(SystemExit) as exc_info:
            pr_cost._pr_cost_report(
                _pr_cost_args(record=True, pr=pr_number, projects=None, all_accounts=all_accounts), _NOW, roots,
            )

        assert exc_info.value.code == 1
        err_lines = capsys.readouterr().err.splitlines()
        empty_scope_line = _empty_scope_line(" in account-1" if all_accounts else "")
        assert err_lines.index(empty_scope_line) < err_lines.index(refusal_line)
        assert ledger_path.read_bytes() == before_bytes


class TestMergedPrPayloadCheck:
    @pytest.mark.parametrize("arg_overrides", [
        pytest.param({}, id="read-mode"),
        pytest.param({"record": True}, id="record"),
    ])
    def test_a_payload_missing_the_cross_repository_flag_exits_1_and_writes_no_ledger(
        self, tmp_path, monkeypatch, capsys, arg_overrides,
    ):
        (root,) = _arrange_roots(tmp_path, monkeypatch)
        monkeypatch.setattr(subprocess, "run", _fake_pr_cost_subprocess_run(
            merged_prs=[_merged_pr(1, "feature-a")], withheld_fields=frozenset({"isCrossRepository"}),
        ))

        with pytest.raises(SystemExit) as exc_info:
            pr_cost._pr_cost_report(_pr_cost_args(projects=None, **arg_overrides), _NOW, [root])

        assert exc_info.value.code == 1
        assert capsys.readouterr().err.splitlines()[-1] == _PAYLOAD_REFUSAL_LINE
        assert not _ledger_path_of(root).exists()


class TestForceRecaptureCallSitePassesBothScopes:
    def test_a_repo_scoped_force_recapture_appends_its_row_over_a_larger_row_with_an_empty_scope(
        self, fake_projects, tmp_path, monkeypatch,
    ):
        ledger_path = _arrange_record_run(fake_projects, tmp_path, monkeypatch, branches=("feature-a",))
        monkeypatch.setattr(
            scope, "_repo_scoped_project_slugs", lambda command_label="skill-invocation": [fake_projects.name],
        )
        pr_cost_ledger._write_pr_cost_ledger_file(ledger_path, [_sample_pr_cost_row(
            pr_number=1, machine=_SEEDED_MACHINE_IDENTITY, captured_at="2026-01-01T00:00:00Z",
            review_rounds=_cell_of(review_rounds.REVIEW_ROUND_RULE, code_review=[1, 1]),
        )])

        _run_record(fake_projects, pr=1, force=True, projects=None)

        prior_row, recaptured_row = _ledger_rows(ledger_path)
        assert prior_row["capture_scope"] == ""
        assert recaptured_row["capture_scope"] == pr_cost_ledger._PR_COST_CAPTURE_SCOPE_REPO
        assert recaptured_row["supersedes"] == "2026-01-01T00:00:00Z"
        assert len(recaptured_row["review_rounds"]["rounds"]["code-review"]) == 0

    def test_a_repo_scoped_force_recapture_is_refused_over_a_larger_row_with_the_repo_scope(
        self, fake_projects, tmp_path, monkeypatch, capsys,
    ):
        ledger_path = _arrange_record_run(fake_projects, tmp_path, monkeypatch, branches=("feature-a",))
        monkeypatch.setattr(
            scope, "_repo_scoped_project_slugs", lambda command_label="skill-invocation": [fake_projects.name],
        )
        pr_cost_ledger._write_pr_cost_ledger_file(ledger_path, [_sample_pr_cost_row(
            pr_number=1, machine=_SEEDED_MACHINE_IDENTITY, captured_at="2026-01-01T00:00:00Z",
            capture_scope=pr_cost_ledger._PR_COST_CAPTURE_SCOPE_REPO,
            review_rounds=_cell_of(review_rounds.REVIEW_ROUND_RULE, code_review=[1, 1]),
        )])
        ledger_bytes_before = ledger_path.read_bytes()

        with pytest.raises(SystemExit) as exc_info:
            _run_record(fake_projects, pr=1, force=True, projects=None)

        assert exc_info.value.code == 1
        assert _force_refusal_line(1, _SEEDED_MACHINE_IDENTITY, _REASON_LESS_COMPLETE) in capsys.readouterr().err.splitlines()
        assert ledger_path.read_bytes() == ledger_bytes_before


class TestAlreadyCapturedLineNamesTheRowsScope:
    @pytest.mark.parametrize(("capture_scope", "expected_hint"), [
        pytest.param(pr_cost_ledger._PR_COST_CAPTURE_SCOPE_GLOB, _GLOB_RESCOPE_HINT, id="glob-row-names-the-re-scope"),
        pytest.param(pr_cost_ledger._PR_COST_CAPTURE_SCOPE_REPO, "", id="repo-row-keeps-the-plain-line"),
        pytest.param("", _EMPTY_SCOPE_RESCOPE_HINT, id="legacy-empty-scope-row-names-the-re-scope"),
    ])
    def test_an_already_captured_pr_prints_the_re_scope_hint_for_a_glob_or_legacy_row_and_none_for_a_repo_row(
        self, fake_projects, tmp_path, monkeypatch, capsys, capture_scope, expected_hint,
    ):
        ledger_path = _arrange_record_run(fake_projects, tmp_path, monkeypatch, branches=("feature-a",))
        pr_cost_ledger._write_pr_cost_ledger_file(ledger_path, [_sample_pr_cost_row(
            pr_number=1, machine=_SEEDED_MACHINE_IDENTITY, capture_scope=capture_scope,
        )])

        with pytest.raises(SystemExit) as exc_info:
            _run_record(fake_projects, pr=1)

        assert exc_info.value.code == 1
        assert _already_captured_line(1) + expected_hint in capsys.readouterr().err.splitlines()
