"""Tests for publication_scope: the single-account root, the wider-scope refusal, the scope header and ledger-file selection."""
import argparse
import hashlib
import os
import sys
from collections import Counter
from pathlib import Path

import pytest
from helpers import CLAUDE_DIR, init_git_repo_with_commit

# claude/.claude/ itself, so `hooks.tests...` below resolves, as in test_review_ledger_lib.py.
sys.path.insert(0, str(CLAUDE_DIR))
from hooks.tests._lib_sh_helpers import _run_lib_call  # noqa: E402
from transcript_analysis import publication_scope, scope  # noqa: E402

from .conftest import _INHERITED_GIT_VARIABLES, _git, _write_named_ledger_file  # noqa: E402

# review-ledger.sh's directory under the config dir, which _write_named_ledger_file writes into.
_LEDGER_DIR_NAME = "review-narrative-ledger"
_FOREIGN_HASH = "f" * 64


def _args(*, this_repo: bool = True, projects: str = "*") -> argparse.Namespace:
    return argparse.Namespace(this_repo=this_repo, projects=projects)


class TestSingleAccountRoots:
    @pytest.mark.parametrize("command_label", ["read-cost", "reviewer-reads"])
    def test_roots_are_the_active_config_dirs_projects_directory(self, fake_projects, command_label):
        assert publication_scope._single_account_roots(command_label) == [fake_projects.parent]

    @pytest.mark.parametrize("command_label", ["read-cost", "reviewer-reads"])
    def test_unresolvable_config_dir_exits_2_under_the_command_label(self, monkeypatch, capsys, command_label):
        def unresolvable_config_dir():
            raise ValueError("CLAUDE_CONFIG_DIR is not absolute")

        monkeypatch.setattr(scope, "config_dir", unresolvable_config_dir)
        with pytest.raises(SystemExit) as raised:
            publication_scope._single_account_roots(command_label)
        assert raised.value.code == 2
        assert capsys.readouterr().err == f"{command_label}: CLAUDE_CONFIG_DIR is not absolute\n"


class TestRefuseWiderScope:
    _COMMAND_LABEL = "reviewer-reads"

    def test_this_repo_on_one_root_is_accepted(self, tmp_path):
        publication_scope._refuse_wider_scope(_args(), [tmp_path], self._COMMAND_LABEL)

    def test_refused_without_this_repo_under_the_command_label(self, tmp_path, capsys):
        with pytest.raises(SystemExit) as raised:
            publication_scope._refuse_wider_scope(_args(this_repo=False), [tmp_path], self._COMMAND_LABEL)
        assert raised.value.code == 2
        captured = capsys.readouterr()
        assert captured.err == (
            "reviewer-reads: requires --this-repo and refuses any --projects scope -- see docs/transcript-analysis.md\n"
        )
        assert captured.out == ""

    def test_refused_with_a_projects_glob_under_the_command_label(self, tmp_path, capsys):
        with pytest.raises(SystemExit) as raised:
            publication_scope._refuse_wider_scope(_args(projects="-home-*"), [tmp_path], self._COMMAND_LABEL)
        assert raised.value.code == 2
        assert capsys.readouterr().err == (
            "reviewer-reads: requires --this-repo and refuses any --projects scope -- see docs/transcript-analysis.md\n"
        )

    def test_refused_with_two_roots_under_the_command_label(self, tmp_path, capsys):
        with pytest.raises(SystemExit) as raised:
            publication_scope._refuse_wider_scope(
                _args(), [tmp_path / "account-a", tmp_path / "account-b"], self._COMMAND_LABEL,
            )
        assert raised.value.code == 2
        assert capsys.readouterr().err == (
            "reviewer-reads: resolved to more than one root -- refusing to report a multi-account figure\n"
        )


class TestScopeHeader:
    def test_header_is_titled_by_the_command_label(self):
        assert publication_scope._scope_header("this repo (2 project dirs)", "reviewer-reads") == (
            "REVIEWER READS SOURCES (this repo (2 project dirs); reads one account (the active account),"
            " the working directory's repository only; ~/.claude/transcript-config-dirs not consulted)"
        )


class TestLedgerRepoHash:
    @pytest.mark.parametrize("path", ["/work/repo", "/work/a repo with spaces", "/work/répo/テスト"])
    def test_equals_the_hook_libraries_marker_repo_hash(self, path):
        marker_lib = _run_lib_call(f'_marker_lib_repo_hash "{path}"', env=dict(os.environ))
        assert marker_lib.returncode == 0, marker_lib.stderr
        assert publication_scope._ledger_repo_hash(path) == marker_lib.stdout.strip()

    def test_hashes_the_raw_bytes_of_a_path_that_is_not_valid_utf8(self):
        path_with_lone_byte = "/work/caf" + os.fsdecode(b"\xe9")

        assert publication_scope._ledger_repo_hash(path_with_lone_byte) == hashlib.sha256(b"/work/caf\xe9").hexdigest()


class TestThisRepoLedgerFiles:
    _MAIN = "/work/main-checkout"
    _LINKED = "/work/linked-checkout"

    def test_keeps_a_branch_file_and_a_session_file_of_each_worktree(self, tmp_path):
        ledger_dir = tmp_path / _LEDGER_DIR_NAME
        kept = [
            _write_named_ledger_file(tmp_path, publication_scope._ledger_repo_hash(worktree), slot, [])
            for worktree in (self._MAIN, self._LINKED)
            for slot in ("b" * 64, "session-1")
        ]

        files = publication_scope._this_repo_ledger_files(ledger_dir, [self._MAIN, self._LINKED], Counter())

        assert files == sorted(kept)

    def test_drops_a_file_that_is_not_named_for_a_listed_worktree(self, tmp_path):
        ledger_dir = tmp_path / _LEDGER_DIR_NAME
        _write_named_ledger_file(tmp_path, _FOREIGN_HASH, "session-1", [])
        _write_named_ledger_file(
            tmp_path, publication_scope._ledger_repo_hash("/work/removed-checkout"), "session-1", [],
        )
        kept = _write_named_ledger_file(tmp_path, publication_scope._ledger_repo_hash(self._MAIN), "session-1", [])

        assert publication_scope._this_repo_ledger_files(ledger_dir, [self._MAIN], Counter()) == [kept]

    def test_drops_a_name_with_no_dot_a_non_jsonl_name_and_a_directory(self, tmp_path):
        ledger_dir = tmp_path / _LEDGER_DIR_NAME
        repo_hash = publication_scope._ledger_repo_hash(self._MAIN)
        kept = _write_named_ledger_file(tmp_path, repo_hash, "session-1", [])
        (ledger_dir / repo_hash).write_text("")
        (ledger_dir / f"{repo_hash}.session-2.txt").write_text("")
        (ledger_dir / f"{repo_hash}.session-3.jsonl").mkdir()

        assert publication_scope._this_repo_ledger_files(ledger_dir, [self._MAIN], Counter()) == [kept]

    def test_drops_a_jsonl_name_whose_worktree_hash_is_not_the_first_segment_before_a_slot(self, tmp_path):
        ledger_dir = tmp_path / _LEDGER_DIR_NAME
        main_hash = publication_scope._ledger_repo_hash(self._MAIN)
        kept = _write_named_ledger_file(tmp_path, main_hash, "session-1", [])
        ledger_dir.joinpath(f"{main_hash}.jsonl").write_text("")
        _write_named_ledger_file(tmp_path, _FOREIGN_HASH, main_hash, [])
        _write_named_ledger_file(tmp_path, main_hash + "0", "session-1", [])

        assert publication_scope._this_repo_ledger_files(ledger_dir, [self._MAIN], Counter()) == [kept]

    def test_keeps_a_dangling_symlink_with_a_matching_name_so_the_open_fails(self, tmp_path):
        ledger_dir = tmp_path / _LEDGER_DIR_NAME
        ledger_dir.mkdir()
        dangling = ledger_dir / f"{publication_scope._ledger_repo_hash(self._MAIN)}.session-1.jsonl"
        dangling.symlink_to(tmp_path / "absent-target")

        assert publication_scope._this_repo_ledger_files(ledger_dir, [self._MAIN], Counter()) == [dangling]

    def test_keeps_a_matching_entry_that_cannot_be_statted_so_the_open_counts_it_unreadable(
        self, tmp_path, monkeypatch,
    ):
        ledger_dir = tmp_path / _LEDGER_DIR_NAME
        unstattable = _write_named_ledger_file(tmp_path, publication_scope._ledger_repo_hash(self._MAIN), "session-1", [])
        path_is_dir = Path.is_dir

        def is_dir_failing_for_the_entry(path, *args, **kwargs):
            if path == unstattable:
                raise PermissionError("cannot stat")
            return path_is_dir(path, *args, **kwargs)

        monkeypatch.setattr(Path, "is_dir", is_dir_failing_for_the_entry)

        assert publication_scope._this_repo_ledger_files(ledger_dir, [self._MAIN], Counter()) == [unstattable]

    def test_matches_a_symlinked_worktree_path_as_printed_and_as_resolved(self, tmp_path):
        real_worktree = tmp_path / "real-checkout"
        real_worktree.mkdir()
        printed_worktree = tmp_path / "linked-path"
        printed_worktree.symlink_to(real_worktree)
        ledger_dir = tmp_path / _LEDGER_DIR_NAME
        printed_file = _write_named_ledger_file(
            tmp_path, publication_scope._ledger_repo_hash(str(printed_worktree)), "s1", [],
        )
        resolved_file = _write_named_ledger_file(
            tmp_path, publication_scope._ledger_repo_hash(str(real_worktree.resolve())), "s2", [],
        )
        _write_named_ledger_file(tmp_path, _FOREIGN_HASH, "s3", [])

        files = publication_scope._this_repo_ledger_files(ledger_dir, [str(printed_worktree)], Counter())

        assert files == sorted([printed_file, resolved_file])

    def test_matches_the_toplevel_each_worktree_of_a_real_repository_prints(self, tmp_path, monkeypatch):
        for variable in _INHERITED_GIT_VARIABLES:
            monkeypatch.delenv(variable, raising=False)
        main_checkout = init_git_repo_with_commit(tmp_path / "main-checkout")
        linked_checkout = tmp_path / "linked-checkout"
        _git(main_checkout, "worktree", "add", "-q", str(linked_checkout))
        toplevel_hashes = [
            publication_scope._ledger_repo_hash(_git(checkout, "rev-parse", "--show-toplevel").strip())
            for checkout in (main_checkout, linked_checkout)
        ]
        ledger_dir = tmp_path / _LEDGER_DIR_NAME
        toplevel_files = [
            _write_named_ledger_file(tmp_path, toplevel_hash, f"session-{position}", [])
            for position, toplevel_hash in enumerate(toplevel_hashes)
        ]
        monkeypatch.chdir(main_checkout)

        worktree_paths = scope._repo_worktree_paths("reviewer-reads")
        files = publication_scope._this_repo_ledger_files(ledger_dir, worktree_paths, Counter())

        assert files == sorted(toplevel_files)

    def test_absent_ledger_directory_yields_no_files_and_no_gap(self, tmp_path):
        gaps: Counter = Counter()

        assert publication_scope._this_repo_ledger_files(tmp_path / "absent", [self._MAIN], gaps) == []
        assert gaps == Counter()

    @pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses file permission bits")
    def test_unreadable_ledger_directory_records_a_gap(self, tmp_path):
        ledger_dir = tmp_path / _LEDGER_DIR_NAME
        ledger_dir.mkdir()
        os.chmod(ledger_dir, 0o000)
        gaps: Counter = Counter()
        try:
            files = publication_scope._this_repo_ledger_files(ledger_dir, [self._MAIN], gaps)
        finally:
            os.chmod(ledger_dir, 0o755)  # restore before tmp_path teardown

        assert files == []
        assert gaps == Counter({publication_scope._GAP_LEDGER_DIR: 1})
