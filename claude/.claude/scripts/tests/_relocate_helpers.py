"""Helpers shared by the relocate-claude-config.sh test modules.

Tests drive the REAL `stow`/`stow -D` binary (not a stub): stow's own symlink-adopt semantics are exactly
what the script's correctness depends on, and a fake stow would let a wrong working directory or -t/-d
targeting pass silently. This module shims only the `claude` CLI on PATH, matching
test_update_claude_config_plugins.py's precedent.

`_run_sourced` sources the script and calls its functions in one shell. It keeps the caller's PATH with no
`claude` shim, so a sourced call that can reach `claude` passes a `path=` that leads with a shim dir.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import textwrap
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "relocate-claude-config.sh"
# The hang guard for the subprocess calls that pass it as `timeout`: a loop that never ends fails the test instead of stalling CI.
_SUBPROCESS_TIMEOUT_SECONDS = 60

# chmod 0o555 does not stop root from writing, so the unwritable-directory cases cannot fail as intended.
requires_non_root = pytest.mark.skipif(os.geteuid() == 0, reason="root ignores the read-only modes this case relies on")


# ---------------------------------------------------------------------------
# Fixtures: a fake claude-config checkout, real stow, and a claude CLI shim
# ---------------------------------------------------------------------------


def _make_repo(tmp_path: Path, name: str = "repo") -> Path:
    """A fake claude-config checkout with just enough shape for the script's
    canary check (.claude-plugin/marketplace.json), its own copy of the
    script under test (what the final `install -m 755` self-copy step
    reads from), one hook file (per-entry symlink probe target), and one
    ~/.local/bin wrapper (exercises stow's second target tree), plus one
    claude-skills package entry (the package every run also re-links)."""
    repo = tmp_path / name
    hooks_dir = repo / "claude" / ".claude" / "hooks"
    scripts_dir = repo / "claude" / ".claude" / "scripts"
    local_bin_dir = repo / "claude" / ".local" / "bin"
    plugin_dir = repo / ".claude-plugin"
    skill_dir = repo / "claude-skills" / "skills" / "example"
    hooks_dir.mkdir(parents=True)
    scripts_dir.mkdir(parents=True)
    local_bin_dir.mkdir(parents=True)
    plugin_dir.mkdir(parents=True)
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# example skill\n")

    (hooks_dir / "_lib.sh").write_text("# fake _lib.sh\n")
    shutil.copy2(_SCRIPT, scripts_dir / "relocate-claude-config.sh")
    (scripts_dir / "relocate-claude-config.sh").chmod(0o755)
    (local_bin_dir / "some-wrapper").write_text("#!/bin/bash\necho wrapper\n")
    (local_bin_dir / "some-wrapper").chmod(0o755)
    (plugin_dir / "marketplace.json").write_text('{"plugins": []}\n')
    return repo


def _stow(repo: Path, home: Path, *, with_claude_skills: bool = False) -> subprocess.CompletedProcess:
    """Stow `repo`'s claude package into `home`, per-entry form (both
    target directories pre-created, matching install.sh's own tree-fold
    guard). `with_claude_skills` also stows the claude-skills package into
    ~/.claude with plain stow, as install.sh does, so ~/.claude/skills is one
    folded link into `repo`."""
    (home / ".claude").mkdir(parents=True, exist_ok=True)
    (home / ".local" / "bin").mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["stow", "-v", "--adopt", "-t", str(home), "claude"],
        cwd=repo, check=True, capture_output=True, text=True, env=_script_env(home),
    )
    if with_claude_skills:
        # A real ~/.claude holds untracked state. With only stow-managed links
        # in it, `stow -D claude` refolds ~/.claude into a link to the
        # claude-skills package.
        (home / ".claude" / "untracked-state.txt").write_text("untracked\n")
        subprocess.run(
            ["stow", "-v", "-t", str(home / ".claude"), "claude-skills"],
            cwd=repo, check=True, capture_output=True, text=True, env=_script_env(home),
        )
    return result


def _stow_tree_folded(repo: Path, home: Path) -> subprocess.CompletedProcess:
    """Stow with ~/.claude deliberately NOT pre-created, so stow tree-folds
    it into a single symlink — the legacy form."""
    (home / ".local" / "bin").mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        ["stow", "-v", "--adopt", "-t", str(home), "claude"],
        cwd=repo, check=True, capture_output=True, text=True, env=_script_env(home),
    )


def _make_claude_shim(
    bin_dir: Path,
    marketplace_entries: list[dict],
    remove_log: Path,
    add_log: Path,
    fail_subcommands: frozenset[str] = frozenset(),
) -> None:
    """`fail_subcommands` names which of {"remove", "add"} should exit
    non-zero instead of logging -- for pinning sync_marketplace_registration's
    explicit error-handling around those calls."""
    marketplace_list_json = json.dumps(marketplace_entries)
    fail_subcommands_repr = repr(set(fail_subcommands))
    shim = textwrap.dedent(f"""\
        #!/usr/bin/env python3
        import sys

        args = sys.argv[1:]
        fail_subcommands = {fail_subcommands_repr}

        def is_subcommand(*parts):
            return args[:len(parts)] == list(parts)

        if is_subcommand("plugin", "marketplace", "list") and "--json" in args:
            print({marketplace_list_json!r})
            sys.exit(0)

        if is_subcommand("plugin", "marketplace", "remove"):
            if "remove" in fail_subcommands:
                print("simulated remove failure", file=sys.stderr)
                sys.exit(1)
            with open({str(remove_log)!r}, "a") as f:
                f.write(args[3] + chr(10))
            sys.exit(0)

        if is_subcommand("plugin", "marketplace", "add"):
            if "add" in fail_subcommands:
                print("simulated add failure", file=sys.stderr)
                sys.exit(1)
            # The path is passed as `--scope user -- <path>` (row H) so it is
            # always the last argument, regardless of flag order.
            with open({str(add_log)!r}, "a") as f:
                f.write(args[-1] + chr(10))
            sys.exit(0)

        print("Unhandled: " + str(args), file=sys.stderr)
        sys.exit(1)
    """)
    shim_path = bin_dir / "claude"
    shim_path.write_text(shim)
    shim_path.chmod(0o755)


def _read_log(log: Path) -> list[str]:
    if not log.exists():
        return []
    return [line for line in log.read_text().splitlines() if line]


def _script_env(home: Path, *path_dirs: Path) -> dict[str, str]:
    """The environment for a run against the fake `home`, with `path_dirs`
    (the claude shim dir, the installed-copy dir) ahead of the real PATH."""
    env = dict(os.environ)
    env["HOME"] = str(home)
    # Stow reads STOW_DIR ahead of its working directory, so an exported value would redirect every stow run.
    env.pop("STOW_DIR", None)
    if path_dirs:
        env["PATH"] = ":".join([*(str(path_dir) for path_dir in path_dirs), env["PATH"]])
    return env


def _run_script(
    *args: str,
    home: Path,
    bin_dir: Path | None = None,
    leading_path_dirs: Sequence[Path] = (),
    timeout: float | None = None,
) -> subprocess.CompletedProcess:
    """Run the whole script against the fake `home`. `leading_path_dirs` (a shim dir, say) precede `bin_dir`
    on PATH, and `timeout` ends a hung run as a failure."""
    env = _script_env(home, *leading_path_dirs, *([bin_dir] if bin_dir is not None else []))
    return subprocess.run(
        [str(_SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=timeout,
    )


def _last_nonempty_line(text: str) -> str:
    """The last line holding anything: the closing text ends with a newline."""
    return [line for line in text.splitlines() if line.strip()][-1]


def _claude_shim(
    tmp_path: Path,
    marketplace_entries: list[dict] | None = None,
    fail_subcommands: frozenset[str] = frozenset(),
) -> tuple[Path, Path, Path]:
    """Build a bin_dir with the claude shim installed; return (bin_dir, remove_log, add_log)."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    remove_log = tmp_path / "remove.log"
    add_log = tmp_path / "add.log"
    _make_claude_shim(bin_dir, marketplace_entries or [], remove_log, add_log, fail_subcommands=fail_subcommands)
    return bin_dir, remove_log, add_log


_BACKUP_DIR_REFUSAL_FRAGMENTS = {
    "symlink": "already exists as a symlink",
    "regular file": "exists and is not a directory",
}


def _plant_unusable_backup_dir(
    home: Path, tmp_path: Path, kind: str
) -> tuple[Callable[[], object], object]:
    """Make $BACKUP_DIR a symlink to an empty directory or a regular file.
    Returns `(observe, untouched)`: `observe()` reads what the guard must
    leave alone, and equals `untouched` until something writes there."""
    backup_path = home / ".claude-config-relocate-backup"
    if kind == "symlink":
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        backup_path.symlink_to(elsewhere)
        return (lambda: list(elsewhere.iterdir())), []
    backup_path.write_text("not a directory\n")
    return backup_path.read_text, "not a directory\n"


# A space, a single quote, `$x` and one unpaired backtick: a double-quoted
# print of this path either expands `$x` or fails to parse.
_AWKWARD_DESTINATION_NAME = "new repo's $x`"


def _run_printed_retry_line(
    first_run_stderr: str, home: Path, bin_dir: Path, timeout: float | None = None
) -> subprocess.CompletedProcess:
    """Run the line a failed run's stderr ends with, as a user would: bash
    resolves its command through PATH, so a missing installed copy fails here
    instead of falling through to a real copy elsewhere on PATH."""
    installed_copy = home / ".local" / "bin" / "relocate-claude-config"
    assert installed_copy.is_file() and not installed_copy.is_symlink(), f"no regular-file installed copy at {installed_copy}"
    return subprocess.run(
        ["bash", "-c", _last_nonempty_line(first_run_stderr)],
        capture_output=True, text=True, check=False,
        env=_script_env(home, home / ".local" / "bin", bin_dir), timeout=timeout,
    )


def _backup_entry_names(home: Path) -> list[str]:
    backup_dir = home / ".claude-config-relocate-backup"
    return sorted(entry.name for entry in backup_dir.iterdir()) if backup_dir.exists() else []


def _relocation_args_for_mode(tmp_path: Path, home: Path, old_repo: Path, mode: str) -> tuple[Path, list[str]]:
    """The destination and script args for a relocation run. Primary moves the
    checkout itself; repair first renames it to the destination, as if moved
    outside a Claude Code session."""
    if mode == "primary":
        new_repo = home / "new-repo"
        return new_repo, [str(new_repo)]
    new_repo = tmp_path / "new-repo"
    old_repo.rename(new_repo)
    return new_repo, ["--repair", "--allow-outside-home", str(new_repo)]


_BASH = shutil.which("bash") or "bash"


def _intercepting_function(tool: str, condition: str, body: str | None = None) -> str:
    """Bash text for a function that shadows `tool`. `condition` tests `$destination` (the last
    argument) and `$forced` (a flag argument before `--` holds an `f`). `body` runs when it holds
    and defaults to failing with a real-shaped message that names the destination."""
    if body is None:
        body = f"printf '{tool}: %s: Permission denied\\n' \"$destination\" >&2; return 1"
    return (
        f"{tool}() {{\n"
        '  local destination="${!#}" forced=false arg\n'
        '  for arg in "$@"; do\n'
        '    case "$arg" in --) break ;; -*f*) forced=true ;; esac\n'
        "  done\n"
        f"  if {condition}; then {body}; fi\n"
        f'  command {tool} "$@"\n'
        "}\n"
    )


@dataclass
class _SourcedRun:
    returncode: int
    stdout: str
    stderr: str
    call_outputs: list[str]
    call_statuses: list[int]
    tail: str


_CALL_MARKER = re.compile(r"\n@@CALL (\d+) (\d+)@@\n")


def _run_sourced(
    home: Path,
    steps: list[str | list[str]],
    *,
    cwd: Path,
    prelude: str = "",
    bare: bool = False,
    path: str | None = None,
) -> _SourcedRun:
    """Source the script and run `steps` in one shell: a `str` is a bash fragment, a `list` is one call's
    argv. A marker line after each call ends its output slice. By default each call is an `if` condition,
    as production runs the units, so errexit is off. `bare` calls it plain with errexit on, as production
    calls the runner."""
    lines = ['source "$1"', prelude]
    call_count = 0
    for step in steps:
        if isinstance(step, str):
            lines.append(step)
            continue
        command = shlex.join(step)
        if bare:
            lines += [command, "status=0"]
        else:
            lines.append(f"if {command}; then status=0; else status=$?; fi")
        lines.append(f'printf "\\n@@CALL {call_count} %s@@\\n" "$status"')
        call_count += 1
    env = _script_env(home)
    if path is not None:
        env["PATH"] = path
    completed = subprocess.run(
        [_BASH, "-c", "\n".join(lines), "relocate-claude-config", str(_SCRIPT)],
        cwd=cwd, capture_output=True, text=True, env=env, check=False, timeout=_SUBPROCESS_TIMEOUT_SECONDS,
    )
    parts = _CALL_MARKER.split(completed.stdout)
    return _SourcedRun(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        call_outputs=parts[0::3][:-1],
        call_statuses=[int(status) for status in parts[2::3]],
        tail=parts[-1],
    )
