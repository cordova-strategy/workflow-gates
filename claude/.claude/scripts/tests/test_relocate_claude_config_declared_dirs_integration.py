"""Integration-layer tests for relocate-claude-config.sh's re-pointing of the config dirs listed in
~/.claude/transcript-config-dirs: whole runs in both modes, for wiring only.
"""
from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from ._declared_dirs_helpers import (
    _PACKAGE_ROOT,
    _ROOTS_LABEL,
    _SKILLS_ROOT,
    _SUBPROCESS_TIMEOUT_SECONDS,
    _left_alone,
    _live_link,
    _outcomes,
    _stale_link,
    _write_roots_file,
)
from .test_relocate_claude_config import (
    _SCRIPT,
    _claude_shim,
    _make_repo,
    _relocation_args_for_mode,
    _run_printed_retry_line,
    _script_env,
    _stow,
)


@dataclass
class _ListedAccounts:
    home: Path
    bin_dir: Path
    new_repo: Path
    args: list[str]
    accounts: dict[str, Path]
    old_texts: dict[str, str]
    listing_of_b: list[str]


def _build_listed_accounts(tmp_path: Path, mode: str) -> _ListedAccounts:
    home = tmp_path / "home"
    old_repo = _make_repo(tmp_path, "old-repo")
    _stow(old_repo, home, with_claude_skills=True)
    bin_dir, _, _ = _claude_shim(tmp_path)
    other_repo = _make_repo(tmp_path, "other-repo")
    accounts = {name: tmp_path / name for name in ("acct-a", "acct-b", "acct-c", "acct-unlisted")}
    old_texts = {
        "a-hooks": _stale_link(accounts["acct-a"], "hooks", old_repo),
        "a-example": _stale_link(accounts["acct-a"], "skills/example", old_repo, _SKILLS_ROOT),
        "a-retired": _stale_link(accounts["acct-a"], "retired", old_repo),
        "unlisted-hooks": _stale_link(accounts["acct-unlisted"], "hooks", old_repo),
        "c-hooks": _live_link(accounts["acct-c"], "hooks", other_repo),
    }
    accounts["acct-b"].mkdir()
    (accounts["acct-b"] / "settings.json").write_text("{}\n")
    (accounts["acct-b"] / "notes.txt").write_text("notes\n")
    old_texts["b-scripts"] = str(tmp_path / "elsewhere" / "scripts")
    (accounts["acct-b"] / "scripts").symlink_to(old_texts["b-scripts"])
    _write_roots_file(
        home,
        [
            "# my accounts",
            "~/.claude",
            str(accounts["acct-a"]),
            str(tmp_path / "acct-missing"),
            str(accounts["acct-b"]),
            str(accounts["acct-c"]),
        ],
    )
    new_repo, args = _relocation_args_for_mode(tmp_path, home, old_repo, mode)
    return _ListedAccounts(
        home=home,
        bin_dir=bin_dir,
        new_repo=new_repo,
        args=args,
        accounts=accounts,
        old_texts=old_texts,
        listing_of_b=sorted(entry.name for entry in accounts["acct-b"].iterdir()),
    )


@pytest.mark.parametrize("mode", ["primary", "repair"])
def test_both_modes_repoint_listed_dirs_and_report_each(tmp_path: Path, mode: str) -> None:
    scene = _build_listed_accounts(tmp_path, mode)
    acct_a = scene.accounts["acct-a"]

    result = subprocess.run(
        [str(_SCRIPT), *scene.args],
        capture_output=True, text=True, check=False, env=_script_env(scene.home, scene.bin_dir),
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
    )

    assert result.returncode == 0, result.stderr
    assert (acct_a / "hooks").resolve() == (scene.new_repo / _PACKAGE_ROOT / "hooks").resolve()
    assert (acct_a / "skills" / "example").resolve() == (scene.new_repo / _SKILLS_ROOT / "skills" / "example").resolve()
    assert os.readlink(acct_a / "retired") == scene.old_texts["a-retired"]
    assert os.readlink(scene.accounts["acct-c"] / "hooks") == scene.old_texts["c-hooks"]
    assert os.readlink(scene.accounts["acct-unlisted"] / "hooks") == scene.old_texts["unlisted-hooks"]
    assert sorted(entry.name for entry in scene.accounts["acct-b"].iterdir()) == scene.listing_of_b
    backup_dir = scene.home / ".claude-config-relocate-backup"
    numbered_backups = {entry.name: os.readlink(entry) for entry in backup_dir.iterdir() if re.search(r"\.L\d+\.", entry.name)}
    assert sorted(re.sub(r"\.[^.]+$", "", name) for name in numbered_backups) == ["example.L3", "hooks.L3"]
    assert {name.split(".")[0]: text for name, text in numbered_backups.items()} == {
        "hooks": scene.old_texts["a-hooks"],
        "example": scene.old_texts["a-example"],
    }
    assert f"the dir on line 2 of {_ROOTS_LABEL} is ~/.claude, which the stows above cover" in result.stdout
    assert _outcomes(result.stdout) == [(3, 2, 0, 0, 0), (5, 0, 0, 1, 0), (6, 0, 0, 0, 0)]
    assert _left_alone(result.stdout) == ["scripts"]
    for line_number in (2, 3, 4, 5, 6):
        assert f"checking line {line_number} of {_ROOTS_LABEL}" in result.stdout
    assert f"checking line 1 of {_ROOTS_LABEL}" not in result.stdout
    for line_number in (3, 5, 6):
        walking = result.stdout.index(f"walking the dir on line {line_number} of {_ROOTS_LABEL}")
        assert walking < result.stdout.index(f"the dir on line {line_number} of {_ROOTS_LABEL}: re-pointed")
    assert result.stderr.count("is not an absolute path to an existing directory") == 1
    assert f"line 4 of {_ROOTS_LABEL} is not an absolute path" in result.stderr
    assert "transcript-config-dirs:line-" not in result.stderr
    assert "acct-" not in result.stdout and "acct-" not in result.stderr
    assert "register-marketplace" in result.stdout
    assert "relocate-claude-config --repair [--allow-outside-home]" in result.stdout
    assert "with the flag when this run passed it" in result.stdout
    assert "gives this command write access to its links" in result.stdout
    assert "including any listed in" not in result.stdout


def _write_failing_mv_shim(shim_dir: Path, failing_destination: Path, manifest: Path, manifest_record: Path) -> None:
    """An `mv` that fails for one destination, after copying the manifest as it stands to `manifest_record`.
    Every other call goes to the real `mv`, found before the shim's directory joins PATH."""
    shim_dir.mkdir()
    real_mv = shutil.which("mv")
    assert real_mv is not None
    shim = shim_dir / "mv"
    shim.write_text(
        "#!/bin/bash\n"
        'for last_argument in "$@"; do :; done\n'
        f'if [ "$last_argument" = {shlex.quote(str(failing_destination))} ]; then\n'
        f"  cp -- {shlex.quote(str(manifest))} {shlex.quote(str(manifest_record))} 2>/dev/null\n"
        '  echo "mv: $last_argument: Permission denied" >&2\n'
        "  exit 1\n"
        "fi\n"
        f'exec {shlex.quote(real_mv)} "$@"\n'
    )
    shim.chmod(0o755)


@pytest.mark.parametrize("mode", ["primary", "repair"])
def test_a_failed_dir_exits_3_and_the_printed_retry_repoints_it(tmp_path: Path, mode: str) -> None:
    home = tmp_path / "home"
    old_repo = _make_repo(tmp_path, "old-repo")
    _stow(old_repo, home, with_claude_skills=True)
    bin_dir, _, _ = _claude_shim(tmp_path)
    failing_account = tmp_path / "acct-a"
    passing_account = tmp_path / "acct-b"
    failing_text = _stale_link(failing_account, "hooks", old_repo)
    _stale_link(passing_account, "hooks", old_repo)
    _write_roots_file(home, [str(failing_account), str(passing_account)])
    new_repo, args = _relocation_args_for_mode(tmp_path, home, old_repo, mode)
    manifest = home / ".claude-config-source"
    manifest_record = tmp_path / "manifest-at-failure"
    _write_failing_mv_shim(tmp_path / "shim-bin", failing_account / "hooks", manifest, manifest_record)
    assert not manifest.exists() or manifest.read_text().strip() != str(new_repo)

    first_run = subprocess.run(
        [str(_SCRIPT), *args],
        capture_output=True, text=True, check=False, env=_script_env(home, tmp_path / "shim-bin", bin_dir),
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
    )

    assert first_run.returncode == 3, first_run.stderr
    assert "re-linking failed for: transcript-config-dirs:line-1" in first_run.stderr
    assert "could not rename the new link over it" in first_run.stderr
    assert f"re-pointing the dir on line 1 of {_ROOTS_LABEL} failed" in first_run.stderr
    assert f"A transcript-config-dirs:line-<N> entry is the dir on line <N> of {_ROOTS_LABEL}" in first_run.stderr
    assert f"delete the dir's line from {_ROOTS_LABEL} so this command leaves it alone" in first_run.stderr
    assert "acct-" not in first_run.stderr and "acct-" not in first_run.stdout
    assert _outcomes(first_run.stdout)[0] == (1, 0, 1, 0, 0)
    assert os.readlink(failing_account / "hooks") == failing_text
    assert (passing_account / "hooks").resolve() == (new_repo / _PACKAGE_ROOT / "hooks").resolve()
    assert (home / ".claude" / "hooks").resolve() == (new_repo / _PACKAGE_ROOT / "hooks").resolve()
    assert manifest_record.read_text() == manifest.read_text()

    retry = _run_printed_retry_line(first_run.stderr, home, bin_dir)

    assert retry.returncode == 0, retry.stderr
    assert (failing_account / "hooks").resolve() == (new_repo / _PACKAGE_ROOT / "hooks").resolve()
