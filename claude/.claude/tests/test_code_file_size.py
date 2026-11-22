"""Fails when a tracked `.py` or `.sh` file passes 1,000 lines without an exception row, or differs from its row's ceiling.

A new file counts once it is staged.

Decision record: docs/design-decisions/code-file-line-limit.md. Exception table: code-file-size-exceptions.toml.
"""
from __future__ import annotations

import inspect
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import code_file_size
import pytest
from code_file_size import (
    GIT_TIMEOUT_SECONDS,
    LINE_LIMIT,
    REPOSITORY_ENV_VARIABLES,
    SEAM_PLACEHOLDER,
    SHAPE_TEST_NODE_ID,
    SKELETON_END_LINE,
    SKELETON_START_LINE,
    TABLE_FILE_NAME,
    TableStage,
    Violation,
    ViolationKind,
    count_physical_lines,
    count_tracked_code_files,
    evaluate,
    fail_with_report,
    load_table,
    parse_index_listing,
    render,
    serialize_row,
    serialize_rows,
    size_report,
    split_header_comment,
)
from helpers import REPO_ROOT, init_git_repo, isolated_git_env

TABLE_PATH = REPO_ROOT / "code-file-size-exceptions.toml"

# The opening phrase of each header section a printed message cites: the no-row message cites the verdict block,
# the decode problem cites the conflict rule, and the header's own layout rule points at the shape test.
HEADER_RULE_PHRASES = ("Choosing a verdict:", "Layout rule:", "Conflict rule:", "Split rule:")

SYNTHETIC_HEADER = "# synthetic header\n# second line\n\n"
TABLE_PROBLEM_LINE = (
    "The exception table has a problem, so no file sizes were checked. "
    "Run claude/.claude/tests/test_code_file_size.py::test_exception_table_shape to see it."
)
REMEDY_HEADING_PREFIX = "If this branch changed the file"
RESTORE_COMMAND = "git checkout origin/main -- code-file-size-exceptions.toml"


def _split_pending_row(ceiling: int, seam: str = "seam text", issue: int | None = None) -> dict:
    row = {"ceiling": ceiling, "verdict": "split pending", "seam": seam}
    if issue is not None:
        row["issue"] = issue
    return row


def _structural_row(ceiling: int, reason: str = "reason text") -> dict:
    return {"ceiling": ceiling, "verdict": "structural exception", "reason": reason}


def _canonical_text(rows: dict, header: str = SYNTHETIC_HEADER) -> str:
    return header + serialize_rows(rows)


def _row_text(*field_lines: str, path: str = "a.py") -> str:
    return f'["{path}"]\n' + "\n".join(field_lines) + "\n"


def _violation(kind: ViolationKind, path: str = "a.py", count: int | None = 1500, ceiling: int | None = None) -> Violation:
    return Violation(kind, path, count, ceiling)


@pytest.fixture(scope="module")
def real_counts() -> dict[str, int]:
    return count_tracked_code_files(REPO_ROOT)


# --- The three tests against the real repository ---------------------------------------------------------------


def test_code_file_sizes(real_counts):
    fail_with_report(size_report(real_counts, TABLE_PATH.read_bytes()))


def test_exception_table_shape():
    problems = load_table(TABLE_PATH.read_bytes()).problems
    fail_with_report("\n".join(problems) if problems else None)


def test_exception_table_header():
    header, _ = split_header_comment(TABLE_PATH.read_bytes().decode("utf-8"))

    shape_test_name = SHAPE_TEST_NODE_ID.rpartition("::")[2]
    missing_phrases = [phrase for phrase in (*HEADER_RULE_PHRASES, shape_test_name) if phrase not in header]

    assert missing_phrases == []


def test_shape_test_node_id_names_a_test_in_this_file():
    node_path, _, test_name = SHAPE_TEST_NODE_ID.partition("::")

    assert (REPO_ROOT / node_path).resolve() == Path(__file__).resolve()
    node_test = getattr(sys.modules[__name__], test_name, None)
    assert inspect.isfunction(node_test)
    assert node_test.__module__ == __name__


def test_printed_table_file_name_is_the_file_the_real_table_tests_read():
    assert TABLE_PATH.name == TABLE_FILE_NAME


def test_real_corpus_is_non_empty_and_reaches_beyond_the_precedent_roots(real_counts):
    paths = list(real_counts)

    assert paths
    assert any(path.endswith(".py") for path in paths)
    assert any(path.endswith(".sh") for path in paths)
    assert any(not path.startswith(("claude/", "claude-skills/", "plugins/")) for path in paths)


# --- count_physical_lines --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("content", "expected_count"),
    [
        pytest.param(b"a\nb", 1, id="final-line-without-newline-is-not-counted"),
        pytest.param(b"a\nb\n", 2, id="each-newline-counts-once"),
        pytest.param(b"a\r\nb\r\n", 2, id="crlf-counts-once-per-newline"),
        pytest.param("a\u2028b\n".encode(), 1, id="u2028-adds-no-line"),
        pytest.param(b"", 0, id="empty-content-counts-zero"),
    ],
)
def test_count_physical_lines(content, expected_count):
    assert count_physical_lines(content) == expected_count


# --- parse_index_listing ---------------------------------------------------------------------------------------


def _index_record(mode: str, path: str, stage: int = 0) -> bytes:
    return f"{mode} {'a' * 40} {stage}\t{path}".encode() + b"\0"


def test_parse_index_listing_includes_an_executable_sh_entry():
    assert parse_index_listing(_index_record("100755", "install.sh")) == ["install.sh"]


def test_parse_index_listing_excludes_symlink_and_gitlink_entries():
    raw = _index_record("120000", "link.py") + _index_record("160000", "vendored.sh") + _index_record("100644", "real.py")

    assert parse_index_listing(raw) == ["real.py"]


def test_parse_index_listing_returns_an_unmerged_path_once():
    raw = b"".join(_index_record("100644", "conflicted.py", stage) for stage in (1, 2, 3))

    assert parse_index_listing(raw) == ["conflicted.py"]


def test_parse_index_listing_counts_an_unmerged_path_with_one_regular_entry():
    raw = _index_record("120000", "swapped.py", 2) + _index_record("100644", "swapped.py", 3)

    assert parse_index_listing(raw) == ["swapped.py"]


def test_parse_index_listing_keeps_a_space_and_non_ascii_path_intact():
    raw = _index_record("100644", "dir with space/a b.py") + _index_record("100644", "módulo/é.sh")

    assert parse_index_listing(raw) == sorted(["dir with space/a b.py", "módulo/é.sh"])


def test_parse_index_listing_excludes_a_txt_entry():
    assert parse_index_listing(_index_record("100644", "notes.txt")) == []


def test_parse_index_listing_of_empty_output_is_empty():
    assert parse_index_listing(b"") == []


# --- count_tracked_code_files over a throwaway repository ------------------------------------------------------


@pytest.fixture
def git_env(tmp_path) -> dict:
    empty_xdg_config_home = tmp_path / "empty-xdg"
    empty_xdg_config_home.mkdir()
    ambient_env = {name: value for name, value in os.environ.items() if not name.startswith("GIT_")}
    return isolated_git_env(ambient_env, empty_xdg_config_home)


@pytest.fixture
def repo(tmp_path, git_env) -> Path:
    return init_git_repo(tmp_path / "repo", branch="main", env=git_env)


def _git(repo: Path, git_env: dict, *args: str, check: bool = True) -> None:
    subprocess.run(["git", *args], cwd=repo, env=git_env, check=check, capture_output=True)


def _write(repo: Path, relative_path: str, content: str) -> None:
    target = repo / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)


def test_enumeration_counts_a_nested_sh_file(repo, git_env):
    _write(repo, "pkg/tool.sh", "a\nb\n")
    _git(repo, git_env, "add", "pkg/tool.sh")

    assert count_tracked_code_files(repo) == {"pkg/tool.sh": 2}


def test_enumeration_counts_a_new_file_only_once_staged(repo, git_env):
    _write(repo, "new.py", "a\n")
    assert count_tracked_code_files(repo) == {}

    _git(repo, git_env, "add", "new.py")

    assert count_tracked_code_files(repo) == {"new.py": 1}


def test_enumeration_excludes_a_tracked_symlink_to_a_py_file(repo, git_env):
    _write(repo, "real.py", "a\n")
    (repo / "link.py").symlink_to("real.py")
    _git(repo, git_env, "add", "real.py", "link.py")

    assert count_tracked_code_files(repo) == {"real.py": 1}


def test_enumeration_excludes_a_tracked_sh_file_deleted_from_the_working_tree(repo, git_env):
    _write(repo, "kept.py", "a\n")
    _write(repo, "gone.sh", "a\n")
    _git(repo, git_env, "add", "kept.py", "gone.sh")
    (repo / "gone.sh").unlink()

    assert count_tracked_code_files(repo) == {"kept.py": 1}


def test_enumeration_counts_the_working_tree_lines_of_an_unstaged_edit(repo, git_env):
    _write(repo, "edited.py", "a\n")
    _git(repo, git_env, "add", "edited.py")
    _write(repo, "edited.py", "a\nb\nc\n")

    assert count_tracked_code_files(repo) == {"edited.py": 3}


def test_enumeration_counts_a_conflicted_path_once(repo, git_env):
    _write(repo, "conflicted.py", "base\n")
    _git(repo, git_env, "add", "conflicted.py")
    _git(repo, git_env, "commit", "-q", "-m", "base")
    _git(repo, git_env, "checkout", "-q", "-b", "side")
    _write(repo, "conflicted.py", "side\n")
    _git(repo, git_env, "commit", "-q", "-a", "-m", "side")
    _git(repo, git_env, "checkout", "-q", "main")
    _write(repo, "conflicted.py", "main\n")
    _git(repo, git_env, "commit", "-q", "-a", "-m", "main")
    _git(repo, git_env, "merge", "-q", "--no-edit", "side", check=False)

    conflicted_lines = (repo / "conflicted.py").read_bytes().count(b"\n")
    assert conflicted_lines > 1
    assert count_tracked_code_files(repo) == {"conflicted.py": conflicted_lines}


@pytest.mark.parametrize("variable_name", REPOSITORY_ENV_VARIABLES)
def test_enumeration_ignores_an_ambient_repository_redirecting_variable(repo, git_env, tmp_path, monkeypatch, variable_name):
    _write(repo, "a.py", "a\n")
    _git(repo, git_env, "add", "a.py")
    # Git ignores a missing GIT_WORK_TREE path when listing the index, but a work tree that is the repository's parent
    # directory makes it list nothing, so that value is what discriminates an inherited GIT_WORK_TREE.
    redirect_target = repo.parent if variable_name == "GIT_WORK_TREE" else tmp_path / "no-such-path"
    monkeypatch.setenv(variable_name, str(redirect_target))

    assert count_tracked_code_files(repo) == {"a.py": 1}


def test_enumeration_error_carries_git_stderr_when_git_fails(tmp_path, monkeypatch):
    not_a_repository = tmp_path / "not-a-repository"
    not_a_repository.mkdir()
    # The ceiling stops git from walking up into a repository that encloses tmp_path, and LC_ALL=C keeps git's message in English.
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    monkeypatch.setenv("LC_ALL", "C")

    with pytest.raises(RuntimeError, match="not a git repository"):
        count_tracked_code_files(not_a_repository)


def test_enumeration_error_names_the_timeout_and_carries_partial_stderr_when_git_hangs(tmp_path, monkeypatch):
    def hanging_git(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"], stderr=b"waiting on a lock")

    monkeypatch.setattr(code_file_size.subprocess, "run", hanging_git)

    with pytest.raises(RuntimeError, match=f"did not finish within {GIT_TIMEOUT_SECONDS} seconds: waiting on a lock"):
        count_tracked_code_files(tmp_path)


def test_enumeration_error_names_the_timeout_when_the_hung_git_left_no_stderr(tmp_path, monkeypatch):
    def hanging_git(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"], stderr=None)

    monkeypatch.setattr(code_file_size.subprocess, "run", hanging_git)

    with pytest.raises(RuntimeError, match=f"did not finish within {GIT_TIMEOUT_SECONDS} seconds: $"):
        count_tracked_code_files(tmp_path)


# --- evaluate --------------------------------------------------------------------------------------------------


def test_file_with_no_row_at_the_limit_passes():
    assert evaluate({"a.py": LINE_LIMIT}, {}) == []


def test_file_with_no_row_over_the_limit_is_no_row():
    assert evaluate({"a.py": LINE_LIMIT + 1}, {}) == [Violation(ViolationKind.NO_ROW, "a.py", 1001, None)]


def test_row_equal_to_the_count_passes():
    assert evaluate({"a.py": 1001}, {"a.py": _split_pending_row(1001)}) == []


def test_row_above_the_count_is_under_ceiling_with_the_count_to_write():
    violations = evaluate({"a.py": 1001}, {"a.py": _split_pending_row(1002)})

    assert violations == [Violation(ViolationKind.UNDER_CEILING, "a.py", 1001, 1002)]


def test_row_below_the_count_is_over_ceiling():
    violations = evaluate({"a.py": 1002}, {"a.py": _split_pending_row(1001)})

    assert violations == [Violation(ViolationKind.OVER_CEILING, "a.py", 1002, 1001)]


def test_row_for_a_file_at_the_limit_is_under_limit_only():
    violations = evaluate({"a.py": LINE_LIMIT}, {"a.py": _split_pending_row(1001)})

    assert violations == [Violation(ViolationKind.UNDER_LIMIT, "a.py", LINE_LIMIT, 1001)]


def test_row_for_a_path_that_is_not_counted_is_not_counted():
    violations = evaluate({}, {"gone.py": _split_pending_row(1500)})

    assert violations == [Violation(ViolationKind.NOT_COUNTED, "gone.py", None, 1500)]


def test_violations_from_out_of_order_input_come_back_sorted_by_path():
    violations = evaluate({"b.py": 2000, "a.py": 3000}, {})

    assert [violation.path for violation in violations] == ["a.py", "b.py"]


# --- render ----------------------------------------------------------------------------------------------------


def _lines_after(text: str, heading_prefix: str, line_count: int) -> list[str]:
    lines = text.split("\n")
    heading_index = next(index for index, line in enumerate(lines) if line.startswith(heading_prefix))
    return lines[heading_index + 1 : heading_index + 1 + line_count]


def test_remedy_block_lists_the_three_remedies_in_order_after_its_heading():
    message = render([_violation(ViolationKind.NO_ROW)], {})

    first, second, third = _lines_after(message, REMEDY_HEADING_PREFIX, 3)

    assert first.startswith("1. Move the new code into a new module or test file")
    assert second.startswith("2. Split the file along a named seam")
    assert third.startswith("3. Add or raise the file's row in code-file-size-exceptions.toml")


def test_message_holds_the_preface_the_heading_and_both_prohibitions():
    message = render([_violation(ViolationKind.NO_ROW)], {})

    assert "merge origin/main and run the check again before writing any printed value" in message
    assert REMEDY_HEADING_PREFIX in message
    assert "Do not split a file by position, such as into a `_part2` file." in message
    assert "Do not fit a file under the limit by deleting comments or joining lines." in message


@pytest.mark.parametrize(
    "fixed_text",
    [
        pytest.param("For a listed file this branch did not change:", id="procedure-heading-sentinel"),
        pytest.param("Open a fix PR only on their go-ahead.", id="go-ahead-before-opening-a-fix-pr"),
        pytest.param("Push to no open fix PR's branch, your own included.", id="no-push-to-another-fix-pr-branch"),
    ],
)
def test_message_with_only_an_under_limit_line_still_prints_the_did_not_change_procedure(fixed_text):
    message = render([_violation(ViolationKind.UNDER_LIMIT, count=900, ceiling=1500)], {"a.py": _split_pending_row(1500)})

    assert fixed_text in message


def test_fix_pr_search_title_equals_the_title_the_procedure_prescribes():
    message = render([_violation(ViolationKind.UNDER_LIMIT, count=900, ceiling=1500)], {"a.py": _split_pending_row(1500)})

    searched_titles = re.findall(r'in:title "([^"]+)"', message)
    prescribed_titles = re.findall(r"Title it exactly `([^`]+)`", message)

    assert len(searched_titles) == 1
    assert searched_titles == prescribed_titles


def test_rename_line_carries_its_sorted_position_and_not_applicable_clauses():
    violations = [_violation(ViolationKind.NO_ROW, "new.py"), _violation(ViolationKind.NOT_COUNTED, "old.py", None, 1500)]

    message = render(violations, {"old.py": _split_pending_row(1500)})

    assert "move the row to its sorted position" in message
    assert "the seam placeholder and the remedies below do not apply to that path" in message


@pytest.mark.parametrize(
    ("violations", "rows", "rename_line_count"),
    [
        pytest.param(
            [_violation(ViolationKind.NO_ROW, "new.py"), _violation(ViolationKind.NOT_COUNTED, "old.py", None, 1500)],
            {"old.py": _split_pending_row(1500)},
            1,
            id="no-row-and-not-counted-together",
        ),
        pytest.param([_violation(ViolationKind.NO_ROW, "new.py")], {}, 0, id="no-row-alone"),
        pytest.param(
            [_violation(ViolationKind.NOT_COUNTED, "old.py", None, 1500)],
            {"old.py": _split_pending_row(1500)},
            0,
            id="not-counted-alone",
        ),
    ],
)
def test_rename_line_prints_once_only_when_a_no_row_and_a_not_counted_line_appear_together(violations, rows, rename_line_count):
    message = render(violations, rows)

    assert message.count("move the row to its sorted position") == rename_line_count


def _skeleton_after(message: str, path: str) -> tuple[str, str]:
    """The skeleton printed for `path` and the line that introduces it."""
    lines = message.split("\n")
    introducing_index = next(index for index, line in enumerate(lines) if line.startswith(f"{path}: "))
    assert lines[introducing_index + 1] == SKELETON_START_LINE
    end_index = lines.index(SKELETON_END_LINE, introducing_index)
    return "\n".join(lines[introducing_index + 2 : end_index]), lines[introducing_index]


def _anchor_named_by(introducing_line: str) -> str | None:
    marker = "it goes after the row for "
    if marker not in introducing_line:
        return None
    return introducing_line.split(marker)[1].split(". ")[0]


def _table_with_skeleton_inserted(rows: dict, skeleton: str, anchor: str | None) -> str:
    blocks = [serialize_row(path, rows[path]) for path in sorted(rows)]
    insert_at = 0 if anchor is None else 1 + blocks.index(serialize_row(anchor, rows[anchor]))
    blocks.insert(insert_at, skeleton)
    return SYNTHETIC_HEADER + "\n\n".join(blocks) + "\n"


def test_no_row_skeleton_pasted_after_the_row_its_line_names_loads_without_a_problem():
    rows = {"a.py": _split_pending_row(1100), "z.py": _structural_row(1300)}
    message = render([_violation(ViolationKind.NO_ROW, "m.py", 1500)], rows)
    skeleton, introducing_line = _skeleton_after(message, "m.py")
    anchor = _anchor_named_by(introducing_line)

    assert anchor == "a.py"
    filled_skeleton = skeleton.replace(SEAM_PLACEHOLDER, "a real seam")
    table = _table_with_skeleton_inserted(rows, filled_skeleton, anchor)
    loaded = load_table(table.encode())
    assert loaded.problems == []
    assert set(loaded.rows) == {"a.py", "m.py", "z.py"}


def test_no_row_skeleton_with_its_placeholder_left_in_is_rejected_at_the_schema_stage():
    message = render([_violation(ViolationKind.NO_ROW, "m.py", 1500)], {})
    skeleton, _ = _skeleton_after(message, "m.py")

    loaded = load_table((SYNTHETIC_HEADER + skeleton + "\n").encode())

    assert loaded.failed_stage is TableStage.SCHEMA


def test_first_row_skeleton_is_introduced_as_the_first_row_and_loads_without_a_problem():
    message = render([_violation(ViolationKind.NO_ROW, "m.py", 1500)], {})
    skeleton, introducing_line = _skeleton_after(message, "m.py")

    assert "it is the first row" in introducing_line
    assert load_table((SYNTHETIC_HEADER + skeleton.replace(SEAM_PLACEHOLDER, "a real seam") + "\n").encode()).problems == []


def test_second_of_two_adjacent_no_row_lines_names_the_first_as_its_predecessor():
    violations = [_violation(ViolationKind.NO_ROW, "b.py"), _violation(ViolationKind.NO_ROW, "c.py")]

    message = render(violations, {"a.py": _split_pending_row(1100)})

    _, first_line = _skeleton_after(message, "b.py")
    _, second_line = _skeleton_after(message, "c.py")
    assert _anchor_named_by(first_line) == "a.py"
    assert _anchor_named_by(second_line) == "b.py"


def test_over_ceiling_line_on_a_structural_row_prints_its_reason_and_qualifies_remedies_one_and_two():
    violation = _violation(ViolationKind.OVER_CEILING, "a.py", 1600, 1500)

    message = render([violation], {"a.py": _structural_row(1500, reason="the loader reads one file")})

    assert "The row's reason: the loader reads one file" in message
    first, second, third = _lines_after(message, REMEDY_HEADING_PREFIX, 3)
    assert first.endswith("unless the reason printed above rules it out.")
    assert second.endswith("unless the reason printed above rules it out.")
    assert "unless" not in third


def test_over_ceiling_line_on_a_split_pending_row_prints_no_reason_and_no_qualifier():
    violation = _violation(ViolationKind.OVER_CEILING, "a.py", 1600, 1500)

    message = render([violation], {"a.py": _split_pending_row(1500)})

    assert "The row's reason" not in message
    assert "unless the reason printed above" not in message


def test_over_ceiling_line_prints_the_count_as_the_value_to_write():
    message = render([_violation(ViolationKind.OVER_CEILING, "a.py", 1502, 1501)], {"a.py": _split_pending_row(1501)})

    assert "a.py: 1502 lines" in message
    assert "Write ceiling = 1502." in message


def test_under_ceiling_line_prints_the_value_to_write_and_no_growth_remedies():
    message = render([_violation(ViolationKind.UNDER_CEILING, "a.py", 1501, 1502)], {"a.py": _split_pending_row(1502)})

    assert "Write ceiling = 1501." in message
    assert REMEDY_HEADING_PREFIX not in message


def test_under_limit_line_prints_no_ceiling_value_and_no_remedy_block():
    message = render([_violation(ViolationKind.UNDER_LIMIT, "a.py", 900, 1500)], {"a.py": _split_pending_row(1500)})

    assert "a.py: 900 lines" in message
    assert "ceiling =" not in message
    assert REMEDY_HEADING_PREFIX not in message
    assert "Remove the row's lines and one blank line beside them." in message


def test_not_counted_line_says_the_path_is_not_a_tracked_regular_file():
    message = render([_violation(ViolationKind.NOT_COUNTED, "gone.py", None, 1500)], {"gone.py": _split_pending_row(1500)})

    assert "gone.py: not a tracked regular `.py`/`.sh` file" in message


# --- load_table ------------------------------------------------------------------------------------------------

SHAPE_ROWS = {
    "claude/.claude/hooks/tests/test_marker_script.py": _split_pending_row(
        7303, seam="Test-class families following marker.sh's status and write halves", issue=1530
    ),
    "docs/ünïcode/tool.sh": _structural_row(1200, reason="the installer is one file by design"),
    "dir with space/a b.py": _split_pending_row(1001),
    'quote"and\\backslash.py': _split_pending_row(1002, seam='say "hi" \\ done'),
}
CEILING = "ceiling = 1001"
SPLIT_VERDICT = 'verdict = "split pending"'
STRUCTURAL_VERDICT = 'verdict = "structural exception"'
SEAM = 'seam = "s"'
REASON = 'reason = "r"'
CANONICAL_ROW_A = _row_text(CEILING, SPLIT_VERDICT, SEAM, path="a.py")
CANONICAL_ROW_B = _row_text("ceiling = 1002", SPLIT_VERDICT, SEAM, path="b.py")


def test_table_accepts_a_header_comment_followed_by_canonical_rows():
    loaded = load_table(_canonical_text(SHAPE_ROWS).encode())

    assert loaded.failed_stage is None
    assert loaded.problems == []
    assert loaded.rows == SHAPE_ROWS


def test_table_accepts_the_same_text_with_crlf_line_ends():
    loaded = load_table(_canonical_text(SHAPE_ROWS).replace("\n", "\r\n").encode())

    assert loaded.problems == []
    assert loaded.rows == SHAPE_ROWS


def test_table_accepts_a_header_only_file():
    loaded = load_table(SYNTHETIC_HEADER.encode())

    assert loaded.problems == []
    assert loaded.rows == {}


def test_table_accepts_a_header_with_an_indented_comment_and_a_whitespace_only_line():
    header = "# first\n   # indented comment\n \t \n# last\n"

    loaded = load_table(_canonical_text(SHAPE_ROWS, header=header).encode())

    assert loaded.problems == []


def test_header_comment_line_holding_u2028_followed_by_header_shaped_text_adds_no_row():
    header = '# note\u2028["fake.py"]\n'

    loaded = load_table(_canonical_text(SHAPE_ROWS, header=header).encode())

    assert loaded.problems == []
    assert "fake.py" not in loaded.rows


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(SYNTHETIC_HEADER.encode() + b"<<<<<<< HEAD\n" + CANONICAL_ROW_A.encode(), id="conflict-marker-text"),
        pytest.param((CANONICAL_ROW_A + "\n" + CANONICAL_ROW_A).encode(), id="path-declared-twice"),
        pytest.param(b"[dir/a.py]\nceiling = 1001\n", id="unquoted-header-holding-a-slash"),
        pytest.param(b"\xff\xfe\x00", id="bytes-that-are-not-utf-8"),
    ],
)
def test_table_decode_failure_is_one_problem_pointing_at_the_conflict_rule_with_the_rules_block(data):
    loaded = load_table(data)

    assert loaded.failed_stage is TableStage.DECODE
    assert len(loaded.problems) == 1
    assert "conflict rule in the header comment" in loaded.problems[0]
    assert "exactly one final newline" in loaded.problems[0]


def test_bare_header_is_one_schema_problem_saying_to_quote_the_whole_path():
    loaded = load_table(b"[install.sh]\n")

    assert loaded.failed_stage is TableStage.SCHEMA
    assert len(loaded.problems) == 1
    assert loaded.problems[0].startswith("install:")
    assert '["install.sh"]' in loaded.problems[0]


def test_two_bare_headers_sharing_a_prefix_are_one_schema_problem_listing_both_quoted_paths():
    loaded = load_table(b"[install.sh]\n[install.py]\n")

    assert loaded.failed_stage is TableStage.SCHEMA
    assert len(loaded.problems) == 1
    assert '["install.py"]' in loaded.problems[0]
    assert '["install.sh"]' in loaded.problems[0]


@pytest.mark.parametrize(
    "inner_row",
    [
        pytest.param('"b.py" = { ceiling = 1002 }\n', id="inline-table-row"),
        pytest.param('"b.py".ceiling = 1002\n', id="dotted-key-row"),
    ],
)
def test_row_written_below_another_row_is_one_problem_naming_it_as_written_inside_that_row(inner_row):
    loaded = load_table((CANONICAL_ROW_A + inner_row).encode())

    assert loaded.failed_stage is TableStage.SCHEMA
    assert len(loaded.problems) == 1
    assert loaded.problems[0].startswith("a.py: holds a row written inside it")
    assert '["b.py"]' in loaded.problems[0]


def test_array_of_tables_header_is_a_schema_problem_naming_its_row():
    loaded = load_table(b'[["a.py"]]\nceiling = 1001\n')

    assert loaded.failed_stage is TableStage.SCHEMA
    assert loaded.problems[0].startswith("a.py: not a table")


def test_top_level_key_that_is_not_a_table_is_a_schema_problem_naming_it():
    loaded = load_table(b"stray = 1\n")

    assert loaded.failed_stage is TableStage.SCHEMA
    assert loaded.problems[0].startswith("stray: not a table")


@pytest.mark.parametrize(
    "seam_line",
    [
        pytest.param('seam = "one\\ntwo"', id="single-line-string-with-escaped-newline"),
        pytest.param('seam = """\none\ntwo"""', id="multi-line-string-holding-a-line-break"),
    ],
)
def test_seam_holding_a_line_break_is_a_schema_problem_naming_its_row(seam_line):
    loaded = load_table(_row_text("ceiling = 1001", 'verdict = "split pending"', seam_line).encode())

    assert loaded.failed_stage is TableStage.SCHEMA
    assert loaded.problems == ["a.py: seam holds a line break or control character, so it cannot print on one line."]


def _schema_case(case_id: str, *field_lines: str, problem_fragment: str):
    return pytest.param(field_lines, problem_fragment, id=case_id)


@pytest.mark.parametrize(
    ("field_lines", "problem_fragment"),
    [
        _schema_case("bool-ceiling", "ceiling = true", SPLIT_VERDICT, SEAM, problem_fragment="ceiling must be an integer"),
        _schema_case("string-ceiling", 'ceiling = "1001"', SPLIT_VERDICT, SEAM, problem_fragment="ceiling must be an integer"),
        _schema_case("missing-ceiling", SPLIT_VERDICT, SEAM, problem_fragment="ceiling is missing"),
        _schema_case("ceiling-at-limit", "ceiling = 1000", SPLIT_VERDICT, SEAM, problem_fragment="ceiling must be over 1000"),
        _schema_case("unknown-verdict", CEILING, 'verdict = "later"', SEAM, problem_fragment="verdict must be"),
        _schema_case("missing-verdict", CEILING, SEAM, problem_fragment="verdict must be"),
        _schema_case("bool-issue", CEILING, SPLIT_VERDICT, SEAM, "issue = true", problem_fragment="issue must be a positive"),
        _schema_case("zero-issue", CEILING, SPLIT_VERDICT, SEAM, "issue = 0", problem_fragment="issue must be a positive"),
        _schema_case(
            "structural-row-with-a-seam", CEILING, STRUCTURAL_VERDICT, REASON, SEAM,
            problem_fragment="a structural exception row takes no seam",
        ),
        _schema_case(
            "structural-row-with-an-issue", CEILING, STRUCTURAL_VERDICT, REASON, "issue = 5",
            problem_fragment="a structural exception row takes no issue",
        ),
        _schema_case(
            "split-pending-row-with-a-reason", CEILING, SPLIT_VERDICT, SEAM, REASON,
            problem_fragment="a split pending row takes no reason",
        ),
        _schema_case("empty-seam", CEILING, SPLIT_VERDICT, 'seam = ""', problem_fragment="seam must be a non-empty string"),
        _schema_case("missing-seam", CEILING, SPLIT_VERDICT, problem_fragment="seam must be a non-empty string"),
        _schema_case("missing-reason", CEILING, STRUCTURAL_VERDICT, problem_fragment="reason must be a non-empty string"),
        _schema_case("unknown-key", CEILING, SPLIT_VERDICT, SEAM, "extra = 1", problem_fragment="unknown key ['extra']"),
        _schema_case(
            "placeholder-seam", CEILING, SPLIT_VERDICT, f'seam = "{SEAM_PLACEHOLDER}"',
            problem_fragment="still the skeleton's placeholder",
        ),
    ],
)
def test_each_schema_rule_violation_is_a_problem_naming_its_row(field_lines, problem_fragment):
    loaded = load_table(_row_text(*field_lines).encode())

    assert loaded.failed_stage is TableStage.SCHEMA
    assert any(problem.startswith("a.py:") and problem_fragment in problem for problem in loaded.problems), loaded.problems


def test_schema_problems_name_every_offending_row():
    text = _row_text("ceiling = 1000", 'verdict = "split pending"', 'seam = "s"', path="a.py") + "\n"
    text += _row_text("ceiling = 1001", 'verdict = "nope"', path="b.py")

    loaded = load_table(text.encode())

    assert [problem.split(":")[0] for problem in loaded.problems] == ["a.py", "b.py"]


def _layout_cases() -> list:
    inline_first_row = '"a.py" = { ceiling = 1001, verdict = "split pending", seam = "s" }\n'
    dotted_first_row = '"a.py".ceiling = 1001\n"a.py".verdict = "split pending"\n"a.py".seam = "s"\n'
    literal_header = "['a.py']\n" + "\n".join([CEILING, SPLIT_VERDICT, SEAM]) + "\n"
    spaced_header = '[ "a.py" ]\n' + "\n".join([CEILING, SPLIT_VERDICT, SEAM]) + "\n"
    issue_before_seam = _row_text(CEILING, SPLIT_VERDICT, "issue = 5", SEAM)
    context_seam = " " + SEAM
    return [
        pytest.param(inline_first_row, '+["a.py"]', id="inline-table-first-row"),
        pytest.param(dotted_first_row, '+["a.py"]', id="dotted-key-first-row"),
        pytest.param(literal_header, '+["a.py"]', id="literal-string-header"),
        pytest.param(spaced_header, '+["a.py"]', id="header-with-inner-spaces"),
        pytest.param(CANONICAL_ROW_A.replace('["a.py"]', '["a.py"] # note'), '+["a.py"]', id="trailing-comment-on-header"),
        pytest.param(CANONICAL_ROW_A.replace("1001", "1001 # note"), "+" + CEILING, id="trailing-comment-on-field"),
        pytest.param(CANONICAL_ROW_A + "# between\n\n" + CANONICAL_ROW_B, "-# between", id="comment-between-rows"),
        pytest.param(CANONICAL_ROW_A.replace(SEAM, "seam = 's'"), "+" + SEAM, id="literal-string-value"),
        pytest.param(CANONICAL_ROW_A.replace(SEAM, 'seam = """\ns"""'), "+" + SEAM, id="triple-quoted-with-trimmed-newline"),
        pytest.param(
            CANONICAL_ROW_A.replace(SEAM, 'seam = """\\\n   s"""'), "+" + SEAM, id="triple-quoted-with-line-ending-backslash"
        ),
        pytest.param(CANONICAL_ROW_A.replace("1001", "1_001"), "+" + CEILING, id="integer-with-underscore"),
        pytest.param(issue_before_seam, "+" + SEAM, id="issue-before-seam"),
        pytest.param(CANONICAL_ROW_B + "\n" + CANONICAL_ROW_A, '+["a.py"]', id="rows-out-of-order"),
        pytest.param(CANONICAL_ROW_A + "\n\n" + CANONICAL_ROW_B, ' ["b.py"]', id="two-blank-lines-between-rows"),
        pytest.param(CANONICAL_ROW_A + "\n", "@@ -8,2 +8 @@\n \n-", id="blank-line-after-the-last-row"),
        pytest.param(CANONICAL_ROW_A.rstrip("\n"), context_seam, id="no-final-newline"),
    ]


@pytest.mark.parametrize(("body", "canonical_fragment"), _layout_cases())
def test_layout_difference_is_a_diff_holding_the_canonical_line(body, canonical_fragment):
    loaded = load_table((SYNTHETIC_HEADER + body).encode())

    assert loaded.failed_stage is TableStage.LAYOUT
    assert len(loaded.problems) == 1
    assert canonical_fragment in loaded.problems[0]
    assert "+++ canonical" in loaded.problems[0]


def test_layout_problem_holds_the_rules_block_and_the_diff_labels():
    loaded = load_table((SYNTHETIC_HEADER + CANONICAL_ROW_A.rstrip("\n")).encode())

    problem = loaded.problems[0]
    assert "exactly one final newline" in problem
    assert "no trailing whitespace" in problem
    assert "--- yours" in problem
    assert "+++ canonical" in problem


def test_text_with_a_schema_problem_and_a_layout_difference_reports_only_the_schema_problem():
    text = SYNTHETIC_HEADER + CANONICAL_ROW_A.replace("1001", "true # note")

    loaded = load_table(text.encode())

    assert loaded.failed_stage is TableStage.SCHEMA
    assert all("+++ canonical" not in problem for problem in loaded.problems)


def _fifty_rows() -> dict:
    return {f"dir/f{index:02d}.py": _split_pending_row(1001 + index, seam="s") for index in range(50)}


def test_one_commented_row_among_fifty_shows_one_hunk_with_one_line_of_context():
    header = "# first header line\n# second header line\n"
    lines = _canonical_text(_fifty_rows(), header=header).split("\n")
    middle_ceiling_index = next(index for index, line in enumerate(lines) if line.startswith("ceiling = 1026"))
    lines[middle_ceiling_index] += " # note"

    problem = load_table("\n".join(lines).encode()).problems[0]

    diff_lines = problem.split("\n")
    hunk_headers = [line for line in diff_lines if line.startswith("@@")]
    assert len(hunk_headers) == 1
    yours_range_start = int(hunk_headers[0].split()[1].lstrip("-").split(",")[0])
    assert yours_range_start == middle_ceiling_index  # one line above the 1-based line number of the changed line
    context_header_lines = [line for line in diff_lines if line.startswith(' ["dir/f')]
    assert context_header_lines == [' ["dir/f25.py"]']


def test_a_comment_on_every_row_shows_the_first_forty_diff_lines_then_the_count_left_out_and_the_restore_line():
    lines = _canonical_text(_fifty_rows()).split("\n")
    commented_lines = [line + " # note" if line.startswith("ceiling = ") else line for line in lines]

    problem = load_table("\n".join(commented_lines).encode()).problems[0]

    problem_lines = problem.split("\n")
    notice_index = next(index for index, line in enumerate(problem_lines) if "more diff lines not shown" in line)
    assert problem_lines[notice_index - 40] == "--- yours"
    assert problem_lines[notice_index - 39] == "+++ canonical"
    assert int(problem_lines[notice_index].split()[1]) > 0
    assert RESTORE_COMMAND in problem_lines[notice_index]


# --- serialize_rows --------------------------------------------------------------------------------------------


def test_serialized_rows_parse_back_to_the_rows_they_came_from():
    rows = {
        'quote"back\\slash\ttab\u0085.py': _split_pending_row(1001, seam='say "hi" \\ café', issue=7),
        "non-ascii/ünïcode.sh": _structural_row(1500, reason='the "loader" reads \\ one file: ünï'),
        "plain.py": _split_pending_row(2000, seam="plain seam"),
    }

    assert tomllib.loads(serialize_rows(rows)) == rows


def test_serialize_rows_of_the_documented_row_equals_its_literal_text():
    rows = {
        "claude/.claude/hooks/tests/test_marker_script.py": _split_pending_row(
            7303, seam="Test-class families following marker.sh's status and write halves: ...", issue=1530
        )
    }
    expected = (
        '["claude/.claude/hooks/tests/test_marker_script.py"]\n'
        "ceiling = 7303\n"
        'verdict = "split pending"\n'
        'seam = "Test-class families following marker.sh\'s status and write halves: ..."\n'
        "issue = 1530\n"
    )

    assert serialize_rows(rows) == expected


# --- size_report -----------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "table_text",
    [
        pytest.param(SYNTHETIC_HEADER + "<<<<<<< HEAD\n" + CANONICAL_ROW_A, id="conflicted-text"),
        pytest.param(
            SYNTHETIC_HEADER + _row_text('verdict = "split pending"', 'seam = "s"'), id="missing-ceiling"
        ),
        pytest.param(
            SYNTHETIC_HEADER + _row_text("ceiling = true", 'verdict = "split pending"', 'seam = "s"'), id="boolean-ceiling"
        ),
    ],
)
def test_size_report_of_a_table_with_a_decode_or_schema_problem_is_the_fixed_table_problem_line(table_text):
    assert size_report({"a.py": 1500}, table_text.encode()) == TABLE_PROBLEM_LINE


def test_size_report_over_a_layout_only_difference_still_reports_a_mismatched_row():
    table_text = SYNTHETIC_HEADER + CANONICAL_ROW_A.replace("1001", "1001 # note")

    report = size_report({"a.py": 1500}, table_text.encode())

    assert report is not None
    assert "a.py: 1500 lines" in report
    assert "Write ceiling = 1500." in report


def test_size_report_over_a_layout_only_difference_with_matching_counts_is_none():
    table_text = SYNTHETIC_HEADER + CANONICAL_ROW_A.replace("1001", "1001 # note")

    assert size_report({"a.py": 1001}, table_text.encode()) is None


def test_size_report_over_canonical_text_with_matching_counts_is_none():
    table_text = SYNTHETIC_HEADER + CANONICAL_ROW_A + "\n" + CANONICAL_ROW_B

    assert size_report({"a.py": 1001, "b.py": 1002, "small.py": 10}, table_text.encode()) is None


def test_size_report_over_canonical_text_with_one_mismatched_row_names_it_and_its_value():
    table_text = SYNTHETIC_HEADER + CANONICAL_ROW_A + "\n" + CANONICAL_ROW_B

    report = size_report({"a.py": 1001, "b.py": 1003}, table_text.encode())

    assert report is not None
    assert "b.py: 1003 lines" in report
    assert "Write ceiling = 1003." in report
    assert "a.py: 1001 lines" not in report


# --- fail_with_report ------------------------------------------------------------------------------------------


def test_fail_with_report_raises_with_exactly_the_report_and_no_python_trace():
    with pytest.raises(pytest.fail.Exception) as raised:
        fail_with_report("first line\nsecond line")

    assert raised.value.msg == "first line\nsecond line"
    assert raised.value.pytrace is False


def test_fail_with_report_returns_on_none():
    assert fail_with_report(None) is None
