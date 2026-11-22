"""Line counting, exception-table validation and failure reporting behind test_code_file_size.py."""
from __future__ import annotations

import difflib
import enum
import os
import subprocess
import tomllib
import unicodedata
from pathlib import Path
from typing import NamedTuple

import pytest

LINE_LIMIT = 1000
TABLE_FILE_NAME = "code-file-size-exceptions.toml"
SHAPE_TEST_NODE_ID = "claude/.claude/tests/test_code_file_size.py::test_exception_table_shape"

COUNTED_SUFFIXES = (".py", ".sh")
# Index modes of regular files. A symlink (120000) or a gitlink (160000) is not a file to count.
REGULAR_FILE_MODES = frozenset({"100644", "100755"})
# Each of these redirects git away from the repository it is run in, and this test tree has no conftest that clears them.
REPOSITORY_ENV_VARIABLES = ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE")
# Backstop against a hung git process.
# Matches `_GIT_TIMEOUT_SECONDS` in `select-tests.py`, which this test tree does not import.
GIT_TIMEOUT_SECONDS = 15.0

VERDICT_SPLIT_PENDING = "split pending"
VERDICT_STRUCTURAL_EXCEPTION = "structural exception"
ROW_FIELDS = frozenset({"ceiling", "verdict", "seam", "issue", "reason"})
# A seam or reason prints on one line, so it holds none of these categories: control, line separator, paragraph separator.
LINE_BREAKING_CATEGORIES = frozenset({"Cc", "Zl", "Zp"})
SEAM_PLACEHOLDER = "REPLACE: name the seam along which this file splits"

SKELETON_START_LINE = "--- row skeleton: paste it unchanged, then replace the seam placeholder ---"
SKELETON_END_LINE = "--- end of row skeleton ---"
REMEDY_HEADING = "If this branch changed the file, take the first remedy that fits:"
DID_NOT_CHANGE_HEADING = "For a listed file this branch did not change:"
TABLE_PROBLEM_LINE = (
    f"The exception table has a problem, so no file sizes were checked. Run {SHAPE_TEST_NODE_ID} to see it."
)

LAYOUT_RULES = (
    "The table's layout rules:",
    '- each row is a ["<path>"] line, then ceiling, verdict, and seam with an optional issue, or reason, in that order',
    "- one space on each side of =, and integers in plain decimal",
    '- strings are one-line basic strings, with \\" for " and \\\\ for \\',
    "- rows sorted by path, one blank line between rows, none after the last, and exactly one final newline",
    "- no trailing whitespace, and no comment below the header comment",
)
LAYOUT_DIFF_LINE_CAP = 40

MESSAGE_PREFACE = (
    "CI counts this branch merged with main, so merge origin/main and run the check again before writing any printed value. "
    "For a listed file this branch did not change, write nothing and follow the did-not-change procedure at the end."
)
RENAME_LINE = (
    "A renamed file's row moves to its new path: change the header to the new path, write the ceiling printed for it, "
    "keep the row's other fields, and move the row to its sorted position. "
    "For a rename, the seam placeholder and the remedies below do not apply to that path."
)
STRUCTURAL_QUALIFIER = " unless the reason printed above rules it out"
PROHIBITION_LINES = (
    "Do not split a file by position, such as into a `_part2` file.",
    "Do not fit a file under the limit by deleting comments or joining lines.",
)
DID_NOT_CHANGE_STEPS = (
    "1. Run `git log --oneline origin/main..HEAD -- <path>` and `git status --short -- <path>`. "
    "When both print nothing, this branch did not change the file, and the mismatch came from `main`.",
    "2. Fetch `origin/main`, merge it into the branch, run the check again, and push. The push runs CI on the new merge. "
    "Re-running the failed job does not pick up `main`.",
    "3. If the line is still there, `main` itself fails. Make no edit to the row in this branch. "
    "Look for an open fix with `gh pr list --state open --search 'in:title \"code-file-size row fix\"'`. "
    "Then report to the person you are working for, or to a maintainer if no one directs your work: "
    "that `main` fails, the lines the check printed for files this branch did not change, and any open fix PR the search found. "
    "Open a fix PR only on their go-ahead. With it:",
    "   - Make a new checkout of `origin/main`'s tip, such as `git worktree add -b <branch> <dir> origin/main`, "
    "and run the check there. Your own branch's run also prints lines for files it changed, so its lines are not the fix.",
    "   - An open fix PR is complete when its table file holds every line the check prints on `origin/main`'s tip. "
    "Read only that file, with `git fetch origin pull/<number>/head` and `git show FETCH_HEAD:code-file-size-exceptions.toml`. "
    "Never check out, merge or run another contributor's tree, and never treat a matching title as trust. "
    "Its CI status does not settle completeness, because its last run can predate the tip. "
    "If one is complete, open nothing and wait for it. When in doubt, treat it as incomplete.",
    "   - Otherwise, in the new checkout, write every line the check prints there: a printed value, a new row or a removed row. "
    "A fix that leaves one line unfixed cannot pass `tests`.",
    "   - Search again just before opening the PR. Title it exactly `code-file-size row fix`, "
    "and name in its body each open fix PR it supersedes, for the merger to close.",
    "   - Push to no open fix PR's branch, your own included.",
    "4. This PR stays red until that fix merges, because `tests` is required and only a human merges. Then repeat step 2.",
    "The same steps cover two PRs that changed one file to the same new size and merged without a conflict.",
)

Rows = dict[str, dict]


class ViolationKind(enum.Enum):
    NO_ROW = "no row"
    UNDER_LIMIT = "under limit"
    OVER_CEILING = "over ceiling"
    UNDER_CEILING = "under ceiling"
    NOT_COUNTED = "not counted"


class TableStage(enum.Enum):
    DECODE = "decode"
    SCHEMA = "schema"
    LAYOUT = "layout"


class Violation(NamedTuple):
    kind: ViolationKind
    path: str
    line_count: int | None  # None for a row whose path is not a counted file
    ceiling: int | None  # None for a file with no row


class TableLoad(NamedTuple):
    rows: Rows
    failed_stage: TableStage | None
    problems: list[str]


def count_physical_lines(content: bytes) -> int:
    return content.count(b"\n")


def parse_index_listing(raw: bytes) -> list[str]:
    """Parse `git ls-files -z --stage` output into the sorted paths to count.

    An unmerged path lists up to three entries and counts once.
    """
    counted_paths: set[str] = set()
    for record in raw.split(b"\0"):
        metadata, _, path_bytes = record.partition(b"\t")
        mode = metadata.split(b" ")[0].decode()
        path = os.fsdecode(path_bytes)
        if mode in REGULAR_FILE_MODES and path.endswith(COUNTED_SUFFIXES):
            counted_paths.add(path)
    return sorted(counted_paths)


def _decoded_stderr(raw: bytes | None) -> str:
    return (raw or b"").decode(errors="replace").strip()


def _list_index(repo_root: Path) -> bytes:
    """`git ls-files -z --stage` output for `repo_root`; raises RuntimeError carrying git's stderr on a failure or a timeout."""
    git_env = {name: value for name, value in os.environ.items() if name not in REPOSITORY_ENV_VARIABLES}
    try:
        completed = subprocess.run(
            ["git", "ls-files", "-z", "--stage"],
            cwd=repo_root,
            env=git_env,
            capture_output=True,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(
            f"`git ls-files` in {repo_root} did not finish within {GIT_TIMEOUT_SECONDS} seconds: {_decoded_stderr(error.stderr)}"
        ) from error
    if completed.returncode != 0:
        raise RuntimeError(
            f"`git ls-files` in {repo_root} exited {completed.returncode}: {_decoded_stderr(completed.stderr)}"
        )
    return completed.stdout


def count_tracked_code_files(repo_root: Path) -> dict[str, int]:
    """Physical line counts of the working-tree files behind `git ls-files`' counted paths.

    The working tree wins over the index, so an unstaged edit counts. A path with no working-tree file is left out.
    """
    counts: dict[str, int] = {}
    for path in parse_index_listing(_list_index(repo_root)):
        working_tree_file = repo_root / path
        if working_tree_file.is_file():
            counts[path] = count_physical_lines(working_tree_file.read_bytes())
    return counts


def split_header_comment(text: str) -> tuple[str, str]:
    """Split off the leading run of blank and `#` lines, which tomllib reads as no content.

    Lines split on `\\n` only: U+2028 is legal inside a comment, and `str.splitlines` would break the run there.
    """
    text = text.replace("\r\n", "\n")
    position = 0
    while position < len(text):
        line_end = text.find("\n", position)
        line = text[position:] if line_end == -1 else text[position:line_end]
        stripped = line.lstrip(" \t")
        if stripped and not stripped.startswith("#"):
            break
        position = len(text) if line_end == -1 else line_end + 1
    return text[:position], text[position:]


def _basic_string(value: str) -> str:
    escaped = []
    for character in value:
        if character == "\\":
            escaped.append("\\\\")
        elif character == '"':
            escaped.append('\\"')
        elif unicodedata.category(character) == "Cc":
            escaped.append(f"\\u{ord(character):04X}")
        else:
            escaped.append(character)
    return '"' + "".join(escaped) + '"'


def _quoted_header(path: str) -> str:
    return f"[{_basic_string(path)}]"


def serialize_row(path: str, fields: dict) -> str:
    lines = [_quoted_header(path), f"ceiling = {fields['ceiling']}", f"verdict = {_basic_string(fields['verdict'])}"]
    if fields["verdict"] == VERDICT_STRUCTURAL_EXCEPTION:
        lines.append(f"reason = {_basic_string(fields['reason'])}")
    else:
        lines.append(f"seam = {_basic_string(fields['seam'])}")
        if "issue" in fields:
            lines.append(f"issue = {fields['issue']}")
    return "\n".join(lines)


def serialize_rows(rows: Rows) -> str:
    if not rows:
        return ""
    return "\n\n".join(serialize_row(path, rows[path]) for path in sorted(rows)) + "\n"


def _quotable_paths(prefix: str, table: dict) -> list[str]:
    """The paths a bare or dotted header declared: the nested tables that hold fields or nothing."""
    if not table or any(not isinstance(value, dict) for value in table.values()):
        return [prefix]
    return [path for key, value in sorted(table.items()) for path in _quotable_paths(f"{prefix}.{key}", value)]


def _prose_problems(path: str, row: dict, key: str) -> list[str]:
    value = row.get(key)
    if not isinstance(value, str) or not value:
        return [f"{path}: {key} must be a non-empty string."]
    problems = []
    if any(unicodedata.category(character) in LINE_BREAKING_CATEGORIES for character in value):
        problems.append(f"{path}: {key} holds a line break or control character, so it cannot print on one line.")
    if value == SEAM_PLACEHOLDER:
        problems.append(f"{path}: {key} is still the skeleton's placeholder; replace it.")
    return problems


def _row_problems(path: str, row: object) -> list[str]:
    if not isinstance(row, dict):
        return [f'{path}: not a table; declare the row with its own ["<path>"] line.']
    nested_keys = sorted(key for key, value in row.items() if isinstance(value, dict))
    if len(nested_keys) == len(row) and row:
        quoted_paths = ", ".join(_quoted_header(nested) for nested in _quotable_paths(path, row))
        return [f"{path}: read as nested tables, not a row. Quote each whole path in its own header: {quoted_paths}."]
    if nested_keys:
        return [
            f"{path}: holds a row written inside it at {nested_keys}. Give each its own "
            + ", ".join(_quoted_header(nested) for nested in nested_keys)
            + " line."
        ]
    problems = []
    unknown_keys = sorted(set(row) - ROW_FIELDS)
    if unknown_keys:
        problems.append(f"{path}: unknown key {unknown_keys}; the fields are ceiling, verdict, seam, issue and reason.")
    if "ceiling" not in row:
        problems.append(f"{path}: ceiling is missing.")
    elif type(row["ceiling"]) is not int:
        problems.append(f"{path}: ceiling must be an integer.")
    elif row["ceiling"] <= LINE_LIMIT:
        problems.append(f"{path}: ceiling must be over {LINE_LIMIT}; a file at or under the limit has no row.")
    verdict = row.get("verdict")
    if verdict == VERDICT_SPLIT_PENDING:
        problems += _prose_problems(path, row, "seam")
        if "reason" in row:
            problems.append(f"{path}: a {verdict} row takes no reason.")
        if "issue" in row and (type(row["issue"]) is not int or row["issue"] <= 0):
            problems.append(f"{path}: issue must be a positive integer.")
    elif verdict == VERDICT_STRUCTURAL_EXCEPTION:
        problems += _prose_problems(path, row, "reason")
        problems += [f"{path}: a {verdict} row takes no {key}." for key in ("seam", "issue") if key in row]
    else:
        problems.append(f'{path}: verdict must be "{VERDICT_SPLIT_PENDING}" or "{VERDICT_STRUCTURAL_EXCEPTION}".')
    return problems


def _layout_problem(text: str, canonical_text: str) -> str:
    diff = list(
        difflib.unified_diff(
            text.split("\n"), canonical_text.split("\n"), fromfile="yours", tofile="canonical", n=1, lineterm=""
        )
    )
    lines = [
        *LAYOUT_RULES,
        "Read the diff as follows: `-` lines are yours and `+` lines are canonical, "
        "and the line numbers after `-` are your file's.",
        *diff[:LAYOUT_DIFF_LINE_CAP],
    ]
    if len(diff) > LAYOUT_DIFF_LINE_CAP:
        lines.append(
            f"... {len(diff) - LAYOUT_DIFF_LINE_CAP} more diff lines not shown. A file this far from canonical is quicker to "
            f"restore with `git checkout origin/main -- {TABLE_FILE_NAME}` and edit again by hand."
        )
    return "\n".join(lines)


def load_table(data: bytes) -> TableLoad:
    """Validate the exception table in three stages, stopping at the first that reports a problem."""
    try:
        text = data.decode("utf-8")
        parsed = tomllib.loads(text)
    except ValueError as error:  # TOMLDecodeError and UnicodeDecodeError both subclass ValueError
        problem = "\n".join(
            [
                f"The exception table does not parse: {error}",
                f"If this is a merge conflict, follow the conflict rule in the header comment of {TABLE_FILE_NAME}.",
                *LAYOUT_RULES,
            ]
        )
        return TableLoad({}, TableStage.DECODE, [problem])
    schema_problems = [problem for path, row in parsed.items() for problem in _row_problems(path, row)]
    if schema_problems:
        return TableLoad({}, TableStage.SCHEMA, schema_problems)
    header, body = split_header_comment(text)
    canonical_body = serialize_rows(parsed)
    if body == canonical_body:
        return TableLoad(parsed, None, [])
    return TableLoad(parsed, TableStage.LAYOUT, [_layout_problem(text.replace("\r\n", "\n"), header + canonical_body)])


def evaluate(counts: dict[str, int], rows: Rows) -> list[Violation]:
    violations = []
    for path in sorted(counts.keys() | rows.keys()):
        count = counts.get(path)
        ceiling = rows[path]["ceiling"] if path in rows else None
        if count is None:
            violations.append(Violation(ViolationKind.NOT_COUNTED, path, None, ceiling))
        elif ceiling is None:
            if count > LINE_LIMIT:
                violations.append(Violation(ViolationKind.NO_ROW, path, count, None))
        elif count <= LINE_LIMIT:
            violations.append(Violation(ViolationKind.UNDER_LIMIT, path, count, ceiling))
        elif count > ceiling:
            violations.append(Violation(ViolationKind.OVER_CEILING, path, count, ceiling))
        elif count < ceiling:
            violations.append(Violation(ViolationKind.UNDER_CEILING, path, count, ceiling))
    return violations


def _no_row_lines(violation: Violation, preceding_path: str | None) -> list[str]:
    placement = "it is the first row" if preceding_path is None else f"it goes after the row for {preceding_path}"
    skeleton = serialize_row(
        violation.path,
        {"ceiling": violation.line_count, "verdict": VERDICT_SPLIT_PENDING, "seam": SEAM_PLACEHOLDER},
    )
    return [
        f"{violation.path}: {violation.line_count} lines, over the {LINE_LIMIT}-line limit, with no row. "
        f"Add one; {placement}. Rows are separated by one blank line.",
        SKELETON_START_LINE,
        skeleton,
        SKELETON_END_LINE,
        f'A file that cannot be split takes verdict = "{VERDICT_STRUCTURAL_EXCEPTION}" and a reason instead; '
        f"the header of {TABLE_FILE_NAME} says when.",
    ]


def _violation_lines(violation: Violation, rows: Rows, preceding_path: str | None) -> list[str]:
    path, count = violation.path, violation.line_count
    if violation.kind is ViolationKind.NO_ROW:
        return _no_row_lines(violation, preceding_path)
    if violation.kind is ViolationKind.UNDER_LIMIT:
        return [
            f"{path}: {count} lines, at or under the {LINE_LIMIT}-line limit, so it needs no row. "
            "Remove the row's lines and one blank line beside them."
        ]
    if violation.kind is ViolationKind.NOT_COUNTED:
        return [
            f"{path}: not a tracked regular `.py`/`.sh` file, so its row is stale. "
            "Remove the row's lines and one blank line beside them, or after a rename move the row to the new path."
        ]
    lines = [f"{path}: {count} lines, and its row holds {violation.ceiling}. Write ceiling = {count}."]
    row = rows[path]
    if violation.kind is ViolationKind.OVER_CEILING and row["verdict"] == VERDICT_STRUCTURAL_EXCEPTION:
        lines.append(f"The row's reason: {row['reason']}")
    return lines


def render(violations: list[Violation], rows: Rows) -> str:
    """Build the failure message. It has no base to diff against, so the did-not-change procedure prints every time."""
    sections = [[MESSAGE_PREFACE]]
    skeleton_paths: list[str] = []
    for violation in violations:
        preceding_paths = [path for path in (*rows, *skeleton_paths) if path < violation.path]
        preceding_path = max(preceding_paths, default=None)
        sections.append(_violation_lines(violation, rows, preceding_path))
        if violation.kind is ViolationKind.NO_ROW:
            skeleton_paths.append(violation.path)
    kinds = {violation.kind for violation in violations}
    if ViolationKind.NO_ROW in kinds and ViolationKind.NOT_COUNTED in kinds:
        sections.append([RENAME_LINE])
    if ViolationKind.NO_ROW in kinds or ViolationKind.OVER_CEILING in kinds:
        structural_over_ceiling = any(
            violation.kind is ViolationKind.OVER_CEILING and rows[violation.path]["verdict"] == VERDICT_STRUCTURAL_EXCEPTION
            for violation in violations
        )
        qualifier = STRUCTURAL_QUALIFIER if structural_over_ceiling else ""
        sections.append(
            [
                REMEDY_HEADING,
                f"1. Move the new code into a new module or test file{qualifier}.",
                f"2. Split the file along a named seam, such as a subcommand, a domain or a detector{qualifier}.",
                f"3. Add or raise the file's row in {TABLE_FILE_NAME}, with a seam or a reason.",
            ]
        )
    sections.append(list(PROHIBITION_LINES))
    sections.append([DID_NOT_CHANGE_HEADING, *DID_NOT_CHANGE_STEPS])
    return "\n\n".join("\n".join(section) for section in sections)


def size_report(counts: dict[str, int], table_data: bytes) -> str | None:
    """The size test's body: None when every file passes. A layout problem alone never hides a size value."""
    table = load_table(table_data)
    if table.failed_stage in (TableStage.DECODE, TableStage.SCHEMA):
        return TABLE_PROBLEM_LINE
    violations = evaluate(counts, table.rows)
    return render(violations, table.rows) if violations else None


def fail_with_report(report: str | None) -> None:
    """Fail with `report` printed verbatim; a bare assertion would show it through pytest's truncated repr."""
    if report is not None:
        pytest.fail(report, pytrace=False)
