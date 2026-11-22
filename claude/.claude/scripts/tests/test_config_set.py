"""Tests for config-set.sh's exit-code contract and written bytes.

The input matrices for the value-type rule and the enforcement-critical key
list live in test_config_lib.py; this file holds one subprocess case per
branch, plus two cases run once per input because the property each pins
exists only at the CLI.
"""
from __future__ import annotations

import dataclasses
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest
from helpers import SCRIPTS_DIR

from ._config_script_helpers import (
    CONFIG_KEYS_PSV,
    CONFIG_SH,
    ENFORCEMENT_CRITICAL_SAFE_VALUES,
    SKIP_UNDER_ROOT,
    isolated_scripts_dir,
    path_with_caller_bash_first,
    run_script,
)

sys.path.insert(0, str(SCRIPTS_DIR))
from _config import SchemaRow, schema  # noqa: E402

_CONFIG_SET_SH_NAME = "config-set.sh"
_WROTE_LINE_PREFIX = "config-set.sh: wrote "
_FIFO_TIMEOUT_SECONDS = 10
_AGENT_REPORTS_TO_ENGINEER = "An agent reports this to the engineer and "

# config-keys.psv's column order, as SchemaRow declares it. The coerced bool duplicates the raw
# legacy-probe column, so only the raw field stands for a column.
_SCHEMA_COLUMN_FIELDS = [
    field.name for field in dataclasses.fields(SchemaRow) if field.name != "legacy_probe_on_resolution_failure"
]
_HUMAN_NAME_COLUMN_INDEX = _SCHEMA_COLUMN_FIELDS.index("human_name")
_ADJACENT_SCHEMA_KEYS = " ".join(list(schema())[:2])


def _enforcement_critical_keys() -> list[str]:
    """Reads the key list from _config.sh's bash variable, the oracle for test_critical_key_list_matches_the_library_variable."""
    result = subprocess.run(
        ["bash", "-c", '. "$1" && printf "%s" "$_CONFIG_ENFORCEMENT_CRITICAL_KEYS"', "bash", str(CONFIG_SH)],
        capture_output=True,
        text=True,
        check=True,
    )
    keys = sorted(result.stdout.split())
    assert keys, "no enforcement-critical keys read from _config.sh"
    return keys


_ENFORCEMENT_CRITICAL_KEYS = sorted(ENFORCEMENT_CRITICAL_SAFE_VALUES)


def _schema_lines_with_row_replaced(key: str, replacement_row: str) -> str:
    """The real schema's text with KEY's row replaced by `replacement_row`, every other row untouched."""
    lines = [
        replacement_row if line.startswith(f"{key}|") else line for line in CONFIG_KEYS_PSV.read_text().splitlines()
    ]
    return "\n".join(lines) + "\n"


def _release_fifo(fifo_path: Path) -> None:
    """A read-write, non-blocking open releases any process still blocked opening the FIFO."""
    os.close(os.open(fifo_path, os.O_RDWR | os.O_NONBLOCK))


def _human_name(key: str) -> str:
    return schema()[key].human_name


def _scripts_dir(tmp_path: Path, schema_content: str | None = None) -> Path:
    return isolated_scripts_dir(
        tmp_path, _CONFIG_SET_SH_NAME, CONFIG_KEYS_PSV.read_text() if schema_content is None else schema_content
    )


def _state_file(tmp_path: Path) -> Path:
    return tmp_path / "home" / ".claude" / "claude-config.toml"


def _write_state(tmp_path: Path, content: str) -> Path:
    state_file = _state_file(tmp_path)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_bytes(content.encode())
    return state_file


def _set(
    scripts_dir: Path,
    tmp_path: Path,
    *args: str,
    claude_config_dir: Path | None = None,
    extra_env: dict | None = None,
    timeout: float | None = None,
) -> subprocess.CompletedProcess:
    return run_script(
        scripts_dir,
        _CONFIG_SET_SH_NAME,
        list(args),
        tmp_path,
        claude_config_dir=claude_config_dir,
        extra_env=extra_env,
        timeout=timeout,
    )


class TestWritesAndExitsZero:
    def test_absent_file_is_created_with_the_row_at_mode_0600(self, tmp_path: Path) -> None:
        result = _set(_scripts_dir(tmp_path), tmp_path, "commit_stall_block", "false")

        assert result.returncode == 0, result.stderr
        state_file = _state_file(tmp_path)
        assert state_file.read_bytes() == b"commit_stall_block = false\n"
        assert stat.S_IMODE(state_file.stat().st_mode) == 0o600
        assert result.stdout == "false\n"
        assert str(state_file) in result.stderr

    @pytest.mark.parametrize(
        "existing_mode",
        [
            pytest.param(0o644, id="mode-0644"),
            pytest.param(0o444, id="read-only-mode-0444", marks=SKIP_UNDER_ROOT),
        ],
    )
    def test_existing_state_file_is_replaced_by_a_regular_file_at_mode_0600(
        self, tmp_path: Path, existing_mode: int
    ) -> None:
        """The write replaces the file rather than editing it in place, so a read-only file is no lock."""
        state_file = _write_state(tmp_path, "handoff_nudge = false\n")
        state_file.chmod(existing_mode)

        result = _set(_scripts_dir(tmp_path), tmp_path, "commit_stall_block", "false")

        assert result.returncode == 0, result.stderr
        assert stat.S_ISREG(state_file.lstat().st_mode)
        assert stat.S_IMODE(state_file.lstat().st_mode) == 0o600
        assert state_file.read_bytes() == b"handoff_nudge = false\ncommit_stall_block = false\n"

    def test_existing_row_is_rewritten_in_place_keeping_comments_blank_lines_and_order(self, tmp_path: Path) -> None:
        state_file = _write_state(
            tmp_path, "# a leading comment\ncommit_stall_block = true\n\nhandoff_nudge = false\n"
        )

        result = _set(_scripts_dir(tmp_path), tmp_path, "handoff_nudge", "true")

        assert result.returncode == 0, result.stderr
        assert state_file.read_bytes() == b"# a leading comment\ncommit_stall_block = true\n\nhandoff_nudge = true\n"
        assert result.stdout == "true\n"

    def test_duplicate_rows_for_the_key_are_all_rewritten(self, tmp_path: Path) -> None:
        state_file = _write_state(
            tmp_path,
            "handoff_nudge = false\n\ncommit_stall_block = false\n\ncommit_stall_block = true\n",
        )

        result = _set(_scripts_dir(tmp_path), tmp_path, "commit_stall_block", "false")

        assert result.returncode == 0, result.stderr
        assert state_file.read_bytes() == (
            b"handoff_nudge = false\n\ncommit_stall_block = false\n\ncommit_stall_block = false\n"
        )

    def test_unterminated_last_line_keeps_the_new_row_on_its_own_line(self, tmp_path: Path) -> None:
        state_file = _write_state(tmp_path, "handoff_nudge = false")

        result = _set(_scripts_dir(tmp_path), tmp_path, "commit_stall_block", "false")

        assert result.returncode == 0, result.stderr
        assert state_file.read_bytes() == b"handoff_nudge = false\ncommit_stall_block = false\n"

    def test_symlinked_state_file_becomes_a_regular_file_and_the_target_is_untouched(self, tmp_path: Path) -> None:
        target = tmp_path / "elsewhere" / "claude-config.toml"
        target.parent.mkdir()
        target.write_bytes(b"handoff_nudge = false\n")
        state_file = _state_file(tmp_path)
        state_file.parent.mkdir(parents=True)
        state_file.symlink_to(target)

        result = _set(_scripts_dir(tmp_path), tmp_path, "commit_stall_block", "false")

        assert result.returncode == 0, result.stderr
        assert target.read_bytes() == b"handoff_nudge = false\n"
        assert not state_file.is_symlink()
        assert state_file.read_bytes() == b"handoff_nudge = false\ncommit_stall_block = false\n"

    def test_enum_literal_is_written_quoted(self, tmp_path: Path) -> None:
        state_file = _state_file(tmp_path)

        result = _set(_scripts_dir(tmp_path), tmp_path, "pr_cost_disclosure", "dollars")

        assert result.returncode == 0, result.stderr
        assert state_file.read_bytes() == b'pr_cost_disclosure = "dollars"\n'
        assert result.stdout == "dollars\n"


class TestRejectedArgumentsExitTwo:
    def test_wrong_argument_count(self, tmp_path: Path) -> None:
        result = _set(_scripts_dir(tmp_path), tmp_path, "commit_stall_block")

        assert result.returncode == 2
        assert result.stdout == ""
        assert "docs/config-file.md" in result.stderr

    def test_unknown_key(self, tmp_path: Path) -> None:
        result = _set(_scripts_dir(tmp_path), tmp_path, "not_a_real_key", "true")

        assert result.returncode == 2
        assert result.stdout == ""
        assert "unknown key 'not_a_real_key'" in result.stderr
        assert not _state_file(tmp_path).exists()

    def test_quoted_enum_value_is_rejected_because_value_is_passed_bare(self, tmp_path: Path) -> None:
        result = _set(_scripts_dir(tmp_path), tmp_path, "pr_cost_disclosure", '"dollars"')

        assert result.returncode == 2
        assert result.stdout == ""
        assert "bare" in result.stderr
        assert not _state_file(tmp_path).exists()

    def test_key_whose_schema_type_is_not_writable_names_the_type_and_creates_no_file(self, tmp_path: Path) -> None:
        unwritable_row = "handoff_nudge|text|true|config-dir|false|config-dir|nudge|presence-disables|Handoff nudge|docs/x.md|d"
        scripts_dir = _scripts_dir(tmp_path, _schema_lines_with_row_replaced("handoff_nudge", unwritable_row))

        result = _set(scripts_dir, tmp_path, "handoff_nudge", "true")

        assert result.returncode == 2
        assert result.stdout == ""
        assert "its schema type 'text' is not writable" in result.stderr
        assert _WROTE_LINE_PREFIX not in result.stderr
        assert not _state_file(tmp_path).exists()

    @pytest.mark.parametrize(
        ("key", "value"),
        [
            pytest.param("handoff_nudge ", "false", id="key-with-trailing-space"),
            pytest.param(_ADJACENT_SCHEMA_KEYS, "false", id="key-spanning-two-adjacent-schema-keys"),
            pytest.param("handoff_*", "false", id="key-glob"),
            pytest.param("-handoff_nudge", "false", id="key-with-leading-dash"),
            pytest.param("handoff_nudge", "true\nworktree_required = false", id="value-smuggling-a-second-row"),
            pytest.param("handoff_nudge", " true", id="value-with-leading-space"),
            pytest.param("handoff_nudge", "*", id="value-glob"),
        ],
    )
    def test_malformed_argument_leaves_the_file_byte_identical(self, tmp_path: Path, key: str, value: str) -> None:
        original = b"commit_stall_block = true\n"
        state_file = _write_state(tmp_path, original.decode())

        result = _set(_scripts_dir(tmp_path), tmp_path, key, value)

        assert result.returncode == 2, result.stderr
        assert result.stdout == ""
        assert state_file.read_bytes() == original


class TestWriteRefusedExitsOne:
    def test_malformed_line_leaves_the_file_byte_identical_and_the_reader_names_it(self, tmp_path: Path) -> None:
        original = b"handoff_nudge = falsecommit_stall_block = false\n"
        state_file = _write_state(tmp_path, original.decode())

        result = _set(_scripts_dir(tmp_path), tmp_path, "commit_stall_block", "false")

        assert result.returncode == 1
        assert result.stdout == ""
        assert state_file.read_bytes() == original
        assert f"warning: skipping malformed line in {state_file}" in result.stderr
        assert _WROTE_LINE_PREFIX not in result.stderr
        assert "notice:" not in result.stderr
        assert "nothing was written" in result.stderr
        assert f"One malformed line in {state_file} blocks every write, whichever key it names" in result.stderr
        assert f"{_AGENT_REPORTS_TO_ENGINEER}does not edit or replace {state_file}" in result.stderr
        assert "The engineer fixes the line the warning names, or the write error, by hand, then re-runs" in result.stderr

    def test_failed_mktemp_leaves_the_file_byte_identical_with_no_malformed_line_warning(
        self, tmp_path: Path
    ) -> None:
        original = b"handoff_nudge = false\n"
        state_file = _write_state(tmp_path, original.decode())
        shim_dir = tmp_path / "failing-mktemp-bin"
        shim_dir.mkdir()
        shim = shim_dir / "mktemp"
        shim.write_text("#!/bin/bash\nexit 1\n")
        shim.chmod(0o755)

        result = _set(
            _scripts_dir(tmp_path),
            tmp_path,
            "commit_stall_block",
            "false",
            extra_env={"PATH": f"{shim_dir}:{path_with_caller_bash_first(tmp_path)}"},
        )

        assert result.returncode == 1
        assert result.stdout == ""
        assert state_file.read_bytes() == original
        assert "warning: skipping malformed line" not in result.stderr
        assert _WROTE_LINE_PREFIX not in result.stderr
        assert "notice:" not in result.stderr
        assert "failed-write error" in result.stderr
        assert f"{_AGENT_REPORTS_TO_ENGINEER}does not edit or replace {state_file}" in result.stderr

    def test_row_written_but_overridden_by_a_home_toml_row_names_that_file_and_resolution_precedence(
        self, tmp_path: Path
    ) -> None:
        """worktree_required resolves config-dir-or-home, so a `true` row in $HOME/.claude's own toml
        still enables it after a row is written at another config dir."""
        home_claude = tmp_path / "home" / ".claude"
        home_claude.mkdir(parents=True)
        (home_claude / "claude-config.toml").write_bytes(b"worktree_required = true\n")
        account_dir = tmp_path / "acct"
        account_dir.mkdir()

        result = _set(_scripts_dir(tmp_path), tmp_path, "worktree_required", "false", claude_config_dir=account_dir)

        assert result.returncode == 1
        assert result.stdout == ""
        assert (account_dir / "claude-config.toml").read_bytes() == b"worktree_required = false\n"
        assert f"{_WROTE_LINE_PREFIX}{account_dir / 'claude-config.toml'}" in result.stderr
        assert (
            f"a `true` in either {account_dir} or $HOME/.claude wins, "
            f"so check for a `true` row in {home_claude / 'claude-config.toml'}"
        ) in result.stderr
        assert "another writer" not in result.stderr
        assert f"{_AGENT_REPORTS_TO_ENGINEER}does not edit or remove either file" in result.stderr
        assert "Resolution precedence" in result.stderr
        assert "notice:" in result.stderr

    def test_row_written_but_overridden_by_a_home_legacy_sentinel_names_that_file_and_when_it_counts(
        self, tmp_path: Path
    ) -> None:
        """A legacy opt-in file under $HOME/.claude enables worktree_required while that dir's toml has
        no row for it, so the message must name the sentinel rather than a toml that does not exist."""
        home_claude = tmp_path / "home" / ".claude"
        home_claude.mkdir(parents=True)
        legacy_sentinel = home_claude / "worktree-required"
        legacy_sentinel.touch()
        account_dir = tmp_path / "acct"
        account_dir.mkdir()

        result = _set(_scripts_dir(tmp_path), tmp_path, "worktree_required", "false", claude_config_dir=account_dir)

        assert result.returncode == 1
        assert result.stdout == ""
        assert (account_dir / "claude-config.toml").read_bytes() == b"worktree_required = false\n"
        assert not (home_claude / "claude-config.toml").exists()
        assert (
            f"or for the legacy file {legacy_sentinel}, which counts only while that claude-config.toml "
            "has no row for 'worktree_required'"
        ) in result.stderr
        assert "another writer" not in result.stderr
        assert f"{_AGENT_REPORTS_TO_ENGINEER}does not edit or remove either file" in result.stderr
        assert "Resolution precedence" in result.stderr
        assert "notice:" in result.stderr

    def test_row_replaced_by_another_writer_before_the_read_back_says_to_re_run(self, tmp_path: Path) -> None:
        """A `mv` shim stands in for a second writer whose replacement lands after ours and before the read-back."""
        shim_dir = tmp_path / "overwriting-mv-bin"
        shim_dir.mkdir()
        shim = shim_dir / "mv"
        shim.write_text('#!/bin/bash\n/bin/mv "$@" || exit\nprintf "handoff_nudge = true\\n" > "${@: -1}"\n')
        shim.chmod(0o755)

        result = _set(
            _scripts_dir(tmp_path),
            tmp_path,
            "handoff_nudge",
            "false",
            extra_env={"PATH": f"{shim_dir}:{path_with_caller_bash_first(tmp_path)}"},
        )

        assert result.returncode == 1
        assert result.stdout == ""
        assert "still resolves to 'true' -- another writer may have replaced the row, so re-run the command to check" in (
            result.stderr
        )
        assert "$HOME/.claude" not in result.stderr
        assert "Resolution precedence" in result.stderr


class TestEnvironmentFailuresExitThree:
    def test_relative_claude_config_dir(self, tmp_path: Path) -> None:
        result = _set(
            _scripts_dir(tmp_path), tmp_path, "handoff_nudge", "false", claude_config_dir=Path("relative/acct")
        )

        assert result.returncode == 3
        assert result.stdout == ""
        assert "CLAUDE_CONFIG_DIR is set to a relative path" in result.stderr
        assert _WROTE_LINE_PREFIX not in result.stderr

    def test_empty_home_with_no_claude_config_dir_exits_three(self, tmp_path: Path) -> None:
        result = _set(_scripts_dir(tmp_path), tmp_path, "handoff_nudge", "false", extra_env={"HOME": ""})

        assert result.returncode == 3
        assert result.stdout == ""
        assert "$HOME is unset/empty" in result.stderr
        assert _WROTE_LINE_PREFIX not in result.stderr

    def test_config_dir_resolving_to_the_filesystem_root(self, tmp_path: Path) -> None:
        """`CLAUDE_CONFIG_DIR=/` resolves to an empty path with status 0, so the message must name the root."""
        result = _set(_scripts_dir(tmp_path), tmp_path, "handoff_nudge", "false", claude_config_dir=Path("/"))

        assert result.returncode == 3
        assert result.stdout == ""
        assert "filesystem root" in result.stderr
        assert _WROTE_LINE_PREFIX not in result.stderr

    def test_schema_row_truncated_after_the_resolution_column_is_written_then_fails_the_read_back(
        self, tmp_path: Path
    ) -> None:
        scripts_dir = _scripts_dir(
            tmp_path, _schema_lines_with_row_replaced("worktree_required", "worktree_required|bool|false|config-dir-or-home")
        )

        result = _set(scripts_dir, tmp_path, "worktree_required", "false")

        assert result.returncode == 3
        assert result.stdout == ""
        assert "present but truncated" in result.stderr
        assert f"{_WROTE_LINE_PREFIX}{_state_file(tmp_path)}" in result.stderr
        assert _state_file(tmp_path).read_bytes() == b"worktree_required = false\n"

    def test_schema_row_with_an_empty_type_column_writes_nothing(self, tmp_path: Path) -> None:
        """The type column gates the write, so an empty one is a partial install rather than an unknown key."""
        scripts_dir = _scripts_dir(tmp_path, _schema_lines_with_row_replaced("worktree_required", "worktree_required|"))

        result = _set(scripts_dir, tmp_path, "worktree_required", "false")

        assert result.returncode == 3
        assert result.stdout == ""
        assert "present but truncated" in result.stderr
        assert "unknown key" not in result.stderr
        assert _WROTE_LINE_PREFIX not in result.stderr
        assert not _state_file(tmp_path).exists()

    def test_schema_file_with_no_rows_writes_nothing(self, tmp_path: Path) -> None:
        scripts_dir = _scripts_dir(tmp_path, "# a comment and no key rows\n")

        result = _set(scripts_dir, tmp_path, "handoff_nudge", "false")

        assert result.returncode == 3
        assert result.stdout == ""
        assert "has no key rows" in result.stderr
        assert "unknown key" not in result.stderr
        assert not _state_file(tmp_path).exists()

    def test_missing_schema_file(self, tmp_path: Path) -> None:
        """Removes the schema copy rather than chmod-ing it, so the case holds under root."""
        scripts_dir = _scripts_dir(tmp_path)
        (tmp_path / "hooks" / "config-keys.psv").unlink()

        result = _set(scripts_dir, tmp_path, "handoff_nudge", "false")

        assert result.returncode == 3
        assert result.stdout == ""
        assert "schema file not found or unreadable" in result.stderr
        assert _WROTE_LINE_PREFIX not in result.stderr

    @SKIP_UNDER_ROOT
    def test_unreadable_state_file_is_named_and_left_byte_identical(self, tmp_path: Path) -> None:
        original = b"handoff_nudge = false\n"
        state_file = _write_state(tmp_path, original.decode())
        state_file.chmod(0o000)
        try:
            result = _set(_scripts_dir(tmp_path), tmp_path, "commit_stall_block", "false")
        finally:
            state_file.chmod(0o600)

        assert result.returncode == 3
        assert result.stdout == ""
        assert str(state_file) in result.stderr
        assert "not a readable regular file" in result.stderr
        assert f"{_AGENT_REPORTS_TO_ENGINEER}leaves {state_file} alone" in result.stderr
        assert "The engineer fixes the path by hand, then re-runs" in result.stderr
        assert _WROTE_LINE_PREFIX not in result.stderr
        assert "notice:" not in result.stderr
        assert state_file.read_bytes() == original

    def test_directory_at_the_state_path_is_refused_with_nothing_created(self, tmp_path: Path) -> None:
        state_path = _state_file(tmp_path)
        state_path.mkdir(parents=True)

        result = _set(_scripts_dir(tmp_path), tmp_path, "commit_stall_block", "false")

        assert result.returncode == 3
        assert result.stdout == ""
        assert str(state_path) in result.stderr
        assert "not a readable regular file" in result.stderr
        assert _WROTE_LINE_PREFIX not in result.stderr
        assert "notice:" not in result.stderr
        assert list(state_path.iterdir()) == []
        assert list(state_path.parent.glob(".claude-config.*")) == []

    def test_dangling_symlink_at_the_state_path_is_refused_and_left_in_place(self, tmp_path: Path) -> None:
        state_path = _state_file(tmp_path)
        state_path.parent.mkdir(parents=True)
        dangling_target = tmp_path / "no-such-target.toml"
        state_path.symlink_to(dangling_target)

        result = _set(_scripts_dir(tmp_path), tmp_path, "commit_stall_block", "false")

        assert result.returncode == 3
        assert result.stdout == ""
        assert "a symlink that does not resolve to one (including a dangling link)" in result.stderr
        assert _WROTE_LINE_PREFIX not in result.stderr
        assert state_path.is_symlink() and state_path.readlink() == dangling_target
        assert not dangling_target.exists()

    def test_fifo_at_the_state_path_is_refused_without_blocking_and_left_in_place(self, tmp_path: Path) -> None:
        """A FIFO blocks any open that has no writer, so the case runs under a timeout."""
        state_path = _state_file(tmp_path)
        state_path.parent.mkdir(parents=True)
        os.mkfifo(state_path)

        try:
            result = _set(
                _scripts_dir(tmp_path), tmp_path, "commit_stall_block", "false", timeout=_FIFO_TIMEOUT_SECONDS
            )
        finally:
            _release_fifo(state_path)

        assert result.returncode == 3
        assert result.stdout == ""
        assert str(state_path) in result.stderr
        assert "not a readable regular file" in result.stderr
        assert _WROTE_LINE_PREFIX not in result.stderr
        assert "notice:" not in result.stderr
        assert stat.S_ISFIFO(state_path.lstat().st_mode)
        assert list(state_path.parent.glob(".claude-config.*")) == []


class TestEnforcementCriticalNotice:
    def test_critical_key_list_matches_the_library_variable(self) -> None:
        assert _enforcement_critical_keys() == _ENFORCEMENT_CRITICAL_KEYS

    @pytest.mark.parametrize("key", _ENFORCEMENT_CRITICAL_KEYS)
    def test_permissive_value_prints_the_notice_with_the_restore_command(self, tmp_path: Path, key: str) -> None:
        scripts_dir = _scripts_dir(tmp_path)

        result = _set(scripts_dir, tmp_path, key, "false")

        assert result.returncode == 0, result.stderr
        assert result.stdout == "false\n"
        config_dir = tmp_path / "home" / ".claude"
        assert "notice:" in result.stderr
        assert f"for every session that uses {config_dir} " in result.stderr
        assert f"false relaxes {_human_name(key)} for every session" in result.stderr
        restore_value = ENFORCEMENT_CRITICAL_SAFE_VALUES[key]
        assert f"To restore it: {scripts_dir / _CONFIG_SET_SH_NAME} {key} {restore_value}" in result.stderr

    def test_restore_hint_runs_as_printed_for_a_script_path_and_config_dir_with_spaces_and_shell_metacharacters(
        self, tmp_path: Path
    ) -> None:
        """The hint is a command an agent relays, so an awkward script path and config dir must each
        round-trip through `bash -c` as one word. The restore runs with no CLAUDE_CONFIG_DIR of its
        own, so it reaches the config dir only through the hint's own prefix."""
        spaced_root = tmp_path / "a dir"
        spaced_root.mkdir()
        probe_cwd = spaced_root / "probe-cwd"
        probe_cwd.mkdir()
        canary = probe_cwd / "canary"
        config_dir = spaced_root / f"cfg dir $(touch {canary.name}); it's"
        scripts_dir = _scripts_dir(spaced_root)

        written = _set(scripts_dir, spaced_root, "commit_stall_block", "false", claude_config_dir=config_dir)

        assert written.returncode == 0, written.stderr
        state_file = config_dir / "claude-config.toml"
        assert state_file.read_bytes() == b"commit_stall_block = false\n"
        restore_marker = "To restore it: "
        restore_command = next(
            line.split(restore_marker, 1)[1] for line in written.stderr.splitlines() if restore_marker in line
        )

        restored = subprocess.run(
            ["bash", "-c", restore_command],
            capture_output=True,
            text=True,
            env={"HOME": str(spaced_root / "home"), "PATH": path_with_caller_bash_first(spaced_root)},
            cwd=probe_cwd,
            check=False,
        )

        assert restored.returncode == 0, restored.stderr
        assert state_file.read_bytes() == b"commit_stall_block = true\n"
        assert not canary.exists()

    def test_restore_hint_prints_one_clean_path_under_an_exported_cdpath(self, tmp_path: Path) -> None:
        """A relative invocation makes `cd` search CDPATH, and a hit through a non-`.` entry prints the
        directory it found, which would put a second line in the captured script path."""
        root = tmp_path.resolve()
        scripts_dir = _scripts_dir(root)
        home = root / "home"
        home.mkdir()

        result = subprocess.run(
            [f"scripts/{_CONFIG_SET_SH_NAME}", "commit_stall_block", "false"],
            capture_output=True,
            text=True,
            env={"HOME": str(home), "PATH": path_with_caller_bash_first(root), "CDPATH": str(root)},
            cwd=root,
            check=False,
        )

        assert result.returncode == 0, result.stderr
        assert f"To restore it: {scripts_dir / _CONFIG_SET_SH_NAME} commit_stall_block true" in result.stderr

    def test_empty_human_name_column_falls_back_to_the_key(self, tmp_path: Path) -> None:
        row_fields = next(
            line for line in CONFIG_KEYS_PSV.read_text().splitlines() if line.startswith("worktree_required|")
        ).split("|")
        assert row_fields[_HUMAN_NAME_COLUMN_INDEX] == _human_name("worktree_required")
        row_fields[_HUMAN_NAME_COLUMN_INDEX] = ""
        scripts_dir = _scripts_dir(
            tmp_path, _schema_lines_with_row_replaced("worktree_required", "|".join(row_fields))
        )

        result = _set(scripts_dir, tmp_path, "worktree_required", "false")

        assert result.returncode == 0, result.stderr
        assert "false relaxes worktree_required for every session" in result.stderr

    @pytest.mark.parametrize("key", _ENFORCEMENT_CRITICAL_KEYS)
    def test_safe_value_prints_no_notice(self, tmp_path: Path, key: str) -> None:
        result = _set(_scripts_dir(tmp_path), tmp_path, key, "true")

        assert result.returncode == 0, result.stderr
        assert result.stdout == "true\n"
        assert "notice:" not in result.stderr

    def test_non_critical_key_prints_no_notice_for_false(self, tmp_path: Path) -> None:
        result = _set(_scripts_dir(tmp_path), tmp_path, "handoff_nudge", "false")

        assert result.returncode == 0, result.stderr
        assert "notice:" not in result.stderr
