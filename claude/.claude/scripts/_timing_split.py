"""Plans the pytest passes for a selection: the parallel and serial passes tests.yml runs, or one unsplit pass."""
import fnmatch
import os
import tomllib
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import NamedTuple

from pytest import ExitCode

TIMING_MARKER = "timing"
TIMING_MARK_TEXT = f"mark.{TIMING_MARKER}"

XDIST_WORKER_ENV_VAR = "PYTEST_XDIST_AUTO_NUM_WORKERS"

# pytest's default python_files, which pyproject.toml does not override.
TEST_FILE_PATTERNS = ("test_*.py", "*_test.py")

SATURATES_CPU_MARKER = "saturates_cpu"

PARALLEL_PASS_MARKER_EXPRESSION = f"not {TIMING_MARKER}"
# CI's serial step runs saturates_cpu tests, and a local serial pass leaves them out because each starts one busy
# process per core.
SERIAL_PASS_MARKER_EXPRESSION = f"{TIMING_MARKER} and not {SATURATES_CPU_MARKER}"

PARALLEL_PASS = "parallel"
SERIAL_PASS = "serial"
UNSPLIT_PASS = "unsplit"

UNSPLIT_REASON_ARGUMENT_FILE = "a caller argument starts with @"
UNSPLIT_REASON_BARE_DOUBLE_DASH = "a caller argument is --"
UNSPLIT_REASON_CALLER_NO_WORKERS = "the caller's -n is 0 or less"
UNSPLIT_REASON_ENVIRONMENT_NO_WORKERS = f"{XDIST_WORKER_ENV_VAR} is 0 or less"
UNSPLIT_REASON_NO_MARKED_FILES = f"no selected file contains {TIMING_MARK_TEXT}"

_MARKER_FLAG = "-m"
_KEYWORD_FLAG = "-k"
_WORKERS_SHORT_FLAG = "-n"
_WORKERS_LONG_FLAG = "--numprocesses"
_SERIAL_WORKERS_OPTION = "-n0"
_IGNORE_OPTION_PREFIX = "--ignore="
_DOUBLE_DASH = "--"

_AUTO_WORKER_COUNTS = ("auto", "logical")
_NODE_ID_SEPARATOR = "::"


class TimingMarkScan(NamedTuple):
    marked_files: tuple[str, ...]
    unmarked_test_files: tuple[str, ...]


class PytestPass(NamedTuple):
    name: str
    added_options: tuple[str, ...]
    ignored_paths: tuple[str, ...]
    pytest_args: list[str]


class PassPlan(NamedTuple):
    passes: tuple[PytestPass, ...]
    unsplit_reason: str | None


class _OptionOccurrence(NamedTuple):
    start: int
    end: int
    value: str


def _match_option(args: Sequence[str], index: int, flag: str) -> _OptionOccurrence | None:
    token = args[index]
    if token == flag:
        has_value = index + 1 < len(args) and not args[index + 1].startswith("-")
        return _OptionOccurrence(index, index + 2, args[index + 1]) if has_value else None
    if token.startswith(f"{flag}="):
        return _OptionOccurrence(index, index + 1, token[len(flag) + 1:])
    if not flag.startswith(_DOUBLE_DASH) and token.startswith(flag):
        return _OptionOccurrence(index, index + 1, token[len(flag):])
    return None


def _find_option_occurrences(args: Sequence[str], flags: Iterable[str]) -> list[_OptionOccurrence]:
    """Finds every occurrence of a value-taking option, in token order, with its token span and value.

    The arguments must hold no bare `--`: plan_passes collapses such a run before any caller of this reads them.
    A bare flag takes the next token only when it exists and does not start with `-`; otherwise the flag is not
    an occurrence, and pytest reports its own usage error.
    """
    flags = tuple(flags)
    occurrences: list[_OptionOccurrence] = []
    index = 0
    while index < len(args):
        matches = (_match_option(args, index, flag) for flag in flags)
        occurrence = next((match for match in matches if match is not None), None)
        if occurrence is None:
            index += 1
        else:
            occurrences.append(occurrence)
            index = occurrence.end
    return occurrences


def split_caller_marker_expression(caller_args: list[str]) -> tuple[str, list[str]]:
    """Removes every recognized `-m` from the caller's arguments and returns the last one's expression, since
    pytest's `-m` is last-wins. An unrecognized form stays, and each pass's own `-m` overrides it.
    """
    occurrences = _find_option_occurrences(caller_args, (_MARKER_FLAG,))
    removed_indexes = {index for occurrence in occurrences for index in range(occurrence.start, occurrence.end)}
    remaining_args = [arg for index, arg in enumerate(caller_args) if index not in removed_indexes]
    expression = occurrences[-1].value if occurrences else ""
    return expression, remaining_args


def no_workers_reason(caller_args: list[str], *, auto_num_workers: str | None) -> str | None:
    """Returns the reason the run would start no xdist workers, or None.

    The last `-n` decides, read the way xdist reads it. auto_num_workers decides only when that `-n` is absent,
    `auto` or `logical`.
    """
    occurrences = _find_option_occurrences(caller_args, (_WORKERS_SHORT_FLAG, _WORKERS_LONG_FLAG))
    if occurrences and occurrences[-1].value not in _AUTO_WORKER_COUNTS:
        try:
            caller_worker_count = int(occurrences[-1].value)
        except ValueError:
            return None
        return UNSPLIT_REASON_CALLER_NO_WORKERS if caller_worker_count <= 0 else None
    try:
        environment_worker_count = int(auto_num_workers) if auto_num_workers is not None else None
    except ValueError:
        return None
    if environment_worker_count is not None and environment_worker_count <= 0:
        return UNSPLIT_REASON_ENVIRONMENT_NO_WORKERS
    return None


def _caller_paths(caller_args: Sequence[str], repo_root: Path) -> list[str]:
    """Normalized paths of the caller arguments that name an existing path under repo_root."""
    value_flags = (_KEYWORD_FLAG, _MARKER_FLAG, _WORKERS_SHORT_FLAG, _WORKERS_LONG_FLAG)
    option_value_indexes = {
        index
        for occurrence in _find_option_occurrences(caller_args, value_flags)
        for index in range(occurrence.start, occurrence.end)
    }
    root = os.path.normpath(repo_root)
    paths = []
    for index, arg in enumerate(caller_args):
        path_part = arg.split(_NODE_ID_SEPARATOR, 1)[0]
        if index in option_value_indexes or arg.startswith("-") or not path_part:
            continue
        candidate = os.path.normpath(os.path.join(repo_root, path_part))
        if Path(candidate).is_relative_to(root) and os.path.exists(candidate):
            paths.append(candidate)
    return paths


def _read_norecursedirs(repo_root: Path) -> tuple[str, ...]:
    """The pyproject.toml norecursedirs patterns, or () when the file or the key is missing or malformed."""
    try:
        with (repo_root / "pyproject.toml").open("rb") as handle:
            config = tomllib.load(handle)
    except (OSError, ValueError):
        return ()
    patterns = config
    for key in ("tool", "pytest", "ini_options", "norecursedirs"):
        if not isinstance(patterns, dict) or key not in patterns:
            return ()
        patterns = patterns[key]
    if not isinstance(patterns, list) or not all(isinstance(pattern, str) for pattern in patterns):
        return ()
    return tuple(patterns)


def _matches_norecursedirs(directory: str, patterns: Iterable[str]) -> bool:
    # Mirrors pytest's fnmatch_ex: a pattern without "/" matches the directory name, and one with "/" matches the
    # absolute path with "*/" prefixed.
    absolute = os.path.abspath(directory)
    for pattern in patterns:
        if "/" not in pattern:
            if fnmatch.fnmatch(os.path.basename(absolute), pattern):
                return True
        else:
            anchored = pattern if pattern.startswith("/") else f"*/{pattern}"
            if fnmatch.fnmatch(absolute, anchored):
                return True
    return False


def _holds_timing_mark(path: str) -> bool:
    try:
        return TIMING_MARK_TEXT.encode() in Path(path).read_bytes()
    except OSError:
        return True


def scan_timing_marks(
    target_paths: Iterable[str], caller_args: Sequence[str], *, repo_root: Path,
) -> TimingMarkScan:
    """Reports which files under the selection hold the timing mark text and which test files do not.

    An unreadable file counts as marked. Only a file found by walking a directory can be an unmarked test file,
    because pytest collects a file named directly whatever its name.
    """
    prune_patterns = _read_norecursedirs(repo_root)
    marked: set[str] = set()
    unmarked: set[str] = set()

    def repo_relative(path: str) -> str:
        return Path(os.path.relpath(path, repo_root)).as_posix()

    for scanned_path in [*target_paths, *_caller_paths(caller_args, repo_root)]:
        absolute = os.path.join(repo_root, scanned_path)
        if os.path.isfile(absolute):
            if _holds_timing_mark(absolute):
                marked.add(repo_relative(absolute))
        elif os.path.isdir(absolute):
            for directory, subdirectories, filenames in os.walk(absolute):
                subdirectories[:] = [
                    name for name in subdirectories
                    if not _matches_norecursedirs(os.path.join(directory, name), prune_patterns)
                ]
                for filename in filenames:
                    if not any(fnmatch.fnmatch(filename, pattern) for pattern in TEST_FILE_PATTERNS):
                        continue
                    file_path = os.path.join(directory, filename)
                    (marked if _holds_timing_mark(file_path) else unmarked).add(repo_relative(file_path))
    return TimingMarkScan(tuple(sorted(marked)), tuple(sorted(unmarked)))


def _combine_marker_expression(caller_expression: str, pass_expression: str) -> str:
    return f"({caller_expression}) and {pass_expression}" if caller_expression else pass_expression


def _unsplit_plan(caller_args: list[str], reason: str) -> PassPlan:
    return PassPlan((PytestPass(UNSPLIT_PASS, (), (), list(caller_args)),), reason)


def _unsplit_reason_from_arguments(caller_args: list[str], *, auto_num_workers: str | None) -> str | None:
    if any(arg.startswith("@") for arg in caller_args):
        return UNSPLIT_REASON_ARGUMENT_FILE
    # pytest reads every token after a `--` as a path, so a split pass's appended options would become missing paths.
    if _DOUBLE_DASH in caller_args:
        return UNSPLIT_REASON_BARE_DOUBLE_DASH
    return no_workers_reason(caller_args, auto_num_workers=auto_num_workers)


def plan_passes(
    caller_args: list[str],
    *,
    auto_num_workers: str | None,
    scan_selection: Callable[[], TimingMarkScan],
) -> PassPlan:
    """Plans the parallel and serial passes, or one unsplit pass with the caller's arguments verbatim.

    scan_selection runs only after the argument-only checks decline, so a run those checks collapse reads no file.
    """
    argument_reason = _unsplit_reason_from_arguments(caller_args, auto_num_workers=auto_num_workers)
    if argument_reason is not None:
        return _unsplit_plan(caller_args, argument_reason)
    scan = scan_selection()
    if not scan.marked_files:
        return _unsplit_plan(caller_args, UNSPLIT_REASON_NO_MARKED_FILES)

    caller_expression, remaining_args = split_caller_marker_expression(caller_args)
    parallel_options = (
        _MARKER_FLAG, _combine_marker_expression(caller_expression, PARALLEL_PASS_MARKER_EXPRESSION),
    )
    serial_options = (
        _MARKER_FLAG,
        _combine_marker_expression(caller_expression, SERIAL_PASS_MARKER_EXPRESSION),
        _SERIAL_WORKERS_OPTION,
    )
    ignored_paths = scan.unmarked_test_files
    ignore_options = [f"{_IGNORE_OPTION_PREFIX}{path}" for path in ignored_paths]
    return PassPlan(
        (
            PytestPass(PARALLEL_PASS, parallel_options, (), [*remaining_args, *parallel_options]),
            PytestPass(
                SERIAL_PASS, serial_options, ignored_paths, [*remaining_args, *serial_options, *ignore_options],
            ),
        ),
        None,
    )


def skips_serial_pass(parallel_exit_code: int) -> bool:
    """Exit 3, exit 4 and a death by signal are a pytest error or a kill, not a test result, so a second pass would
    only repeat it."""
    return parallel_exit_code < 0 or parallel_exit_code in (ExitCode.INTERNAL_ERROR, ExitCode.USAGE_ERROR)


def merge_pass_exit_codes(exit_codes: Sequence[int]) -> int:
    """A pass that collected no tests defers to the other, and otherwise the first failing pass's code wins."""
    if not exit_codes:
        raise ValueError("every plan runs at least one pass")
    collected_codes = [code for code in exit_codes if code != ExitCode.NO_TESTS_COLLECTED]
    if not collected_codes:
        return int(ExitCode.NO_TESTS_COLLECTED)
    for code in collected_codes:
        if code != ExitCode.OK:
            return int(code)
    return int(ExitCode.OK)
