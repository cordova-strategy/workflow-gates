"""Every helper library of a hooks directory is sourced by a shipped shell file.

A helper library is a `_`-prefixed `.sh` file in `claude/.claude/hooks/` or
`plugins/*/hooks/` (see `is_helper_library`). One that nothing sources is dead
weight, or a hook that named itself with a leading `_` to skip the hook checks.
The registered half of this invariant, that no hook config registers a helper
library as a command, lives in `test_hook_alignment.py`.

The check is a text match over `_shipped_shell_files()`, so it guards against
honest mistakes. Its blind spots:

- A heredoc line shaped like a source statement passes it.
- Two libraries that source only each other pass it.
- A sourcer not yet `git add`ed is invisible to it, since the corpus comes from
  `git ls-files`.
- Any directory part ending in `/hooks` counts as sourcing, whatever precedes
  it: a wrong depth such as `../../hooks`, an unset variable, or a plugin root
  in a main-tree hook.
"""
from __future__ import annotations

import functools
import re
from pathlib import PurePosixPath

import pytest
from helpers import REPO_ROOT, is_helper_library

from .test_hook_alignment import ALL_HOOKS_AND_LIBS
from .test_shell_dialect import _read_text, _shipped_shell_files

_HELPER_LIBRARIES = [
    path.relative_to(REPO_ROOT).as_posix() for path in ALL_HOOKS_AND_LIBS if is_helper_library(path.name)
]

_SOURCE_STATEMENT_RE = re.compile(
    r"^\s*(?:if\s+!\s+)?(?:\.|source)\s+\"(?P<directory>.*)/(?P<name>_[\w.-]+\.sh)\""
)
_SAME_DIRECTORY_EXPRESSIONS = frozenset({"${0%/*}", '$(dirname "$0")', '$(dirname "${BASH_SOURCE[0]}")'})
_PLUGINS_SEGMENT = "plugins"


def _tree_of(repo_relative_path: str) -> str | None:
    """The `plugins/<name>` directory a path belongs to, or None for a path outside `plugins/`."""
    parts = PurePosixPath(repo_relative_path).parts
    return f"{parts[0]}/{parts[1]}" if parts[0] == _PLUGINS_SEGMENT else None


def _sources_helper_library(sourcer: str, text: str, library: str) -> bool:
    """True when `text`, the content of repo-relative `sourcer`, has a source statement for repo-relative `library`.

    A plugin's hooks source that plugin's own vendored libraries, so the two
    paths must sit in the same tree. Another helper library counts as a sourcer.
    """
    if sourcer == library or _tree_of(sourcer) != _tree_of(library):
        return False
    library_path = PurePosixPath(library)
    sourcer_beside_library = PurePosixPath(sourcer).parent == library_path.parent
    for line in text.splitlines():
        statement = _SOURCE_STATEMENT_RE.match(line)
        if statement is None or statement.group("name") != library_path.name:
            continue
        directory = statement.group("directory")
        if directory.endswith("/hooks") or (sourcer_beside_library and directory in _SAME_DIRECTORY_EXPRESSIONS):
            return True
    return False


def _unsourced_helper_libraries(libraries: list[str], texts: dict[str, str]) -> list[str]:
    """Each of `libraries`, in order, that no entry of `texts` (repo-relative path to content) sources."""
    return [
        library
        for library in libraries
        if not any(_sources_helper_library(sourcer, text, library) for sourcer, text in texts.items())
    ]


@functools.cache
def _shipped_shell_texts() -> dict[str, str]:
    return {path: _read_text(path) for path in _shipped_shell_files()}


@pytest.mark.parametrize("library", _HELPER_LIBRARIES, ids=_HELPER_LIBRARIES)
def test_every_helper_library_is_sourced_by_a_shipped_shell_file(library: str) -> None:
    assert _unsourced_helper_libraries([library], _shipped_shell_texts()) == [], (
        f"{library} is a helper library (a `_`-prefixed .sh file in a hooks directory) that no shipped "
        "shell file sources. Accepted source shapes: from the library's own directory, "
        '`. "${0%/*}/<name>"`, `. "$(dirname "$0")/<name>"` or `. "$(dirname "${BASH_SOURCE[0]}")/<name>"`; '
        'from anywhere in its tree, a double-quoted operand whose directory part ends in `/hooks`, '
        'such as `. "$(dirname "$0")/../hooks/<name>"`. '
        "A sourcer file not yet `git add`ed is not scanned. "
        "If the file is a hook, drop the leading `_` from its name."
    )


_MAIN_HOOK = "claude/.claude/hooks/some-hook.sh"
_MAIN_LIBRARY = "claude/.claude/hooks/_topic-lib.sh"
_PLUGIN_LIBRARY = "plugins/some-plugin/hooks/_lib.sh"

_SOURCES_HELPER_LIBRARY_CONTROL_TABLE = [
    pytest.param(
        _MAIN_HOOK, '. "${0%/*}/_topic-lib.sh"\n', _MAIN_LIBRARY, True, id="same-directory-dollar-zero-expansion"
    ),
    pytest.param(
        "claude/.claude/scripts/some-script.sh",
        '. "$(dirname "$0")/../hooks/_topic-lib.sh"\n',
        _MAIN_LIBRARY,
        True,
        id="scripts-side-relative-hooks-directory",
    ),
    pytest.param(
        "install.sh",
        'if ! . "$REPO_DIR/claude/.claude/hooks/_topic-lib.sh"; then\n',
        _MAIN_LIBRARY,
        True,
        id="installer-repo-dir-hooks-directory",
    ),
    pytest.param(
        "plugins/some-plugin/hooks/some-hook.sh",
        '. "${CLAUDE_PLUGIN_ROOT}/hooks/_lib.sh"\n',
        _PLUGIN_LIBRARY,
        True,
        id="plugin-hook-plugin-root-hooks-directory",
    ),
    pytest.param(
        "plugins/some-plugin/hooks/some-hook.sh",
        '. "${CLAUDE_PLUGIN_ROOT}/hooks/_topic-lib.sh"\n',
        _MAIN_LIBRARY,
        False,
        id="plugin-sourcer-for-a-main-library",
    ),
    pytest.param(
        "plugins/other-plugin/hooks/some-hook.sh",
        '. "${CLAUDE_PLUGIN_ROOT}/hooks/_lib.sh"\n',
        _PLUGIN_LIBRARY,
        False,
        id="sourcer-in-a-different-plugin",
    ),
    pytest.param(
        "claude/.claude/scripts/some-script.sh",
        '. "$(dirname "$0")/_topic-lib.sh"\n',
        _MAIN_LIBRARY,
        False,
        id="scripts-directory-same-directory-source-of-a-same-named-library",
    ),
    pytest.param(_MAIN_HOOK, 'source "${0%/*}/_topic-lib.sh"\n', _MAIN_LIBRARY, True, id="source-keyword"),
    pytest.param(
        _MAIN_HOOK,
        '. "${0%/*}/_other-lib.sh"\n',
        _MAIN_LIBRARY,
        False,
        id="sourcer-names-a-different-library",
    ),
    pytest.param(
        _MAIN_HOOK, '# . "${0%/*}/_topic-lib.sh"\n', _MAIN_LIBRARY, False, id="comment-line"
    ),
    pytest.param(
        _MAIN_LIBRARY, '. "${0%/*}/_topic-lib.sh"\n', _MAIN_LIBRARY, False, id="library-sourcing-itself"
    ),
    pytest.param(
        _MAIN_HOOK,
        '. "$(dirname "$0")/_topic-lib.sh"\n',
        _MAIN_LIBRARY,
        True,
        id="same-directory-dirname-dollar-zero",
    ),
    pytest.param(
        _MAIN_HOOK,
        '. "$(dirname "${BASH_SOURCE[0]}")/_topic-lib.sh"\n',
        _MAIN_LIBRARY,
        True,
        id="same-directory-dirname-bash-source",
    ),
    pytest.param(
        "claude/.claude/hooks/_other-lib.sh",
        '. "${0%/*}/_topic-lib.sh"\n',
        _MAIN_LIBRARY,
        True,
        id="sourcer-is-a-helper-library",
    ),
]


@pytest.mark.parametrize(("sourcer", "text", "library", "expected"), _SOURCES_HELPER_LIBRARY_CONTROL_TABLE)
def test_sources_helper_library_control_table(sourcer: str, text: str, library: str, expected: bool) -> None:
    assert _sources_helper_library(sourcer, text, library) is expected


@pytest.mark.parametrize(
    ("hook_text", "expected_unsourced"),
    [
        pytest.param('. "${0%/*}/_topic-lib.sh"\n', [], id="sourced"),
        pytest.param("# sources _topic-lib.sh\n", [_MAIN_LIBRARY], id="unsourced"),
        pytest.param('. "${0%/*}/_lib.sh"\n', [_MAIN_LIBRARY], id="another-library-sourced"),
    ],
)
def test_unsourced_helper_libraries_control(hook_text: str, expected_unsourced: list[str]) -> None:
    texts = {_MAIN_HOOK: hook_text, _MAIN_LIBRARY: "topic_fn() { :; }\n"}

    assert _unsourced_helper_libraries([_MAIN_LIBRARY], texts) == expected_unsourced


def test_a_helper_library_sourced_only_by_another_helper_library_is_sourced() -> None:
    texts = {"claude/.claude/hooks/_other-lib.sh": '. "${0%/*}/_topic-lib.sh"\n', _MAIN_LIBRARY: "topic_fn() { :; }\n"}

    assert _unsourced_helper_libraries([_MAIN_LIBRARY], texts) == []


def test_helper_libraries_include_lib_sh_and_config_sh() -> None:
    """An inclusion floor: an empty `_HELPER_LIBRARIES` would leave the sourced test with no cases, which pytest skips."""
    assert {"claude/.claude/hooks/_lib.sh", "claude/.claude/hooks/_config.sh"} <= set(_HELPER_LIBRARIES)
