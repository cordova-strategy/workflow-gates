"""Builders shared by the declared-dirs relocate test modules: roots-file and account fixtures, and the parsers
for the script's outcome lines.
"""
from __future__ import annotations

import os
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path

from ._relocate_helpers import _make_repo, _run_sourced, _SourcedRun

_ROOTS_LABEL = "~/.claude/transcript-config-dirs"
# The reader's warning for an unusable roots-file line, to `.format(line=<N>)`.
_READER_WARNING = (
    "line {line} of " + _ROOTS_LABEL + " is not an absolute path to an existing directory, so that dir is not re-linked"
)
_PACKAGE_ROOT = "claude/.claude"
_SKILLS_ROOT = "claude-skills"
_UNIT_ROOTS = [_PACKAGE_ROOT, _SKILLS_ROOT]
# The roots-file line number every unit-layer call passes, so a backup name's `.L7.` is checkable.
_LINE = 7

_AWKWARD_ENTRY_NAME = "-a b$c]`d@e*f\\g$(touch injected)"
_AWKWARD_DIR_NAME = "-h i$j]`k@l*m\\né$(touch injected)"
# An existing variable name plus a subscript, so an indexed-array subscript built from it runs the substitution.
_SUBSCRIPT_ENTRY_NAME = "HOME[$(touch injected)]"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _write_roots_file(home: Path, lines: list[str], *, final_newline: bool = True) -> Path:
    roots_file = home / ".claude" / "transcript-config-dirs"
    roots_file.parent.mkdir(parents=True, exist_ok=True)
    roots_file.write_bytes(("\n".join(lines) + ("\n" if final_newline else "")).encode())
    return roots_file


def _add_checkout_entry(repo: Path, root: str, relative_path: str) -> Path:
    entry = repo / root / relative_path
    entry.parent.mkdir(parents=True, exist_ok=True)
    entry.write_text("entry\n")
    return entry


def _stale_link(
    account_dir: Path, relative_path: str, old_checkout: Path, root: str = _PACKAGE_ROOT, *, absolute: bool = False
) -> str:
    """A dangling link at `relative_path` into the nonexistent `old_checkout`, with the text Stow writes
    (relative to the link's parent) or the absolute target on request. Returns the text."""
    link = account_dir / relative_path
    link.parent.mkdir(parents=True, exist_ok=True)
    target = old_checkout / root / relative_path
    text = str(target) if absolute else os.path.relpath(target, link.parent.resolve())
    link.symlink_to(text)
    return text


def _live_link(account_dir: Path, relative_path: str, checkout: Path, root: str = _PACKAGE_ROOT) -> str:
    link = account_dir / relative_path
    link.parent.mkdir(parents=True, exist_ok=True)
    text = os.path.relpath(checkout / root / relative_path, link.parent.resolve())
    link.symlink_to(text)
    return text


def _decoy_link(directory: Path, old_checkout: Path) -> str:
    """A dangling `decoy-link` whose text ends in the `hooks` position's shape but sits at no checkout position."""
    text = os.path.relpath(old_checkout / _PACKAGE_ROOT / "hooks", directory.resolve())
    (directory / "decoy-link").symlink_to(text)
    return text


_OUTCOME_LINE = re.compile(
    r"the dir on line (\d+) of ~/\.claude/transcript-config-dirs: re-pointed (\d+), could not re-point (\d+), "
    r"left (\d+) alone, could not search (\d+)"
)
_LEFT_ALONE_LINE = re.compile(
    r"left (.+) alone in the dir on line (\d+) of ~/\.claude/transcript-config-dirs: "
    r"it does not resolve and is not recognized as this repo's link"
)


def _outcomes(stdout: str) -> list[tuple[int, ...]]:
    """Each outcome line's line number, then re-pointed, could not re-point, left alone, could not search."""
    return [tuple(int(count) for count in match.groups()) for match in _OUTCOME_LINE.finditer(stdout)]


def _left_alone(stdout: str) -> list[str]:
    return [match.group(1) for match in _LEFT_ALONE_LINE.finditer(stdout)]


def _backup_copies(home: Path, link_name: str) -> list[Path]:
    backup_dir = home / ".claude-config-relocate-backup"
    prefix = f"{link_name}.L{_LINE}."
    return sorted(entry for entry in backup_dir.iterdir() if entry.name.startswith(prefix)) if backup_dir.exists() else []


@dataclass
class _Scene:
    """One listed dir, `account`, beside a new checkout and a nonexistent old one."""

    root: Path
    home: Path
    new_repo: Path
    old_repo: Path
    account: Path
    scratch: Path
    restore_modes: list[tuple[Path, int]] = field(default_factory=list)

    def run_unit(self, *, prelude: str = "") -> _SourcedRun:
        call = ["_repoint_declared_dir", str(self.new_repo.resolve()), str(self.account.resolve()), str(_LINE), *_UNIT_ROOTS]
        try:
            return _run_sourced(self.home, [call], cwd=self.scratch, prelude=prelude)
        finally:
            self.restore()

    def restrict(self, path: Path, mode: int) -> None:
        self.restore_modes.append((path, path.stat().st_mode & 0o777))
        path.chmod(mode)

    def restore(self) -> None:
        for path, mode in reversed(self.restore_modes):
            path.chmod(mode)
        self.restore_modes.clear()

    def seam_vars(self) -> str:
        return (
            f"ACCT={shlex.quote(str(self.account.resolve()))}\n"
            f"NEW={shlex.quote(str(self.new_repo.resolve()))}\n"
            'BACKUP="$HOME/.claude-config-relocate-backup"\n'
        )


def _scene(tmp_path: Path) -> _Scene:
    home = tmp_path / "home"
    home.mkdir()
    account = tmp_path / "acct-a"
    account.mkdir()
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    return _Scene(
        root=tmp_path,
        home=home,
        new_repo=_make_repo(tmp_path, "new-repo"),
        old_repo=tmp_path / "old-repo",
        account=account,
        scratch=scratch,
    )


@dataclass
class _RunnerScene:
    home: Path
    new_repo: Path
    scratch: Path
    skip_line: str | None = None
    repointed: list[Path] = field(default_factory=list)
    unchanged: dict[Path, str] = field(default_factory=dict)
    expected_counts: tuple[int, int, int, int] | None = None
    # The dirs the roots file lists, in their absolute spelling, whose paths no output may name.
    listed_dirs: list[Path] = field(default_factory=list)

    def write_roots_file(self, *entries: tuple[str, Path]) -> None:
        """Writes the roots file and `listed_dirs` from the same entries, so the dirs a canary checks are the dirs listed."""
        _write_roots_file(self.home, [spelling for spelling, _ in entries])
        self.listed_dirs = [listed_dir for _, listed_dir in entries]


def _runner_scene_base(
    tmp_path: Path, *, home: Path | None = None, new_repo_parent: Path | None = None, new_repo_name: str = "new-repo"
) -> _RunnerScene:
    """A home holding an empty `.claude` and a new checkout under `new_repo_parent` (default: `tmp_path`).
    A `home` passed in may be a symlink to a directory that exists."""
    home = tmp_path / "home" if home is None else home
    (home / ".claude").mkdir(parents=True, exist_ok=True)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    new_repo = _make_repo(tmp_path if new_repo_parent is None else new_repo_parent, new_repo_name)
    return _RunnerScene(home=home, new_repo=new_repo, scratch=scratch)
