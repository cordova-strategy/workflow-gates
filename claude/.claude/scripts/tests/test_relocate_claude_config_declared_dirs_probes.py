"""Unit-layer tests for what relocate-claude-config.sh probes in a listed dir and when.

These source the script and call its functions directly, as test_relocate_claude_config_declared_dirs.py does.
"""
from __future__ import annotations

import shlex
from pathlib import Path

from ._declared_dirs_helpers import (
    _LINE,
    _PACKAGE_ROOT,
    _READER_WARNING,
    _ROOTS_LABEL,
    _add_checkout_entry,
    _outcomes,
    _run_sourced,
    _scene,
    _write_roots_file,
)

_REAL_FILE_CONTENT = "{}\n"
_DIR_TEST_PROBE_MARKER = "@@DIR-TEST-PROBE@@"
_READLINK_PROBE_MARKER = "@@READLINK-PROBE@@"
_WALK_PROBE_MARKER = "@@WALK-PROBE@@"


def _marking_probe_prelude(probed: Path) -> str:
    """Shadow the reader's two probes so each prints its marker on a duplicate of stdout, because the reader
    calls `_readlink_f` inside a command substitution. The `[ -d ]` marker fires only for `probed`, and the
    `_readlink_f` marker for every call. `builtin [` keeps the shadow from recursing."""
    return (
        "exec 3>&1\n"
        f"[() {{ if [[ \"$1\" == -d && \"$2\" == {shlex.quote(str(probed))} ]]; then echo '{_DIR_TEST_PROBE_MARKER}' >&3; fi; "
        'builtin [ "$@"; }\n'
        f"_readlink_f() {{ echo '{_READLINK_PROBE_MARKER}' >&3; command readlink -f -- \"$1\"; }}\n"
    )


def _walk_marking_probe_prelude(walked: Path) -> str:
    """Shadow `[` so the walk's first probe of `walked`, the `[ ! -x ]` search check, prints its marker.
    `builtin [` keeps the shadow from recursing."""
    return (
        f"[() {{ if [[ \"$1\" == '!' && \"$2\" == -x && \"$3\" == {shlex.quote(str(walked))} ]]; then "
        f"echo '{_WALK_PROBE_MARKER}'; fi; "
        'builtin [ "$@"; }\n'
    )


def test_a_real_file_at_a_checkout_position_is_not_searched_or_counted(tmp_path: Path) -> None:
    scene = _scene(tmp_path)
    _add_checkout_entry(scene.new_repo, _PACKAGE_ROOT, "settings.json")
    real_files = [scene.account / "settings.json", scene.account / "hooks" / "_lib.sh"]
    for real_file in real_files:
        real_file.parent.mkdir(parents=True, exist_ok=True)
        real_file.write_text(_REAL_FILE_CONTENT)
        real_file.chmod(0o644)

    run = scene.run_unit()

    assert run.call_statuses == [0], run.stderr
    assert _outcomes(run.stdout) == [(_LINE, 0, 0, 0, 0)]
    assert run.stderr == ""
    for real_file in real_files:
        assert real_file.read_text() == _REAL_FILE_CONTENT


def test_reader_names_a_line_before_it_probes_the_path(tmp_path: Path) -> None:
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    listed = tmp_path / "acct-listed"
    listed.mkdir()
    _write_roots_file(home, ["# a comment", str(listed)])

    run = _run_sourced(home, [["read_declared_config_dirs"]], cwd=tmp_path, prelude=_marking_probe_prelude(listed))

    assert run.call_statuses == [0], run.stderr
    checking_line = f"checking line 2 of {_ROOTS_LABEL}"
    assert checking_line in run.stdout, f"no `{checking_line}` before the probes: {run.stdout!r}"
    for probe_marker in (_DIR_TEST_PROBE_MARKER, _READLINK_PROBE_MARKER):
        assert probe_marker in run.stdout, f"the reader never ran the probe behind {probe_marker}: {run.stdout!r}"
        assert run.stdout.index(checking_line) < run.stdout.index(probe_marker), run.stdout


def test_reader_does_not_name_a_relative_line_that_names_a_real_dir(tmp_path: Path) -> None:
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    listed = tmp_path / "acct-listed"
    listed.mkdir()
    relative_dir_name = "acct-relative"
    (tmp_path / relative_dir_name).mkdir()
    _write_roots_file(home, ["# a comment", relative_dir_name, str(listed)])

    run = _run_sourced(
        home, [["read_declared_config_dirs"]], cwd=tmp_path, prelude=_marking_probe_prelude(Path(relative_dir_name))
    )

    assert run.call_statuses == [0], run.stderr
    assert f"checking line 3 of {_ROOTS_LABEL}" in run.stdout, run.stdout
    assert f"checking line 2 of {_ROOTS_LABEL}" not in run.stdout, run.stdout
    assert _DIR_TEST_PROBE_MARKER not in run.stdout, run.stdout
    # Only the absolute line 3 reaches `_readlink_f`.
    assert run.stdout.count(_READLINK_PROBE_MARKER) == 1, run.stdout
    assert _READER_WARNING.format(line=2) in run.stderr, run.stderr
    assert run.stderr.count("is not an absolute path to an existing directory") == 1, run.stderr


def test_runner_names_each_walked_line_before_its_outcome_and_no_skipped_line(tmp_path: Path) -> None:
    scene = _scene(tmp_path)
    inside_checkout = scene.new_repo / "acct-inside"
    inside_checkout.mkdir()
    _write_roots_file(scene.home, ["~/.claude", str(inside_checkout), str(scene.account)])

    run = _run_sourced(
        scene.home,
        [["relink_declared_dirs", str(scene.new_repo)]],
        cwd=scene.scratch,
        prelude=_walk_marking_probe_prelude(scene.account.resolve()),
    )

    assert run.call_statuses == [0], run.stderr
    walking_line = f"walking the dir on line 3 of {_ROOTS_LABEL}"
    outcome_line = f"the dir on line 3 of {_ROOTS_LABEL}: re-pointed"
    assert walking_line in run.stdout, run.stdout
    assert run.stdout.count(_WALK_PROBE_MARKER) == 1, f"the walk did not probe the dir exactly once: {run.stdout!r}"
    assert run.stdout.index(walking_line) < run.stdout.index(_WALK_PROBE_MARKER) < run.stdout.index(outcome_line), run.stdout
    for skipped_line_number in (1, 2):
        assert f"walking the dir on line {skipped_line_number} of" not in run.stdout, run.stdout
