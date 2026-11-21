"""The scope a command's figures may be published under: one account, the working directory's repository only.

Holds the single-account root, the refusal of any wider scope, the scope header, and the selection of this
repository's review-ledger files, so every command that publishes a repository-scoped figure shares one rule for
each. The helpers are independent: a command refuses a wider scope only by calling `_refuse_wider_scope`. The root,
refusal and header helpers take the command's label, which prefixes their messages.

Imports sibling modules by module (attribute access, not by name) -- see scope.py's own top-of-file comment for why.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
from collections import Counter
from collections.abc import Iterable, Sequence
from pathlib import Path

from transcript_analysis import scope

# Scan-gap level tag for the review-ledger directory listing.
_GAP_LEDGER_DIR = "ledger-dir"


def _single_account_roots(command_label: str) -> list[Path]:
    try:
        return [scope.config_dir() / "projects"]
    except ValueError as exc:
        print(f"{command_label}: {exc}", file=sys.stderr)
        sys.exit(2)


def _refuse_wider_scope(args: argparse.Namespace, roots: Sequence[Path], command_label: str) -> None:
    """Exit 2 unless the scan covers the working directory's repository on exactly one account."""
    if not bool(getattr(args, "this_repo", False)) or getattr(args, "projects", None) not in (None, "*"):
        print(
            f"{command_label}: requires --this-repo and refuses any --projects scope -- see docs/transcript-analysis.md",
            file=sys.stderr,
        )
        sys.exit(2)
    # Defense-in-depth: _single_account_roots yields one root, but a direct caller of a report function bypasses it.
    if len(roots) != 1:
        print(
            f"{command_label}: resolved to more than one root -- refusing to report a multi-account figure",
            file=sys.stderr,
        )
        sys.exit(2)


def _scope_header(scope_label: str, command_label: str) -> str:
    title = command_label.upper().replace("-", " ")
    return (
        f"{title} SOURCES ({scope_label}; reads one account (the active account), the working directory's repository only;"
        f" {scope.TRANSCRIPT_CONFIG_DIRS_LABEL} not consulted)"
    )


def _ledger_repo_hash(path: str) -> str:
    """The sha256 of the path's bytes, the formula `_marker_lib_repo_hash` in hooks/_lib.sh defines."""
    return hashlib.sha256(os.fsencode(path)).hexdigest()


def _this_repo_ledger_files(ledger_dir: Path, worktree_paths: Iterable[str], gaps: Counter[str]) -> list[Path]:
    """The ledger files directly under `ledger_dir` named for one of `worktree_paths`, sorted by name.

    A file is named `<repo hash>.<slot>.jsonl`, and the repo hash digests the path the writer ran in. Each path is
    hashed as printed and as resolved, because `git worktree list` may print a symlinked path the writer saw resolved.
    Identity is the path string, so a deleted worktree path that is later reused matches the earlier checkout's files.
    Opens no file: a dangling symlink with a matching name stays in the list and fails when the caller opens it.
    """
    worktree_paths = list(worktree_paths)
    matching_hashes = {_ledger_repo_hash(path) for path in worktree_paths}
    matching_hashes.update(_ledger_repo_hash(str(Path(path).resolve())) for path in worktree_paths)
    ledger_files = []
    for entry in scope._list_dir_recording_gaps(ledger_dir, gaps, _GAP_LEDGER_DIR):
        repo_hash, has_slot, _slot = entry.name.removesuffix(".jsonl").partition(".")
        if not entry.name.endswith(".jsonl") or not has_slot or repo_hash not in matching_hashes:
            continue
        try:
            if entry.is_dir():
                continue
        except OSError:
            # An entry that cannot be statted stays listed, so the caller's open counts it as unreadable.
            pass
        ledger_files.append(entry)
    return ledger_files
