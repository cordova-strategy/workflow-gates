"""Tests for _branch_records.py's archive-directory resolver.

The parity cases run the bash writer's `branch_records_status` and compare the account directory it computes.
Every marker comes from `build_archive_env`, never from the module's constant, so the `absent` and `present`
cases tie the module's marker name to the lib's.
"""
from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

import _branch_records
import pytest

from . import _branch_records_helpers as records_helpers
from ._branch_records_helpers import SENTINEL_NAME, build_archive_env, list_tree, requires_non_root, run_status

# The autouse fixture applies only where the test module binds it, and an import would trip F401.
process_isolation = records_helpers.process_isolation
expected_account_directory = records_helpers.account_directory
expected_archive_root = records_helpers.archive_root

SUBTREE_NAME = "review-narrative-ledger"

Defer = Callable[[Callable[[], None]], object]


def _config_dir(env: dict[str, str]) -> Path:
    return Path(env["CLAUDE_CONFIG_DIR"])


def _subtree_state(env: dict[str, str]) -> _branch_records.ArchiveSubtree:
    return _branch_records.archive_subtree(_config_dir(env), SUBTREE_NAME, env["HOME"])


def _make_account_directory(env: dict[str, str]) -> Path:
    account_dir = expected_account_directory(env)
    account_dir.mkdir(parents=True, exist_ok=True)
    return account_dir


def _make_subtree(env: dict[str, str]) -> Path:
    subtree = _make_account_directory(env) / SUBTREE_NAME
    subtree.mkdir(exist_ok=True)
    return subtree


# --- encode_component ---


@pytest.mark.parametrize(
    ("path", "encoded"),
    [
        pytest.param("/a/b", "%2Fa%2Fb", id="slashes"),
        pytest.param("/a%2Fb", "%2Fa%252Fb", id="literal-percent-2f-stays-distinct-from-a-slash"),
        pytest.param("/50%", "%2F50%25", id="percent"),
    ],
)
def test_encode_component_escapes_percent_before_slash(path, encoded):
    assert _branch_records.encode_component(path) == encoded


# --- parity with the bash writer ---


def _plain(tmp_path: Path) -> dict[str, str]:
    return build_archive_env(tmp_path)


def _named(directory_name: str) -> Callable[[Path], dict[str, str]]:
    return lambda tmp_path: build_archive_env(tmp_path, config_dir=tmp_path / directory_name)


def _reached_through_symlink(tmp_path: Path) -> dict[str, str]:
    real_config_dir = tmp_path / "real_config"
    real_config_dir.mkdir()
    linked_config_dir = tmp_path / "linked_config"
    linked_config_dir.symlink_to(real_config_dir)
    return build_archive_env(tmp_path, config_dir=linked_config_dir)


def _reached_through_symlink_to_a_newline_named_directory(tmp_path: Path) -> dict[str, str]:
    newline_named_dir = tmp_path / "newline_named\n"
    newline_named_dir.mkdir()
    linked_config_dir = tmp_path / "linked_config"
    linked_config_dir.symlink_to(newline_named_dir)
    return build_archive_env(tmp_path, config_dir=linked_config_dir)


def _dot_dot_after_symlink(tmp_path: Path) -> dict[str, str]:
    real_parent = tmp_path / "real_parent"
    (real_parent / "inner").mkdir(parents=True)
    linked_inner = tmp_path / "linked_inner"
    linked_inner.symlink_to(real_parent / "inner")
    return build_archive_env(tmp_path, config_dir=linked_inner / ".." / "sibling")


def _with_config_dir_suffix(suffix: str) -> Callable[[Path], dict[str, str]]:
    def build_env(tmp_path: Path) -> dict[str, str]:
        env = build_archive_env(tmp_path)
        return {**env, "CLAUDE_CONFIG_DIR": env["CLAUDE_CONFIG_DIR"] + suffix}

    return build_env


def _root_is_resolving_symlink(tmp_path: Path) -> dict[str, str]:
    return build_archive_env(tmp_path, root_symlink_target=tmp_path / "root_target")


def _marker_is_symlink(tmp_path: Path) -> dict[str, str]:
    env = build_archive_env(tmp_path, create_sentinel=False)
    marker_target = tmp_path / "marker_target"
    marker_target.write_text("")
    (expected_archive_root(env) / SENTINEL_NAME).symlink_to(marker_target)
    return env


@pytest.mark.parametrize(
    "build_env",
    [
        pytest.param(_plain, id="plain-name"),
        pytest.param(_named("name with space"), id="name-with-space"),
        pytest.param(_named("name%with%percent"), id="name-with-percent"),
        pytest.param(_named("name%2Fliteral"), id="name-with-literal-percent-2f"),
        pytest.param(_named("nom-é-名前"), id="non-ascii-name"),
        pytest.param(_reached_through_symlink, id="config-dir-through-symlink"),
        pytest.param(
            _reached_through_symlink_to_a_newline_named_directory,
            id="config-dir-through-symlink-to-newline-named-directory",
        ),
        pytest.param(_dot_dot_after_symlink, id="dot-dot-after-symlink"),
        pytest.param(_with_config_dir_suffix("/"), id="trailing-slash"),
        pytest.param(_with_config_dir_suffix("\n"), id="trailing-newline"),
        pytest.param(_root_is_resolving_symlink, id="root-is-resolving-symlink"),
        pytest.param(_marker_is_symlink, id="marker-is-symlink"),
    ],
)
def test_account_directory_matches_the_bash_writer(tmp_path, build_env):
    """Covers case-sensitive, non-normalizing filesystems only, as CI's is: another can spell one path two ways."""
    env = build_env(tmp_path)
    report = run_status(tmp_path, env)
    assert report.state == "ready", report.reason
    assert Path(report.account_dir) == _branch_records.account_directory(_config_dir(env), env["HOME"])


def test_account_directory_differs_from_the_bash_writer_for_a_double_slash_prefix(tmp_path):
    """Pins the divergence `account_directory`'s docstring names: the writer keeps `//`, `realpath` does not."""
    env = build_archive_env(tmp_path)
    double_slash_config_dir = "/" + env["CLAUDE_CONFIG_DIR"]
    report = run_status(tmp_path, {**env, "CLAUDE_CONFIG_DIR": double_slash_config_dir})
    assert report.state == "ready", report.reason
    assert Path(report.account_dir).name.startswith("%2F%2F")
    reader_directory = _branch_records.account_directory(double_slash_config_dir, env["HOME"])
    assert reader_directory != Path(report.account_dir)
    assert reader_directory == expected_account_directory(env)


# --- None results ---


@pytest.mark.parametrize(
    "home",
    [
        pytest.param(None, id="none"),
        pytest.param("", id="empty"),
        pytest.param("relative/home", id="relative"),
        pytest.param("/srv/with\0nul", id="holds-nul"),
    ],
)
def test_archive_root_is_none_unless_home_is_a_non_empty_absolute_path(home):
    assert _branch_records.archive_root(home) is None


def _empty_home(tmp_path: Path) -> tuple[Path | str, str]:
    env = build_archive_env(tmp_path)
    return _config_dir(env), ""


def _relative_config_dir(tmp_path: Path) -> tuple[Path | str, str]:
    env = build_archive_env(tmp_path)
    # `process_isolation` makes `tmp_path` the cwd, so the path resolves to a real directory.
    # Only the absolute-path rule can then refuse it.
    assert Path("archive_config").is_dir()
    return Path("archive_config"), env["HOME"]


def _missing_config_dir(tmp_path: Path) -> tuple[Path | str, str]:
    env = build_archive_env(tmp_path)
    return tmp_path / "missing_config", env["HOME"]


def _config_dir_is_a_file(tmp_path: Path) -> tuple[Path | str, str]:
    env = build_archive_env(tmp_path)
    config_file = tmp_path / "config_file"
    config_file.write_text("")
    return config_file, env["HOME"]


def _config_dir_holds_nul(tmp_path: Path) -> tuple[Path | str, str]:
    env = build_archive_env(tmp_path)
    return str(_config_dir(env)) + "\0", env["HOME"]


def _config_dir_is_a_symlink_loop(tmp_path: Path) -> tuple[Path | str, str]:
    env = build_archive_env(tmp_path)
    loop = tmp_path / "config_loop"
    loop.symlink_to(loop)
    return loop, env["HOME"]


@pytest.mark.parametrize(
    "arrange",
    [
        pytest.param(_empty_home, id="empty-home"),
        pytest.param(_relative_config_dir, id="relative-config-dir"),
        pytest.param(_missing_config_dir, id="missing-config-dir"),
        pytest.param(_config_dir_is_a_file, id="config-dir-is-a-file"),
        pytest.param(_config_dir_holds_nul, id="config-dir-holds-nul"),
        pytest.param(_config_dir_is_a_symlink_loop, id="config-dir-is-a-symlink-loop"),
    ],
)
def test_account_directory_is_none_for_an_unusable_input(tmp_path, arrange):
    config_dir, home = arrange(tmp_path)
    assert _branch_records.account_directory(config_dir, home) is None


# --- subtree states ---


def _present_plain(tmp_path: Path, defer: Defer) -> dict[str, str]:
    env = build_archive_env(tmp_path)
    _make_subtree(env)
    return env


def _present_with_key_off(tmp_path: Path, defer: Defer) -> dict[str, str]:
    env = build_archive_env(tmp_path, key_line="agent_branch_records = false")
    _make_subtree(env)
    return env


def _present_under_root_symlink(tmp_path: Path, defer: Defer) -> dict[str, str]:
    env = build_archive_env(tmp_path, root_symlink_target=tmp_path / "root_target")
    _make_subtree(env)
    return env


def _present_with_marker_symlink(tmp_path: Path, defer: Defer) -> dict[str, str]:
    env = _marker_is_symlink(tmp_path)
    _make_subtree(env)
    return env


def _absent(tmp_path: Path, defer: Defer) -> dict[str, str]:
    env = build_archive_env(tmp_path)
    _make_account_directory(env)
    return env


def _absent_without_account_directory(tmp_path: Path, defer: Defer) -> dict[str, str]:
    return build_archive_env(tmp_path)


def _unmarked_without_root(tmp_path: Path, defer: Defer) -> dict[str, str]:
    return build_archive_env(tmp_path, create_root=False)


def _unmarked_dangling_root_link(tmp_path: Path, defer: Defer) -> dict[str, str]:
    return build_archive_env(tmp_path, root_symlink_target=tmp_path / "gone", create_symlink_target=False)


def _unmarked_root_is_a_file(tmp_path: Path, defer: Defer) -> dict[str, str]:
    env = build_archive_env(tmp_path, create_root=False)
    root = expected_archive_root(env)
    root.parent.mkdir(parents=True)
    root.write_text("")
    return env


def _unmarked_root_holds_subtree_without_marker(tmp_path: Path, defer: Defer) -> dict[str, str]:
    env = build_archive_env(tmp_path, create_sentinel=False)
    _make_subtree(env)
    return env


def _unmarked_marker_is_a_directory(tmp_path: Path, defer: Defer) -> dict[str, str]:
    env = build_archive_env(tmp_path, create_sentinel=False)
    (expected_archive_root(env) / SENTINEL_NAME).mkdir()
    _make_subtree(env)
    return env


def _unmarked_marker_is_a_dangling_link(tmp_path: Path, defer: Defer) -> dict[str, str]:
    env = build_archive_env(tmp_path, create_sentinel=False)
    (expected_archive_root(env) / SENTINEL_NAME).symlink_to(tmp_path / "gone")
    _make_subtree(env)
    return env


def _unmarked_marker_is_a_fifo(tmp_path: Path, defer: Defer) -> dict[str, str]:
    env = build_archive_env(tmp_path, create_sentinel=False)
    os.mkfifo(expected_archive_root(env) / SENTINEL_NAME)
    _make_subtree(env)
    return env


def _unreadable_marker_is_a_link_loop(tmp_path: Path, defer: Defer) -> dict[str, str]:
    env = build_archive_env(tmp_path, create_sentinel=False)
    marker = expected_archive_root(env) / SENTINEL_NAME
    marker.symlink_to(marker)
    _make_subtree(env)
    return env


def _unreadable_root_is_a_link_loop(tmp_path: Path, defer: Defer) -> dict[str, str]:
    env = build_archive_env(tmp_path, create_root=False)
    root = expected_archive_root(env)
    root.parent.mkdir(parents=True)
    root.symlink_to(root)
    return env


def _unreadable_subtree_is_a_file(tmp_path: Path, defer: Defer) -> dict[str, str]:
    env = build_archive_env(tmp_path)
    (_make_account_directory(env) / SUBTREE_NAME).write_text("")
    return env


def _unreadable_subtree_links_outside_account(tmp_path: Path, defer: Defer) -> dict[str, str]:
    env = build_archive_env(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (_make_account_directory(env) / SUBTREE_NAME).symlink_to(outside)
    return env


def _unreadable_subtree_links_outside_through_a_second_link(tmp_path: Path, defer: Defer) -> dict[str, str]:
    env = build_archive_env(tmp_path)
    account_dir = _make_account_directory(env)
    outside = tmp_path / "outside"
    outside.mkdir()
    (account_dir / "hop").symlink_to(outside)
    (account_dir / SUBTREE_NAME).symlink_to(account_dir / "hop")
    return env


def _unreadable_subtree_links_to_archive_root(tmp_path: Path, defer: Defer) -> dict[str, str]:
    env = build_archive_env(tmp_path)
    (_make_account_directory(env) / SUBTREE_NAME).symlink_to(expected_archive_root(env))
    return env


def _unreadable_dangling_subtree_link(tmp_path: Path, defer: Defer) -> dict[str, str]:
    env = build_archive_env(tmp_path)
    (_make_account_directory(env) / SUBTREE_NAME).symlink_to(tmp_path / "gone")
    return env


def _unreadable_subtree_is_a_link_loop(tmp_path: Path, defer: Defer) -> dict[str, str]:
    env = build_archive_env(tmp_path)
    subtree = _make_account_directory(env) / SUBTREE_NAME
    subtree.symlink_to(subtree)
    return env


def _unreadable_subtree_links_to_sibling_subtree(tmp_path: Path, defer: Defer) -> dict[str, str]:
    env = build_archive_env(tmp_path)
    account_dir = _make_account_directory(env)
    (account_dir / "branches").mkdir()
    (account_dir / SUBTREE_NAME).symlink_to(account_dir / "branches")
    return env


def _unreadable_subtree_links_to_deeper_entry(tmp_path: Path, defer: Defer) -> dict[str, str]:
    env = build_archive_env(tmp_path)
    account_dir = _make_account_directory(env)
    (account_dir / "branches" / "key").mkdir(parents=True)
    (account_dir / SUBTREE_NAME).symlink_to(account_dir / "branches" / "key")
    return env


def _unreadable_subtree_link_chain_ends_at_same_named_directory_elsewhere(
    tmp_path: Path, defer: Defer
) -> dict[str, str]:
    env = build_archive_env(tmp_path)
    account_dir = _make_account_directory(env)
    same_named_directory = account_dir / "branches" / "key" / SUBTREE_NAME
    same_named_directory.mkdir(parents=True)
    (account_dir / "hop").symlink_to(same_named_directory)
    (account_dir / SUBTREE_NAME).symlink_to(account_dir / "hop")
    return env


def _unreadable_account_directory_links_to_sibling(tmp_path: Path, defer: Defer) -> dict[str, str]:
    env = build_archive_env(tmp_path)
    sibling_account_dir = expected_archive_root(env) / "sibling-account"
    (sibling_account_dir / SUBTREE_NAME).mkdir(parents=True)
    expected_account_directory(env).symlink_to(sibling_account_dir)
    return env


def _unreadable_account_directory_is_a_dangling_link(tmp_path: Path, defer: Defer) -> dict[str, str]:
    env = build_archive_env(tmp_path)
    expected_account_directory(env).symlink_to(tmp_path / "gone")
    return env


def _unreadable_account_directory_is_a_file(tmp_path: Path, defer: Defer) -> dict[str, str]:
    env = build_archive_env(tmp_path)
    expected_account_directory(env).write_text("")
    return env


def _unreadable_account_component_exceeds_name_max(tmp_path: Path, defer: Defer) -> dict[str, str]:
    name_max = os.pathconf(tmp_path, "PC_NAME_MAX")
    env = build_archive_env(tmp_path, config_dir=tmp_path / ("c" * name_max))
    assert len(expected_account_directory(env).name) > name_max, "the case needs an over-long encoded component"
    return env


def _unreadable_subtree_links_into_prefix_sibling(tmp_path: Path, defer: Defer) -> dict[str, str]:
    env = build_archive_env(tmp_path)
    account_dir = _make_account_directory(env)
    prefix_sibling = account_dir.with_name(account_dir.name + "-extended")
    (prefix_sibling / SUBTREE_NAME).mkdir(parents=True)
    (account_dir / SUBTREE_NAME).symlink_to(prefix_sibling / SUBTREE_NAME)
    return env


def _unreadable_subtree_links_to_account_directory(tmp_path: Path, defer: Defer) -> dict[str, str]:
    env = build_archive_env(tmp_path)
    (_make_account_directory(env) / SUBTREE_NAME).symlink_to(".")
    return env


def _unreadable_root_mode_zero(tmp_path: Path, defer: Defer) -> dict[str, str]:
    env = build_archive_env(tmp_path)
    _make_subtree(env)
    root = expected_archive_root(env)
    root.chmod(0)
    defer(lambda: root.chmod(0o700))
    return env


def _unreadable_account_directory_mode_zero(tmp_path: Path, defer: Defer) -> dict[str, str]:
    env = build_archive_env(tmp_path)
    _make_subtree(env)
    account_dir = expected_account_directory(env)
    account_dir.chmod(0)
    defer(lambda: account_dir.chmod(0o700))
    return env


def _unresolvable_missing_config_dir(tmp_path: Path, defer: Defer) -> dict[str, str]:
    env = build_archive_env(tmp_path)
    return {**env, "CLAUDE_CONFIG_DIR": str(tmp_path / "missing_config")}


def _forbid_directory_listing(*_args, **_kwargs):
    raise AssertionError("archive_subtree listed a directory")


@pytest.mark.parametrize(
    ("arrange", "expected_state"),
    [
        pytest.param(_present_plain, "present", id="present-plain"),
        pytest.param(_present_with_key_off, "present", id="present-with-key-off"),
        pytest.param(_present_under_root_symlink, "present", id="present-under-root-symlink"),
        pytest.param(_present_with_marker_symlink, "present", id="present-with-marker-symlink"),
        pytest.param(_absent, "absent", id="absent"),
        pytest.param(_absent_without_account_directory, "absent", id="absent-without-account-directory"),
        pytest.param(_unmarked_without_root, "unmarked", id="unmarked-without-root"),
        pytest.param(_unmarked_dangling_root_link, "unmarked", id="unmarked-dangling-root-link"),
        pytest.param(_unmarked_root_is_a_file, "unmarked", id="unmarked-root-is-a-file"),
        pytest.param(
            _unmarked_root_holds_subtree_without_marker, "unmarked", id="unmarked-subtree-without-marker"
        ),
        pytest.param(_unmarked_marker_is_a_directory, "unmarked", id="unmarked-marker-is-a-directory"),
        pytest.param(_unmarked_marker_is_a_dangling_link, "unmarked", id="unmarked-marker-is-a-dangling-link"),
        pytest.param(_unmarked_marker_is_a_fifo, "unmarked", id="unmarked-marker-is-a-fifo"),
        pytest.param(_unreadable_marker_is_a_link_loop, "unreadable", id="unreadable-marker-is-a-link-loop"),
        pytest.param(_unreadable_root_is_a_link_loop, "unreadable", id="unreadable-root-is-a-link-loop"),
        pytest.param(_unreadable_subtree_is_a_file, "unreadable", id="unreadable-subtree-is-a-file"),
        pytest.param(
            _unreadable_subtree_links_outside_account, "unreadable", id="unreadable-subtree-links-outside-account"
        ),
        pytest.param(
            _unreadable_subtree_links_outside_through_a_second_link,
            "unreadable",
            id="unreadable-subtree-links-outside-through-a-second-link",
        ),
        pytest.param(
            _unreadable_subtree_links_to_archive_root, "unreadable", id="unreadable-subtree-links-to-archive-root"
        ),
        pytest.param(_unreadable_dangling_subtree_link, "unreadable", id="unreadable-dangling-subtree-link"),
        pytest.param(_unreadable_subtree_is_a_link_loop, "unreadable", id="unreadable-subtree-is-a-link-loop"),
        pytest.param(
            _unreadable_subtree_links_to_sibling_subtree,
            "unreadable",
            id="unreadable-subtree-links-to-sibling-subtree",
        ),
        pytest.param(
            _unreadable_subtree_links_to_deeper_entry, "unreadable", id="unreadable-subtree-links-to-deeper-entry"
        ),
        pytest.param(
            _unreadable_subtree_link_chain_ends_at_same_named_directory_elsewhere,
            "unreadable",
            id="unreadable-subtree-link-chain-ends-at-same-named-directory-elsewhere",
        ),
        pytest.param(
            _unreadable_account_directory_links_to_sibling,
            "unreadable",
            id="unreadable-account-directory-links-to-sibling",
        ),
        pytest.param(
            _unreadable_account_directory_is_a_dangling_link,
            "unreadable",
            id="unreadable-account-directory-is-a-dangling-link",
        ),
        pytest.param(
            _unreadable_account_directory_is_a_file, "unreadable", id="unreadable-account-directory-is-a-file"
        ),
        pytest.param(
            _unreadable_account_component_exceeds_name_max,
            "unreadable",
            id="unreadable-account-component-exceeds-name-max",
        ),
        pytest.param(
            _unreadable_subtree_links_into_prefix_sibling,
            "unreadable",
            id="unreadable-subtree-links-into-prefix-sibling",
        ),
        pytest.param(
            _unreadable_subtree_links_to_account_directory,
            "unreadable",
            id="unreadable-subtree-links-to-account-directory",
        ),
        pytest.param(_unreadable_root_mode_zero, "unreadable", id="unreadable-root-mode-zero", marks=requires_non_root),
        pytest.param(
            _unreadable_account_directory_mode_zero,
            "unreadable",
            id="unreadable-account-directory-mode-zero",
            marks=requires_non_root,
        ),
        pytest.param(_unresolvable_missing_config_dir, "unresolvable", id="unresolvable-missing-config-dir"),
    ],
)
def test_archive_subtree_state(tmp_path, request, monkeypatch, arrange, expected_state):
    """Only a marker stat that finds nothing or a non-regular file gives `unmarked`, so any other stat error gives `unreadable`.

    The call also writes nothing and lists no directory: a write could create the root of an unmounted volume.
    """
    env = arrange(tmp_path, request.addfinalizer)
    tree_before_call = list_tree(tmp_path)
    with monkeypatch.context() as patch:
        patch.setattr(os, "scandir", _forbid_directory_listing)
        patch.setattr(os, "listdir", _forbid_directory_listing)
        subtree = _subtree_state(env)
    assert subtree.state == expected_state
    if expected_state == "present":
        assert subtree.directory == expected_account_directory(env) / SUBTREE_NAME
    else:
        assert subtree.directory is None
    assert list_tree(tmp_path) == tree_before_call


def test_subtree_state_vocabulary_is_the_five_states_callers_compare_against():
    assert {state.value for state in _branch_records.SubtreeState} == {
        "unresolvable",
        "unmarked",
        "unreadable",
        "absent",
        "present",
    }


def test_archive_subtree_is_unreadable_for_a_name_longer_than_the_filesystem_allows(tmp_path):
    env = build_archive_env(tmp_path)
    _make_account_directory(env)
    name_max = os.pathconf(tmp_path, "PC_NAME_MAX")
    subtree = _branch_records.archive_subtree(_config_dir(env), "n" * (name_max + 1), env["HOME"])
    assert subtree.state == "unreadable"
    assert subtree.directory is None


@pytest.mark.parametrize(
    "name",
    [
        pytest.param("", id="empty"),
        pytest.param(".", id="dot"),
        pytest.param("..", id="dot-dot"),
        pytest.param("with/slash", id="holds-slash"),
        pytest.param("with\0nul", id="holds-nul"),
    ],
)
def test_archive_subtree_rejects_a_name_that_is_not_one_component(tmp_path, name):
    env = build_archive_env(tmp_path)
    # With no such config dir nothing after the name check can raise, so the check alone is under test.
    missing_config_dir = tmp_path / "missing_config"
    with pytest.raises(ValueError, match="one path component"):
        _branch_records.archive_subtree(missing_config_dir, name, env["HOME"])
