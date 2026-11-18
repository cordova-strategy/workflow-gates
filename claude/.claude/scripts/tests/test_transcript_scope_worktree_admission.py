"""scope.py's --this-repo worktree-prefix admission and the resolved-scope header's live/unlisted project-dir counts."""
import argparse
import os
from collections import Counter

import pytest
from transcript_analysis import scope

from .conftest import _asst, _stub_git_worktree_listing, _worktree_porcelain, _write_jsonl

_MODEL = "claude-sonnet-4-6"
_WORKTREES_INFIX = "--claude-worktrees-"


def _write_session_dirs(root, *names, extra_record_fields=None):
    """One session per named project directory under `root`, with the directory name as its branch."""
    for name in names:
        project_dir = root / name
        project_dir.mkdir(parents=True)
        record = _asst(_MODEL, branch=name)
        record.update((extra_record_fields or {}).get(name, {}))
        _write_jsonl(project_dir / "s.jsonl", [record])


def _branches_read(sessions):
    return sorted({rec["gitBranch"] for _jsonl, records in sessions for rec in records})


def _this_repo_args(slugs, **extra):
    return argparse.Namespace(this_repo=True, projects="*", _this_repo_slugs=slugs, **extra)


class TestRepoProjectDirMatcherPredicates:
    @pytest.mark.parametrize(
        ("slugs", "name", "admitted", "live"),
        [
            pytest.param(["-repo-main"], "-repo-main", True, True, id="main-slug-is-live"),
            pytest.param(
                ["-repo-main", "-repo-main--claude-worktrees-live"], "-repo-main--claude-worktrees-live", True, True,
                id="live-linked-slug-is-live",
            ),
            pytest.param(["-elsewhere-wt"], "-elsewhere-wt", True, True, id="live-slug-outside-worktrees-dir"),
            pytest.param(["-repo-main"], "-repo-main--claude-worktrees-gone", True, False, id="prefix-extended-is-unlisted"),
            pytest.param(
                ["-repo-main"], "-repo-main--claude-worktrees-live--claude-worktrees-nested", True, False,
                id="nested-worktree-is-unlisted",
            ),
            pytest.param(["-repo-main"], "-repo-main--claude-worktrees-", False, False, id="bare-prefix-is-rejected"),
            pytest.param(["-repo-main"], "-repo-main-fork", False, False, id="sibling-fork-is-rejected"),
            pytest.param(["-repo-main"], "-repo-main-sub", False, False, id="main-subdirectory-is-rejected"),
            pytest.param(
                ["-repo-main"], "-repo-main-fork--claude-worktrees-x", False, False,
                id="sibling-fork-worktree-dir-is-rejected",
            ),
            pytest.param(
                ["-repo-main"], "-repo-main-sub--claude-worktrees-x", False, False,
                id="main-subdirectory-worktree-dir-is-rejected",
            ),
            pytest.param(["-repo-main"], "-Repo-Main", False, False, id="case-variant-of-live-slug-is-rejected"),
            pytest.param(
                ["-repo-main"], "-repo-main--Claude-Worktrees-x", False, False,
                id="case-variant-of-infix-is-rejected",
            ),
            pytest.param(
                ["-repo-main", "-elsewhere-wt"], "-elsewhere-wt--claude-worktrees-x", False, False,
                id="prefix-of-a-non-first-slug-is-rejected",
            ),
            pytest.param(
                ["-work-app"], "-data-work-app--claude-worktrees-x", False, False,
                id="prefix-sitting-mid-name-is-rejected",
            ),
            pytest.param(["-repo-main"], "-home-user-unrelated", False, False, id="unrelated-is-rejected"),
            pytest.param(["-r*-main"], "-rX-main--claude-worktrees-y", False, False, id="glob-metacharacter-is-literal"),
            pytest.param([], "-repo-main--claude-worktrees-gone", False, False, id="empty-slugs-admit-nothing"),
            pytest.param([], "--claude-worktrees-x", False, False, id="empty-slugs-with-infix-only-name"),
        ],
    )
    def test_admits_and_is_live_follow_the_rule(self, slugs, name, admitted, live):
        matcher = scope._repo_project_dir_matcher(slugs)

        assert matcher.admits(name) is admitted
        assert matcher.is_live(name) is live


class TestThisRepoAdmitsUnlistedWorktreeDirs:
    def test_prefix_admits_unlisted_worktree_dirs_and_rejects_near_misses(self, tmp_path):
        slugs = ["-repo-main", "-repo-main--claude-worktrees-live", "-elsewhere-wt"]
        root = tmp_path / "projects"
        _write_session_dirs(
            root, *slugs,
            "-repo-main--claude-worktrees-gone",
            "-repo-main--claude-worktrees-live--claude-worktrees-nested",
            "-repo-main--claude-worktrees-",
            "-repo-main-fork",
            "-repo-main-fork--claude-worktrees-x",
            "-elsewhere-wt--claude-worktrees-x",
            "-data-repo-main--claude-worktrees-x",
            "-home-user-unrelated",
        )

        sessions = list(scope._iter_scoped_sessions(slugs, False, roots=[root]))

        assert _branches_read(sessions) == sorted([
            *slugs,
            "-repo-main--claude-worktrees-gone",
            "-repo-main--claude-worktrees-live--claude-worktrees-nested",
        ])

    def test_a_glob_metacharacter_in_the_main_slug_is_matched_literally(self, tmp_path):
        root = tmp_path / "projects"
        _write_session_dirs(root, "-r*-main--claude-worktrees-y", "-rX-main--claude-worktrees-y")

        sessions = list(scope._iter_scoped_sessions(["-r*-main"], False, roots=[root]))

        assert _branches_read(sessions) == ["-r*-main--claude-worktrees-y"]

    def test_empty_slugs_admit_nothing(self, tmp_path):
        root = tmp_path / "projects"
        _write_session_dirs(root, "-repo-main--claude-worktrees-gone", _WORKTREES_INFIX + "x")

        assert list(scope._iter_scoped_sessions([], False, roots=[root])) == []
        assert scope._scan_root_transcripts(root, "*", slugs=[]) == (0, 0)
        _sessions, label = scope._resolve_project_scope(_this_repo_args([]), "buckets", roots=[root])
        assert label == "this repo (0 project dirs: 0 live, 0 unlisted)"

    def test_one_args_reused_across_per_root_calls_reads_each_roots_unlisted_dir(self, tmp_path):
        root_a = tmp_path / "acct-a"
        root_b = tmp_path / "acct-b"
        _write_session_dirs(root_a, "-repo-main")
        _write_session_dirs(root_b, "-repo-main--claude-worktrees-gone")
        args = _this_repo_args(["-repo-main"])

        sessions_a, label_a = scope._resolve_project_scope(args, "pr-cost", roots=[root_a])
        sessions_b, label_b = scope._resolve_project_scope(args, "pr-cost", roots=[root_b])

        assert _branches_read(sessions_a) == ["-repo-main"]
        assert label_a == "this repo (1 project dirs: 1 live, 0 unlisted)"
        assert _branches_read(sessions_b) == ["-repo-main--claude-worktrees-gone"]
        assert label_b == "this repo (1 project dirs: 0 live, 1 unlisted)"

    def test_unseeded_args_reused_across_per_root_calls_cache_only_the_live_slugs(self, tmp_path, monkeypatch):
        root_a = tmp_path / "acct-a"
        root_b = tmp_path / "acct-b"
        _write_session_dirs(root_a, "-home-user-unrelated")
        _write_session_dirs(root_b, "-repo-main--claude-worktrees-gone")
        _stub_git_worktree_listing(
            monkeypatch,
            _worktree_porcelain("/repo/main", "/repo/main/.claude/worktrees/live"),
            "/repo/main",
            "/repo/main",
        )
        args = argparse.Namespace(this_repo=True, projects="*")

        scope._resolve_project_scope(args, "pr-cost", roots=[root_a])
        slugs_after_first_call = list(args._this_repo_slugs)
        sessions_b, label_b = scope._resolve_project_scope(args, "pr-cost", roots=[root_b])

        assert slugs_after_first_call == ["-repo-main", "-repo-main--claude-worktrees-live"]
        assert _branches_read(sessions_b) == ["-repo-main--claude-worktrees-gone"]
        assert label_b == "this repo (1 project dirs: 0 live, 1 unlisted)"

    @pytest.mark.parametrize(
        ("porcelain", "cwd", "toplevel", "dirs_on_root", "expected_read", "expected_label"),
        [
            pytest.param(
                _worktree_porcelain("/repo/main", "/repo/main/.claude/worktrees/live"),
                "/repo/main/.claude/worktrees/live",
                "/repo/main/.claude/worktrees/live",
                [
                    "-repo-main", "-repo-main--claude-worktrees-live", "-repo-main--claude-worktrees-gone",
                    "-home-user-unrelated",
                ],
                ["-repo-main", "-repo-main--claude-worktrees-gone", "-repo-main--claude-worktrees-live"],
                "this repo (3 project dirs: 2 live, 1 unlisted)",
                id="linked-cwd",
            ),
            pytest.param(
                # Hand-written: _worktree_porcelain prints HEAD and branch lines, which a bare entry does not carry.
                "worktree /srv/app.git\nbare\n\nworktree /srv/wt/live\nHEAD 0000\nbranch refs/heads/x\n",
                "/srv/wt/live",
                "/srv/wt/live",
                ["-srv-app-git--claude-worktrees-gone", "-srv-wt-live--claude-worktrees-x"],
                ["-srv-app-git--claude-worktrees-gone"],
                "this repo (1 project dirs: 0 live, 1 unlisted)",
                id="bare-first",
            ),
        ],
    )
    def test_unseeded_scope_takes_the_prefix_from_the_first_listed_worktree(
        self, tmp_path, monkeypatch, porcelain, cwd, toplevel, dirs_on_root, expected_read, expected_label,
    ):
        root = tmp_path / "projects"
        _write_session_dirs(root, *dirs_on_root)
        _stub_git_worktree_listing(monkeypatch, porcelain, cwd, toplevel)
        args = argparse.Namespace(this_repo=True, projects="*")

        sessions, label = scope._resolve_project_scope(args, "buckets", roots=[root])

        assert _branches_read(sessions) == expected_read
        assert label == expected_label

    def test_lookalike_sibling_and_foreign_clone_dirs_are_admitted_as_an_accepted_residual(self, tmp_path):
        """Pins a known, accepted residual risk: admission is by directory name alone, so a sibling directory whose
        slug starts with the main checkout's slug plus the worktrees infix, and a foreign repo cloned under the
        worktrees directory, are both read as this repo's. A change that alters that posture, in either direction,
        must fail this test."""
        lookalike_sibling = "-repo-main--claude-worktrees-x"
        foreign_clone = "-repo-main--claude-worktrees-clone"
        root = tmp_path / "projects"
        _write_session_dirs(
            root, lookalike_sibling, foreign_clone,
            extra_record_fields={
                lookalike_sibling: {"cwd": "/repo/main--claude-worktrees-x"},
                foreign_clone: {"gitBranch": "foreign-clone"},
            },
        )

        sessions = list(scope._iter_scoped_sessions(["-repo-main"], False, roots=[root]))

        assert _branches_read(sessions) == sorted([lookalike_sibling, "foreign-clone"])


class TestThisRepoProjectDirCounts:
    def test_live_count_follows_the_dirs_present_not_the_number_of_live_slugs(self, tmp_path):
        slugs = ["-repo-main", "-repo-main--claude-worktrees-live", "-repo-main--claude-worktrees-nodir"]
        root = tmp_path / "projects"
        _write_session_dirs(root, slugs[0], slugs[1], "-repo-main--claude-worktrees-gone")

        _sessions, label = scope._resolve_project_scope(_this_repo_args(slugs), "buckets", roots=[root])

        assert label == "this repo (3 project dirs: 2 live, 1 unlisted)"

    def test_counts_follow_resolved_paths_across_roots(self, tmp_path):
        root_a = tmp_path / "acct-a"
        root_b = tmp_path / "acct-b"
        root_a_alias = tmp_path / "acct-a-alias"
        _write_session_dirs(root_a, "-repo-main", "-repo-main--claude-worktrees-gone")
        _write_session_dirs(root_b, "-repo-main--claude-worktrees-gone", "-repo-main--claude-worktrees-other")
        root_a_alias.symlink_to(root_a)

        sessions, label = scope._resolve_project_scope(
            _this_repo_args(["-repo-main"]), "buckets", roots=[root_a, root_b, root_a_alias],
        )

        assert len(list(sessions)) == 4
        assert label == "this repo (4 project dirs: 1 live, 3 unlisted)"

    def test_scan_count_session_count_and_header_agree(self, tmp_path):
        root = tmp_path / "projects"
        _write_session_dirs(
            root, "-repo-main", "-repo-main--claude-worktrees-gone", "-repo-main--claude-worktrees-", "-repo-main-fork",
        )
        (root / "-repo-main--claude-worktrees-file").write_text("not a directory")
        (root / "-repo-main--claude-worktrees-alias").symlink_to(root / "-repo-main--claude-worktrees-gone")
        args = _this_repo_args(["-repo-main"])

        scanned, _skipped = scope._scan_root_transcripts(root, "*", slugs=["-repo-main"])
        sessions, label = scope._resolve_project_scope(args, "buckets", roots=[root])

        assert scanned == 2
        assert len(list(sessions)) == 2
        assert label == "this repo (2 project dirs: 1 live, 1 unlisted)"

    @pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses file permission bits")
    def test_an_unreadable_admitted_dir_counts_and_the_read_records_its_gap(self, tmp_path):
        root = tmp_path / "projects"
        _write_session_dirs(root, "-repo-main--claude-worktrees-gone")
        scan_gaps: Counter[str] = Counter()
        os.chmod(root, 0o444)  # listable, but its entries cannot be stat-ed
        try:
            sessions, label = scope._resolve_project_scope(
                _this_repo_args(["-repo-main"]), "buckets", roots=[root], scan_gaps=scan_gaps,
            )
            assert list(sessions) == []
        finally:
            os.chmod(root, 0o755)

        assert label == "this repo (1 project dirs: 0 live, 1 unlisted)"
        assert scan_gaps == Counter({scope._SCAN_GAP_PROJECT_DIR: 1})

    def test_config_dir_with_only_near_miss_dirs_exits_1_naming_counts_only(self, tmp_path, capsys):
        slugs = ["-repo-main", "-elsewhere-wt"]
        root = tmp_path / "projects"
        _write_session_dirs(root, "-repo-main-fork", "-repo-main--claude-worktrees-", "-elsewhere-wt--claude-worktrees-x")
        args = _this_repo_args(slugs, config_dir=str(tmp_path))

        with pytest.raises(SystemExit) as exc_info:
            scope._resolve_project_scope(args, "buckets", roots=[root])

        stderr = capsys.readouterr().err
        assert exc_info.value.code == 1
        assert "--this-repo matched zero project directories" in stderr
        assert f"{len(slugs)} live worktree slug(s)" in stderr
        for identifying_text in (*slugs, _WORKTREES_INFIX, str(tmp_path)):
            assert identifying_text not in stderr

    @pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses file permission bits")
    def test_config_dir_with_an_unlistable_root_exits_1_saying_it_cannot_list_the_root(self, tmp_path, capsys):
        root = tmp_path / "projects"
        _write_session_dirs(root, "-repo-main--claude-worktrees-gone")
        args = _this_repo_args(["-repo-main"], config_dir=str(tmp_path))
        os.chmod(root, 0o311)  # searchable and writable, but not listable
        try:
            with pytest.raises(SystemExit) as exc_info:
                scope._resolve_project_scope(args, "buckets", roots=[root])
        finally:
            os.chmod(root, 0o755)

        stderr = capsys.readouterr().err
        assert exc_info.value.code == 1
        assert "cannot list" in stderr
        assert "matched zero project directories" not in stderr
        for identifying_text in ("-repo-main", _WORKTREES_INFIX, str(tmp_path)):
            assert identifying_text not in stderr

    @pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses file permission bits")
    def test_an_unlistable_root_is_recorded_once_across_the_count_and_the_read(self, tmp_path):
        root = tmp_path / "projects"
        _write_session_dirs(root, "-repo-main--claude-worktrees-gone")
        scan_gaps: Counter[str] = Counter()
        os.chmod(root, 0o311)  # searchable and writable, but not listable
        try:
            sessions, _label = scope._resolve_project_scope(
                _this_repo_args(["-repo-main"]), "buckets", roots=[root], scan_gaps=scan_gaps,
            )
            assert list(sessions) == []
        finally:
            os.chmod(root, 0o755)

        assert scan_gaps == Counter({scope._SCAN_GAP_ROOT: 1})

    def test_config_dir_with_only_an_unlisted_dir_reads_it(self, tmp_path):
        root = tmp_path / "projects"
        _write_session_dirs(root, "-repo-main--claude-worktrees-gone")
        args = _this_repo_args(["-repo-main"], config_dir=str(tmp_path))

        sessions, label = scope._resolve_project_scope(args, "buckets", roots=[root])

        assert _branches_read(sessions) == ["-repo-main--claude-worktrees-gone"]
        assert label == "this repo (1 project dirs: 0 live, 1 unlisted)"
