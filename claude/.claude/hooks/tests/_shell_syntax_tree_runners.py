"""Shared by the shell-syntax-tree.py tests: the module, shfmt, real bash, the cut-residual fixtures, the position matrix."""
from __future__ import annotations

import functools
import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple

import pytest
from helpers import HOOKS_DIR, production_shfmt_argv, require_shfmt

MODULE_PATH = HOOKS_DIR / "shell-syntax-tree.py"
CONFIG_SH_PATH = HOOKS_DIR / "_config.sh"

# No vendor value applies. The guard only ends a hung run, and sits far above a real run's length.
SUBPROCESS_HANG_GUARD_SECONDS = 60


def load_module():
    """The module, imported by path because its filename is not a valid Python identifier."""
    spec = importlib.util.spec_from_file_location("shell_syntax_tree", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


shell_syntax_tree = load_module()


@functools.cache
def _cached_production_shfmt_argv() -> tuple[str, ...]:
    """Cached for the session because each `production_shfmt_argv()` call sources `_lib.sh` in a fresh bash."""
    return tuple(production_shfmt_argv())


def run_shfmt(command: str | bytes, *, argv: list[str] | None = None, cwd: Path | None = None, env: dict | None = None):
    """Run shfmt, under the gates' own argv unless `argv` is given, with `command` on stdin.

    Skips the test when shfmt is not installed, and fails it under GITHUB_ACTIONS, as `require_shfmt` does.
    """
    require_shfmt()
    stdin_bytes = command if isinstance(command, bytes) else command.encode("utf-8")
    return subprocess.run(
        argv if argv is not None else list(_cached_production_shfmt_argv()),
        input=stdin_bytes,
        capture_output=True,
        cwd=cwd,
        env=env,
        check=False,
        timeout=SUBPROCESS_HANG_GUARD_SECONDS,
    )


def _read_bash_floor() -> tuple[int, int]:
    floor_text = CONFIG_SH_PATH.read_text()
    major = re.search(r"^_BASH_FLOOR_MAJOR=(\d+)$", floor_text, re.MULTILINE)
    minor = re.search(r"^_BASH_FLOOR_MINOR=(\d+)$", floor_text, re.MULTILINE)
    assert major and minor, f"{CONFIG_SH_PATH} does not assign both bash floor constants"
    return int(major.group(1)), int(minor.group(1))


class RealBash(NamedTuple):
    path: str
    version_line: str
    version: tuple[int, int]


@functools.cache
def _bash_on_path() -> RealBash:
    """The bash on PATH by absolute path, with the first line of its `--version` and its major and minor version."""
    bash_path = shutil.which("bash")
    assert bash_path, "no bash on PATH"
    version_output = subprocess.run(
        [bash_path, "--version"], capture_output=True, text=True, check=True, timeout=SUBPROCESS_HANG_GUARD_SECONDS
    )
    version_pair = subprocess.run(
        [bash_path, "-c", 'printf "%s %s" "${BASH_VERSINFO[0]}" "${BASH_VERSINFO[1]}"'],
        capture_output=True,
        text=True,
        check=True,
        timeout=SUBPROCESS_HANG_GUARD_SECONDS,
    ).stdout.split()
    return RealBash(bash_path, version_output.stdout.splitlines()[0], (int(version_pair[0]), int(version_pair[1])))


def real_bash_version_line() -> str:
    """The `bash --version` first line of the bash `run_real_bash` runs, for a failure message."""
    return _bash_on_path().version_line


def run_real_bash(
    script: str, *, env: dict | None = None, isolated: bool = False, check: bool = True
) -> subprocess.CompletedProcess:
    """Run `script` under the bash on PATH. Every real-bash call in the shell-syntax-tree tests goes through here.

    Fails the test, naming the bash, when that bash is below the floor `_config.sh` defines, so a hiding
    old bash shows as a floor failure and not as a comparison diff.
    With `isolated`, the script runs as `env -i PATH=<empty directory> bash --norc --noprofile -c`
    from that directory, so only builtins and functions the script defines can run. `env` must then be None.
    A `check` of False returns a nonzero exit instead of failing the test.
    """
    real_bash = _bash_on_path()
    floor = _read_bash_floor()
    if real_bash.version < floor:
        pytest.fail(
            f"{real_bash.version_line} ({real_bash.path}) is below the bash {floor[0]}.{floor[1]} floor"
            f" that {CONFIG_SH_PATH.name} defines; put a bash at or above it first on PATH"
        )
    bash_argv = [real_bash.path, "--norc", "--noprofile", "-c", script]
    run_kwargs = {"capture_output": True, "check": False, "stdin": subprocess.DEVNULL, "timeout": SUBPROCESS_HANG_GUARD_SECONDS}
    if isolated:
        assert env is None, "an isolated run takes no env"
        with tempfile.TemporaryDirectory() as empty_directory:
            result = subprocess.run(
                ["/usr/bin/env", "-i", f"PATH={empty_directory}", *bash_argv], cwd=empty_directory, **run_kwargs
            )
    else:
        result = subprocess.run(bash_argv, env=env, **run_kwargs)
    if check:
        assert result.returncode == 0, f"{real_bash.version_line} exited {result.returncode}: {result.stderr!r}"
    return result


def run_module(tree_json: bytes, projection: str = "words", *, script_path: Path = MODULE_PATH, env: dict | None = None):
    """Run the module under the interpreter flags `_lib_shell_parse` uses."""
    return subprocess.run(
        [sys.executable, "-I", "-S", str(script_path), projection],
        input=tree_json,
        capture_output=True,
        env=env,
        check=False,
        timeout=SUBPROCESS_HANG_GUARD_SECONDS,
    )


def project_words(command: str | bytes, *, env: dict | None = None) -> subprocess.CompletedProcess:
    """`command` through real shfmt and then the `words` projection. Fails the test when shfmt rejects it."""
    parsed = run_shfmt(command, env=env)
    assert parsed.returncode == 0, f"shfmt exited {parsed.returncode} on {command!r}: {parsed.stderr!r}"
    return run_module(parsed.stdout, env=env)


def simple_commands(command: str) -> list[list[str]]:
    """The words of each simple command in `command`, in the module's order, as bash sees them.

    A blank line ends a command, so an empty word is indistinguishable from the separator and is dropped.
    """
    projected = project_words(command)
    assert projected.returncode == 0, (projected.returncode, projected.stderr)
    commands: list[list[str]] = []
    current: list[str] = []
    for line in projected.stdout.decode("utf-8").split("\n")[:-1]:
        if line:
            current.append(line)
        else:
            commands.append(current)
            current = []
    assert not current, "the projection ended a command without its blank line"
    return commands


# `w` prints its arguments NUL-terminated and then a newline, so bash's output splits into commands at newlines and words at NULs.
# `cat` is stubbed so a `$(cat <<'EOF' ...)` argument runs nothing.
BASH_COMMAND_PRELUDE = "w() { printf '%s\\0' \"$@\"; printf '\\n'; }; cat() { :; }\n"


def module_commands_without(command: str, nested_command_names: frozenset[str]) -> list[list[str]]:
    """The module's commands for `command`, less those in `nested_command_names`: in a substitution or on a pipe's left."""
    return [words for words in simple_commands(command) if not (words and words[0] in nested_command_names)]


def bash_commands(bash_command: str) -> list[list[str]]:
    """The commands real bash prints when it runs `bash_command`, whose command names carry a `w` before them."""
    result = run_real_bash(BASH_COMMAND_PRELUDE + bash_command, isolated=True, check=False)
    return [[word.decode("utf-8") for word in line.split(b"\0")[:-1]] for line in result.stdout.split(b"\n")[:-1]]


def differences_from_real_bash(command: str, bash_command: str, nested_command_names: frozenset[str]) -> list[str]:
    """What differs between the module's words for `command` and what bash prints for `bash_command`.

    A difference is another number of commands, another number of words in a command, or two words that differ.
    A module word holding the placeholder matches any bash word in its place.
    """
    bash_side = bash_commands(bash_command)
    module_side = module_commands_without(command, nested_command_names)
    if len(module_side) != len(bash_side):
        return [
            f"{len(module_side)} commands from the module and {len(bash_side)} from bash:"
            f" module {module_side!r}, bash {bash_side!r}"
        ]
    differences = []
    for index, (module_words, bash_words) in enumerate(zip(module_side, bash_side, strict=True)):
        if len(module_words) != len(bash_words):
            differences.append(
                f"command {index} has {len(module_words)} words from the module and {len(bash_words)} from bash:"
                f" {module_words!r} against {bash_words!r}"
            )
            continue
        differences.extend(
            f"command {index}: module word {module_word!r} against bash word {bash_word!r}"
            for module_word, bash_word in zip(module_words, bash_words, strict=True)
            if module_word != bash_word and shell_syntax_tree.EXPANSION_PLACEHOLDER not in module_word
        )
    return differences


MEMBER = "member"
AGREEMENT = "agreement"
HIDDEN = "hidden"
SHOWN = "shown"
RENAMED_FLAG = "renamed-flag"
AGREES = "agrees-with-bash"

MEMBER_OUTCOMES = frozenset({HIDDEN, SHOWN, RENAMED_FLAG})

FLAG_AND_PATH = "git commit -F /dirty.md"
FLAG_AND_PATH_CALL = f"w {FLAG_AND_PATH}"
_AGREEMENT_SEEN_ON = "agrees on bash 5.3.20, differs on bash 3.2.57"
_FLUSH_COMMENT_SEEN_ON = "bash 5.3.20 and 3.2.57"
_FLUSH_AGREEMENT_SEEN_ON = "agrees on bash 5.3.20"
FLUSH_COMMENT_HEAD_WORDS = ("git", "commit", "-m")


class CutResidualFixture(NamedTuple):
    """One input of the cut residual: a member whose tree shows a command other than the one bash runs, or an agreement case.

    A member's `outcome` is one of three:
    - HIDDEN: `-F` and `/dirty.md` are absent from the words.
    - SHOWN: both are present in one command.
    - RENAMED_FLAG: `-$F` and `/dirty.md` are in one command, and `-F` is absent.

    An agreement case holds the same text for bash in `bash_command`
    and the names of the module's commands nested in a substitution in `nested_command_names`.
    `seen_on` names the bash builds a member's hidden or shown line was run on.
    `visible_head_words` are words of a HIDDEN member's visible part, which one command must still hold.
    `unflushed_twin` is a member's text without the hiding `#`, which projects `-F` and `/dirty.md` in one command.
    """

    id: str
    kind: str
    command: str
    outcome: str
    seen_on: str
    bash_command: str | None = None
    nested_command_names: frozenset[str] = frozenset()
    visible_head_words: tuple[str, ...] = ()
    unflushed_twin: str | None = None


# Closing a member flips its case in every suite that reads this list.
# An agreement case is no member: it is the floor-build check, which a bash that hides its flag-and-path call fails.
CUT_RESIDUAL_FIXTURES = [
    CutResidualFixture(
        "delimiter-mismatch-delimiter-quoted-in-a-non-last-part", MEMBER,
        f'cat <<E"O"F\n$({FLAG_AND_PATH})\nEOF\n', SHOWN, "bash 5.3.20 and 3.2.57",
    ),
    CutResidualFixture(
        "delimiter-mismatch-double-quoted-delimiter-holding-a-backslash", MEMBER,
        f'cat <<"E\\$F"\nbody\nE$F\n{FLAG_AND_PATH}\nE\\$F\n', HIDDEN, "bash 5.3.20 and 3.2.57",
    ),
    # shfmt keeps the escape text of a `$'...'` or `$"..."` delimiter where bash decodes it, so the terminators differ.
    CutResidualFixture(
        "delimiter-mismatch-ansi-c-delimiter-decoding-to-the-terminator", MEMBER,
        f"cat <<$'E\\x4fF'\nEOF\n{FLAG_AND_PATH}\nE\\x4fF\n", HIDDEN, "bash 5.3.20 and 3.2.57",
        visible_head_words=("cat",),
    ),
    CutResidualFixture(
        "delimiter-mismatch-locale-delimiter-holding-a-backslash", MEMBER,
        f'cat <<$"E\\$F"\nbody\nE$F\n{FLAG_AND_PATH}\nE\\$F\n', HIDDEN, "bash 5.3.20 and 3.2.57",
        visible_head_words=("cat",),
    ),
    CutResidualFixture(
        "heredoc-in-backtick-substitution-closing-on-the-opener-line", MEMBER,
        f"x=`: <<EOF`\n{FLAG_AND_PATH}\nEOF\n", HIDDEN, "bash 5.3.20 and 3.2.57",
    ),
    CutResidualFixture(
        "heredoc-in-backtick-substitution-quoted-delimiter-that-is-a-command-line", MEMBER,
        f"x=`: <<'{FLAG_AND_PATH}'`\n{FLAG_AND_PATH}\n", HIDDEN, "bash 5.3.20 and 3.2.57",
    ),
    CutResidualFixture(
        "heredoc-in-backtick-substitution-body-holding-a-bare-backtick", MEMBER,
        f"x=`cat <<'EOF'\n`\n{FLAG_AND_PATH}\nEOF\n`\n", HIDDEN, "bash 5.3.20 and 3.2.57",
    ),
    CutResidualFixture(
        "extglob-pattern-holding-a-brace-substitution", MEMBER,
        f"shopt -s extglob\necho @(${{ {FLAG_AND_PATH}; }}|b)\n", HIDDEN, "bash 5.3.20, the only build with the form",
    ),
    CutResidualFixture(
        "stdin-fed-to-an-interpreter-heredoc-to-a-shell", MEMBER,
        f"bash <<'EOF'\n{FLAG_AND_PATH}\nEOF\n", HIDDEN, "bash 5.3.20 and 3.2.57",
    ),
    CutResidualFixture(
        "stdin-fed-to-an-interpreter-hand-off-across-statements", MEMBER,
        f"exec 3<<'EOF'\n{FLAG_AND_PATH}\nEOF\nbash <&3\n", HIDDEN, "bash 5.3.20 and 3.2.57",
    ),
    CutResidualFixture(
        "stdin-fed-to-an-interpreter-that-is-not-a-shell", MEMBER,
        f"make -f - <<'EOF'\nall:\n\t{FLAG_AND_PATH}\nEOF\n", HIDDEN, "bash 5.3.20 and 3.2.57",
    ),
    CutResidualFixture(
        "backslash-newline-continuation-splitting-a-heredoc-terminator", MEMBER,
        f"cat <<EOF\nbody\nE\\\nOF\n{FLAG_AND_PATH}\nEOF\n", HIDDEN, "bash 5.3.20 and 3.2.57",
    ),
    CutResidualFixture(
        "backslash-newline-heredoc-body-whose-first-line-is-a-lone-backslash", MEMBER,
        f"cat <<EOF\n\\\nEOF\n{FLAG_AND_PATH}\nEOF\n", HIDDEN, "bash 5.3.20 and 3.2.57",
    ),
    CutResidualFixture(
        "backslash-newline-comment-ending-in-a-backslash-on-a-heredoc-opener-line", MEMBER,
        f"cat <<'EOF' # c \\\nX\nEOF\n{FLAG_AND_PATH}\nEOFX\n", HIDDEN, "bash 5.3.20 and 3.2.57",
    ),
    CutResidualFixture(
        "backslash-newline-quoted-heredoc-in-backticks-with-a-split-terminator", MEMBER,
        f"x=`cat <<'EOF'\nbody\nE\\\nOF\n{FLAG_AND_PATH}\nEOF\n`\n", HIDDEN, "bash 5.3.20 and 3.2.57",
    ),
    CutResidualFixture(
        "backslash-newline-single-quoted-words-split-inside-backticks", MEMBER,
        "x=`git commit '-\\\nF' '/dirty\\\n.md'`\n", HIDDEN, "bash 5.3.20 and 3.2.57",
    ),
    CutResidualFixture(
        "backslash-newline-between-dollar-and-open-parenthesis", MEMBER,
        f'echo "$\\\n({FLAG_AND_PATH})"\n', HIDDEN, "bash 5.3.20 and 3.2.57",
    ),
    CutResidualFixture(
        "backslash-newline-before-a-single-quoted-part-of-a-flag", MEMBER,
        "git commit -$\\\n'F' /dirty.md\n", RENAMED_FLAG, "bash 5.3.20 and 3.2.57",
    ),
    CutResidualFixture(
        "backslash-newline-before-a-double-quoted-part-of-a-flag", MEMBER,
        'git commit -$\\\n"F" /dirty.md\n', RENAMED_FLAG, "bash 5.3.20 and 3.2.57",
    ),
    CutResidualFixture(
        "backslash-newline-trailing-comment-ending-in-a-backslash", MEMBER,
        f"cd /x # c \\\n{FLAG_AND_PATH}\n", SHOWN, "bash 5.3.20 and 3.2.57",
        visible_head_words=("cd",),
    ),
    # A `#` flush against the end of a quote or expansion is a comment to shfmt and part of the word to bash,
    # so shfmt drops the rest of the line. The container's closer sits on a later line.
    CutResidualFixture(
        "flush-comment-in-a-subshell", MEMBER,
        '( git commit -m "x"# -F /dirty.md\n)\n', HIDDEN, _FLUSH_COMMENT_SEEN_ON,
        visible_head_words=FLUSH_COMMENT_HEAD_WORDS,
    ),
    CutResidualFixture(
        "flush-comment-in-a-quoted-command-substitution", MEMBER,
        'echo "$( git commit -m "x"# -F /dirty.md\n)"\n', HIDDEN, _FLUSH_COMMENT_SEEN_ON,
        visible_head_words=FLUSH_COMMENT_HEAD_WORDS,
    ),
    CutResidualFixture(
        "flush-comment-in-a-process-substitution", MEMBER,
        'cat <( git commit -m "x"# -F /dirty.md\n)\n', HIDDEN, _FLUSH_COMMENT_SEEN_ON,
        visible_head_words=FLUSH_COMMENT_HEAD_WORDS,
    ),
    CutResidualFixture(
        "flush-comment-in-backticks", MEMBER,
        'echo `git commit -m "x"# -F /dirty.md\n`\n', HIDDEN, _FLUSH_COMMENT_SEEN_ON,
        visible_head_words=FLUSH_COMMENT_HEAD_WORDS,
    ),
    CutResidualFixture(
        "flush-comment-in-a-case-arm", MEMBER,
        'case x in x) git commit -m "x"# -F /dirty.md\n;; esac\n', HIDDEN, _FLUSH_COMMENT_SEEN_ON,
        visible_head_words=FLUSH_COMMENT_HEAD_WORDS,
    ),
    CutResidualFixture(
        "flush-comment-after-an-expansion-in-a-subshell", MEMBER,
        "( git commit -m $x# -F /dirty.md\n)\n", HIDDEN, _FLUSH_COMMENT_SEEN_ON,
        visible_head_words=FLUSH_COMMENT_HEAD_WORDS,
    ),
    CutResidualFixture(
        "flush-comment-in-an-array-literal", MEMBER,
        f'x=( "a"# $({FLAG_AND_PATH})\n)\n', HIDDEN, _FLUSH_COMMENT_SEEN_ON,
        unflushed_twin=f'x=( "a" $({FLAG_AND_PATH})\n)\n',
    ),
    CutResidualFixture(
        "flush-comment-in-a-declared-array-literal", MEMBER,
        f'declare -a x=( "a"# $({FLAG_AND_PATH})\n)\n', HIDDEN, _FLUSH_COMMENT_SEEN_ON,
        unflushed_twin=f'declare -a x=( "a" $({FLAG_AND_PATH})\n)\n',
    ),
    # A `#` right after an array literal's closing `)` hides the rest of the line at top level too.
    CutResidualFixture(
        "flush-comment-after-array-literal-closer", MEMBER,
        f"x=(a)# ; {FLAG_AND_PATH}\n", HIDDEN, "bash 5.3.20",
        unflushed_twin=f"x=(a) ; {FLAG_AND_PATH}\n",
    ),
    # A `#` right after an extglob pattern's closing `)` hides the rest of the line in the same containers.
    # The extglob option is set on its own first line, since bash cannot parse the pattern in the same compound command.
    CutResidualFixture(
        "flush-comment-after-extglob-closer", MEMBER,
        "shopt -s extglob\n( git commit -m @(a|b)# -F /dirty.md\n)\n", HIDDEN, "bash 5.3.20",
        visible_head_words=FLUSH_COMMENT_HEAD_WORDS,
        unflushed_twin="shopt -s extglob\n( git commit -m @(a|b) -F /dirty.md\n)\n",
    ),
    # The class's boundary for a quote or expansion before the `#`: it agrees with bash at top level and inside `{ }`.
    CutResidualFixture(
        "agreement-flush-comment-at-top-level", AGREEMENT,
        'git commit -m "x"# -F /dirty.md\n', AGREES, _FLUSH_AGREEMENT_SEEN_ON,
        'w git commit -m "x"# -F /dirty.md\n',
    ),
    CutResidualFixture(
        "agreement-flush-comment-in-braces", AGREEMENT,
        '{ git commit -m "x"# -F /dirty.md\n}\n', AGREES, _FLUSH_AGREEMENT_SEEN_ON,
        '{ w git commit -m "x"# -F /dirty.md\n}\n',
    ),
    CutResidualFixture(
        "agreement-flush-comment-after-an-expansion-at-top-level", AGREEMENT,
        "git commit -m $x# -F /dirty.md\n", AGREES, _FLUSH_AGREEMENT_SEEN_ON,
        "w git commit -m $x# -F /dirty.md\n",
    ),
    CutResidualFixture(
        "agreement-command-substitution-closer-in-an-unquoted-assignment", AGREEMENT,
        f"x=$(cat <<'EOF'\n1)\n{FLAG_AND_PATH_CALL}\nEOF\n)\necho done\n", AGREES, _AGREEMENT_SEEN_ON,
        f"x=$(cat <<'EOF'\n1)\n{FLAG_AND_PATH_CALL}\nEOF\n)\nw echo done\n", frozenset({"cat"}),
    ),
    CutResidualFixture(
        "agreement-command-substitution-closer-in-an-export", AGREEMENT,
        f"export x=$(cat <<'EOF'\n1)\n{FLAG_AND_PATH_CALL}\nEOF\n)\necho done\n", AGREES, _AGREEMENT_SEEN_ON,
        f"export x=$(cat <<'EOF'\n1)\n{FLAG_AND_PATH_CALL}\nEOF\n)\nw echo done\n", frozenset({"cat"}),
    ),
    CutResidualFixture(
        "agreement-process-substitution-closer", AGREEMENT,
        f"diff <(cat <<'EOF'\n1)\n{FLAG_AND_PATH_CALL}\nEOF\n) /dev/null\n", AGREES, _AGREEMENT_SEEN_ON,
        f"w diff <(cat <<'EOF'\n1)\n{FLAG_AND_PATH_CALL}\nEOF\n) /dev/null\n", frozenset({"cat"}),
    ),
    CutResidualFixture(
        "agreement-parameter-default-closer", AGREEMENT,
        f"y=${{x:-$(cat <<'EOF'\n}}\n{FLAG_AND_PATH_CALL}\nEOF\n)}}\necho done\n", AGREES, _AGREEMENT_SEEN_ON,
        f"y=${{x:-$(cat <<'EOF'\n}}\n{FLAG_AND_PATH_CALL}\nEOF\n)}}\nw echo done\n", frozenset({"cat"}),
    ),
    CutResidualFixture(
        "agreement-array-subscript-closer", AGREEMENT,
        f"a[$(cat <<'EOF'\n1]\n{FLAG_AND_PATH_CALL}\nEOF\n)]=1\necho done\n", AGREES, _AGREEMENT_SEEN_ON,
        f"a[$(cat <<'EOF'\n1]\n{FLAG_AND_PATH_CALL}\nEOF\n)]=1\nw echo done\n", frozenset({"cat"}),
    ),
    CutResidualFixture(
        "agreement-one-line-opener-closing-the-substitution", AGREEMENT,
        f"x=$(: <<EOF)\n{FLAG_AND_PATH_CALL}\nEOF\necho done\n", AGREES, _AGREEMENT_SEEN_ON,
        f"x=$(: <<EOF)\n{FLAG_AND_PATH_CALL}\nEOF\nw echo done\n", frozenset({":"}),
    ),
]  # fmt: skip

CUT_RESIDUAL_MEMBERS = [fixture for fixture in CUT_RESIDUAL_FIXTURES if fixture.kind == MEMBER]
CUT_RESIDUAL_AGREEMENT_CASES = [fixture for fixture in CUT_RESIDUAL_FIXTURES if fixture.kind == AGREEMENT]


def iter_objects(tree) -> Iterator[dict]:
    """Every JSON object in `tree`, at any depth, whatever struct or field holds it."""
    stack = [tree]
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            yield value
            stack.extend(value.values())
        elif isinstance(value, list):
            stack.extend(value)


class ChildPosition(NamedTuple):
    """One place a command can sit: a template with a `{command}` site, and the node types it exercises as holders."""

    construct: str
    template: str
    holder_types: frozenset


def _row(construct: str, template: str, *holder_types: str) -> ChildPosition:
    return ChildPosition(construct, template, frozenset(holder_types))


# Each row puts a command into one child position of a construct. A row's holder types are the node
# types the command sits under, on the path from the tree's root to it. Later projections reuse the rows with other commands.
CHILD_POSITION_MATRIX = [
    _row("top-level statement", "{command}", "File", "CallExpr"),
    _row("left of &&", "{command} && true", "BinaryCmd"),
    _row("right of &&", "true && {command}", "BinaryCmd"),
    _row("left of ||", "{command} || true", "BinaryCmd"),
    _row("right of ||", "true || {command}", "BinaryCmd"),
    _row("left of a pipe", "{command} | cat", "BinaryCmd"),
    _row("right of a pipe", "cat | {command}", "BinaryCmd"),
    _row("right of |&", "cat |& {command}", "BinaryCmd"),
    _row("after a semicolon", "true; {command}", "File"),
    _row("backgrounded statement", "{command} &", "File"),
    _row("negated statement", "! {command}", "File"),
    _row("subshell", "( {command} )", "Subshell"),
    _row("brace group", "{ {command}; }", "Block"),
    _row("time", "time {command}", "TimeClause"),
    _row("coprocess", "coproc {command}", "CoprocClause"),
    _row("named coprocess", "coproc N { {command}; }", "CoprocClause", "Block"),
    _row("function body", "f() { {command}; }", "FuncDecl", "Block"),
    _row("function body subshell", "f() ( {command} )", "FuncDecl", "Subshell"),
    _row("if condition", "if {command}; then true; fi", "IfClause"),
    _row("if body", "if true; then {command}; fi", "IfClause"),
    _row("elif condition", "if true; then true; elif {command}; then true; fi", "IfClause"),
    _row("else body", "if true; then true; else {command}; fi", "IfClause"),
    _row("while condition", "while {command}; do true; done", "WhileClause"),
    _row("while body", "while true; do {command}; done", "WhileClause"),
    _row("until condition", "until {command}; do true; done", "WhileClause"),
    _row("for body", "for i in 1; do {command}; done", "ForClause"),
    _row("for word list", "for i in $({command}); do true; done", "ForClause", "WordIter", "CmdSubst"),
    _row("select body", "select i in 1; do {command}; done", "ForClause"),
    _row("c-style for condition", "for ((i=0; i<$({command}); i++)); do true; done", "CStyleLoop", "CmdSubst", "BinaryArithm"),
    _row("case subject", "case $({command}) in a) true;; esac", "CaseClause", "CmdSubst"),
    _row("case pattern", "case x in $({command})) true;; esac", "CaseClause", "CmdSubst"),
    _row("case body", "case x in a) {command};; esac", "CaseClause"),
    _row("double-bracket operand", "[[ $({command}) == x ]]", "TestClause", "BinaryTest", "Word", "CmdSubst"),
    _row("double-bracket unary operand", "[[ -n $({command}) ]]", "TestClause", "UnaryTest", "Word", "CmdSubst"),
    _row(
        "double-bracket parenthesized operand", "[[ ( -n $({command}) ) ]]",
        "TestClause", "ParenTest", "UnaryTest", "Word", "CmdSubst",
    ),
    _row("arithmetic command", "(( $({command}) + 1 ))", "ArithmCmd", "BinaryArithm", "Word", "CmdSubst"),
    _row("arithmetic unary operand", "(( -$({command}) ))", "ArithmCmd", "UnaryArithm", "Word", "CmdSubst"),
    _row("arithmetic parenthesized operand", "(( ($({command})) ))", "ArithmCmd", "ParenArithm", "Word", "CmdSubst"),
    _row("let", "let x=$({command})", "LetClause", "Word", "CmdSubst"),
    _row("arithmetic expansion", "echo $(( $({command}) ))", "ArithmExp", "Word", "CmdSubst"),
    _row("bracket arithmetic expansion", "echo $[ $({command}) ]", "ArithmExp", "Word", "CmdSubst"),
    _row("command substitution", "echo $({command})", "CmdSubst"),
    _row("backticks", "echo `{command}`", "CmdSubst"),
    _row("double-quoted substitution", 'echo "$({command})"', "DblQuoted", "CmdSubst"),
    _row("input process substitution", "cat <({command})", "ProcSubst"),
    _row("output process substitution", "tee >({command})", "ProcSubst"),
    _row("assignment value", "x=$({command})", "CallExpr", "CmdSubst"),
    _row("assignment prefix of a command", "X=$({command}) true", "CallExpr", "CmdSubst"),
    _row("array element", "x=($({command}))", "CallExpr", "CmdSubst"),
    _row("indexed array element", "x=([1]=$({command}))", "CallExpr", "CmdSubst"),
    _row("declaration argument", "declare x=$({command})", "DeclClause", "CmdSubst"),
    _row("redirect target", "true > $({command})", "CallExpr", "CmdSubst"),
    _row("unquoted heredoc body substitution", "cat <<EOF\n$({command})\nEOF\n", "CallExpr", "CmdSubst"),
    _row("unquoted heredoc body backticks", "cat <<EOF\n`{command}`\nEOF\n", "CallExpr", "CmdSubst"),
    _row("command argument", "echo $({command})", "CallExpr", "CmdSubst"),
    _row("parameter default", "echo ${x:-$({command})}", "ParamExp", "CmdSubst"),
    _row("parameter replacement", "echo ${x/$({command})/y}", "ParamExp", "CmdSubst"),
    _row("parameter slice offset", "echo ${x:$({command}):1}", "ParamExp", "CmdSubst", "Word"),
    _row("parameter index", "echo ${a[$({command})]}", "ParamExp", "CmdSubst", "Word"),
]  # fmt: skip

COMMAND_HOLDING_TYPES = frozenset().union(*(row.holder_types for row in CHILD_POSITION_MATRIX))
