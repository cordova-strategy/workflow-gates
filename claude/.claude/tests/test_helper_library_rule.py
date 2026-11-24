"""Contract tests for the helper-library rule and the isolated-hook builders that link every helper library."""
from __future__ import annotations

from pathlib import Path

# module object for monkeypatch.setattr: both builders read HOOKS_DIR from it at call time
import helpers
import pytest
from helpers import build_isolated_hook, helper_libraries, is_helper_library, symlink_hooks_lib_chain

_SEEDED_LIBRARY_FILE_NAMES = ["_config.sh", "_lib.sh", "_topic-lib.sh"]


@pytest.mark.parametrize(
    ("file_name", "expected"),
    [
        ("_lib.sh", True),
        ("_config.sh", True),
        ("_topic-lib.sh", True),
        ("hook.sh", False),
        ("__init__.py", False),
        ("_x.py", False),
        ("_x.sh.bak", False),
    ],
)
def test_is_helper_library(file_name: str, expected: bool) -> None:
    assert is_helper_library(file_name) is expected


def test_helper_libraries_lists_direct_helper_libraries_sorted(tmp_path: Path) -> None:
    for seeded_name in ["_b.sh", "_a.sh", "hook.sh", "__init__.py", "_x.sh.bak"]:
        (tmp_path / seeded_name).write_text("")
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "_c.sh").write_text("")

    assert helper_libraries(tmp_path) == [tmp_path / "_a.sh", tmp_path / "_b.sh"]


def _seed_hooks_dir(seeded_hooks_dir: Path) -> None:
    seeded_hooks_dir.mkdir()
    for seeded_name in [*_SEEDED_LIBRARY_FILE_NAMES, "config-keys.psv", "hook.sh"]:
        (seeded_hooks_dir / seeded_name).write_text("")


def _assert_links_resolve_into(directory: Path, expected_names: list[str], seeded_hooks_dir: Path) -> None:
    assert sorted(path.name for path in directory.iterdir()) == sorted(expected_names)
    for link in directory.iterdir():
        assert link.is_symlink()
        assert link.resolve() == (seeded_hooks_dir / link.name).resolve()


def test_symlink_hooks_lib_chain_links_every_helper_library(tmp_path: Path, monkeypatch) -> None:
    seeded_hooks_dir = tmp_path / "seeded-hooks"
    _seed_hooks_dir(seeded_hooks_dir)
    monkeypatch.setattr(helpers, "HOOKS_DIR", seeded_hooks_dir)
    destination = tmp_path / "destination"
    destination.mkdir()

    symlink_hooks_lib_chain(destination)

    _assert_links_resolve_into(destination, [*_SEEDED_LIBRARY_FILE_NAMES, "config-keys.psv"], seeded_hooks_dir)


def test_build_isolated_hook_links_every_helper_library(tmp_path: Path, monkeypatch) -> None:
    seeded_hooks_dir = tmp_path / "seeded-hooks"
    _seed_hooks_dir(seeded_hooks_dir)
    monkeypatch.setattr(helpers, "HOOKS_DIR", seeded_hooks_dir)

    isolated_hook = build_isolated_hook(tmp_path, seeded_hooks_dir / "hook.sh")

    _assert_links_resolve_into(isolated_hook.parent, ["hook.sh", *_SEEDED_LIBRARY_FILE_NAMES], seeded_hooks_dir)
