"""Tests for relocate-claude-config.sh's repair of the checkout's linked worktrees.

Whole-script cases run both modes against a real git checkout with real linked worktrees, and git is the oracle
for every link. The runner cases source the script and call its functions directly: `repair_linked_worktrees` after
the test renames the checkout, as an out-of-band move would, and `_collect_worktree_candidates` on a fixture tree.
Fixture git calls run under an isolated environment, so neither a contributor's git config nor an inherited
repository variable reaches a fixture.
"""
from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path

import pytest
from helpers import init_git_repo, isolated_git_env

from ._relocate_helpers import (
    _AWKWARD_DESTINATION_NAME,
    _BASH,
    _SUBPROCESS_TIMEOUT_SECONDS,
    _claude_shim,
    _intercepting_function,
    _last_nonempty_line,
    _make_repo,
    _relocation_args_for_mode,
    _run_printed_retry_line,
    _run_script,
    _run_sourced,
    _SourcedRun,
    _stow,
)
from .conftest import _break_worktree_git_link, _clean_env

_WORKTREES = Path(".claude") / "worktrees"
_BROKEN_GIT_LINK = "gitdir: /nonexistent/gitdir\n"
# A file `_make_git_checkout` commits (`_make_repo` writes it), so a worktree checks it out as tracked content.
_TRACKED_FILE = Path("claude") / ".claude" / "hooks" / "_lib.sh"
# The manual steps tell the user to confirm a record is stale before removing it, and offer no command for it.
_REMOVAL_CONFIRMATION = "remove its record yourself only after you confirm its directory is gone"
_WORKTREE_RECORD_REMOVAL_COMMANDS = ("worktree prune", "worktree remove")


def _fixture_env(tmp_path: Path) -> dict[str, str]:
    empty_xdg_config_home = tmp_path / "fixture-xdg-config-home"
    empty_xdg_config_home.mkdir(exist_ok=True)
    return isolated_git_env(_clean_env(), empty_xdg_config_home)


def _fixture_git(tmp_path: Path, cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, env=_fixture_env(tmp_path), capture_output=True, text=True, check=True
    ).stdout


def _make_git_checkout(tmp_path: Path, name: str = "old-repo", *, parent: Path | None = None) -> Path:
    """A fake claude-config checkout that is also a git repository with one commit."""
    repo = _make_repo(parent or tmp_path, name)
    init_git_repo(repo, branch="main", env=_fixture_env(tmp_path))
    _fixture_git(tmp_path, repo, "add", "-A")
    _fixture_git(tmp_path, repo, "commit", "-q", "-m", "seed")
    return repo


def _add_worktree(tmp_path: Path, checkout: Path, worktree: Path) -> Path:
    """Add a detached linked worktree and return its physical path, the form git records."""
    physical_path = worktree.resolve()
    _fixture_git(tmp_path, checkout, "worktree", "add", "-q", "--detach", str(physical_path))
    return physical_path


def _make_decoy_with_worktree(tmp_path: Path, name: str = "decoy") -> tuple[Path, Path, dict[str, bytes]]:
    """A git checkout with one linked worktree `w`, and a snapshot of their admin files to compare after a run."""
    decoy = _make_git_checkout(tmp_path, name)
    decoy_worktree = _add_worktree(tmp_path, decoy, tmp_path / f"{name}-worktrees" / "w")
    return decoy, decoy_worktree, _snapshot_admin_files(decoy, decoy_worktree)


def _assert_links_resolve(tmp_path: Path, checkout: Path, worktree: Path) -> None:
    """The worktree names the checkout's `.git`, and the checkout lists the worktree at its current path."""
    common_dir = _fixture_git(tmp_path, worktree, "rev-parse", "--path-format=absolute", "--git-common-dir").strip()
    assert Path(common_dir).resolve() == (checkout / ".git").resolve()
    listing = _fixture_git(tmp_path, checkout, "worktree", "list", "--porcelain").splitlines()
    assert f"worktree {worktree.resolve()}" in listing


def _bash_quote(text: str) -> str:
    """`text` as the script's `printf %q` prints it."""
    return subprocess.run(
        [_BASH, "-c", 'printf %q "$1"', "bash", text], capture_output=True, text=True, check=True
    ).stdout


def _snapshot_admin_files(repo: Path, *worktrees: Path) -> dict[str, bytes]:
    admin_files = [path for path in (repo / ".git" / "worktrees").rglob("*") if path.is_file()]
    admin_files += [worktree / ".git" for worktree in worktrees]
    return {str(path): path.read_bytes() for path in admin_files}


def _lines_holding(text: str, fragment: str) -> list[str]:
    return [line for line in text.splitlines() if fragment in line]


def _assert_removal_needs_confirmation(output: str) -> None:
    assert _REMOVAL_CONFIRMATION in " ".join(output.split())
    for removal_command in _WORKTREE_RECORD_REMOVAL_COMMANDS:
        assert removal_command not in output


def _run_repair_runner(tmp_path: Path, checkout: Path, *, prelude: str = "") -> tuple[_SourcedRun, list[str]]:
    """Call `repair_linked_worktrees` bare, as production does, then read RELINK_FAILURES."""
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    run = _run_sourced(
        home,
        [["repair_linked_worktrees", str(checkout)], 'printf "failures=%s\\n" "${RELINK_FAILURES[*]}"'],
        cwd=tmp_path, prelude=prelude, bare=True,
    )
    assert run.returncode == 0, run.stderr
    assert run.call_statuses == [0]
    return run, run.tail.removeprefix("failures=").split()


def _installed_git_checkout(tmp_path: Path) -> tuple[Path, Path, Path]:
    """A home with a git checkout stowed into it, plus the claude shim dir. Returns (home, old_repo, bin_dir)."""
    home = tmp_path / "home"
    old_repo = _make_git_checkout(tmp_path)
    _stow(old_repo, home)
    bin_dir, _, _ = _claude_shim(tmp_path)
    return home, old_repo, bin_dir


class TestWholeScriptWorktreeRepair:
    @pytest.mark.parametrize("mode", ["primary", "repair"])
    def test_both_modes_relink_every_worktree_and_name_the_outside_one_before_git_runs(
        self, tmp_path: Path, mode: str
    ) -> None:
        home, old_repo, bin_dir = _installed_git_checkout(tmp_path)
        old_root = old_repo.resolve()
        plain = _add_worktree(tmp_path, old_repo, old_repo / _WORKTREES / "plain")
        locked = _add_worktree(tmp_path, old_repo, old_repo / _WORKTREES / "locked")
        _fixture_git(tmp_path, old_repo, "worktree", "lock", str(locked))
        dirty = _add_worktree(tmp_path, old_repo, old_repo / _WORKTREES / "dirty")
        (dirty / _TRACKED_FILE).write_text("changed\n")
        (dirty / "untracked.txt").write_text("untracked\n")
        first_nested = _add_worktree(tmp_path, old_repo, old_repo / _WORKTREES / "TICKET-1" / "nested")
        second_nested = _add_worktree(tmp_path, old_repo, old_repo / _WORKTREES / "TICKET-2" / "nested")
        (plain / "sub").mkdir()
        (plain / "sub" / ".git").write_text(_BROKEN_GIT_LINK)
        outside = _add_worktree(tmp_path, old_repo, tmp_path / "outside worktree")
        listed_config_dir = tmp_path / "listed-config-dir"
        listed_config_dir.mkdir()
        (home / ".claude" / "transcript-config-dirs").write_text(f"{listed_config_dir}\n")

        destination = (home if mode == "primary" else tmp_path) / _AWKWARD_DESTINATION_NAME
        if mode == "primary":
            args = [str(destination)]
        else:
            old_repo.rename(destination)
            args = ["--repair", "--allow-outside-home", str(destination)]
        result = _run_script(*args, home=home, bin_dir=bin_dir)

        assert result.returncode == 0, result.stderr
        new_root = destination.resolve()
        repaired_worktrees = (plain, locked, dirty, first_nested, second_nested)
        moved_worktrees = [new_root / worktree.relative_to(old_root) for worktree in repaired_worktrees]
        for worktree in [*moved_worktrees, outside]:
            _assert_links_resolve(tmp_path, destination, worktree)
        assert len(list((new_root / ".git" / "worktrees").glob("*/locked"))) == 1
        assert (new_root / dirty.relative_to(old_root) / _TRACKED_FILE).read_text() == "changed\n"
        assert (new_root / dirty.relative_to(old_root) / "untracked.txt").read_text() == "untracked\n"
        assert (new_root / plain.relative_to(old_root) / "sub" / ".git").read_text() == _BROKEN_GIT_LINK
        outside_reached = _lines_holding(result.stdout, "also reaches")
        assert len(outside_reached) == 1
        quoted_outside = _bash_quote(str(outside))
        assert "outside\\ worktree" in quoted_outside
        assert outside_reached[0].count(quoted_outside) == 2
        assert f"git -C <other checkout> worktree repair {quoted_outside}" in outside_reached[0]
        assert "which does not exist" not in result.stdout + result.stderr
        repair_heading = f"repairing linked worktrees of {_bash_quote(str(new_root))}"
        assert repair_heading in result.stdout
        assert result.stdout.index("walking the dir on line 1") < result.stdout.index(repair_heading)

        second_result = _run_script("--repair", "--allow-outside-home", str(destination), home=home, bin_dir=bin_dir)

        assert second_result.returncode == 0, second_result.stderr
        second_outside_reached = _lines_holding(second_result.stdout, "also reaches")
        assert len(second_outside_reached) == 1
        assert second_outside_reached[0].count(quoted_outside) == 2

    @pytest.mark.parametrize("mode", ["primary", "repair"])
    def test_failed_repair_exits_3_and_the_printed_retry_clears_it(self, tmp_path: Path, mode: str) -> None:
        home, old_repo, bin_dir = _installed_git_checkout(tmp_path)
        old_root = old_repo.resolve()
        plain = _add_worktree(tmp_path, old_repo, old_repo / _WORKTREES / "plain")
        stray = old_repo / _WORKTREES / "stray"
        stray.mkdir()
        _break_worktree_git_link(stray)
        outside = _add_worktree(tmp_path, old_repo, tmp_path / "outside worktree")
        outside.rename(tmp_path / "outside-worktree-moved")

        new_repo, args = _relocation_args_for_mode(tmp_path, home, old_repo, mode)
        result = _run_script(*args, home=home, bin_dir=bin_dir)

        new_root = new_repo.resolve()
        assert result.returncode == 3, result.stderr
        assert str(new_root / _WORKTREES / "stray") in result.stderr
        missing_record_lines = _lines_holding(result.stderr, "which does not exist")
        assert len(missing_record_lines) == 1
        assert f"at {_bash_quote(str(outside))}, which does not exist" in missing_record_lines[0]
        assert _bash_quote(str(plain)) not in missing_record_lines[0]
        assert "re-linking failed for: linked-worktrees" in result.stderr
        assert _last_nonempty_line(result.stderr).startswith("relocate-claude-config --repair")
        _assert_removal_needs_confirmation(result.stderr)
        _assert_links_resolve(tmp_path, new_repo, new_root / plain.relative_to(old_root))

        (new_root / _WORKTREES / "stray" / ".git").unlink()
        retry = _run_printed_retry_line(result.stderr, home, bin_dir, timeout=_SUBPROCESS_TIMEOUT_SECONDS)

        assert retry.returncode == 0, retry.stderr
        assert "also reaches" not in retry.stdout

    def test_missing_records_are_reported_and_kept_while_the_run_exits_0(self, tmp_path: Path) -> None:
        home, old_repo, bin_dir = _installed_git_checkout(tmp_path)
        unlocked = _add_worktree(tmp_path, old_repo, tmp_path / "gone-unlocked")
        locked = _add_worktree(tmp_path, old_repo, tmp_path / "gone-locked")
        _fixture_git(tmp_path, old_repo, "worktree", "lock", str(locked))
        remaining = _add_worktree(tmp_path, old_repo, tmp_path / "remaining")
        unlocked.rename(tmp_path / "moved-unlocked")
        locked.rename(tmp_path / "moved-locked")

        new_repo, args = _relocation_args_for_mode(tmp_path, home, old_repo, "primary")
        result = _run_script(*args, home=home, bin_dir=bin_dir)

        assert result.returncode == 0, result.stderr
        assert result.stderr.count("which does not exist") == 2
        assert f"at {_bash_quote(str(locked))}, which does not exist" in result.stderr
        assert (new_repo / ".git" / "worktrees" / "gone-unlocked").is_dir()
        assert (new_repo / ".git" / "worktrees" / "gone-locked").is_dir()
        _assert_links_resolve(tmp_path, new_repo, remaining)
        assert "Done." in result.stdout
        assert "is not linked to the checkout" in result.stdout
        _assert_removal_needs_confirmation(result.stdout)


class TestRepairLinkedWorktreesRunner:
    @pytest.mark.parametrize("name", ["GIT_DIR", "GIT_COMMON_DIR"])
    def test_an_inherited_repository_variable_does_not_redirect_the_repair(self, tmp_path: Path, name: str) -> None:
        checkout = _make_git_checkout(tmp_path)
        _add_worktree(tmp_path, checkout, checkout / _WORKTREES / "w")
        decoy, decoy_worktree, decoy_before = _make_decoy_with_worktree(tmp_path)
        moved = tmp_path / "moved"
        checkout.rename(moved)

        _, failures = _run_repair_runner(tmp_path, moved, prelude=f"export {name}={shlex.quote(str(decoy / '.git'))}")

        assert _snapshot_admin_files(decoy, decoy_worktree) == decoy_before
        assert failures == []
        _assert_links_resolve(tmp_path, moved, moved / _WORKTREES / "w")

    @pytest.mark.parametrize("git_entry", ["absent", "gitfile", "dangling-symlink"])
    def test_runs_no_git_unless_the_checkout_git_is_a_real_directory(self, tmp_path: Path, git_entry: str) -> None:
        checkout = _make_repo(tmp_path)
        if git_entry == "gitfile":
            (checkout / ".git").write_text(_BROKEN_GIT_LINK)
        elif git_entry == "dangling-symlink":
            (checkout / ".git").symlink_to(tmp_path / "nonexistent-git-dir")

        run, failures = _run_repair_runner(tmp_path, checkout)

        assert failures == []
        assert "repairing linked worktrees" not in run.stdout
        if git_entry == "absent":
            assert "no linked worktree was repaired" not in run.stderr
            assert "symbolic link" not in run.stderr
        else:
            assert "no linked worktree was repaired" in run.stderr

    def test_a_checkout_git_symlinked_to_another_repository_leaves_that_repository_untouched(
        self, tmp_path: Path
    ) -> None:
        checkout = _make_repo(tmp_path)
        decoy, decoy_worktree, decoy_before = _make_decoy_with_worktree(tmp_path)
        assert (decoy / ".git" / "worktrees" / "w").is_dir()
        # `git worktree repair` rewrites the admin `gitdir` file named by a stale candidate.
        stale_candidate = checkout / _WORKTREES / "w"
        stale_candidate.mkdir(parents=True)
        (stale_candidate / ".git").write_text("gitdir: /stale/path/.git/worktrees/w\n")
        (checkout / ".git").symlink_to(decoy / ".git")

        run, failures = _run_repair_runner(tmp_path, checkout)

        assert _snapshot_admin_files(decoy, decoy_worktree) == decoy_before
        assert failures == []
        assert "repairing linked worktrees" not in run.stdout
        assert "no linked worktree was repaired" in run.stderr

    def test_a_failed_first_listing_fails_the_unit_before_the_repair_runs(self, tmp_path: Path) -> None:
        checkout = _make_git_checkout(tmp_path)
        _add_worktree(tmp_path, checkout, checkout / _WORKTREES / "plain")
        moved = tmp_path / "moved"
        checkout.rename(moved)
        moved_plain = moved / _WORKTREES / "plain"
        link_before = (moved_plain / ".git").read_text()
        failing_listing = _intercepting_function("git", '[[ " $* " == *" list "* ]]', "return 1")

        _, failures = _run_repair_runner(tmp_path, moved, prelude=failing_listing)

        assert failures == ["linked-worktrees"]
        assert (moved_plain / ".git").read_text() == link_before

    def test_a_failed_second_listing_fails_the_unit_after_the_repair_ran(self, tmp_path: Path) -> None:
        checkout = _make_git_checkout(tmp_path)
        _add_worktree(tmp_path, checkout, checkout / _WORKTREES / "plain")
        moved = tmp_path / "moved"
        checkout.rename(moved)
        moved_plain = moved / _WORKTREES / "plain"
        listing_count_file = tmp_path / "listing-count"
        # A subshell cannot keep a variable across calls, so the shim counts `worktree list` calls in a file.
        count_file = shlex.quote(str(listing_count_file))
        failing_second_listing = _intercepting_function(
            "git",
            '[[ " $* " == *" list "* ]]',
            f"local count=0; if [ -f {count_file} ]; then count=$(cat {count_file}); fi;"
            f" echo $((count + 1)) > {count_file}; if [ \"$count\" -ge 1 ]; then return 1; fi",
        )

        _, failures = _run_repair_runner(tmp_path, moved, prelude=failing_second_listing)

        assert failures == ["linked-worktrees"]
        assert listing_count_file.read_text().strip() == "2"
        _assert_links_resolve(tmp_path, moved, moved_plain)

    def test_the_outside_worktree_is_announced_before_git_repair_runs(self, tmp_path: Path) -> None:
        checkout = _make_git_checkout(tmp_path)
        _add_worktree(tmp_path, checkout, checkout / _WORKTREES / "plain")
        outside = _add_worktree(tmp_path, checkout, tmp_path / "outside")
        moved = tmp_path / "moved"
        checkout.rename(moved)
        repair_marker = "@@GIT-REPAIR-RAN@@"
        marking_repair = _intercepting_function("git", '[[ " $* " == *" repair "* ]]', f"echo {repair_marker}")

        run, failures = _run_repair_runner(tmp_path, moved, prelude=marking_repair)

        assert failures == []
        announced = _lines_holding(run.stdout, "also reaches")
        assert len(announced) == 1
        assert _bash_quote(str(outside)) in announced[0]
        assert run.stdout.index(announced[0]) < run.stdout.index(repair_marker)

    def test_a_relative_path_in_a_listing_is_tested_for_existence_from_the_checkout(self, tmp_path: Path) -> None:
        checkout = _make_git_checkout(tmp_path)
        (checkout / "relative-worktree").mkdir()
        # The shim supplies a relative record; no real-git case in this file produces one.
        relative_listing = _intercepting_function(
            "git",
            '[[ " $* " == *" list "* ]]',
            "printf 'worktree /main-record\\n\\nworktree relative-worktree\\n'; return 0",
        )

        run, failures = _run_repair_runner(tmp_path, checkout, prelude=relative_listing)

        assert failures == []
        announced = _lines_holding(run.stdout, "also reaches")
        assert len(announced) == 1
        assert "relative-worktree" in announced[0]
        assert "which does not exist" not in run.stderr

    def test_a_checkout_reached_through_a_symlinked_parent_is_compared_by_physical_paths(
        self, tmp_path: Path
    ) -> None:
        checkout = _make_git_checkout(tmp_path)
        plain = _add_worktree(tmp_path, checkout, checkout / _WORKTREES / "plain")
        nested = _add_worktree(tmp_path, checkout, checkout / _WORKTREES / "TICKET-1" / "nested")
        real_parent = tmp_path / "real-parent"
        real_parent.mkdir()
        checkout.rename(real_parent / "moved")
        linked_parent = tmp_path / "linked-parent"
        linked_parent.symlink_to(real_parent)
        linked_checkout = linked_parent / "moved"
        linked_plain = linked_checkout / _WORKTREES / "plain"
        # A record that names its worktree through the symlink still compares equal to the physical candidate.
        record_dir = next((real_parent / "moved" / ".git" / "worktrees").glob("plain*"))
        (record_dir / "gitdir").write_text(f"{linked_plain}/.git\n")

        run, failures = _run_repair_runner(tmp_path, linked_checkout)

        assert failures == []
        for worktree in (plain, nested):
            _assert_links_resolve(tmp_path, linked_checkout, linked_checkout / worktree.relative_to(checkout.resolve()))
        assert "also reaches" not in run.stdout

    def test_a_git_directory_git_will_not_open_stops_at_the_checkout_not_a_parent_repository(
        self, tmp_path: Path
    ) -> None:
        other_repo, other_worktree, other_before = _make_decoy_with_worktree(tmp_path, "other")
        inner = _make_git_checkout(tmp_path, "inner", parent=other_repo)
        _add_worktree(tmp_path, inner, inner / _WORKTREES / "w")
        moved = other_repo / "moved"
        inner.rename(moved)
        shutil.rmtree(moved / ".git")
        (moved / ".git").mkdir()
        (moved / ".git" / "HEAD").write_text("ref: refs/heads/main\n")

        run, failures = _run_repair_runner(tmp_path, moved)

        assert _snapshot_admin_files(other_repo, other_worktree) == other_before
        assert failures == ["linked-worktrees"]
        assert "also reaches" not in run.stdout

    def test_a_worktree_nested_past_two_levels_is_announced_and_not_named_to_git(self, tmp_path: Path) -> None:
        checkout = _make_git_checkout(tmp_path)
        _add_worktree(tmp_path, checkout, checkout / _WORKTREES / "plain")
        moved = tmp_path / "moved"
        checkout.rename(moved)
        third_level = _add_worktree(tmp_path, moved, moved / _WORKTREES / "TICKET-1" / "a" / "b")

        run, failures = _run_repair_runner(tmp_path, moved)

        assert failures == []
        announced = _lines_holding(run.stdout, "also reaches")
        assert len(announced) == 1
        assert _bash_quote(str(third_level)) in announced[0]

    def test_collecting_candidates_keeps_a_worktree_and_skips_a_full_clone(self, tmp_path: Path) -> None:
        worktrees_dir = tmp_path / _WORKTREES
        real_candidate = worktrees_dir / "real"
        real_candidate.mkdir(parents=True)
        (real_candidate / ".git").write_text(_BROKEN_GIT_LINK)
        full_clone = init_git_repo(worktrees_dir / "clone", branch="main", env=_fixture_env(tmp_path))
        (full_clone / "sub").mkdir()
        (full_clone / "sub" / ".git").write_text(_BROKEN_GIT_LINK)
        home = tmp_path / "home"
        home.mkdir()

        run = _run_sourced(
            home,
            [
                "shopt -s nullglob",
                "candidates=()",
                f"_collect_worktree_candidates {shlex.quote(str(worktrees_dir))} 2",
                'printf "%s\\n" "${candidates[@]}"',
            ],
            cwd=tmp_path,
        )

        assert run.returncode == 0, run.stderr
        assert run.tail.splitlines() == [str(real_candidate)]
