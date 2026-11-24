"""Tests for relocate-claude-config.sh's --repair recovery and quarantine-sweep classes.

This file holds the TestRepair* classes (PerEntryForm, TreeFoldedForm, SweepsEachLocation, QuarantineInvariant).
It also holds TestBackupDirSymlinkGuard, whose tests run in both modes.
The remaining classes, including TestQuarantineMoveFailure, live in test_relocate_claude_config.py.

Like test_relocate_claude_config.py, these use the real `stow` against a fake checkout and an isolated $HOME.
"""
from __future__ import annotations

import os
import subprocess
import textwrap
from pathlib import Path

import pytest

from ._relocate_helpers import (
    _BACKUP_DIR_REFUSAL_FRAGMENTS,
    _SCRIPT,
    _SUBPROCESS_TIMEOUT_SECONDS,
    _backup_entry_names,
    _claude_shim,
    _make_repo,
    _plant_unusable_backup_dir,
    _read_log,
    _run_script,
    _script_env,
    _stow,
    _stow_tree_folded,
)

# ---------------------------------------------------------------------------
# --repair flow (repo already moved outside any Claude Code session)
# ---------------------------------------------------------------------------


class TestRepairPerEntryForm:
    def test_repair_recovers_after_out_of_band_move(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        old_repo = _make_repo(tmp_path, "old-repo")
        _stow(old_repo, home)

        # Simulate an out-of-band move: rename without unstowing first.
        new_repo = tmp_path / "new-repo"
        old_repo.rename(new_repo)
        assert (home / ".claude" / "hooks").is_symlink()
        assert not (home / ".claude" / "hooks").exists()  # dangling

        bin_dir, remove_log, add_log = _claude_shim(tmp_path)

        result = _run_script("--repair", "--allow-outside-home", str(new_repo), home=home, bin_dir=bin_dir)

        assert result.returncode == 0, result.stderr
        assert (home / ".claude" / "hooks").resolve() == (new_repo / "claude" / ".claude" / "hooks").resolve()
        assert (home / ".local" / "bin" / "some-wrapper").resolve() == (
            new_repo / "claude" / ".local" / "bin" / "some-wrapper"
        ).resolve()
        assert (home / ".claude-config-source").read_text().strip() == str(new_repo)
        assert _read_log(add_log) == [str(new_repo)]
        installed = home / ".local" / "bin" / "relocate-claude-config"
        assert installed.is_file() and not installed.is_symlink()
        assert f"Done. ~/.claude and ~/.local/bin now point at: {new_repo}" in result.stdout
        assert "Reminders:" not in result.stdout
        assert "Not done by this command:" in result.stdout
        assert "no dangling stow-managed entries found to quarantine" not in result.stdout


@pytest.mark.parametrize("kind", ["symlink", "regular file"])
class TestBackupDirSymlinkGuard:
    def test_repair_refuses_when_backup_dir_is_a_symlink_or_regular_file(
        self, tmp_path: Path, kind: str
    ) -> None:
        """BACKUP_DIR is a fixed, predictable path -- a pre-planted symlink
        there must not be silently followed when quarantining dangling
        entries into it, and a regular file there cannot hold them."""
        home = tmp_path / "home"
        old_repo = _make_repo(tmp_path, "old-repo")
        _stow(old_repo, home)

        new_repo = tmp_path / "new-repo"
        old_repo.rename(new_repo)  # out-of-band move -- leaves dangling entries to quarantine

        observe_backup_dir, untouched_backup_dir = _plant_unusable_backup_dir(home, tmp_path, kind)

        bin_dir, _, _ = _claude_shim(tmp_path)
        result = _run_script("--repair", "--allow-outside-home", str(new_repo), home=home, bin_dir=bin_dir)

        assert result.returncode == 1
        assert _BACKUP_DIR_REFUSAL_FRAGMENTS[kind] in result.stderr
        assert observe_backup_dir() == untouched_backup_dir
        # The guard refused before the quarantine ran, so nothing moved.
        assert "could not move" not in result.stderr
        assert "quarantining dangling" not in result.stdout
        assert (home / ".claude" / "hooks").is_symlink()
        assert not (home / ".claude" / "hooks").exists()
        assert not (home / ".claude-config-source").exists()
        assert not (home / ".local" / "bin" / "relocate-claude-config").exists()

    def test_primary_refuses_before_anything_changes(self, tmp_path: Path, kind: str) -> None:
        home = tmp_path / "home"
        old_repo = _make_repo(tmp_path, "old-repo")
        _stow(old_repo, home, with_claude_skills=True)
        observe_backup_dir, untouched_backup_dir = _plant_unusable_backup_dir(home, tmp_path, kind)
        bin_dir, _, _ = _claude_shim(tmp_path)

        new_repo = home / "new-repo"
        result = _run_script(str(new_repo), home=home, bin_dir=bin_dir)

        assert result.returncode == 1
        assert _BACKUP_DIR_REFUSAL_FRAGMENTS[kind] in result.stderr
        assert "unstowing" not in result.stdout
        assert "moving" not in result.stdout
        assert observe_backup_dir() == untouched_backup_dir
        assert old_repo.is_dir()
        assert not new_repo.exists()
        assert (home / ".claude" / "hooks").resolve() == (old_repo / "claude" / ".claude" / "hooks").resolve()
        assert (home / ".claude" / "skills").resolve() == (old_repo / "claude-skills" / "skills").resolve()

    def test_repair_refuses_for_tree_folded_claude(self, tmp_path: Path, kind: str) -> None:
        home = tmp_path / "home"
        old_repo = _make_repo(tmp_path, "old-repo")
        _stow_tree_folded(old_repo, home)
        new_repo = tmp_path / "new-repo"
        old_repo.rename(new_repo)
        observe_backup_dir, untouched_backup_dir = _plant_unusable_backup_dir(home, tmp_path, kind)
        bin_dir, _, _ = _claude_shim(tmp_path)

        result = _run_script("--repair", "--allow-outside-home", str(new_repo), home=home, bin_dir=bin_dir)

        assert result.returncode == 1
        assert _BACKUP_DIR_REFUSAL_FRAGMENTS[kind] in result.stderr
        assert observe_backup_dir() == untouched_backup_dir
        assert (home / ".claude").is_symlink()
        assert not (home / ".claude").exists()


class TestRepairTreeFoldedForm:
    def test_repair_recovers_tree_folded_claude(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        old_repo = _make_repo(tmp_path, "old-repo")
        _stow_tree_folded(old_repo, home)
        assert (home / ".claude").is_symlink()  # sanity: tree-folded, not per-entry

        new_repo = tmp_path / "new-repo"
        old_repo.rename(new_repo)
        assert not (home / ".claude").exists()  # dangling

        bin_dir, remove_log, add_log = _claude_shim(tmp_path)

        result = _run_script("--repair", "--allow-outside-home", str(new_repo), home=home, bin_dir=bin_dir)

        assert result.returncode == 0, result.stderr
        assert (home / ".claude" / "hooks" / "_lib.sh").is_file()
        backup_dir = home / ".claude-config-relocate-backup"
        assert backup_dir.is_dir()
        assert any(entry.name.startswith(".claude.") for entry in backup_dir.iterdir())
        assert "no dangling stow-managed entries found to quarantine" not in result.stdout


def _remove_dangling_links(directory: Path) -> None:
    for entry in directory.iterdir():
        if entry.is_symlink() and not entry.exists():
            entry.unlink()


class TestRepairSweepsEachLocation:
    @pytest.mark.parametrize("dangling_location", ["tree-folded ~/.claude", "per-entry ~/.claude/*", "~/.local/bin/*"])
    def test_repair_quarantines_when_only_one_location_holds_a_dangling_link(
        self, tmp_path: Path, dangling_location: str
    ) -> None:
        """Each location's quarantine result feeds the sweep's "found
        something" report separately, so a run where only one location is
        dangling pins that location's own contribution."""
        home = tmp_path / "home"
        old_repo = _make_repo(tmp_path, "old-repo")
        if dangling_location == "tree-folded ~/.claude":
            _stow_tree_folded(old_repo, home)
        else:
            _stow(old_repo, home)
        new_repo = tmp_path / "new-repo"
        old_repo.rename(new_repo)
        if dangling_location == "~/.local/bin/*":
            _remove_dangling_links(home / ".claude")
        else:
            _remove_dangling_links(home / ".local" / "bin")
        bin_dir, _, _ = _claude_shim(tmp_path)

        result = _run_script("--repair", "--allow-outside-home", str(new_repo), home=home, bin_dir=bin_dir)

        assert result.returncode == 0, result.stderr
        assert "quarantining dangling" in result.stdout
        assert "no dangling stow-managed entries found to quarantine" not in result.stdout


class TestRepairQuarantineInvariant:
    def test_dot_named_dangling_link_is_left_in_place(self, tmp_path: Path) -> None:
        """The sweep skips names that start with a dot, so a dangling
        dot-named link survives next to a non-dot one that is quarantined."""
        home = tmp_path / "home"
        old_repo = _make_repo(tmp_path, "old-repo")
        _stow(old_repo, home)
        new_repo = tmp_path / "new-repo"
        old_repo.rename(new_repo)
        dot_named_link = home / ".claude" / ".dangling-dot-entry"
        dot_named_link_text = str(tmp_path / "nowhere")
        dot_named_link.symlink_to(dot_named_link_text)
        bin_dir, _, _ = _claude_shim(tmp_path)

        result = _run_script("--repair", "--allow-outside-home", str(new_repo), home=home, bin_dir=bin_dir)

        assert result.returncode == 0, result.stderr
        assert dot_named_link.is_symlink()
        assert os.readlink(dot_named_link) == dot_named_link_text
        backup_names = {entry.name for entry in (home / ".claude-config-relocate-backup").iterdir()}
        assert not any(name.startswith(".dangling-dot-entry") for name in backup_names)
        assert any(name.startswith("hooks.") for name in backup_names)

    def test_live_symlink_and_real_directory_left_untouched(self, tmp_path: Path) -> None:
        """Only a confirmed-broken symlink is quarantined — a live
        (non-broken) symlink and a real directory sitting alongside the
        dangling stow-managed entries must survive untouched."""
        home = tmp_path / "home"
        old_repo = _make_repo(tmp_path, "old-repo")
        _stow(old_repo, home)

        new_repo = tmp_path / "new-repo"
        old_repo.rename(new_repo)

        live_target = tmp_path / "live-target"
        live_target.mkdir()
        (home / ".claude" / "live-thing").symlink_to(live_target)
        (home / ".claude" / "real-thing").mkdir()

        bin_dir, remove_log, add_log = _claude_shim(tmp_path)

        result = _run_script("--repair", "--allow-outside-home", str(new_repo), home=home, bin_dir=bin_dir)

        assert result.returncode == 0, result.stderr
        assert (home / ".claude" / "live-thing").resolve() == live_target.resolve()
        assert (home / ".claude" / "real-thing").is_dir()
        assert not (home / ".claude" / "real-thing").is_symlink()

        backup_dir = home / ".claude-config-relocate-backup"
        backup_basenames = {entry.name.split(".", 1)[0] for entry in backup_dir.iterdir()}
        assert "hooks" in backup_basenames
        assert "live-thing" not in backup_basenames
        assert "real-thing" not in backup_basenames

    def test_repair_refuses_when_new_path_is_not_a_legitimate_checkout(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        old_repo = _make_repo(tmp_path, "old-repo")
        _stow(old_repo, home)
        new_repo = tmp_path / "new-repo"
        old_repo.rename(new_repo)
        (new_repo / ".claude-plugin" / "marketplace.json").unlink()  # break the canary

        bin_dir, _, _ = _claude_shim(tmp_path)
        result = _run_script("--repair", "--allow-outside-home", str(new_repo), home=home, bin_dir=bin_dir)

        assert result.returncode != 0
        assert "does not look like a claude-config checkout" in result.stderr
        # Nothing quarantined -- positive evidence must come BEFORE any ~/.claude write.
        assert not (home / ".claude-config-relocate-backup").exists()

    def test_same_named_dangling_links_get_their_own_backups(self, tmp_path: Path) -> None:
        """Run directly: two dangling links with one name, in different dirs, quarantined by consecutive calls."""
        home = tmp_path / "home"
        (home / ".local" / "bin").mkdir(parents=True)
        (home / ".claude").mkdir()
        first_link = home / ".claude" / "dup-name"
        second_link = home / ".local" / "bin" / "dup-name"
        first_link.symlink_to(tmp_path / "gone-one")
        second_link.symlink_to(tmp_path / "gone-two")

        result = subprocess.run(
            ["bash", "-c", 'source "$1"; _quarantine_if_dangling "$2"; _quarantine_if_dangling "$3"',
             "_", str(_SCRIPT), str(first_link), str(second_link)],
            capture_output=True, text=True, check=False, env=_script_env(home), timeout=_SUBPROCESS_TIMEOUT_SECONDS,
        )

        assert result.returncode == 0, result.stderr
        backups = sorted((home / ".claude-config-relocate-backup").glob("dup-name.*"))
        assert sorted(os.readlink(backup) for backup in backups) == sorted(
            [str(tmp_path / "gone-one"), str(tmp_path / "gone-two")]
        )

    def test_a_failed_move_after_the_placeholder_leaves_no_placeholder(self, tmp_path: Path) -> None:
        """Run directly, with `mv` failing for a destination in the backup dir: the real fault arrives only after
        the placeholder file exists, which a read-only backup dir cannot reproduce."""
        home = tmp_path / "home"
        (home / ".claude").mkdir(parents=True)
        dangling = home / ".claude" / "dup-name"
        dangling.symlink_to(tmp_path / "gone")
        backup_dir = home / ".claude-config-relocate-backup"
        script = textwrap.dedent("""\
            source "$1"
            mv() {
              if [[ "${!#}" == "$HOME/.claude-config-relocate-backup"/* ]]; then
                printf 'mv: %s: Permission denied\\n' "${!#}" >&2
                return 1
              fi
              command mv "$@"
            }
            if _quarantine_if_dangling "$2"; then :; fi
            echo continued-after-call
        """)

        result = subprocess.run(
            ["bash", "-c", script, "_", str(_SCRIPT), str(dangling)],
            capture_output=True, text=True, check=False, env=_script_env(home), timeout=_SUBPROCESS_TIMEOUT_SECONDS,
        )

        assert result.returncode == 1
        assert "continued-after-call" not in result.stdout
        assert f"could not move {dangling} into {backup_dir}" in result.stderr
        assert dangling.is_symlink() and os.readlink(dangling) == str(tmp_path / "gone")
        assert _backup_entry_names(home) == []
