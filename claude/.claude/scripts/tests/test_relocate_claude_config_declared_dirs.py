"""Unit-layer tests for relocate-claude-config.sh's re-pointing of the config dirs listed in
~/.claude/transcript-config-dirs.

These source the script and call its functions directly. The real `stow` is the oracle for link
ownership, as in test_relocate_claude_config.py. The full-run tests live in
test_relocate_claude_config_declared_dirs_integration.py.
"""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from ._declared_dirs_helpers import (
    _AWKWARD_DIR_NAME,
    _AWKWARD_ENTRY_NAME,
    _LINE,
    _PACKAGE_ROOT,
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
    _runner_scene_base,
    _RunnerScene,
    _Scene,
    _scene,
    _SourcedRun,
    _stale_link,
    _write_roots_file,
)
from ._relocate_helpers import (
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


def _case_trailing_newline_text(scene: _Scene) -> _Expect:
    return _left_alone_expectation(scene, "hooks", f"{scene.old_repo / _PACKAGE_ROOT / 'hooks'}\n")


def _case_newline_ending_name(scene: _Scene) -> _Expect:
    """The checkout also holds the same name without the newline, which a re-point that dropped it would pick."""
    sibling_name = "newline-entry"
    entry_name = f"{sibling_name}\n"
    _add_checkout_entry(scene.new_repo, _PACKAGE_ROOT, entry_name)
    sibling = _add_checkout_entry(scene.new_repo, _PACKAGE_ROOT, sibling_name)
    sibling_content = "sibling\n"
    sibling.write_text(sibling_content)
    text = _stale_link(scene.account, entry_name, scene.old_repo)
    assert text.endswith("\n")

    def sibling_is_unchanged_and_unlinked(run: _SourcedRun) -> None:
        assert sibling.read_text() == sibling_content
        assert not sibling.is_symlink()
        assert not os.path.lexists(scene.account / sibling_name)

    return _Expect(
        counts=(1, 0, 0, 0), repointed={entry_name: (_PACKAGE_ROOT, text)}, extra=sibling_is_unchanged_and_unlinked
    )


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
    "trailing-newline-text": _case_trailing_newline_text,
    "newline-ending-name": _case_newline_ending_name,
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


def _assert_neither_stream_names_a_link_text_or_an_old_checkout(
    run: _SourcedRun, link_texts: Sequence[str], old_checkouts: Sequence[Path]
) -> None:
    """A link's text and an old checkout's path can identify an engagement. The listed-dir units print neither,
    unlike the primary form's own `unstowing` and `moving` lines."""
    old_checkout_spellings = {
        spelling for old_checkout in old_checkouts for spelling in (str(old_checkout), str(old_checkout.resolve()))
    }
    for stream in (run.stdout, run.stderr):
        for link_text in link_texts:
            assert link_text not in stream
        for old_checkout_spelling in old_checkout_spellings:
            assert old_checkout_spelling not in stream


def _assert_neither_stream_names_a_listed_dir(run: _SourcedRun, listed_dirs: Sequence[Path], home: Path) -> None:
    """A listed dir's path, typed or physical, can identify an account. The backup dir under `home` is the one
    place the output names a path by design, so its spelling is set aside first."""
    assert listed_dirs, "a canary over no listed dirs passes vacuously"
    backup_dir_spelling = str(home / ".claude-config-relocate-backup")
    listed_dir_spellings = {spelling for listed_dir in listed_dirs for spelling in (str(listed_dir), str(listed_dir.resolve()))}
    for stream in (run.stdout, run.stderr):
        printed = stream.replace(backup_dir_spelling, "")
        for listed_dir_spelling in listed_dir_spellings:
            assert listed_dir_spelling not in printed


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
    link_texts = [old_text for _, old_text in expect.repointed.values()] + list(expect.unchanged.values())
    _assert_neither_stream_names_a_link_text_or_an_old_checkout(run, link_texts, [scene.old_repo, scene.root / "other-old-repo"])
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

def _could_not_repoint(link_name: str, cause: str) -> str:
    return f"could not re-point {link_name} in the dir on line {_LINE} of {_ROOTS_LABEL}: {cause}"


def _stray_entries(scene: _Scene) -> list[str]:
    return sorted(entry.name for entry in scene.account.iterdir() if ".relocate-claude-config." in entry.name)


def _hooks_was_replaced_by_an_empty_directory(scene: _Scene) -> None:
    assert list((scene.account / "hooks").iterdir()) == []


def _hooks_was_replaced_by_a_live_link(scene: _Scene) -> None:
    assert os.readlink(scene.account / "hooks") == str(scene.new_repo.resolve() / _PACKAGE_ROOT / "hooks")


def _planted_temporary_name_is_untouched(scene: _Scene) -> None:
    (planted,) = _stray_entries(scene)
    assert [entry.name for entry in (scene.account / planted).iterdir()] == ["inner"]


@dataclass
class _FailureRow:
    """One seam's full postcondition, for an account holding stale `hooks` and `scripts` links."""

    stderr_fragments: tuple[str, ...]
    counts: tuple[int, int, int, int]
    old_links: tuple[str, ...]  # links still holding their stale text
    repointed_links: tuple[str, ...]  # links that now resolve into the new checkout
    backup_copies: dict[str, int]  # link name -> `<name>.L<N>.*` entries left in the backup dir
    prelude: str = ""
    account_mode: int | None = None  # the account dir's mode while the unit runs
    stray_count: int = 0  # `.<name>.relocate-claude-config.*` entries left in the account dir
    extra_check: Callable[[_Scene], None] | None = None


# The backup copy is written before the recheck and the rename, and no later step removes it.
# So the recheck-* and rename rows keep one `hooks` copy although `hooks` was not re-pointed,
# and the README says each retry before the fix can add another copy.
_FAILURE_ROWS: dict[str, _FailureRow] = {
    "temp-link": _FailureRow(
        prelude=_intercepting_function(
            "ln",
            f"{_HOOKS_CONDITION} || {_TEMP_LINK_CONDITION}",
            "if $forced; then rm -f -- \"$destination\"; fi; "
            "printf 'ln: %s: Permission denied\\n' \"$destination\" >&2; return 1",
        ),
        stderr_fragments=(_could_not_repoint("hooks", "could not create the new link"),),
        counts=(1, 1, 0, 0),
        old_links=("hooks",),
        repointed_links=("scripts",),
        backup_copies={"hooks": 0, "scripts": 1},
    ),
    "bad-text": _FailureRow(
        prelude=_BAD_TEXT_LINK_PRELUDE,
        stderr_fragments=(_could_not_repoint("hooks", "the new link does not resolve"),),
        counts=(1, 1, 0, 0),
        old_links=("hooks",),
        repointed_links=("scripts",),
        backup_copies={"hooks": 0, "scripts": 1},
    ),
    "rm-cleanup": _FailureRow(
        prelude=_BAD_TEXT_LINK_PRELUDE
        + _intercepting_function(
            "rm",
            _TEMP_LINK_CONDITION,
            "printf 'rm: %s: Permission denied\\n' \"$destination\" >&2; command rm \"$@\"; return 1",
        ),
        stderr_fragments=(_could_not_repoint("hooks", "the new link does not resolve"),),
        counts=(1, 1, 0, 0),
        old_links=("hooks",),
        repointed_links=("scripts",),
        backup_copies={"hooks": 0, "scripts": 1},
    ),
    "readlink-link": _FailureRow(
        prelude=(
            'readlink() { if [[ "$1" == -n && "$2" == -- && "$3" == "$ACCT/hooks" ]]; then return 1; fi; '
            'command readlink "$@"; }\n'
        ),
        stderr_fragments=(_could_not_repoint("hooks", "could not read its text"),),
        counts=(1, 1, 0, 0),
        old_links=("hooks",),
        repointed_links=("scripts",),
        backup_copies={"hooks": 0, "scripts": 1},
    ),
    "backup-copy": _FailureRow(
        prelude=_intercepting_function("ln", '[[ "$destination" == "$BACKUP"/hooks.* ]]'),
        stderr_fragments=(_could_not_repoint("hooks", "could not copy it into the backup dir"),),
        counts=(1, 1, 0, 0),
        old_links=("hooks",),
        repointed_links=("scripts",),
        backup_copies={"hooks": 0, "scripts": 1},
    ),
    "recheck-dir": _FailureRow(
        prelude=_intercepting_function(
            "ln", _TEMP_LINK_CONDITION, 'command ln "$@" || return 1; rm -f -- "$ACCT/hooks"; mkdir -- "$ACCT/hooks"; return 0'
        ),
        stderr_fragments=(_could_not_repoint("hooks", "it changed during the run"),),
        counts=(1, 1, 0, 0),
        old_links=(),
        repointed_links=("scripts",),
        backup_copies={"hooks": 1, "scripts": 1},
        extra_check=_hooks_was_replaced_by_an_empty_directory,
    ),
    "recheck-live": _FailureRow(
        prelude=_intercepting_function(
            "ln",
            _TEMP_LINK_CONDITION,
            'command ln "$@" || return 1; rm -f -- "$ACCT/hooks"; '
            'command ln -s -- "$NEW/claude/.claude/hooks" "$ACCT/hooks"; return 0',
        ),
        stderr_fragments=(_could_not_repoint("hooks", "it changed during the run"),),
        counts=(1, 1, 0, 0),
        old_links=(),
        repointed_links=("scripts",),
        backup_copies={"hooks": 1, "scripts": 1},
        extra_check=_hooks_was_replaced_by_a_live_link,
    ),
    "rename": _FailureRow(
        prelude=_intercepting_function("mv", _HOOKS_CONDITION),
        stderr_fragments=(_could_not_repoint("hooks", "could not rename the new link over it"),),
        counts=(1, 1, 0, 0),
        old_links=("hooks",),
        repointed_links=("scripts",),
        backup_copies={"hooks": 1, "scripts": 1},
    ),
    "unwritable": _FailureRow(
        account_mode=0o555,
        stderr_fragments=(
            _could_not_repoint("hooks", "could not create the new link"),
            _could_not_repoint("scripts", "could not create the new link"),
        ),
        counts=(0, 2, 0, 0),
        old_links=("hooks", "scripts"),
        repointed_links=(),
        backup_copies={"hooks": 0, "scripts": 0},
    ),
    "unsearchable": _FailureRow(
        account_mode=0o644,
        stderr_fragments=(f"could not search . in the dir on line {_LINE} of {_ROOTS_LABEL}",),
        counts=(0, 0, 0, 1),
        old_links=("hooks", "scripts"),
        repointed_links=(),
        backup_copies={"hooks": 0, "scripts": 0},
    ),
    "temp-name-taken": _FailureRow(
        prelude=(
            'mkdir -- "$ACCT/.hooks.relocate-claude-config.$$"\n'
            'echo kept > "$ACCT/.hooks.relocate-claude-config.$$/inner"\n'
        ),
        stderr_fragments=(_could_not_repoint("hooks", "its temporary name is taken"),),
        counts=(1, 1, 0, 0),
        old_links=("hooks",),
        repointed_links=("scripts",),
        backup_copies={"hooks": 0, "scripts": 1},
        stray_count=1,
        extra_check=_planted_temporary_name_is_untouched,
    ),
}


@pytest.mark.parametrize(
    "case",
    [
        pytest.param(case, marks=requires_non_root) if row.account_mode is not None else case
        for case, row in _FAILURE_ROWS.items()
    ],
)
def test_failure_keeps_the_old_link_and_leaves_no_strays(tmp_path: Path, case: str) -> None:
    row = _FAILURE_ROWS[case]
    scene = _scene(tmp_path)
    old_texts = {link_name: _stale_link(scene.account, link_name, scene.old_repo) for link_name in ("hooks", "scripts")}
    if row.account_mode is not None:
        scene.restrict(scene.account, row.account_mode)

    run = scene.run_unit(prelude=scene.seam_vars() + row.prelude)

    assert run.call_statuses == [1], run.stderr
    assert _outcomes(run.stdout) == [(_LINE, *row.counts)]
    assert _left_alone(run.stdout) == []
    for fragment in row.stderr_fragments:
        assert fragment in run.stderr
    for link_name in row.old_links:
        assert os.readlink(scene.account / link_name) == old_texts[link_name]
    for link_name in row.repointed_links:
        assert (scene.account / link_name).resolve() == (scene.new_repo / _PACKAGE_ROOT / link_name).resolve()
    assert {link_name: len(_backup_copies(scene.home, link_name)) for link_name in row.backup_copies} == row.backup_copies
    assert len(_stray_entries(scene)) == row.stray_count
    if row.extra_check is not None:
        row.extra_check(scene)
    _assert_neither_stream_names_an_account(run)
    _assert_neither_stream_names_a_link_text_or_an_old_checkout(run, list(old_texts.values()), [scene.old_repo])


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
    assert _stray_entries(scene) == []
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
    assert _stray_entries(scene) == []
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

    run = scene.run_unit(prelude=recording_prelude)

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


def _scene_home_claude(tmp_path: Path) -> _RunnerScene:
    scene = _runner_scene_base(tmp_path)
    scene.write_roots_file(("~/.claude", scene.home / ".claude"))
    scene.unchanged[scene.home / ".claude" / "hooks"] = _stale_link(scene.home / ".claude", "hooks", tmp_path / "old-repo")
    scene.skip_line = f"the dir on line 1 of {_ROOTS_LABEL} is ~/.claude, which the stows above cover"
    return scene


def _scene_inside_checkout(tmp_path: Path) -> _RunnerScene:
    scene = _runner_scene_base(tmp_path)
    inside = scene.new_repo / "acct-inside"
    inside.mkdir()
    scene.write_roots_file((str(inside), inside))
    scene.unchanged[inside / "hooks"] = _stale_link(inside, "hooks", tmp_path / "old-repo")
    scene.skip_line = f"the dir on line 1 of {_ROOTS_LABEL} lies inside the checkout, which this command never re-links"
    return scene


def _scene_checkout_itself(tmp_path: Path) -> _RunnerScene:
    scene = _runner_scene_base(tmp_path)
    scene.write_roots_file((str(scene.new_repo), scene.new_repo))
    scene.unchanged[scene.new_repo / "hooks"] = _stale_link(scene.new_repo, "hooks", tmp_path / "old-repo")
    scene.skip_line = f"the dir on line 1 of {_ROOTS_LABEL} lies inside the checkout, which this command never re-links"
    return scene


def _scene_home_claude_symlinked(tmp_path: Path) -> _RunnerScene:
    real_home = tmp_path / "acct-real-home"
    real_home.mkdir()
    linked_home = tmp_path / "acct-home-link"
    linked_home.symlink_to(real_home)
    scene = _runner_scene_base(tmp_path, home=linked_home)
    scene.write_roots_file(("~/.claude", linked_home / ".claude"))
    scene.unchanged[real_home / ".claude" / "hooks"] = _stale_link(real_home / ".claude", "hooks", tmp_path / "old-repo")
    scene.skip_line = f"the dir on line 1 of {_ROOTS_LABEL} is ~/.claude, which the stows above cover"
    return scene


def _scene_sibling_prefix(tmp_path: Path) -> _RunnerScene:
    scene = _runner_scene_base(tmp_path)
    sibling = tmp_path / "new-repo-acct-sibling"
    sibling.mkdir()
    scene.write_roots_file((str(sibling), sibling))
    _stale_link(sibling, "hooks", tmp_path / "old-repo")
    scene.repointed = [sibling / "hooks"]
    scene.expected_counts = (1, 0, 0, 0)
    return scene


def _scene_home(tmp_path: Path) -> _RunnerScene:
    scene = _runner_scene_base(tmp_path, new_repo_parent=tmp_path / "home")
    home = scene.home
    scene.write_roots_file(("~", home))
    _stale_link(home, "hooks", tmp_path / "old-repo")
    scene.repointed = [home / "hooks"]
    scene.unchanged[home / ".claude" / "decoy-link"] = _decoy_link(home / ".claude", tmp_path / "old-repo")
    scene.expected_counts = (1, 0, 0, 0)
    return scene


def _scene_checkout_parent(tmp_path: Path) -> _RunnerScene:
    parent = tmp_path / "acct-parent"
    scene = _runner_scene_base(tmp_path, new_repo_parent=parent, new_repo_name="-new-repo")
    scene.write_roots_file((str(parent), parent))
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
    _assert_neither_stream_names_a_listed_dir(run, scene.listed_dirs, scene.home)
    _assert_neither_stream_names_an_account(run)


@pytest.mark.parametrize(
    ("checkout_parent", "checkout_name", "glob_matched_sibling"),
    [
        pytest.param("", "new*", "newer-parent", id="star"),
        pytest.param("", "new?", "newx", id="question-mark"),
        pytest.param("Projects [old]", "repo", "Projects o/repo", id="brackets"),
    ],
)
def test_runner_reads_glob_characters_in_the_checkout_path_literally(
    tmp_path: Path, checkout_parent: str, checkout_name: str, glob_matched_sibling: str
) -> None:
    parent = tmp_path / checkout_parent
    parent.mkdir(exist_ok=True)
    scene = _runner_scene_base(tmp_path, new_repo_parent=parent, new_repo_name=checkout_name)
    inside = scene.new_repo / "acct-inside"
    inside.mkdir()
    inside_link_text = _stale_link(inside, "hooks", tmp_path / "old-repo")
    # An unquoted checkout path would read as a pattern in the `[[ "$dir_real" == "$new_real"/* ]]`
    # containment test in `relink_declared_dirs` and match this sibling, skipping it wrongly.
    sibling = tmp_path / glob_matched_sibling / "acct-sibling"
    sibling.mkdir(parents=True)
    _stale_link(sibling, "hooks", tmp_path / "old-repo")
    checkout_link_text = _stale_link(scene.new_repo, "hooks", tmp_path / "old-repo")
    scene.write_roots_file((str(inside), inside), (str(sibling), sibling), (str(scene.new_repo), scene.new_repo))

    run = _run_runner(scene.home, scene.new_repo, scene.scratch)

    assert run.call_statuses == [0], run.stderr
    for line in (1, 3):
        skip_line = f"the dir on line {line} of {_ROOTS_LABEL} lies inside the checkout, which this command never re-links"
        assert skip_line in run.stdout
    assert os.readlink(inside / "hooks") == inside_link_text
    assert os.readlink(scene.new_repo / "hooks") == checkout_link_text
    assert _outcomes(run.stdout) == [(2, 1, 0, 0, 0)]
    assert (sibling / "hooks").resolve() == (scene.new_repo / _PACKAGE_ROOT / "hooks").resolve()
    _assert_neither_stream_names_a_listed_dir(run, scene.listed_dirs, scene.home)
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
    _assert_neither_stream_names_an_account(run)


@dataclass
class _AwkwardRunner:
    home: Path
    scratch: Path
    account: Path
    typed_new_path: Path
    new_repo: Path
    expected_text: str
    listed_dirs: list[Path]


def _build_awkward_runner(tmp_path: Path) -> _AwkwardRunner:
    """A listed dir whose name holds a space, `$` and `*`, reached through a symlinked parent and then directly,
    and a checkout named `_AWKWARD_DESTINATION_NAME` that the call spells through a symlinked parent."""
    real_parent = tmp_path / "real-parent"
    real_parent.mkdir()
    (tmp_path / "link-parent").symlink_to(real_parent)
    account = real_parent / "acct-a dir $x*"
    account.mkdir()
    real_new_parent = tmp_path / "real-new-parent"
    real_new_parent.mkdir()
    (tmp_path / "link-new-parent").symlink_to(real_new_parent)
    scene = _runner_scene_base(tmp_path, new_repo_parent=real_new_parent, new_repo_name=_AWKWARD_DESTINATION_NAME)
    _stale_link(account, "hooks", tmp_path / "old-repo")
    typed_account = tmp_path / "link-parent" / account.name
    scene.write_roots_file((str(typed_account), typed_account), (str(account), account))
    return _AwkwardRunner(
        home=scene.home,
        scratch=scene.scratch,
        account=account,
        typed_new_path=tmp_path / "link-new-parent" / _AWKWARD_DESTINATION_NAME,
        new_repo=scene.new_repo,
        expected_text=os.path.relpath(scene.new_repo / _PACKAGE_ROOT / "hooks", account),
        listed_dirs=scene.listed_dirs,
    )


def test_runner_resolves_symlinked_and_awkward_paths(tmp_path: Path) -> None:
    scene = _build_awkward_runner(tmp_path)

    run = _run_runner(scene.home, scene.typed_new_path, scene.scratch)

    assert run.call_statuses == [0], run.stderr
    assert os.readlink(scene.account / "hooks") == scene.expected_text
    # One outcome row, on line 1: the dir listed a second time, on line 2, is walked once.
    assert _outcomes(run.stdout) == [(1, 1, 0, 0, 0)]
    _assert_neither_stream_names_a_listed_dir(run, scene.listed_dirs, scene.home)
    _assert_neither_stream_names_an_account(run)


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
        pytest.param("/a/x*", "/a/xy/d", "../xy/d", id="star-in-start-is-not-a-pattern"),
        pytest.param("/a/x?", "/a/xy/d", "../xy/d", id="question-mark-in-start-is-not-a-pattern"),
        pytest.param("/a/[b]", "/a/[b]/c", "c", id="brackets-in-start-match-literally"),
        pytest.param("/a/[b]", "/a/b/c", "../b/c", id="brackets-in-start-do-not-match-a-member"),
        pytest.param("/a/x*", "/a/x*/d", "d", id="star-in-start-with-target-beneath-is-not-a-pattern"),
        pytest.param("/a/[b]", "/a/[b]", ".", id="brackets-in-equal-paths-match-literally"),
    ],
)
def test_relative_path(tmp_path: Path, from_dir: str, to_path: str, expected: str) -> None:
    run = _run_sourced(tmp_path, [["_relative_path", from_dir, to_path]], cwd=tmp_path)

    assert run.call_statuses == [0], run.stderr
    assert run.call_outputs == [expected]


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


# ---------------------------------------------------------------------------
# print_manual_steps: closing text
# ---------------------------------------------------------------------------


def _bullet_holding(lines: list[str], needle: str) -> list[str]:
    """The `  - ` bullet, opener first, that holds the one line containing `needle`."""
    holding = [index for index, line in enumerate(lines) if needle in line]
    assert len(holding) == 1, holding
    opener = max(index for index in range(holding[0] + 1) if lines[index].startswith("  - "))
    following_openers = [index for index in range(holding[0] + 1, len(lines)) if lines[index].startswith("  - ")]
    return lines[opener : following_openers[0] if following_openers else len(lines)]


def test_manual_steps_name_the_retry_flag_and_give_registration_its_own_bullet(tmp_path: Path) -> None:
    run = _run_sourced(tmp_path, [["print_manual_steps"]], cwd=tmp_path)

    assert run.call_statuses == [0], run.stderr
    lines = run.call_outputs[0].splitlines()
    assert any("register-marketplace" in line for line in lines)
    assert any("with the flag when this run passed it" in line for line in lines)
    assert "marketplace" in _bullet_holding(lines, "register-marketplace")[0]
