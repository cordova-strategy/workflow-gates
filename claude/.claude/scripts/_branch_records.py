"""Locates an account's directory in the agent-branch-records archive, for readers.

`docs/agent-branch-records.md` § "Snapshots" is the home of the layout this mirrors. The root path and
the marker name repeat `_branch-records-lib.sh`'s values, and `tests/test__branch_records.py` pins them
to the lib. This module never reads `claude-config.toml` or the `agent_branch_records` key, because a
reader serves archived data whether or not the key is still on. No function reads HOME or the environment,
and none writes, lists or globs the archive root.

Only `archive_subtree` attests anything about a path, and only for the instant of the call. A caller
reads the archive through it and re-validates each entry it opens, because the archive's contents are untrusted.
"""
from __future__ import annotations

import enum
import os
import stat
from dataclasses import dataclass
from pathlib import Path

ARCHIVE_ROOT_RELATIVE_PATH = Path(".local") / "state" / "agent-branch-records"
SENTINEL_NAME = ".agent-branch-records-root"


class SubtreeState(enum.StrEnum):
    UNRESOLVABLE = "unresolvable"
    UNMARKED = "unmarked"
    UNREADABLE = "unreadable"
    ABSENT = "absent"
    PRESENT = "present"


@dataclass(frozen=True)
class ArchiveSubtree:
    """`directory` is set only when `state` is `present`.

    `present` is a verdict valid at the instant of the call. `directory` is the unresolved path, and its contents
    are untrusted: a caller re-validates each entry at use time with a no-follow `lstat`.
    """

    state: SubtreeState
    directory: Path | None = None


def encode_component(path: str | os.PathLike[str]) -> str:
    """Encodes `path` as one path component, replacing `%` before `/` so a literal `%2F` stays distinct from an encoded slash."""
    return os.fspath(path).replace("%", "%25").replace("/", "%2F")


def archive_root(home: str | os.PathLike[str] | None) -> Path | None:
    """The archive root under `home`, or None unless `home` is a non-empty absolute path.

    The writer reads an empty HOME as the root `/.local/state/agent-branch-records`, which this refuses to resolve.
    The returned path attests nothing: it is not checked for a marker, a link or containment. Read through `archive_subtree`.
    """
    if home is None:
        return None
    home_text = os.fspath(home)
    if not home_text or "\0" in home_text or not os.path.isabs(home_text):
        return None
    return Path(home_text) / ARCHIVE_ROOT_RELATIVE_PATH


def account_directory(config_dir: str | os.PathLike[str], home: str | os.PathLike[str] | None) -> Path | None:
    """The account's archive directory, or None when `home` or `config_dir` is unusable or `config_dir` is no directory.

    The writer canonicalizes `config_dir` with `cd -P` and `pwd -P` inside command substitutions, which drop trailing
    newlines. This drops them from `config_dir` and from its canonical path too.
    The one known divergence is any `//` prefix bash's `pwd -P` prints, which `os.path.realpath` never keeps.
    The writer's directory then differs from this one, so a reader misses what the writer archived.
    The returned path attests nothing: it is not checked for a marker, a link or containment. Read through `archive_subtree`.
    """
    root = archive_root(home)
    config_dir_text = os.fspath(config_dir).rstrip("\n")
    if root is None or not os.path.isabs(config_dir_text):
        return None
    try:
        canonical_config_dir = os.path.realpath(config_dir_text, strict=True)
    except (OSError, ValueError):
        return None
    if not os.path.isdir(canonical_config_dir):
        return None
    return root / encode_component(canonical_config_dir.rstrip("\n"))


def archive_subtree(
    config_dir: str | os.PathLike[str], name: str, home: str | os.PathLike[str] | None
) -> ArchiveSubtree:
    """Classifies the account's subtree `name`, a single path component, taking the first state that applies.

    The root's marker is checked before anything under the root, so an archive volume that is not mounted
    is never read as an empty one. Only a marker stat that finds nothing or a non-regular file gives
    `unmarked`: any other stat failure gives `unreadable`.

    Other `unreadable` causes:
    - The account directory is a link, or exists as anything but a directory.
    - The subtree is not a directory.
    - The subtree's real path is not exactly the account directory's real path joined with `name`.
    - Any other failed stat, lstat or realpath on the account directory or the subtree,
      including a dangling or looping subtree link.
    """
    if not name or name in (".", "..") or "/" in name or "\0" in name:
        raise ValueError(f"an archive subtree name must be one path component, got {name!r}")

    account_dir = account_directory(config_dir, home)
    if account_dir is None:
        return ArchiveSubtree(SubtreeState.UNRESOLVABLE)
    root = account_dir.parent

    try:
        # A stat follows a link, as the writer's `test -f` does.
        marker_mode = os.stat(root / SENTINEL_NAME).st_mode
    except (FileNotFoundError, NotADirectoryError):
        return ArchiveSubtree(SubtreeState.UNMARKED)
    except OSError:
        return ArchiveSubtree(SubtreeState.UNREADABLE)
    if not stat.S_ISREG(marker_mode):
        return ArchiveSubtree(SubtreeState.UNMARKED)

    try:
        account_mode = os.lstat(account_dir).st_mode
    except FileNotFoundError:
        return ArchiveSubtree(SubtreeState.ABSENT)
    except OSError:
        return ArchiveSubtree(SubtreeState.UNREADABLE)
    # A link here could name a sibling account's directory.
    if not stat.S_ISDIR(account_mode):
        return ArchiveSubtree(SubtreeState.UNREADABLE)

    subtree = account_dir / name
    try:
        os.lstat(subtree)
    except FileNotFoundError:
        return ArchiveSubtree(SubtreeState.ABSENT)
    except OSError:
        return ArchiveSubtree(SubtreeState.UNREADABLE)
    try:
        real_account_dir = Path(os.path.realpath(account_dir, strict=True))
        real_subtree = Path(os.path.realpath(subtree, strict=True))
    except OSError:
        return ArchiveSubtree(SubtreeState.UNREADABLE)
    # Equality, not containment: a link to a sibling subtree or a deeper entry of the same account is not this subtree.
    if not real_subtree.is_dir() or real_subtree != real_account_dir / name:
        return ArchiveSubtree(SubtreeState.UNREADABLE)
    return ArchiveSubtree(SubtreeState.PRESENT, subtree)
