"""Tests for config-get.sh's own exit-code contract.

config-get.sh sources _config.sh via a path relative to its own location, so
isolating its schema file needs the matching directory layout that
`_config_script_helpers.py` builds.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from ._config_script_helpers import (
    CONFIG_KEYS_PSV,
    CONFIG_SH,
    isolated_scripts_dir,
    path_with_caller_bash_first,
    run_script,
)

_CONFIG_GET_SH_NAME = "config-get.sh"


def _isolated_scripts_dir(tmp_path: Path, schema_content: str) -> Path:
    return isolated_scripts_dir(tmp_path, _CONFIG_GET_SH_NAME, schema_content)


def _run(
    scripts_dir: Path, key: str, tmp_path: Path, claude_config_dir: Path | None = None
) -> subprocess.CompletedProcess:
    return run_script(scripts_dir, _CONFIG_GET_SH_NAME, [key], tmp_path, claude_config_dir)


class TestExitCodeContract:
    def test_known_key_default_resolves_exit_1(self, tmp_path: Path) -> None:
        scripts_dir = _isolated_scripts_dir(tmp_path, CONFIG_KEYS_PSV.read_text())
        result = _run(scripts_dir, "worktree_required", tmp_path)
        assert result.returncode == 1
        assert result.stdout == "false\n"

    def test_row_truncated_after_resolution_column_returns_exit_3_not_a_silent_enable(
        self, tmp_path: Path
    ) -> None:
        """Security regression: config-get.sh must not treat _config_value's
        new exit 4 (row present but truncated after an earlier column) as an
        unrecognized status that falls through to printing an empty VALUE and
        exiting 0 -- "" != "false" would silently report an enforcement-
        critical key as enabled. worktree_required is the key this matters
        most for: its row is the one real row whose
        legacy-probe-on-resolution-failure column is `true`, so this is the
        exact truncation shape _config.sh's own exit-4 fix guards against."""
        lines = [
            "worktree_required|bool|false|config-dir-or-home" if line.startswith("worktree_required|") else line
            for line in CONFIG_KEYS_PSV.read_text().splitlines()
        ]
        scripts_dir = _isolated_scripts_dir(tmp_path, "\n".join(lines) + "\n")

        result = _run(scripts_dir, "worktree_required", tmp_path)

        assert result.returncode == 3
        assert result.stdout == ""
        assert "worktree_required" in result.stderr

    def test_unknown_key_returns_exit_2(self, tmp_path: Path) -> None:
        scripts_dir = _isolated_scripts_dir(tmp_path, CONFIG_KEYS_PSV.read_text())
        result = _run(scripts_dir, "not_a_real_key", tmp_path)
        assert result.returncode == 2


class TestWritePointerNamesTheDocNotTheCommand:
    """An agent reads these messages whenever it probes for a write verb. They point at the doc, so a
    relayed setter command always passes through the doc's engineer-only qualifier."""

    def test_usage_message_points_at_the_doc_and_prints_no_setter_command(self, tmp_path: Path) -> None:
        scripts_dir = _isolated_scripts_dir(tmp_path, CONFIG_KEYS_PSV.read_text())

        result = run_script(scripts_dir, _CONFIG_GET_SH_NAME, [], tmp_path)

        assert result.returncode == 2
        assert result.stdout == ""
        assert 'docs/config-file.md "Writing a value"' in result.stderr
        assert "config-set.sh" not in result.stderr

    def test_set_message_points_at_the_doc_and_prints_no_setter_command(self, tmp_path: Path) -> None:
        scripts_dir = _isolated_scripts_dir(tmp_path, CONFIG_KEYS_PSV.read_text())

        result = _run(scripts_dir, "set", tmp_path)

        assert result.returncode == 2
        assert result.stdout == ""
        assert 'docs/config-file.md "Writing a value"' in result.stderr
        assert "config-set.sh" not in result.stderr


class TestArchitectFixPlanPilotGate:
    """Pin config-get.sh's exit-code contract against architect_fix_plan_pilot's
    real schema row, which no skill reads. The row stays at false so a scaffolded
    config holding it reads without a warning, and because the session config-keys
    recorder and the routing guard read it."""

    _KEY = "architect_fix_plan_pilot"

    def _config_dir(self, tmp_path: Path) -> Path:
        config_dir = tmp_path / "home" / ".claude"
        config_dir.mkdir(parents=True)
        return config_dir

    def test_fresh_home_with_no_state_file_exits_1(self, tmp_path: Path) -> None:
        scripts_dir = _isolated_scripts_dir(tmp_path, CONFIG_KEYS_PSV.read_text())
        result = _run(scripts_dir, self._KEY, tmp_path)
        assert result.returncode == 1
        assert result.stdout == "false\n"

    def test_hand_written_true_row_exits_0(self, tmp_path: Path) -> None:
        scripts_dir = _isolated_scripts_dir(tmp_path, CONFIG_KEYS_PSV.read_text())
        (self._config_dir(tmp_path) / "claude-config.toml").write_text(f"{self._KEY} = true\n")
        result = _run(scripts_dir, self._KEY, tmp_path)
        assert result.returncode == 0
        assert result.stdout == "true\n"

    def test_scaffolded_false_row_exits_1(self, tmp_path: Path) -> None:
        scripts_dir = _isolated_scripts_dir(tmp_path, CONFIG_KEYS_PSV.read_text())
        config_dir = self._config_dir(tmp_path)
        # Explicit config-dir argument and a scrubbed env keep the scaffold
        # from writing to the invoking account's own config dir.
        scaffold = subprocess.run(
            ["bash", "-c", f'set -uo pipefail; . "{CONFIG_SH}"; _config_scaffold "" "{config_dir}"'],
            capture_output=True,
            text=True,
            env={"HOME": str(tmp_path / "home"), "PATH": path_with_caller_bash_first(tmp_path)},
            check=False,
        )
        assert scaffold.returncode == 0, scaffold.stderr
        assert f"{self._KEY} = false" in (config_dir / "claude-config.toml").read_text().splitlines()

        result = _run(scripts_dir, self._KEY, tmp_path)

        assert result.returncode == 1
        assert result.stdout == "false\n"

    def test_true_only_in_home_claude_dir_exits_1_when_claude_config_dir_is_another_account(
        self, tmp_path: Path
    ) -> None:
        """The key is per-account: a home-level file must not turn it on for an
        account whose CLAUDE_CONFIG_DIR points elsewhere."""
        scripts_dir = _isolated_scripts_dir(tmp_path, CONFIG_KEYS_PSV.read_text())
        (self._config_dir(tmp_path) / "claude-config.toml").write_text(f"{self._KEY} = true\n")
        account_dir = tmp_path / "acct"
        account_dir.mkdir()

        result = _run(scripts_dir, self._KEY, tmp_path, claude_config_dir=account_dir)

        assert result.returncode == 1
        assert result.stdout == "false\n"

    def test_relative_claude_config_dir_exits_3_with_empty_stdout_not_a_silent_enable(
        self, tmp_path: Path
    ) -> None:
        """An unresolvable config dir (status 2 in config-get.sh) exits 3 with
        no stdout. test_config_py.py already pins the exit code; this case
        adds the empty-stdout assertion on the key's real row. Falling
        through would print an empty VALUE, and "" != "false" would read as on
        in a mis-set environment."""
        scripts_dir = _isolated_scripts_dir(tmp_path, CONFIG_KEYS_PSV.read_text())
        (self._config_dir(tmp_path) / "claude-config.toml").write_text(f"{self._KEY} = true\n")

        result = _run(scripts_dir, self._KEY, tmp_path, claude_config_dir=Path("relative/acct"))

        assert result.returncode == 3
        assert result.stdout == ""

    def test_true_in_claude_config_dir_exits_0(self, tmp_path: Path) -> None:
        scripts_dir = _isolated_scripts_dir(tmp_path, CONFIG_KEYS_PSV.read_text())
        account_dir = tmp_path / "acct"
        account_dir.mkdir()
        (account_dir / "claude-config.toml").write_text(f"{self._KEY} = true\n")

        result = _run(scripts_dir, self._KEY, tmp_path, claude_config_dir=account_dir)

        assert result.returncode == 0
        assert result.stdout == "true\n"


class TestArchitectDispositionChallengePilotGate(TestArchitectFixPlanPilotGate):
    """Extends the sibling key's exit-code coverage to this key mechanically; pins nothing specific to
    this key beyond its row's shape."""

    _KEY = "architect_disposition_challenge_pilot"
