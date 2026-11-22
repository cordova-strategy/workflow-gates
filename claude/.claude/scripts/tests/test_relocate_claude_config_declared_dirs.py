"""Unit-layer tests for relocate-claude-config.sh's re-pointing of the config dirs listed in
~/.claude/transcript-config-dirs.

These source the script and call its functions directly. The real `stow` is the oracle for link
ownership, as in test_relocate_claude_config.py. The full-run tests live in
test_relocate_claude_config_declared_dirs_integration.py.
"""
from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import _config_dir
import pytest
from helpers import build_path_without

from ._declared_dirs_helpers import (
    _AWKWARD_DIR_NAME,
    _AWKWARD_ENTRY_NAME,
    _LINE,
    _PACKAGE_ROOT,
    _READER_WARNING,
    _ROOTS_LABEL,
    _SKILLS_ROOT,
    _SUBSCRIPT_ENTRY_NAME,
    _add_checkout_entry,
    _backup_copies,
    _decoy_link,
    _intercepting_function,
    _left_alone,
    _live_link,
    _outcomes,
    _run_sourced,
    _Scene,
    _scene,
    _SourcedRun,
    _stale_link,
    _write_roots_file,
)
from .test_relocate_claude_config import (
    _AWKWARD_DESTINATION_NAME,
    _BACKUP_DIR_REFUSAL_FRAGMENTS,
    _backup_entry_names,
    _make_repo,
    _plant_unusable_backup_dir,
    _script_env,
    requires_non_root,
)

# ---------------------------------------------------------------------------
# Decision table: one listed dir through _repoint_declared_dir
# ---------------------------------------------------------------------------


@dataclass
class _Expect:
    counts: tuple[int, int, int, int] = (0, 0, 0, 0)
    returncode: int = 0
    repointed: dict[str, tuple[str, str]] = field(default_factory=dict)  # position -> (root, old text)
    unchanged: dict[str, str] = field(default_factory=dict)  # position -> text
    left: list[str] = field(default_factory=list)
    stderr_fragments: list[str] = field(default_factory=list)
    extra: Callable[[_SourcedRun], None] | None = None


def _case_stale_relative(scene: _Scene) -> _Expect:
    text = _stale_link(scene.account, "hooks", scene.old_repo)
    return _Expect(counts=(1, 0, 0, 0), repointed={"hooks": (_PACKAGE_ROOT, text)})


def _case_stale_absolute(scene: _Scene) -> _Expect:
    text = _stale_link(scene.account, "hooks", scene.old_repo, absolute=True)
    return _Expect(counts=(1, 0, 0, 0), repointed={"hooks": (_PACKAGE_ROOT, text)})


def _case_stale_nested(scene: _Scene) -> _Expect:
    _add_checkout_entry(scene.new_repo, _PACKAGE_ROOT, "hooks/.second-hook")
    repointed = {
        position: (_PACKAGE_ROOT, _stale_link(scene.account, position, scene.old_repo))
        for position in ("hooks/_lib.sh", "hooks/.second-hook", "scripts")
    }
    return _Expect(counts=(3, 0, 0, 0), repointed=repointed)


def _case_stale_other_checkout(scene: _Scene) -> _Expect:
    text = _stale_link(scene.account, "hooks", scene.root / "other-old-repo")
    return _Expect(counts=(1, 0, 0, 0), repointed={"hooks": (_PACKAGE_ROOT, text)})


def _case_dash_led_text(scene: _Scene) -> _Expect:
    text = _stale_link(scene.account, "hooks", scene.account / "-old-repo")
    assert text.startswith("-")
    return _Expect(counts=(1, 0, 0, 0), repointed={"hooks": (_PACKAGE_ROOT, text)})


def _case_awkward_name(scene: _Scene) -> _Expect:
    _add_checkout_entry(scene.new_repo, _PACKAGE_ROOT, _AWKWARD_ENTRY_NAME)
    _add_checkout_entry(scene.new_repo, _PACKAGE_ROOT, f"{_AWKWARD_DIR_NAME}/inner")
    names = (_AWKWARD_ENTRY_NAME, f"{_AWKWARD_DIR_NAME}/inner")
    return _Expect(
        counts=(2, 0, 0, 0),
        repointed={name: (_PACKAGE_ROOT, _stale_link(scene.account, name, scene.old_repo)) for name in names},
    )


def _case_subscript_name(scene: _Scene) -> _Expect:
    """Its own case, and the checkout's only entry under the package root.

    The walk visits entries in the locale's glob order, and an arithmetic error on any earlier entry ends the walk.
    With no other entry, the name's substitution site is reached whatever the collation."""
    for entry_name in ("hooks", "scripts"):
        shutil.rmtree(scene.new_repo / _PACKAGE_ROOT / entry_name)
    _add_checkout_entry(scene.new_repo, _PACKAGE_ROOT, _SUBSCRIPT_ENTRY_NAME)
    text = _stale_link(scene.account, _SUBSCRIPT_ENTRY_NAME, scene.old_repo)
    return _Expect(counts=(1, 0, 0, 0), repointed={_SUBSCRIPT_ENTRY_NAME: (_PACKAGE_ROOT, text)})


def _case_live_link(scene: _Scene) -> _Expect:
    second_repo = _make_repo(scene.root, "second-repo")
    return _Expect(unchanged={"hooks": _live_link(scene.account, "hooks", second_repo)})


def _left_alone_expectation(scene: _Scene, position: str, link_text: str) -> _Expect:
    link = scene.account / position
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(link_text)
    return _Expect(counts=(0, 0, 1, 0), unchanged={position: link_text}, left=[position])


def _case_other_shape(scene: _Scene) -> _Expect:
    return _left_alone_expectation(scene, "hooks", "../elsewhere/hooks")


def _case_near_miss_text(scene: _Scene) -> _Expect:
    return _left_alone_expectation(scene, "skills", "../old-repo/x-claude-skills/skills")


def _case_wrong_root_text(scene: _Scene) -> _Expect:
    return _left_alone_expectation(scene, "hooks", "../old-repo/claude-skills/hooks")


def _case_glob_in_name(scene: _Scene) -> _Expect:
    _add_checkout_entry(scene.new_repo, _PACKAGE_ROOT, "star*")
    return _left_alone_expectation(scene, "star*", "../old-repo/claude/.claude/star-other")


def _case_not_a_checkout_position(scene: _Scene) -> _Expect:
    text = _stale_link(scene.account, "retired", scene.old_repo)
    return _Expect(unchanged={"retired": text})


def _case_under_a_linked_dir(scene: _Scene) -> _Expect:
    second_repo = _make_repo(scene.root, "second-repo")
    inner_link = second_repo / _PACKAGE_ROOT / "hooks" / "_lib.sh"
    inner_link.unlink()
    inner_text = os.path.relpath(scene.old_repo / _PACKAGE_ROOT / "hooks" / "_lib.sh", inner_link.parent)
    inner_link.symlink_to(inner_text)
    hooks_text = _live_link(scene.account, "hooks", second_repo)

    def inner_link_is_unchanged_and_unnamed(run: _SourcedRun) -> None:
        assert os.readlink(inner_link) == inner_text
        assert "_lib.sh" not in run.stdout

    return _Expect(unchanged={"hooks": hooks_text}, extra=inner_link_is_unchanged_and_unnamed)


def _case_linked_checkout_dir(scene: _Scene) -> _Expect:
    linked_target = scene.root / "link-target"
    linked_target.mkdir()
    (linked_target / "inner").write_text("inner\n")
    (scene.new_repo / _PACKAGE_ROOT / "linked").symlink_to(linked_target)
    text = _stale_link(scene.account, "linked/inner", scene.old_repo)

    def no_stream_names_inner(run: _SourcedRun) -> None:
        assert "inner" not in run.stdout
        assert "inner" not in run.stderr

    return _Expect(unchanged={"linked/inner": text}, extra=no_stream_names_inner)


def _case_shared_position(scene: _Scene) -> _Expect:
    _add_checkout_entry(scene.new_repo, _PACKAGE_ROOT, "shared/a")
    _add_checkout_entry(scene.new_repo, _SKILLS_ROOT, "shared/b")
    a_text = _stale_link(scene.account, "shared/a", scene.old_repo)
    b_text = "../../elsewhere/shared/b"
    (scene.account / "shared" / "b").symlink_to(b_text)
    return _Expect(
        counts=(1, 0, 1, 0),
        repointed={"shared/a": (_PACKAGE_ROOT, a_text)},
        unchanged={"shared/b": b_text},
        left=["shared/b"],
    )


def _case_unsearchable_nested(scene: _Scene) -> _Expect:
    text = _stale_link(scene.account, "hooks/_lib.sh", scene.old_repo)
    scene.restrict(scene.account / "hooks", 0o644)
    return _Expect(
        counts=(0, 0, 0, 1),
        returncode=1,
        unchanged={"hooks/_lib.sh": text},
        stderr_fragments=[f"could not search hooks in the dir on line {_LINE} of {_ROOTS_LABEL}"],
    )


_DECISION_CASES: dict[str, Callable[[_Scene], _Expect]] = {
    "stale-relative": _case_stale_relative,
    "stale-absolute": _case_stale_absolute,
    "stale-nested": _case_stale_nested,
    "stale-other-checkout": _case_stale_other_checkout,
    "dash-led-text": _case_dash_led_text,
    "awkward-name": _case_awkward_name,
    "subscript-name": _case_subscript_name,
    "live-link": _case_live_link,
    "other-shape": _case_other_shape,
    "near-miss-text": _case_near_miss_text,
    "wrong-root-text": _case_wrong_root_text,
    "glob-in-name": _case_glob_in_name,
    "not-a-checkout-position": _case_not_a_checkout_position,
    "under-a-linked-dir": _case_under_a_linked_dir,
    "linked-checkout-dir": _case_linked_checkout_dir,
    "shared-position": _case_shared_position,
    "unsearchable-nested": _case_unsearchable_nested,
}


def _assert_neither_stream_names_an_account(run: _SourcedRun) -> None:
    assert "acct-" not in run.stdout
    assert "acct-" not in run.stderr


@pytest.mark.parametrize(
    "case",
    [pytest.param(case, marks=requires_non_root) if case == "unsearchable-nested" else case for case in _DECISION_CASES],
)
def test_repoint_decision_table(tmp_path: Path, case: str) -> None:
    scene = _scene(tmp_path)
    expect = _DECISION_CASES[case](scene)

    run = scene.run_unit()

    assert run.call_statuses == [expect.returncode], run.stderr
    assert _outcomes(run.stdout) == [(_LINE, *expect.counts)]
    assert _left_alone(run.stdout) == expect.left
    for position, (root, old_text) in expect.repointed.items():
        link = scene.account / position
        target = scene.new_repo / root / position
        assert link.resolve() == target.resolve()
        assert os.readlink(link) == os.path.relpath(target.resolve(), link.parent.resolve())
        copies = _backup_copies(scene.home, link.name)
        assert len(copies) == 1
        assert os.readlink(copies[0]) == old_text
        assert f"re-pointed {position} in the dir on line {_LINE} of {_ROOTS_LABEL}; its old link is in {copies[0]}" in run.stdout
    for position, text in expect.unchanged.items():
        assert os.readlink(scene.account / position) == text
    assert len(_backup_entry_names(scene.home)) == len(expect.repointed)
    for fragment in expect.stderr_fragments:
        assert fragment in run.stderr
    assert not (scene.scratch / "injected").exists()
    _assert_neither_stream_names_an_account(run)
    if expect.extra is not None:
        expect.extra(run)


# ---------------------------------------------------------------------------
# Failure seams: a failing step keeps the old link and leaves nothing stray
# ---------------------------------------------------------------------------

_TEMP_LINK_CONDITION = '[[ "$destination" == "$ACCT"/.hooks.relocate-claude-config.* ]]'
_HOOKS_CONDITION = '[[ "$destination" == "$ACCT"/hooks ]]'

_BAD_TEXT_LINK_PRELUDE = _intercepting_function(
    "ln", _TEMP_LINK_CONDITION, 'command ln -s -- "$ACCT/nowhere" "$destination"; return 0'
)

_FAILURE_PRELUDES: dict[str, str] = {
    "temp-link": _intercepting_function(
        "ln",
        f'{_HOOKS_CONDITION} || {_TEMP_LINK_CONDITION}',
        "if $forced; then rm -f -- \"$destination\"; fi; "
        "printf 'ln: %s: Permission denied\\n' \"$destination\" >&2; return 1",
    ),
    "bad-text": _BAD_TEXT_LINK_PRELUDE,
    "rm-cleanup": _BAD_TEXT_LINK_PRELUDE
    + _intercepting_function(
        "rm",
        _TEMP_LINK_CONDITION,
        "printf 'rm: %s: Permission denied\\n' \"$destination\" >&2; command rm \"$@\"; return 1",
    ),
    "readlink-link": 'readlink() { if [[ "$1" == -- && "$2" == "$ACCT/hooks" ]]; then return 1; fi; command readlink "$@"; }\n',
    "backup-copy": _intercepting_function("ln", '[[ "$destination" == "$BACKUP"/hooks.* ]]'),
    "recheck-dir": _intercepting_function(
        "ln", _TEMP_LINK_CONDITION, 'command ln "$@" || return 1; rm -f -- "$ACCT/hooks"; mkdir -- "$ACCT/hooks"; return 0'
    ),
    "recheck-live": _intercepting_function(
        "ln",
        _TEMP_LINK_CONDITION,
        'command ln "$@" || return 1; rm -f -- "$ACCT/hooks"; '
        'command ln -s -- "$NEW/claude/.claude/hooks" "$ACCT/hooks"; return 0',
    ),
    "rename": _intercepting_function("mv", _HOOKS_CONDITION),
    "unwritable": "",
    "unsearchable": "",
    "temp-name-taken": (
        'mkdir -- "$ACCT/.hooks.relocate-claude-config.$$"\n'
        'echo kept > "$ACCT/.hooks.relocate-claude-config.$$/inner"\n'
    ),
}

# cause, outcome counts, hooks.L<N>.* copies left
_FAILURE_EXPECTATIONS: dict[str, tuple[str, tuple[int, int, int, int], int]] = {
    "temp-link": ("could not create the new link", (1, 1, 0, 0), 0),
    "bad-text": ("the new link does not resolve", (1, 1, 0, 0), 0),
    "rm-cleanup": ("the new link does not resolve", (1, 1, 0, 0), 0),
    "readlink-link": ("could not read its text", (1, 1, 0, 0), 0),
    "backup-copy": ("could not copy it into the backup dir", (1, 1, 0, 0), 0),
    "recheck-dir": ("it changed during the run", (1, 1, 0, 0), 1),
    "recheck-live": ("it changed during the run", (1, 1, 0, 0), 1),
    "rename": ("could not rename the new link over it", (1, 1, 0, 0), 1),
    "unwritable": ("could not create the new link", (0, 2, 0, 0), 0),
    "unsearchable": ("", (0, 0, 0, 1), 0),
    "temp-name-taken": ("its temporary name is taken", (1, 1, 0, 0), 0),
}


@pytest.mark.parametrize(
    "case",
    [
        pytest.param(case, marks=requires_non_root) if case in ("unwritable", "unsearchable") else case
        for case in _FAILURE_PRELUDES
    ],
)
def test_failure_keeps_the_old_link_and_leaves_no_strays(tmp_path: Path, case: str) -> None:
    scene = _scene(tmp_path)
    hooks_text = _stale_link(scene.account, "hooks", scene.old_repo)
    scripts_text = _stale_link(scene.account, "scripts", scene.old_repo)
    cause, counts, hooks_copies = _FAILURE_EXPECTATIONS[case]
    if case == "unwritable":
        scene.restrict(scene.account, 0o555)
    elif case == "unsearchable":
        scene.restrict(scene.account, 0o644)

    run = scene.run_unit(prelude=scene.seam_vars() + _FAILURE_PRELUDES[case])

    assert run.call_statuses == [1], run.stderr
    assert _outcomes(run.stdout) == [(_LINE, *counts)]
    assert _left_alone(run.stdout) == []
    if case == "unsearchable":
        assert f"could not search . in the dir on line {_LINE} of {_ROOTS_LABEL}" in run.stderr
    else:
        failed_links = ["hooks", "scripts"] if case == "unwritable" else ["hooks"]
        for failed_link in failed_links:
            assert f"could not re-point {failed_link} in the dir on line {_LINE} of {_ROOTS_LABEL}: {cause}" in run.stderr
    if not case.startswith("recheck-"):
        assert os.readlink(scene.account / "hooks") == hooks_text
    scripts_failed = case in ("unwritable", "unsearchable")
    if scripts_failed:
        assert os.readlink(scene.account / "scripts") == scripts_text
    else:
        assert (scene.account / "scripts").resolve() == (scene.new_repo / _PACKAGE_ROOT / "scripts").resolve()
    assert len(_backup_copies(scene.home, "hooks")) == hooks_copies
    assert len(_backup_copies(scene.home, "scripts")) == (0 if scripts_failed else 1)
    strays = sorted(entry.name for entry in scene.account.iterdir() if ".relocate-claude-config." in entry.name)
    if case == "temp-name-taken":
        (planted,) = strays
        assert [entry.name for entry in (scene.account / planted).iterdir()] == ["inner"]
    else:
        assert strays == []
    if case == "recheck-dir":
        assert list((scene.account / "hooks").iterdir()) == []
    if case == "recheck-live":
        assert os.readlink(scene.account / "hooks") == str(scene.new_repo.resolve() / _PACKAGE_ROOT / "hooks")
    _assert_neither_stream_names_an_account(run)


_BACKUP_COPY_CAUSE = "could not copy it into the backup dir"


@pytest.mark.parametrize("kind", ["symlink", "regular file"])
def test_backup_dir_refusal_reaches_the_repoint_unit(tmp_path: Path, kind: str) -> None:
    scene = _scene(tmp_path)
    hooks_text = _stale_link(scene.account, "hooks", scene.old_repo)
    observe_backup_dir, untouched_backup_dir = _plant_unusable_backup_dir(scene.home, tmp_path, kind)

    run = scene.run_unit()

    assert run.call_statuses == [1], run.stderr
    assert _outcomes(run.stdout) == [(_LINE, 0, 1, 0, 0)]
    assert os.readlink(scene.account / "hooks") == hooks_text
    assert [entry.name for entry in scene.account.iterdir() if ".relocate-claude-config." in entry.name] == []
    assert observe_backup_dir() == untouched_backup_dir
    assert _BACKUP_DIR_REFUSAL_FRAGMENTS[kind] in run.stderr
    assert f"could not re-point hooks in the dir on line {_LINE} of {_ROOTS_LABEL}: {_BACKUP_COPY_CAUSE}" in run.stderr


@requires_non_root
@pytest.mark.parametrize("fault", ["backup dir unwritable", "backup dir cannot be created"])
def test_backup_dir_the_tools_cannot_write_surfaces_their_message(tmp_path: Path, fault: str) -> None:
    scene = _scene(tmp_path)
    hooks_text = _stale_link(scene.account, "hooks", scene.old_repo)
    backup_dir = scene.home / ".claude-config-relocate-backup"
    if fault == "backup dir unwritable":
        backup_dir.mkdir()
        scene.restrict(backup_dir, 0o555)
    else:
        scene.restrict(scene.home, 0o555)

    run = scene.run_unit()

    assert run.call_statuses == [1], run.stderr
    assert _outcomes(run.stdout) == [(_LINE, 0, 1, 0, 0)]
    assert f"could not re-point hooks in the dir on line {_LINE} of {_ROOTS_LABEL}: {_BACKUP_COPY_CAUSE}" in run.stderr
    tool_lines = [line for line in run.stderr.splitlines() if not line.startswith("relocate-claude-config: ")]
    assert any(str(backup_dir) in line for line in tool_lines), run.stderr
    assert os.readlink(scene.account / "hooks") == hooks_text
    assert [entry.name for entry in scene.account.iterdir() if ".relocate-claude-config." in entry.name] == []
    assert (list(backup_dir.iterdir()) if backup_dir.exists() else []) == []
    _assert_neither_stream_names_an_account(run)


@pytest.mark.parametrize("mode", ["writable", pytest.param("read-only", marks=requires_non_root)])
def test_a_dir_with_nothing_to_re_point_is_not_written(tmp_path: Path, mode: str) -> None:
    scene = _scene(tmp_path)
    _live_link(scene.account, "hooks", scene.new_repo)
    record = scene.scratch / "tool-calls"
    mtime_before = scene.account.stat().st_mtime_ns
    recording_prelude = f"RECORD={shlex.quote(str(record))}\n" + "".join(
        f"{tool}() {{ printf '%s\\n' \"{tool} $*\" >> \"$RECORD\"; command {tool} \"$@\"; }}\n"
        for tool in ("ln", "mv", "rm", "mktemp")
    )
    if mode == "read-only":
        scene.restrict(scene.account, 0o555)

    run = scene.run_unit(prelude="" if mode == "read-only" else recording_prelude)

    assert run.call_statuses == [0], run.stderr
    assert _outcomes(run.stdout) == [(_LINE, 0, 0, 0, 0)]
    assert not record.exists()
    assert not (scene.home / ".claude-config-relocate-backup").exists()
    assert scene.account.stat().st_mtime_ns == mtime_before


# ---------------------------------------------------------------------------
# Runner: which listed dirs are walked, and how failures are recorded
# ---------------------------------------------------------------------------


def _run_runner(home: Path, new_path: Path, cwd: Path) -> _SourcedRun:
    return _run_sourced(home, [["relink_declared_dirs", str(new_path)]], cwd=cwd)


@dataclass
class _RunnerScene:
    home: Path
    new_repo: Path
    scratch: Path
    skip_line: str | None = None
    repointed: list[Path] = field(default_factory=list)
    unchanged: dict[Path, str] = field(default_factory=dict)
    expected_counts: tuple[int, int, int, int] | None = None


def _runner_scene_base(tmp_path: Path) -> _RunnerScene:
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    return _RunnerScene(home=home, new_repo=_make_repo(tmp_path, "new-repo"), scratch=scratch)


def _scene_home_claude(tmp_path: Path) -> _RunnerScene:
    scene = _runner_scene_base(tmp_path)
    _write_roots_file(scene.home, ["~/.claude"])
    scene.unchanged[scene.home / ".claude" / "hooks"] = _stale_link(scene.home / ".claude", "hooks", tmp_path / "old-repo")
    scene.skip_line = f"the dir on line 1 of {_ROOTS_LABEL} is ~/.claude, which the stows above cover"
    return scene


def _scene_inside_checkout(tmp_path: Path) -> _RunnerScene:
    scene = _runner_scene_base(tmp_path)
    inside = scene.new_repo / "acct-inside"
    inside.mkdir()
    _write_roots_file(scene.home, [str(inside)])
    scene.unchanged[inside / "hooks"] = _stale_link(inside, "hooks", tmp_path / "old-repo")
    scene.skip_line = f"the dir on line 1 of {_ROOTS_LABEL} lies inside the checkout, which this command never re-links"
    return scene


def _scene_checkout_itself(tmp_path: Path) -> _RunnerScene:
    scene = _runner_scene_base(tmp_path)
    _write_roots_file(scene.home, [str(scene.new_repo)])
    scene.unchanged[scene.new_repo / "hooks"] = _stale_link(scene.new_repo, "hooks", tmp_path / "old-repo")
    scene.skip_line = f"the dir on line 1 of {_ROOTS_LABEL} lies inside the checkout, which this command never re-links"
    return scene


def _scene_home_claude_symlinked(tmp_path: Path) -> _RunnerScene:
    real_home = tmp_path / "acct-real-home"
    (real_home / ".claude").mkdir(parents=True)
    linked_home = tmp_path / "acct-home-link"
    linked_home.symlink_to(real_home)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    scene = _RunnerScene(home=linked_home, new_repo=_make_repo(tmp_path, "new-repo"), scratch=scratch)
    _write_roots_file(linked_home, ["~/.claude"])
    scene.unchanged[real_home / ".claude" / "hooks"] = _stale_link(real_home / ".claude", "hooks", tmp_path / "old-repo")
    scene.skip_line = f"the dir on line 1 of {_ROOTS_LABEL} is ~/.claude, which the stows above cover"
    return scene


def _scene_sibling_prefix(tmp_path: Path) -> _RunnerScene:
    scene = _runner_scene_base(tmp_path)
    sibling = tmp_path / "new-repo-acct-sibling"
    sibling.mkdir()
    _write_roots_file(scene.home, [str(sibling)])
    _stale_link(sibling, "hooks", tmp_path / "old-repo")
    scene.repointed = [sibling / "hooks"]
    scene.expected_counts = (1, 0, 0, 0)
    return scene


def _scene_home(tmp_path: Path) -> _RunnerScene:
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    scene = _RunnerScene(home=home, new_repo=_make_repo(home, "new-repo"), scratch=scratch)
    _write_roots_file(home, ["~"])
    _stale_link(home, "hooks", tmp_path / "old-repo")
    scene.repointed = [home / "hooks"]
    scene.unchanged[home / ".claude" / "decoy-link"] = _decoy_link(home / ".claude", tmp_path / "old-repo")
    scene.expected_counts = (1, 0, 0, 0)
    return scene


def _scene_checkout_parent(tmp_path: Path) -> _RunnerScene:
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    parent = tmp_path / "acct-parent"
    scene = _RunnerScene(home=home, new_repo=_make_repo(parent, "-new-repo"), scratch=scratch)
    _write_roots_file(home, [str(parent)])
    _stale_link(parent, "hooks", tmp_path / "old-repo")
    scene.repointed = [parent / "hooks"]
    scene.unchanged[scene.new_repo / "decoy-link"] = _decoy_link(scene.new_repo, tmp_path / "old-repo")
    scene.expected_counts = (1, 0, 0, 0)
    return scene


_RUNNER_SCENES: dict[str, Callable[[Path], _RunnerScene]] = {
    "home-claude": _scene_home_claude,
    "inside-checkout": _scene_inside_checkout,
    "home-claude-symlinked": _scene_home_claude_symlinked,
    "sibling-prefix": _scene_sibling_prefix,
    "home": _scene_home,
    "checkout-parent": _scene_checkout_parent,
    "checkout-itself": _scene_checkout_itself,
}


@pytest.mark.parametrize("case", list(_RUNNER_SCENES))
def test_runner_skips_home_claude_and_the_checkout_and_bounds_ancestors(tmp_path: Path, case: str) -> None:
    scene = _RUNNER_SCENES[case](tmp_path)

    run = _run_runner(scene.home, scene.new_repo, scene.scratch)

    assert run.call_statuses == [0], run.stderr
    if scene.skip_line is not None:
        assert scene.skip_line in run.stdout
        assert _outcomes(run.stdout) == []
    for link in scene.repointed:
        assert link.resolve() == (scene.new_repo / _PACKAGE_ROOT / "hooks").resolve()
        assert os.readlink(link) == os.path.relpath(scene.new_repo.resolve() / _PACKAGE_ROOT / "hooks", link.parent.resolve())
    for link, text in scene.unchanged.items():
        assert os.readlink(link) == text
    if scene.expected_counts is not None:
        assert [counts[1:] for counts in _outcomes(run.stdout)] == [scene.expected_counts]
    _assert_neither_stream_names_an_account(run)


def _failing_mv_for(account: Path) -> str:
    return (
        f"ACCT={shlex.quote(str(account))}\n"
        + _intercepting_function("mv", '[[ "$destination" == "$ACCT"/hooks ]]')
    )


def test_runner_appends_failures_and_follows_relink_packages_targets(tmp_path: Path) -> None:
    scene = _runner_scene_base(tmp_path)
    old_repo = tmp_path / "old-repo"
    _add_checkout_entry(scene.new_repo, "other-pkg", "thing")
    _add_checkout_entry(scene.new_repo, "extra-pkg", "thing2")
    failing_account = tmp_path / "acct-a"
    _stale_link(failing_account, "hooks", old_repo)
    passing_account = tmp_path / "acct-b"
    _stale_link(passing_account, "hooks", old_repo)
    thing_text = _stale_link(passing_account, "thing", old_repo, "other-pkg")
    _stale_link(passing_account, "thing2", old_repo, "extra-pkg")
    _write_roots_file(scene.home, [str(failing_account), str(passing_account)])
    prelude = (
        _failing_mv_for(failing_account)
        + "RELINK_FAILURES=(earlier-pkg)\nRELINK_PACKAGES+=($'other-pkg\\t.other' $'extra-pkg\\t.claude')\n"
    )

    run = _run_sourced(
        scene.home,
        [["relink_declared_dirs", str(scene.new_repo)], 'printf "failures=%s\\n" "${RELINK_FAILURES[*]}"'],
        cwd=scene.scratch,
        prelude=prelude,
    )

    assert run.call_statuses == [0], run.stderr
    assert "failures=earlier-pkg transcript-config-dirs:line-1\n" in run.tail
    assert (passing_account / "hooks").resolve() == (scene.new_repo / _PACKAGE_ROOT / "hooks").resolve()
    assert os.readlink(passing_account / "thing") == thing_text
    assert (passing_account / "thing2").resolve() == (scene.new_repo / "extra-pkg" / "thing2").resolve()


@dataclass
class _AwkwardRunner:
    home: Path
    scratch: Path
    account: Path
    typed_new_path: Path
    new_repo: Path
    expected_text: str


def _build_awkward_runner(tmp_path: Path) -> _AwkwardRunner:
    """A listed dir whose name holds a space, `$` and `*`, reached through a symlinked parent and then directly,
    and a checkout named `_AWKWARD_DESTINATION_NAME` that the call spells through a symlinked parent."""
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    real_parent = tmp_path / "real-parent"
    real_parent.mkdir()
    (tmp_path / "link-parent").symlink_to(real_parent)
    account = real_parent / "acct-a dir $x*"
    account.mkdir()
    real_new_parent = tmp_path / "real-new-parent"
    real_new_parent.mkdir()
    (tmp_path / "link-new-parent").symlink_to(real_new_parent)
    new_repo = _make_repo(real_new_parent, _AWKWARD_DESTINATION_NAME)
    _stale_link(account, "hooks", tmp_path / "old-repo")
    _write_roots_file(home, [str(tmp_path / "link-parent" / account.name), str(account)])
    return _AwkwardRunner(
        home=home,
        scratch=scratch,
        account=account,
        typed_new_path=tmp_path / "link-new-parent" / _AWKWARD_DESTINATION_NAME,
        new_repo=new_repo,
        expected_text=os.path.relpath(new_repo / _PACKAGE_ROOT / "hooks", account),
    )


def test_runner_resolves_symlinked_and_awkward_paths(tmp_path: Path) -> None:
    scene = _build_awkward_runner(tmp_path)

    run = _run_runner(scene.home, scene.typed_new_path, scene.scratch)

    assert run.call_statuses == [0], run.stderr
    assert os.readlink(scene.account / "hooks") == scene.expected_text
    assert [counts[1:] for counts in _outcomes(run.stdout)] == [(1, 0, 0, 0)]


def test_runner_dedupes_a_dir_listed_twice(tmp_path: Path) -> None:
    scene = _build_awkward_runner(tmp_path)

    run = _run_runner(scene.home, scene.typed_new_path, scene.scratch)

    assert [counts[0] for counts in _outcomes(run.stdout)] == [1]


def test_runner_second_call_is_idempotent(tmp_path: Path) -> None:
    scene = _build_awkward_runner(tmp_path)
    call = ["relink_declared_dirs", str(scene.typed_new_path)]

    run = _run_sourced(scene.home, [call, call], cwd=scene.scratch)

    assert run.call_statuses == [0, 0], run.stderr
    assert [counts[1:] for counts in _outcomes(run.call_outputs[0])] == [(1, 0, 0, 0)]
    assert [counts[1:] for counts in _outcomes(run.call_outputs[1])] == [(0, 0, 0, 0)]
    assert len(_backup_entry_names(scene.home)) == 1


def test_runner_resets_declared_rows_on_each_call(tmp_path: Path) -> None:
    scene = _build_awkward_runner(tmp_path)
    second_account = tmp_path / "acct-second"
    _stale_link(second_account, "hooks", tmp_path / "old-repo")
    roots_file = scene.home / ".claude" / "transcript-config-dirs"
    rewrite_roots_file = f"printf '%s\\n' '#' '#' '#' {shlex.quote(str(second_account))} > {shlex.quote(str(roots_file))}"
    call = ["relink_declared_dirs", str(scene.typed_new_path)]

    run = _run_sourced(scene.home, [call, rewrite_roots_file, call], cwd=scene.scratch)

    assert run.call_statuses == [0, 0], run.stderr
    assert [counts[:2] for counts in _outcomes(run.call_outputs[0])] == [(1, 1)]
    assert _outcomes(run.call_outputs[1]) == [(4, 1, 0, 0, 0)]
    assert (second_account / "hooks").resolve() == (scene.new_repo / _PACKAGE_ROOT / "hooks").resolve()


# ---------------------------------------------------------------------------
# Roots-file states: the runner never aborts the errexit-on main shell
# ---------------------------------------------------------------------------

_NO_DIR_STATES = ("missing", "directory", "empty", "comment-only", "unreadable")


@pytest.mark.parametrize(
    "state",
    [
        pytest.param("unreadable", marks=requires_non_root) if state == "unreadable" else state
        for state in (
            *_NO_DIR_STATES,
            "readlink-fails",
            "last-relative",
            "last-missing-dir",
            "last-duplicate",
            "no-readlink",
            "no-readlink-no-file",
        )
    ],
)
def test_reader_and_runner_survive_every_roots_file_state(tmp_path: Path, state: str) -> None:
    scene = _runner_scene_base(tmp_path)
    old_repo = tmp_path / "old-repo"
    roots_file = scene.home / ".claude" / "transcript-config-dirs"
    listed = tmp_path / "acct-listed"
    listed.mkdir()
    (tmp_path / "scratch" / "acct-relative").mkdir()
    unlisted_text = ""
    if state in _NO_DIR_STATES:
        unlisted = scene.home / "acct-unlisted"
        unlisted_text = _stale_link(unlisted, "hooks", old_repo)
    prelude = ""
    path = None
    expected_warning_lines: list[int] = []
    listed_lines = {
        "readlink-fails": [str(listed)],
        "last-relative": [str(listed), "acct-relative"],
        "last-missing-dir": [str(listed), str(tmp_path / "acct-missing")],
        "last-duplicate": [str(listed), str(listed)],
    }
    if state == "directory":
        roots_file.mkdir()
    elif state == "empty":
        roots_file.write_text("")
    elif state == "comment-only":
        roots_file.write_text("# only a comment\n")
    elif state == "unreadable":
        roots_file.write_text("/never/read\n")
        roots_file.chmod(0o000)
    elif state == "readlink-fails":
        _write_roots_file(scene.home, listed_lines[state])
        prelude = "readlink() { return 1; }\n"
        expected_warning_lines = [1]
    elif state in listed_lines:
        _write_roots_file(scene.home, listed_lines[state])
        expected_warning_lines = [] if state == "last-duplicate" else [2]
    elif state == "no-readlink":
        _write_roots_file(scene.home, [str(listed)])
        unlisted_text = _stale_link(listed, "hooks", old_repo)
        farm = tmp_path / "farm"
        farm.mkdir()
        path = build_path_without("readlink", farm)
    elif state == "no-readlink-no-file":
        farm = tmp_path / "farm"
        farm.mkdir()
        path = build_path_without("readlink", farm)
    try:
        run = _run_sourced(
            scene.home,
            [["relink_declared_dirs", str(scene.new_repo)], 'echo "survived"'],
            cwd=scene.scratch,
            prelude=prelude,
            bare=True,
            path=path,
        )
    finally:
        if state == "unreadable":
            roots_file.chmod(0o644)

    assert run.returncode == 0, run.stderr
    assert "survived\n" in run.tail
    expected_stderr = [
        f"relocate-claude-config: {_READER_WARNING.format(line=line)}" for line in expected_warning_lines
    ]
    if state == "no-readlink":
        expected_stderr = [
            f"relocate-claude-config: readlink is not available, so no dir listed in {_ROOTS_LABEL} is re-linked"
        ]
        assert "checking" not in run.stdout and "walking" not in run.stdout
        assert _outcomes(run.stdout) == []
    assert run.stderr.splitlines() == expected_stderr
    if state in _NO_DIR_STATES:
        assert os.readlink(scene.home / "acct-unlisted" / "hooks") == unlisted_text
    if state == "no-readlink":
        assert os.readlink(listed / "hooks") == unlisted_text
    assert not (scene.home / ".claude-config-relocate-backup").exists()


# ---------------------------------------------------------------------------
# The bash reader against _config_dir.py's parser
# ---------------------------------------------------------------------------


def _warned_lines(stderr: str, pattern: str) -> list[int]:
    return [int(match.group(1)) for match in re.finditer(pattern, stderr)]


def test_reader_matches_config_dir_parser(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    # Only the absolute-path check rejects the relative line: a real directory has its name.
    (scratch / "acct-relative").mkdir()
    padded = home / "acct-padded"
    tab_padded = tmp_path / "acct-tab"
    crlf = tmp_path / "acct-crlf"
    mid_hash = tmp_path / "acct-mid#line"
    regular_file = tmp_path / "acct-regular-file"
    linked_dir = tmp_path / "real-parent" / "acct-linked"
    awkward = tmp_path / "acct-w]`@*\\$(touch injected)"
    last = tmp_path / "acct-last"
    for directory in (padded, tab_padded, crlf, mid_hash, linked_dir, awkward, last):
        directory.mkdir(parents=True)
    regular_file.write_text("not a directory\n")
    (tmp_path / "link-parent").symlink_to(tmp_path / "real-parent")
    lines = [
        "# a comment",
        "",
        "   # an indented comment",
        "   ",
        "\r",
        "  ~/acct-padded  ",
        f"\t{tab_padded}\t",
        f"{crlf}\r",
        "~",
        str(mid_hash),
        "~acct-user/x",
        "acct-relative",
        str(tmp_path / "acct-missing"),
        str(regular_file),
        str(tab_padded),
        str(linked_dir),
        str(tmp_path / "link-parent" / "acct-linked"),
        str(awkward),
        str(awkward),
        str(last),
    ]
    roots_file = _write_roots_file(home, lines, final_newline=False)

    run = _run_sourced(
        home,
        [["read_declared_config_dirs"], 'printf "%s\\n" "${DECLARED_CONFIG_DIRS[@]}"'],
        cwd=scratch,
    )
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("TRANSCRIPT_CONFIG_DIRS_FILE", str(roots_file))
    monkeypatch.chdir(scratch)
    python_roots = _config_dir.declared_roots_matching(Path.is_dir, warn_prefix="parity")
    python_warned = _warned_lines(capsys.readouterr().err, r"declared root (\d+) unreadable")

    assert run.returncode == 0, run.stderr
    bash_rows = [row.split("\t", 1) for row in run.stdout.splitlines() if "\t" in row]
    assert [Path(path) for _, path in bash_rows] == [root.resolve() for root in python_roots]
    assert _warned_lines(run.stderr, r"line (\d+) of ~/\.claude/transcript-config-dirs is not an absolute") == python_warned
    for line_number, path in bash_rows:
        listed_line = lines[int(line_number) - 1].strip()
        listed_line = str(home) if listed_line == "~" else listed_line.replace("~/", f"{home}/", 1)
        assert Path(listed_line).resolve() == Path(path)
    assert not (scratch / "injected").exists()


def test_reader_and_parser_both_give_nothing_for_a_directory_roots_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = tmp_path / "home"
    (home / ".claude" / "transcript-config-dirs").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("TRANSCRIPT_CONFIG_DIRS_FILE", str(home / ".claude" / "transcript-config-dirs"))
    capsys.readouterr()

    run = _run_sourced(home, [["read_declared_config_dirs"], 'echo "rows=${#DECLARED_CONFIG_DIRS[@]}"'], cwd=tmp_path)
    python_roots = _config_dir.declared_roots_matching(Path.is_dir, warn_prefix="parity")

    assert run.returncode == 0, run.stderr
    assert "rows=0\n" in run.tail
    assert run.stderr == ""
    assert python_roots == []
    assert capsys.readouterr().err == ""


# ---------------------------------------------------------------------------
# _relative_path
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("from_dir", "to_path", "expected"),
    [
        pytest.param("/a/b/c", "/a/d/e", "../../d/e", id="sibling-subtrees"),
        pytest.param("/a/b", "/a/b/c/d", "c/d", id="descendant"),
        pytest.param("/a/b", "/a/bc/d", "../bc/d", id="shared-name-prefix"),
        pytest.param("/a/b", "/c/d", "../../c/d", id="different-first-components"),
        pytest.param("/", "/a/b", "a/b", id="root-as-start"),
        pytest.param("/a/b/c", "/a", "../..", id="target-is-an-ancestor"),
        pytest.param("/a/b", "/a/b", ".", id="equal-paths"),
        pytest.param("/a b/c", "/a b/d e", "../d e", id="path-with-a-space"),
    ],
)
def test_relative_path(tmp_path: Path, from_dir: str, to_path: str, expected: str) -> None:
    run = _run_sourced(tmp_path, [["_relative_path", from_dir, to_path]], cwd=tmp_path)

    assert run.call_statuses == [0], run.stderr
    assert run.call_outputs == [expected]


# ---------------------------------------------------------------------------
# Backup names: unique per move
# ---------------------------------------------------------------------------


def test_same_named_dangling_links_get_their_own_backups(tmp_path: Path) -> None:
    home = tmp_path / "home"
    (home / ".local" / "bin").mkdir(parents=True)
    (home / ".claude").mkdir()
    first_link = home / ".claude" / "dup-name"
    second_link = home / ".local" / "bin" / "dup-name"
    first_link.symlink_to(tmp_path / "gone-one")
    second_link.symlink_to(tmp_path / "gone-two")

    run = _run_sourced(
        home,
        [["_quarantine_if_dangling", str(first_link)], ["_quarantine_if_dangling", str(second_link)]],
        cwd=tmp_path,
    )

    assert run.call_statuses == [0, 0], run.stderr
    backups = sorted((home / ".claude-config-relocate-backup").glob("dup-name.*"))
    assert sorted(os.readlink(backup) for backup in backups) == sorted([str(tmp_path / "gone-one"), str(tmp_path / "gone-two")])


def test_a_failed_quarantine_move_leaves_no_placeholder(tmp_path: Path) -> None:
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    dangling = home / ".claude" / "dup-name"
    dangling.symlink_to(tmp_path / "gone")
    prelude = 'BACKUP="$HOME/.claude-config-relocate-backup"\n' + _intercepting_function(
        "mv", '[[ "$destination" == "$BACKUP"/* ]]'
    )

    run = _run_sourced(home, [["_quarantine_if_dangling", str(dangling)]], cwd=tmp_path, prelude=prelude)

    assert run.returncode == 1
    assert f"could not move {dangling} into {home / '.claude-config-relocate-backup'}" in run.stderr
    assert dangling.is_symlink() and os.readlink(dangling) == str(tmp_path / "gone")
    assert _backup_entry_names(home) == []


# ---------------------------------------------------------------------------
# Stow owns a re-pointed link
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("package", ["claude-skills", "claude"])
def test_stow_owns_a_repointed_link(tmp_path: Path, package: str) -> None:
    scene = _scene(tmp_path)
    _stale_link(scene.account, "hooks", scene.old_repo)
    _stale_link(scene.account, "skills", scene.old_repo, _SKILLS_ROOT)
    assert scene.run_unit().call_statuses == [0]
    if package == "claude-skills":
        stow_args, removed = ["-d", str(scene.new_repo), "-t", str(scene.account), "claude-skills"], "skills"
    else:
        stow_args, removed = ["-d", str(scene.new_repo / "claude"), "-t", str(scene.account), ".claude"], "hooks"

    result = subprocess.run(["stow", "-D", *stow_args], capture_output=True, text=True, check=False, env=_script_env(scene.home))

    assert result.returncode == 0, result.stderr
    assert not (scene.account / removed).is_symlink()
