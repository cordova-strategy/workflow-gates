"""Isolated-layout helpers shared by the config script tests.

Both scripts source `_config.sh` via a path relative to their own location
(`$(dirname "$0")/../hooks/_config.sh`), so isolating the schema file needs a
matching directory layout: a `scripts/` dir holding a symlink to the script,
and a sibling `hooks/` dir holding the `_config.sh` and `config-keys.psv` it
resolves against.
"""
from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest
from helpers import HOOKS_DIR, REPO_ROOT, SCRIPTS_DIR, link_bash_into

CONFIG_SH = HOOKS_DIR / "_config.sh"
CONFIG_KEYS_PSV = HOOKS_DIR / "config-keys.psv"
STOW_SOURCE_SETTINGS_PATH = REPO_ROOT / "claude" / ".claude" / "settings.json"

# Each enforcement-critical key's fail-closed value, as _config.sh's
# _config_enforcement_critical_safe_value returns it.
ENFORCEMENT_CRITICAL_SAFE_VALUES = {
    "worktree_required": "true",
    "round_consult_gate": "true",
    "commit_stall_block": "true",
    "authorization_boundary_restore": "true",
}

SKIP_UNDER_ROOT = pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="root bypasses discretionary file-permission bits (CAP_DAC_OVERRIDE on Linux), "
    "so chmod(0o000) does not make the file unreadable",
)


def stow_source_ask_rules() -> list[str]:
    """The `permissions.ask` rules the stow source's settings.json declares."""
    return json.loads(STOW_SOURCE_SETTINGS_PATH.read_text())["permissions"]["ask"]


def engineer_only_qualifier() -> str:
    """The qualifier text `_config.sh` defines, the one wording every printed setter command carries."""
    result = subprocess.run(
        ["bash", "-c", '. "$1"; printf "%s" "$_CONFIG_SETTER_ENGINEER_ONLY_QUALIFIER"', "bash", str(CONFIG_SH)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout, "_config.sh defines no _CONFIG_SETTER_ENGINEER_ONLY_QUALIFIER"
    return result.stdout


def isolated_scripts_dir(tmp_path: Path, script_name: str, schema_content: str) -> Path:
    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir()
    (hooks_dir / "_config.sh").symlink_to(CONFIG_SH)
    (hooks_dir / "config-keys.psv").write_text(schema_content)
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / script_name).symlink_to(SCRIPTS_DIR / script_name)
    return scripts_dir


def path_with_caller_bash_first(tmp_path: Path) -> str:
    """A PATH whose `bash` is the caller's, ahead of the system directories that supply the other tools."""
    bash_dir = tmp_path / "bash-first"
    bash_dir.mkdir(exist_ok=True)
    link_bash_into(bash_dir)
    return f"{bash_dir}:/usr/bin:/bin"


def run_script(
    scripts_dir: Path,
    script_name: str,
    args: Sequence[str],
    tmp_path: Path,
    claude_config_dir: Path | None = None,
    extra_env: Mapping[str, str] | None = None,
    timeout: float | None = None,
) -> subprocess.CompletedProcess:
    """Runs the isolated script with only HOME, PATH, an optional CLAUDE_CONFIG_DIR and `extra_env`.

    An `extra_env` PATH replaces the default one, so a caller that wants a shim directory first
    builds it from `path_with_caller_bash_first`. A `timeout` turns a hang into a TimeoutExpired failure.
    """
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    env = {"HOME": str(home), "PATH": path_with_caller_bash_first(tmp_path)}
    if claude_config_dir is not None:
        env["CLAUDE_CONFIG_DIR"] = str(claude_config_dir)
    if extra_env is not None:
        env.update(extra_env)
    return subprocess.run(
        [str(scripts_dir / script_name), *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=timeout,
    )
