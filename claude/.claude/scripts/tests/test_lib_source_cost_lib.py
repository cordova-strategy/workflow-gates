"""Direct unit tests for scripts/dev/_lib-source-cost-lib.sh.

Each case sources the lib under `set -euo pipefail` in `bash -c` and feeds it
fixed input, so none of them times anything. The anchors, labels and file
contents are synthetic: no case names a function of the real shell libraries.
"""
from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path

import pytest
from helpers import REPO_ROOT

from .conftest import _clean_env

_LIB_UNDER_TEST = REPO_ROOT / "scripts" / "dev" / "_lib-source-cost-lib.sh"


def _run_bash(script_body: str) -> subprocess.CompletedProcess:
    """Source the lib, then run script_body under `set -euo pipefail`.

    A bare call that returns nonzero aborts the shell with that status, which
    is how the stop cases observe their exit code.
    """
    full_script = f"set -euo pipefail\n. {shlex.quote(str(_LIB_UNDER_TEST))}\n{script_body}\n"
    return subprocess.run(
        ["bash", "-c", full_script],
        capture_output=True,
        text=True,
        check=False,
        env=_clean_env(BASH_ENV=None, ENV=None),
    )


def _stdout_lines(result: subprocess.CompletedProcess) -> list[str]:
    assert result.returncode == 0, result.stderr
    return result.stdout.splitlines()


def _assert_stop(result: subprocess.CompletedProcess, stage: str, *fragments: str) -> None:
    """A stop exits 1, prints nothing on stdout and one `lib-source-cost: <stage>:` line on stderr."""
    assert result.returncode == 1, result.stderr
    assert result.stdout == ""
    stop_lines = [line for line in result.stderr.splitlines() if line.startswith(f"lib-source-cost: {stage}:")]
    assert stop_lines, result.stderr
    for fragment in fragments:
        assert fragment in result.stderr


# The synthetic pair of measured files. Line numbers below are pinned by the cases.
_SYNTHETIC_LIB_LINES = [
    "# synthetic lib",  # 1
    '. "${BASH_SOURCE[0]%/*}/_config.sh"',  # 2
    "alpha_one() {",  # 3
    "  echo one",  # 4
    "}",  # 5
    "",  # 6
    "alpha_two() (",  # 7
    "  echo two",  # 8
    ")",  # 9
    "",  # 10
    "beta_one() {",  # 11
    "  echo beta",  # 12
    "}",  # 13
]
_SYNTHETIC_CONFIG_LINES = [
    "gamma_one() {",  # 1
    "  echo g1",  # 2
    "}",  # 3
    "gamma_two() {",  # 4
    "  echo g2",  # 5
    "}",  # 6
]
_SYNTHETIC_ROWS = "\n".join(
    [
        "1|first|_lib.sh|alpha_one|alpha_two",
        "2|second|_config.sh|gamma_one|gamma_two",
        "3|third|_lib.sh|beta_one|beta_one",
    ]
)
_SYNTHETIC_SPANS = "\n".join(
    [
        "1|first|_lib.sh|3|9|7|2",
        "2|second|_config.sh|1|6|6|2",
        "3|third|_lib.sh|11|13|3|1",
    ]
)


def _write_lines(path: Path, lines: list[str]) -> None:
    path.write_text("".join(f"{line}\n" for line in lines))


def _make_source_dir(
    directory: Path,
    lib_lines: list[str] | None = None,
    config_lines: list[str] | None = None,
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    _write_lines(directory / "_lib.sh", _SYNTHETIC_LIB_LINES if lib_lines is None else lib_lines)
    _write_lines(directory / "_config.sh", _SYNTHETIC_CONFIG_LINES if config_lines is None else config_lines)
    (directory / "config-keys.psv").write_text("# synthetic schema\n")
    return directory


# ---------------------------------------------------------------------------
# Flag values
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["0", "01", "x", "", "-3", "1.5", "1234567890"])
def test_flag_value_rejected_as_a_count(value):
    result = _run_bash(f"lsc_flag_value_ok {shlex.quote(value)}")

    assert result.returncode == 1


@pytest.mark.parametrize("value", ["1", "2", "200", "123456789"])
def test_flag_value_accepted_as_an_iteration_count(value):
    result = _run_bash(f"lsc_flag_value_ok {shlex.quote(value)}")

    assert result.returncode == 0


def test_flag_value_of_one_fails_the_repetition_minimum_of_two():
    result = _run_bash("lsc_flag_value_ok 1 2")

    assert result.returncode == 1


def test_flag_value_of_two_meets_the_repetition_minimum_of_two():
    result = _run_bash("lsc_flag_value_ok 2 2")

    assert result.returncode == 0


# ---------------------------------------------------------------------------
# Cluster file
# ---------------------------------------------------------------------------


def test_parse_clusters_keeps_row_order_and_skips_comments_and_blank_lines(tmp_path):
    cluster_file = tmp_path / "clusters.psv"
    _write_lines(
        cluster_file,
        [
            "# comment",
            "alpha|_lib.sh|alpha_one|alpha_two",
            "",
            "beta|_config.sh|gamma_one|gamma_two",
            "alpha|_lib.sh|beta_one|beta_one",
        ],
    )

    result = _run_bash(f"lsc_parse_clusters {shlex.quote(str(cluster_file))}")

    assert _stdout_lines(result) == [
        "2|alpha|_lib.sh|alpha_one|alpha_two",
        "4|beta|_config.sh|gamma_one|gamma_two",
        "5|alpha|_lib.sh|beta_one|beta_one",
    ]


@pytest.mark.parametrize(
    "invalid_row",
    [
        "alpha|_lib.sh|alpha_one",
        "alpha|_lib.sh|alpha_one|alpha_two|extra",
        "alpha||alpha_one|alpha_two",
        "alpha|_lib.sh|alpha_one|",
        "alpha|other.sh|alpha_one|alpha_two",
        "Bad_Label|_lib.sh|alpha_one|alpha_two",
        "alpha|_lib.sh|alpha one|alpha_two",
        "alpha|_lib.sh|alpha_one|alpha two",
    ],
    ids=[
        "three-fields",
        "five-fields",
        "empty-field",
        "trailing-empty-field",
        "unknown-file",
        "bad-label",
        "function-name-with-space",
        "last-function-name-with-space",
    ],
)
def test_parse_clusters_stops_on_an_invalid_row_naming_its_line(tmp_path, invalid_row):
    cluster_file = tmp_path / "clusters.psv"
    _write_lines(cluster_file, ["# comment", invalid_row])

    result = _run_bash(f"lsc_parse_clusters {shlex.quote(str(cluster_file))}")

    _assert_stop(result, "cluster-file", f"{cluster_file}:2:")


def test_parse_clusters_returns_an_unterminated_last_row_and_skips_whitespace_only_lines(tmp_path):
    cluster_file = tmp_path / "clusters.psv"
    cluster_file.write_text("# comment\n \t \nalpha|_lib.sh|alpha_one|alpha_two\nbeta|_config.sh|gamma_one|gamma_two")

    result = _run_bash(f"lsc_parse_clusters {shlex.quote(str(cluster_file))}")

    assert _stdout_lines(result) == [
        "3|alpha|_lib.sh|alpha_one|alpha_two",
        "4|beta|_config.sh|gamma_one|gamma_two",
    ]


def test_parse_clusters_stops_when_the_file_holds_no_rows(tmp_path):
    cluster_file = tmp_path / "clusters.psv"
    _write_lines(cluster_file, ["# comment", ""])

    result = _run_bash(f"lsc_parse_clusters {shlex.quote(str(cluster_file))}")

    _assert_stop(result, "cluster-file", "no rows")


def test_parse_clusters_stops_when_the_file_is_missing(tmp_path):
    missing_file = tmp_path / "absent.psv"

    result = _run_bash(f"lsc_parse_clusters {shlex.quote(str(missing_file))}")

    _assert_stop(result, "cluster-file", "cannot read")


# ---------------------------------------------------------------------------
# Start-line lookup
# ---------------------------------------------------------------------------


def _lookup(source_dir: Path, rows: str) -> subprocess.CompletedProcess:
    return _run_bash(f"lsc_lookup_starts {shlex.quote(str(source_dir))} {shlex.quote(rows)}")


def test_lookup_reports_each_anchors_start_line_and_file(tmp_path):
    source_dir = _make_source_dir(tmp_path / "src")

    result = _lookup(source_dir, _SYNTHETIC_ROWS)

    assert _stdout_lines(result) == [
        "alpha_one 3 _lib.sh",
        "alpha_two 7 _lib.sh",
        "gamma_one 1 _config.sh",
        "gamma_two 4 _config.sh",
        "beta_one 11 _lib.sh",
    ]


def test_lookup_reports_a_name_defined_twice_at_its_later_line(tmp_path):
    source_dir = _make_source_dir(tmp_path / "src", lib_lines=[*_SYNTHETIC_LIB_LINES, "beta_one() (", "  echo again", ")"])

    result = _lookup(source_dir, "1|dup|_lib.sh|beta_one|beta_one")

    assert _stdout_lines(result) == ["beta_one 14 _lib.sh"]


def test_lookup_resolves_anchors_when_the_source_returns_one_after_defining_them(tmp_path):
    source_dir = _make_source_dir(tmp_path / "src", lib_lines=[*_SYNTHETIC_LIB_LINES, "return 1"])

    result = _lookup(source_dir, _SYNTHETIC_ROWS)

    assert _stdout_lines(result)[0] == "alpha_one 3 _lib.sh"


def test_lookup_ignores_output_the_source_prints(tmp_path):
    source_dir = _make_source_dir(
        tmp_path / "src",
        lib_lines=["echo noise; echo noise >&2", *_SYNTHETIC_LIB_LINES],
    )

    result = _lookup(source_dir, "1|first|_lib.sh|alpha_one|alpha_one")

    assert _stdout_lines(result) == ["alpha_one 4 _lib.sh"]
    assert result.stderr == ""


def test_lookup_runs_the_child_with_dollar_zero_set_to_lookup(tmp_path):
    marker = tmp_path / "zero-arg"
    source_dir = _make_source_dir(
        tmp_path / "src",
        lib_lines=[f'printf "%s" "$0" > {shlex.quote(str(marker))}', *_SYNTHETIC_LIB_LINES],
    )

    _lookup(source_dir, "1|first|_lib.sh|alpha_one|alpha_one")

    assert marker.read_text() == "lookup"


def test_lookup_stops_on_an_undefined_anchor(tmp_path):
    source_dir = _make_source_dir(tmp_path / "src")

    result = _lookup(source_dir, "7|first|_lib.sh|alpha_one|absent_fn")

    _assert_stop(result, "lookup", "PSV line 7", "absent_fn")


def test_lookup_stops_on_an_anchor_defined_in_the_other_file(tmp_path):
    source_dir = _make_source_dir(tmp_path / "src")

    result = _lookup(source_dir, "5|first|_config.sh|alpha_one|gamma_two")

    _assert_stop(result, "lookup", "PSV line 5", "alpha_one", "_lib.sh")


@pytest.mark.parametrize("broken_file", ["_lib.sh", "_config.sh"])
def test_resolve_spans_stops_on_a_syntax_error_between_a_rows_anchors_before_any_lookup(tmp_path, broken_file):
    """The error sits after the first anchor, so a lookup run first would report the second one as undefined."""
    broken_lines = {
        "_lib.sh": [*_SYNTHETIC_LIB_LINES[:5], "if then", *_SYNTHETIC_LIB_LINES[5:]],
        "_config.sh": [*_SYNTHETIC_CONFIG_LINES[:3], "if then", *_SYNTHETIC_CONFIG_LINES[3:]],
    }
    source_dir = _make_source_dir(
        tmp_path / "src",
        lib_lines=broken_lines["_lib.sh"] if broken_file == "_lib.sh" else None,
        config_lines=broken_lines["_config.sh"] if broken_file == "_config.sh" else None,
    )

    result = _run_bash(f"lsc_resolve_spans {shlex.quote(str(source_dir))} {shlex.quote(_SYNTHETIC_ROWS)}")

    _assert_stop(result, "syntax")
    stderr_lines = result.stderr.splitlines()
    assert stderr_lines[0].startswith(f"lib-source-cost: syntax: {broken_file}:"), result.stderr
    assert [line for line in stderr_lines if line.startswith("lib-source-cost: lookup:")] == []


# ---------------------------------------------------------------------------
# Span resolution
# ---------------------------------------------------------------------------

_SPAN_FILE_LINES = [
    "# header",  # 1
    "keep_one() {",  # 2
    "  :",  # 3
    "}",  # 4
    "first_fn() {",  # 5
    "  echo a",  # 6
    "}",  # 7
    "",  # 8
    "middle_fn() {",  # 9
    "  echo m",  # 10
    "}",  # 11
    "last_fn() {",  # 12
    "  echo l",  # 13
    "}",  # 14
    "",  # 15
    "subshell_fn() (",  # 16
    "  echo s",  # 17
    ")",  # 18
    "keep_two() {",  # 19
    "  :",  # 20
    "}",  # 21
]


def _resolve_span(
    tmp_path: Path,
    file_lines: list[str],
    first: str,
    first_start: int,
    last: str,
    last_start: int,
) -> subprocess.CompletedProcess:
    span_file = tmp_path / "span-file.sh"
    _write_lines(span_file, file_lines)
    return _run_bash(
        f"mapfile -t file_lines < {shlex.quote(str(span_file))}\n"
        f"lsc_resolve_span 4 file_lines {first} {first_start} {last} {last_start}"
    )


def test_index_definitions_lists_every_definition_line_by_name_and_in_file_order(tmp_path):
    span_file = tmp_path / "span-file.sh"
    _write_lines(span_file, [*_SPAN_FILE_LINES, "first_fn() (", "  :", ")", "  indented_fn() {", "not_a_definition {"])

    result = _run_bash(
        f"mapfile -t file_lines < {shlex.quote(str(span_file))}\n"
        "declare -A definitions_by_name=()\n"
        "declare -a all_definition_lines=()\n"
        "lsc_index_definitions file_lines definitions_by_name all_definition_lines\n"
        'echo "${definitions_by_name[first_fn]}|${definitions_by_name[subshell_fn]}|${#definitions_by_name[@]}"\n'
        'echo "${all_definition_lines[*]}"'
    )

    assert _stdout_lines(result) == ["5 22|16|6", "2 5 9 12 16 19 22"]


def _resolve_span_with_index_arguments(tmp_path: Path, index_arguments: str) -> subprocess.CompletedProcess:
    span_file = tmp_path / "span-file.sh"
    _write_lines(span_file, _SPAN_FILE_LINES)
    return _run_bash(
        f"mapfile -t file_lines < {shlex.quote(str(span_file))}\n"
        "declare -A lib_definitions=()\n"
        "declare -a lib_definition_lines=()\n"
        "lsc_index_definitions file_lines lib_definitions lib_definition_lines\n"
        f"lsc_resolve_span 4 file_lines first_fn 5 last_fn 12 {index_arguments}"
    )


def test_resolve_span_gives_the_same_row_with_a_callers_index_as_without_one(tmp_path):
    with_index = _resolve_span_with_index_arguments(tmp_path, "lib_definitions lib_definition_lines")
    without_index = _resolve_span(tmp_path, _SPAN_FILE_LINES, "first_fn", 5, "last_fn", 12)

    assert _stdout_lines(with_index) == _stdout_lines(without_index) == ["5|14|10|3"]
    assert with_index.stderr == ""


@pytest.mark.parametrize(
    "index_arguments",
    ["lib_definitions", "''  lib_definition_lines"],
    ids=["by-name-array-only", "all-lines-array-only"],
)
def test_resolve_span_stops_when_only_one_index_array_is_passed(tmp_path, index_arguments):
    result = _resolve_span_with_index_arguments(tmp_path, index_arguments)

    _assert_stop(result, "span", "PSV line 4", "both index arrays")


def test_resolve_span_covers_several_functions_through_the_last_closer(tmp_path):
    result = _resolve_span(tmp_path, _SPAN_FILE_LINES, "first_fn", 5, "last_fn", 12)

    assert _stdout_lines(result) == ["5|14|10|3"]


def test_resolve_span_ends_a_subshell_function_at_a_closing_parenthesis(tmp_path):
    result = _resolve_span(tmp_path, _SPAN_FILE_LINES, "subshell_fn", 16, "subshell_fn", 16)

    assert _stdout_lines(result) == ["16|18|3|1"]


def test_resolve_span_of_one_brace_function_counts_that_function_only(tmp_path):
    result = _resolve_span(tmp_path, _SPAN_FILE_LINES, "first_fn", 5, "first_fn", 5)

    assert _stdout_lines(result) == ["5|7|3|1"]


def test_resolve_span_stops_when_an_anchor_has_no_definition_line(tmp_path):
    result = _resolve_span(tmp_path, _SPAN_FILE_LINES, "first_fn", 5, "absent_fn", 12)

    _assert_stop(result, "span", "PSV line 4", "absent_fn has 0 definition lines")


def test_resolve_span_stops_when_an_anchor_has_several_definition_lines(tmp_path):
    duplicated = [*_SPAN_FILE_LINES, "first_fn() {", "  :", "}"]

    result = _resolve_span(tmp_path, duplicated, "first_fn", 5, "last_fn", 12)

    _assert_stop(result, "span", "first_fn has 2 definition lines")


def test_resolve_span_stops_when_the_definition_line_differs_from_the_one_bash_reported(tmp_path):
    result = _resolve_span(tmp_path, _SPAN_FILE_LINES, "first_fn", 9, "last_fn", 12)

    _assert_stop(result, "span", "first_fn is defined at line 5 but bash reports line 9")


def test_resolve_span_stops_when_the_last_definition_line_differs_from_the_one_bash_reported(tmp_path):
    result = _resolve_span(tmp_path, _SPAN_FILE_LINES, "first_fn", 5, "last_fn", 9)

    _assert_stop(result, "span", "last_fn is defined at line 12 but bash reports line 9")


def test_resolve_span_stops_when_the_last_function_is_defined_before_the_first(tmp_path):
    result = _resolve_span(tmp_path, _SPAN_FILE_LINES, "last_fn", 12, "first_fn", 5)

    _assert_stop(result, "span", "first_fn is defined before last_fn")


def test_resolve_span_stops_when_no_closer_follows_the_last_function(tmp_path):
    result = _resolve_span(tmp_path, ["open_fn() {", "  echo no closer"], "open_fn", 1, "open_fn", 1)

    _assert_stop(result, "span", "no closer after open_fn at line 1")


def test_resolve_span_stops_when_the_closer_rule_overruns_into_another_definition(tmp_path):
    indented_closer = ["open_fn() {", "  echo", "  }", "next_fn() {", "  :", "}"]

    result = _resolve_span(tmp_path, indented_closer, "open_fn", 1, "open_fn", 1)

    _assert_stop(result, "span", "next_fn is defined at line 4 between open_fn and its closer at line 6")


def test_check_span_overlap_accepts_adjacent_spans_and_spans_in_different_files():
    result = _run_bash(
        "lsc_check_span_overlap '1|a|_lib.sh|3|9|7|2\n2|b|_lib.sh|10|12|3|1\n3|c|_config.sh|3|9|7|2'"
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "overlapping_spans",
    [
        "1|a|_lib.sh|3|9|7|2\n2|b|_lib.sh|9|12|4|1",
        "1|a|_lib.sh|3|20|18|4\n2|b|_lib.sh|5|8|4|1",
        "1|a|_lib.sh|3|9|7|2\n2|b|_lib.sh|3|9|7|2",
    ],
    ids=["shared-last-line", "nested", "repeated-row"],
)
def test_check_span_overlap_stops_naming_both_psv_lines(overlapping_spans):
    result = _run_bash(f"lsc_check_span_overlap {shlex.quote(overlapping_spans)}")

    _assert_stop(result, "span", "PSV lines 1 and 2", "_lib.sh")


def test_resolve_spans_prints_one_span_per_row_in_row_order(tmp_path):
    source_dir = _make_source_dir(tmp_path / "src")

    result = _run_bash(f"lsc_resolve_spans {shlex.quote(str(source_dir))} {shlex.quote(_SYNTHETIC_ROWS)}")

    assert _stdout_lines(result) == _SYNTHETIC_SPANS.splitlines()


def test_resolve_spans_stops_on_a_repeated_row(tmp_path):
    source_dir = _make_source_dir(tmp_path / "src")
    repeated_rows = "1|a|_lib.sh|alpha_one|alpha_one\n2|b|_lib.sh|alpha_one|alpha_one"

    result = _run_bash(f"lsc_resolve_spans {shlex.quote(str(source_dir))} {shlex.quote(repeated_rows)}")

    _assert_stop(result, "span", "PSV lines 1 and 2")


# ---------------------------------------------------------------------------
# Arm edits
# ---------------------------------------------------------------------------


def _numbered_file(path: Path, count: int = 10) -> Path:
    _write_lines(path, [f"l{number}" for number in range(1, count + 1)])
    return path


def test_delete_spans_removes_a_non_contiguous_cluster(tmp_path):
    source_file = _numbered_file(tmp_path / "source.sh")
    dest_file = tmp_path / "dest.sh"

    result = _run_bash(f"lsc_delete_spans {shlex.quote(str(source_file))} {shlex.quote(str(dest_file))} 2-3 7-8")

    assert result.returncode == 0, result.stderr
    assert dest_file.read_text() == "l1\nl4\nl5\nl6\nl9\nl10\n"


def test_delete_spans_of_every_line_writes_an_empty_file(tmp_path):
    source_file = _numbered_file(tmp_path / "source.sh", count=3)
    dest_file = tmp_path / "dest.sh"

    result = _run_bash(f"lsc_delete_spans {shlex.quote(str(source_file))} {shlex.quote(str(dest_file))} 1-3")

    assert result.returncode == 0, result.stderr
    assert dest_file.read_bytes() == b""


def test_delete_spans_ends_a_last_line_that_lacks_a_newline_with_one(tmp_path):
    source_file = tmp_path / "source.sh"
    source_file.write_text("l1\nl2\nl3")
    dest_file = tmp_path / "dest.sh"

    result = _run_bash(f"lsc_delete_spans {shlex.quote(str(source_file))} {shlex.quote(str(dest_file))} 1-1")

    assert result.returncode == 0, result.stderr
    assert dest_file.read_text() == "l2\nl3\n"


def test_delete_spans_stops_on_a_malformed_range(tmp_path):
    source_file = _numbered_file(tmp_path / "source.sh")
    dest_file = tmp_path / "dest.sh"

    result = _run_bash(f"lsc_delete_spans {shlex.quote(str(source_file))} {shlex.quote(str(dest_file))} 3-x")

    _assert_stop(result, "arm", "bad range: 3-x")


def test_tail_cut_spans_moves_the_ranges_in_file_order_behind_a_bare_return(tmp_path):
    source_file = _numbered_file(tmp_path / "source.sh")
    dest_file = tmp_path / "dest.sh"

    result = _run_bash(f"lsc_tail_cut_spans {shlex.quote(str(source_file))} {shlex.quote(str(dest_file))} 7-8 2-3")

    assert result.returncode == 0, result.stderr
    assert dest_file.read_text() == "l1\nl4\nl5\nl6\nl9\nl10\nreturn 0\nl2\nl3\nl7\nl8\n"


# Lines a `while read` or `echo` rewrite would alter: backslashes, printf directives, padding, expansions and tabs.
# A bare `-n`, `-e` or `-E` line vanishes under `echo "$line"`, because echo takes it as an option.
_HOSTILE_LINES = [
    r"-n \back\slash\n",
    r"-e %s %d 100%",
    "-n",
    "-e",
    "-E",
    "   padded with spaces   ",
    "$HOME ${USER} $(date) `id`",
    "tab\there",
    r"\\ double \\",
]


def _hostile_file(path: Path) -> Path:
    path.write_bytes("".join(f"{line}\n" for line in _HOSTILE_LINES).encode())
    return path


def test_delete_spans_keeps_the_lines_it_leaves_byte_for_byte(tmp_path):
    source_file = _hostile_file(tmp_path / "source.sh")
    dest_file = tmp_path / "dest.sh"

    result = _run_bash(f"lsc_delete_spans {shlex.quote(str(source_file))} {shlex.quote(str(dest_file))} 8-9")

    assert result.returncode == 0, result.stderr
    assert dest_file.read_bytes() == "".join(f"{line}\n" for line in _HOSTILE_LINES[:7]).encode()


def test_tail_cut_spans_keeps_and_moves_lines_byte_for_byte(tmp_path):
    source_file = _hostile_file(tmp_path / "source.sh")
    dest_file = tmp_path / "dest.sh"

    result = _run_bash(f"lsc_tail_cut_spans {shlex.quote(str(source_file))} {shlex.quote(str(dest_file))} 3-4")

    assert result.returncode == 0, result.stderr
    kept = [*_HOSTILE_LINES[:2], *_HOSTILE_LINES[4:]]
    moved = _HOSTILE_LINES[2:4]
    assert dest_file.read_bytes() == "".join(f"{line}\n" for line in [*kept, "return 0", *moved]).encode()


def test_write_light_arm_writes_the_exact_one_line_dirname_files(tmp_path):
    results = {
        label: _run_bash(f"lsc_write_light_arm {label} {shlex.quote(str(tmp_path / label))}")
        for label in ("baseline", "dirname-fork", "param-expansion")
    }

    assert all(result.returncode == 0 for result in results.values())
    assert (tmp_path / "baseline").read_bytes() == b""
    assert (tmp_path / "dirname-fork").read_text() == 'arm_directory="$(dirname "${BASH_SOURCE[0]}")"\n'
    assert (tmp_path / "param-expansion").read_text() == 'arm_directory="${BASH_SOURCE[0]%/*}"\n'


def test_sourcing_each_dirname_arm_forks_dirname_only_for_dirname_fork_and_assigns_the_same_directory(tmp_path):
    real_dirname = shutil.which("dirname")
    assert real_dirname is not None
    arm_dir = tmp_path / "arms"
    arm_dir.mkdir()
    stub_dir = tmp_path / "stub"
    stub_dir.mkdir()
    call_log = tmp_path / "dirname-calls.log"
    logging_dirname = stub_dir / "dirname"
    logging_dirname.write_text(f'#!/bin/sh\necho called >> {shlex.quote(str(call_log))}\nexec {shlex.quote(real_dirname)} "$@"\n')
    logging_dirname.chmod(0o755)

    assigned_directory = {}
    call_counts = {}
    for label in ("baseline", "dirname-fork", "param-expansion"):
        arm_file = shlex.quote(str(arm_dir / label))
        call_log.write_text("")
        result = _run_bash(
            f'lsc_write_light_arm {label} {arm_file}; PATH={shlex.quote(str(stub_dir))}:"$PATH"; '
            f'. {arm_file}; printf "%s" "${{arm_directory-}}"'
        )
        assert result.returncode == 0, result.stderr
        assigned_directory[label] = result.stdout
        call_counts[label] = len(call_log.read_text().splitlines())

    assert call_counts == {"baseline": 0, "dirname-fork": 1, "param-expansion": 0}
    assert assigned_directory == {"baseline": "", "dirname-fork": str(arm_dir), "param-expansion": str(arm_dir)}


def test_write_light_arm_stops_on_a_heavy_label(tmp_path):
    result = _run_bash(f"lsc_write_light_arm full {shlex.quote(str(tmp_path / 'entry.sh'))}")

    _assert_stop(result, "arm", "not a light arm: full")


def _build_arm(tmp_path: Path, label: str) -> tuple[subprocess.CompletedProcess, Path, Path]:
    source_dir = _make_source_dir(tmp_path / "src")
    arm_dir = tmp_path / "arms" / label
    result = _run_bash(
        f"lsc_build_arm {shlex.quote(label)} {shlex.quote(_SYNTHETIC_SPANS)} "
        f"{shlex.quote(str(source_dir))} {shlex.quote(str(arm_dir))}"
    )
    return result, source_dir, arm_dir


@pytest.mark.parametrize("label", ["full", "control"])
def test_build_arm_of_an_unedited_arm_copies_all_three_files_byte_for_byte(tmp_path, label):
    result, source_dir, arm_dir = _build_arm(tmp_path, label)

    assert result.returncode == 0, result.stderr
    for name in ("_lib.sh", "_config.sh", "config-keys.psv"):
        assert (arm_dir / name).read_bytes() == (source_dir / name).read_bytes()


def test_build_arm_of_one_cluster_edits_only_the_file_that_holds_its_spans(tmp_path):
    result, source_dir, arm_dir = _build_arm(tmp_path, "minus-second")

    assert result.returncode == 0, result.stderr
    assert (arm_dir / "_lib.sh").read_bytes() == (source_dir / "_lib.sh").read_bytes()
    assert (arm_dir / "_config.sh").read_bytes() == b""
    assert (arm_dir / "config-keys.psv").read_bytes() == (source_dir / "config-keys.psv").read_bytes()


def test_build_arm_of_a_cluster_deletes_its_spans_from_the_sourcing_file(tmp_path):
    result, _, arm_dir = _build_arm(tmp_path, "minus-first")

    assert result.returncode == 0, result.stderr
    assert (arm_dir / "_lib.sh").read_text().splitlines() == [
        *_SYNTHETIC_LIB_LINES[:2],
        *_SYNTHETIC_LIB_LINES[9:],
    ]
    assert (arm_dir / "_config.sh").read_text().splitlines() == _SYNTHETIC_CONFIG_LINES


def test_build_arm_of_total_deletion_deletes_every_span_from_both_files(tmp_path):
    result, _, arm_dir = _build_arm(tmp_path, "total-deletion")

    assert result.returncode == 0, result.stderr
    assert (arm_dir / "_lib.sh").read_text().splitlines() == ["# synthetic lib", _SYNTHETIC_LIB_LINES[1], ""]
    assert (arm_dir / "_config.sh").read_bytes() == b""


def test_build_arm_of_the_tail_cut_moves_the_same_spans_that_total_deletion_deletes(tmp_path):
    result, _, arm_dir = _build_arm(tmp_path, "tail-cut")

    assert result.returncode == 0, result.stderr
    assert (arm_dir / "_lib.sh").read_text().splitlines() == [
        "# synthetic lib",
        _SYNTHETIC_LIB_LINES[1],
        "",
        "return 0",
        *_SYNTHETIC_LIB_LINES[2:9],
        *_SYNTHETIC_LIB_LINES[10:],
    ]
    assert (arm_dir / "_config.sh").read_text().splitlines() == ["return 0", *_SYNTHETIC_CONFIG_LINES]


def _status_of_a_call_with_errexit_off(call: str) -> subprocess.CompletedProcess:
    """Run `call` the way the script does, under `|| status=$?`, where -e is off inside the callee."""
    return _run_bash(f'status=0\n{call} || status=$?\necho "$status"')


def test_copy_measured_files_returns_one_at_the_first_missing_file_and_copies_nothing_after_it(tmp_path):
    source_dir = _make_source_dir(tmp_path / "src")
    (source_dir / "_config.sh").unlink()
    dest_dir = tmp_path / "dest"

    result = _status_of_a_call_with_errexit_off(
        f"lsc_copy_measured_files {shlex.quote(str(source_dir))} {shlex.quote(str(dest_dir))}"
    )

    assert _stdout_lines(result) == ["1"]
    assert sorted(path.name for path in dest_dir.iterdir()) == ["_lib.sh"]


def test_copy_measured_files_returns_one_when_the_destination_cannot_be_created(tmp_path):
    source_dir = _make_source_dir(tmp_path / "src")
    blocker = tmp_path / "blocker"
    blocker.write_text("a file, not a directory")

    result = _status_of_a_call_with_errexit_off(
        f"lsc_copy_measured_files {shlex.quote(str(source_dir))} {shlex.quote(str(blocker / 'dest'))}"
    )

    assert _stdout_lines(result) == ["1"]


@pytest.mark.parametrize("label", ["full", "control", "minus-first", "total-deletion", "tail-cut"])
def test_build_arm_returns_one_when_a_measured_file_is_missing_from_the_source(tmp_path, label):
    source_dir = _make_source_dir(tmp_path / "src")
    (source_dir / "_config.sh").unlink()

    result = _status_of_a_call_with_errexit_off(
        f"lsc_build_arm {shlex.quote(label)} {shlex.quote(_SYNTHETIC_SPANS)} "
        f"{shlex.quote(str(source_dir))} {shlex.quote(str(tmp_path / 'arm'))}"
    )

    assert _stdout_lines(result) == ["1"]


@pytest.mark.parametrize("label", ["full", "minus-first", "baseline"])
def test_build_arm_returns_one_when_the_arm_directory_cannot_be_created(tmp_path, label):
    source_dir = _make_source_dir(tmp_path / "src")
    blocker = tmp_path / "blocker"
    blocker.write_text("a file, not a directory")

    result = _status_of_a_call_with_errexit_off(
        f"lsc_build_arm {shlex.quote(label)} {shlex.quote(_SYNTHETIC_SPANS)} "
        f"{shlex.quote(str(source_dir))} {shlex.quote(str(blocker / 'arm'))}"
    )

    assert _stdout_lines(result) == ["1"]


@pytest.mark.parametrize("label", ["baseline", "dirname-fork", "param-expansion"])
def test_build_arm_of_a_light_arm_writes_only_its_entry_file(tmp_path, label):
    result, _, arm_dir = _build_arm(tmp_path, label)

    assert result.returncode == 0, result.stderr
    assert [path.name for path in arm_dir.iterdir()] == ["entry.sh"]


def test_build_arm_stops_on_a_cluster_with_no_spans(tmp_path):
    result, _, _ = _build_arm(tmp_path, "minus-absent")

    _assert_stop(result, "arm", "minus-absent removes no spans")


def test_build_arm_stops_on_an_unknown_label(tmp_path):
    result, _, _ = _build_arm(tmp_path, "sideways")

    _assert_stop(result, "arm", "unknown arm label: sideways")


# ---------------------------------------------------------------------------
# Arm list, references and rotation
# ---------------------------------------------------------------------------

_TWO_CLUSTER_SPANS = "\n".join(
    [
        "1|split|_lib.sh|3|9|7|2",
        "2|cfg|_config.sh|1|6|6|2",
        "3|split|_lib.sh|11|13|3|1",
    ]
)
_TWO_CLUSTER_LABELS = [
    "full",
    "minus-split",
    "minus-cfg",
    "total-deletion",
    "tail-cut",
    "control",
    "baseline",
    "dirname-fork",
    "param-expansion",
]


def test_arm_labels_lists_each_cluster_once_in_order_of_its_first_row():
    result = _run_bash(f"lsc_arm_labels {shlex.quote(_TWO_CLUSTER_SPANS)}")

    assert _stdout_lines(result) == _TWO_CLUSTER_LABELS


@pytest.mark.parametrize(
    ("label", "reference", "kind"),
    [
        ("full", "baseline", "cost"),
        ("minus-split", "full", "saving"),
        ("total-deletion", "full", "saving"),
        ("tail-cut", "full", "saving"),
        ("control", "full", "saving"),
        ("baseline", "", "none"),
        ("dirname-fork", "baseline", "cost"),
        ("param-expansion", "dirname-fork", "saving"),
    ],
)
def test_arm_reference_and_kind_of_every_fixed_arm(label, reference, kind):
    result = _run_bash(f"lsc_arm_reference {label}\nlsc_arm_kind {label}")

    assert _stdout_lines(result) == [reference, kind]


@pytest.mark.parametrize("function", ["lsc_arm_reference", "lsc_arm_kind", "lsc_arm_entry"])
def test_arm_functions_stop_on_an_unknown_label(function):
    result = _run_bash(f"{function} sideways")

    _assert_stop(result, "arm", "unknown arm label: sideways")


@pytest.mark.parametrize(
    ("label", "entry"),
    [
        ("full", "_lib.sh"),
        ("minus-split", "_lib.sh"),
        ("tail-cut", "_lib.sh"),
        ("baseline", "entry.sh"),
        ("dirname-fork", "entry.sh"),
        ("param-expansion", "entry.sh"),
    ],
)
def test_arm_entry_is_the_file_the_arms_child_sources(label, entry):
    result = _run_bash(f"lsc_arm_entry {label}")

    assert _stdout_lines(result) == [entry]


def test_arm_ranges_lists_a_clusters_spans_in_one_file_in_span_order():
    result = _run_bash(
        f"lsc_arm_ranges {shlex.quote(_TWO_CLUSTER_SPANS)} _lib.sh split\n"
        f"lsc_arm_ranges {shlex.quote(_TWO_CLUSTER_SPANS)} _lib.sh\n"
        f"lsc_arm_ranges {shlex.quote(_TWO_CLUSTER_SPANS)} _config.sh split"
    )

    assert _stdout_lines(result) == ["3-9", "11-13", "3-9", "11-13"]


@pytest.mark.parametrize(
    ("round_number", "expected"),
    [
        (0, "0 1 2 3 4 5 6 7 8"),
        (1, "1 2 3 4 5 6 7 8 0"),
        (9, "0 1 2 3 4 5 6 7 8"),
        (13, "4 5 6 7 8 0 1 2 3"),
    ],
)
def test_rotated_indexes_start_at_the_round_modulo_the_arm_count(round_number, expected):
    result = _run_bash(f"lsc_rotated_indexes {round_number} 9")

    assert _stdout_lines(result) == [expected]


def test_rotated_indexes_stop_on_an_empty_arm_list():
    result = _run_bash("lsc_rotated_indexes 3 0")

    _assert_stop(result, "rotation")


@pytest.mark.parametrize(
    ("round_number", "iterations", "repetition"),
    [(0, 2, 1), (1, 2, 1), (2, 2, 2), (3, 2, 2), (0, 200, 1), (199, 200, 1), (200, 200, 2), (599, 200, 3)],
)
def test_round_repetition_counts_rounds_from_zero_and_repetitions_from_one(round_number, iterations, repetition):
    result = _run_bash(f"lsc_round_repetition {round_number} {iterations}")

    assert _stdout_lines(result) == [str(repetition)]


# ---------------------------------------------------------------------------
# Per-repetition minimum fold
# ---------------------------------------------------------------------------


def test_fold_keeps_the_smallest_sample_per_repetition_and_never_carries_one_across():
    """Samples 900, 700, 800 and 850 over four rounds at 2 iterations give minimums 700 and 800.

    A fold that never resets would read 700 and 700, and one keyed by round
    modulo repetitions would read 800 and 700.
    """
    result = _run_bash(
        "declare -A sample_minimums=()\n"
        "round=0\n"
        "for micros in 900 700 800 850; do\n"
        '  lsc_fold_sample sample_minimums 4 "$(lsc_round_repetition "$round" 2)" "$micros"\n'
        "  round=$((round + 1))\n"
        "done\n"
        "lsc_fold_sample sample_minimums 1 1 5000\n"
        "minimums=$(lsc_arm_minimums sample_minimums 4 2)\n"
        "echo \"$minimums\"\n"
        "read -r -a values <<<\"$minimums\"\n"
        'lsc_figure "${values[@]}"\n'
        'lsc_spread "${values[@]}"\n'
        "lsc_arm_minimums sample_minimums 1 1"
    )

    assert _stdout_lines(result) == ["700 800", "700", "100", "5000"]


def test_arm_minimums_stop_when_a_repetition_has_no_sample():
    result = _run_bash(
        "declare -A sample_minimums=()\n"
        "lsc_fold_sample sample_minimums 0 1 10\n"
        "lsc_arm_minimums sample_minimums 0 2"
    )

    _assert_stop(result, "fold", "arm 0 has no sample in repetition 2")


def test_figure_and_spread_of_a_single_value():
    result = _run_bash("lsc_figure 42\nlsc_spread 42")

    assert _stdout_lines(result) == ["42", "0"]


# ---------------------------------------------------------------------------
# Arithmetic
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("micros", "signed", "unsigned"),
    [
        (-848, "-0.848", "-0.848"),
        (-1000, "-1.000", "-1.000"),
        (0, "+0.000", "0.000"),
        (1, "+0.001", "0.001"),
        (123456, "+123.456", "123.456"),
    ],
)
def test_format_ms_signs_and_pads_to_three_decimals(micros, signed, unsigned):
    result = _run_bash(f"lsc_format_ms {micros} signed\nlsc_format_ms {micros} unsigned")

    assert _stdout_lines(result) == [signed, unsigned]


def test_format_ms_stops_on_an_unknown_mode():
    result = _run_bash("lsc_format_ms 5 plain")

    _assert_stop(result, "format", "mode must be signed or unsigned")


@pytest.mark.parametrize(
    ("kind", "arm_figure", "reference_figure", "delta"),
    [
        ("cost", 5000, 2000, 3000),
        ("cost", 2000, 5000, -3000),
        ("saving", 2000, 5000, 3000),
        ("saving", 5000, 2000, -3000),
    ],
)
def test_delta_is_arm_minus_reference_for_a_cost_and_reference_minus_arm_for_a_saving(
    kind, arm_figure, reference_figure, delta
):
    result = _run_bash(f"lsc_delta_micros {kind} {arm_figure} {reference_figure}")

    assert _stdout_lines(result) == [str(delta)]


def test_delta_stops_on_an_unknown_kind():
    result = _run_bash("lsc_delta_micros gain 1 2")

    _assert_stop(result, "delta", "kind must be cost or saving")


@pytest.mark.parametrize(
    ("noise", "arm_spread", "reference_spread", "expected"),
    [
        (300, 100, 200, "300 baseline"),
        (300, 500, 200, "500 arm-label"),
        (300, 100, 700, "700 reference-label"),
        (300, 300, 200, "300 baseline"),
        (300, 500, 500, "500 arm-label"),
        (300, 100, 300, "300 baseline"),
    ],
    ids=["noise", "arm", "reference", "tie-with-noise", "tie-between-arm-and-reference", "reference-ties-noise"],
)
def test_applied_floor_is_the_largest_spread_and_names_its_owner_first_on_a_tie(
    noise, arm_spread, reference_spread, expected
):
    result = _run_bash(f"lsc_applied_floor {noise} arm-label {arm_spread} reference-label {reference_spread}")

    assert _stdout_lines(result) == [expected]


@pytest.mark.parametrize(
    ("delta", "floor", "verdict"),
    [
        (99, 100, "below"),
        (100, 100, "above"),
        (101, 100, "above"),
        (-99, 100, "below"),
        (-100, 100, "above"),
        (-101, 100, "above"),
        (0, 0, "above"),
    ],
)
def test_verdict_is_below_only_when_the_absolute_delta_is_under_the_floor(delta, floor, verdict):
    result = _run_bash(f"lsc_verdict {delta} {floor}")

    assert _stdout_lines(result) == [verdict]


# ---------------------------------------------------------------------------
# Report lines
# ---------------------------------------------------------------------------


def test_format_span_line_names_every_field():
    result = _run_bash("lsc_format_span_line '3|split|_lib.sh|5|14|10|3'")

    assert _stdout_lines(result) == ["span cluster=split file=_lib.sh lines=5-14 line_count=10 functions=3"]


def test_format_arm_line_of_baseline_carries_no_comparison_fields():
    result = _run_bash("lsc_format_arm_line baseline 700,800 700 100")

    assert _stdout_lines(result) == ["arm label=baseline mins_ms=0.700,0.800 figure_ms=0.700 spread_ms=0.100"]


def test_format_arm_line_of_a_cost_and_of_a_negative_saving():
    result = _run_bash(
        "lsc_format_arm_line full 61000,62000,60500 60500 1500 baseline cost 35000 1500 baseline above\n"
        "lsc_format_arm_line control 60400,60900 60400 500 full saving -848 1000 full below"
    )

    assert _stdout_lines(result) == [
        "arm label=full mins_ms=61.000,62.000,60.500 figure_ms=60.500 spread_ms=1.500 "
        "ref=baseline cost_ms=+35.000 floor_ms=1.500 floor_from=baseline verdict=above",
        "arm label=control mins_ms=60.400,60.900 figure_ms=60.400 spread_ms=0.500 "
        "ref=full saving_ms=-0.848 floor_ms=1.000 floor_from=full verdict=below",
    ]


def test_format_arm_line_stops_on_a_partial_comparison():
    result = _run_bash("lsc_format_arm_line full 1,2 1 1 baseline cost")

    _assert_stop(result, "format", "4 or 10 arguments")


_FOLDED_MINIMUMS = (
    "declare -A sample_minimums=()\n"
    "lsc_fold_sample sample_minimums 0 1 60000\n"
    "lsc_fold_sample sample_minimums 0 2 61000\n"
    "lsc_fold_sample sample_minimums 1 1 50000\n"
    "lsc_fold_sample sample_minimums 1 2 52000\n"
    "lsc_fold_sample sample_minimums 2 1 25000\n"
    "lsc_fold_sample sample_minimums 2 2 25300\n"
    "lsc_fold_sample sample_minimums 3 1 60400\n"
    "lsc_fold_sample sample_minimums 3 2 60900\n"
)


def test_report_arm_lines_compute_each_arm_against_its_reference_and_applied_floor():
    result = _run_bash(
        _FOLDED_MINIMUMS + "lsc_report_arm_lines sample_minimums 2 full minus-x baseline control"
    )

    assert _stdout_lines(result) == [
        "arm label=full mins_ms=60.000,61.000 figure_ms=60.000 spread_ms=1.000 "
        "ref=baseline cost_ms=+35.000 floor_ms=1.000 floor_from=full verdict=above",
        "arm label=minus-x mins_ms=50.000,52.000 figure_ms=50.000 spread_ms=2.000 "
        "ref=full saving_ms=+10.000 floor_ms=2.000 floor_from=minus-x verdict=above",
        "arm label=baseline mins_ms=25.000,25.300 figure_ms=25.000 spread_ms=0.300",
        "arm label=control mins_ms=60.400,60.900 figure_ms=60.400 spread_ms=0.500 "
        "ref=full saving_ms=-0.400 floor_ms=1.000 floor_from=full verdict=below",
    ]


def test_noise_floor_is_baselines_spread():
    result = _run_bash(_FOLDED_MINIMUMS + "lsc_noise_floor_micros sample_minimums 2 full minus-x baseline control")

    assert _stdout_lines(result) == ["300"]


def test_noise_floor_stops_when_no_arm_is_baseline():
    result = _run_bash(_FOLDED_MINIMUMS + "lsc_noise_floor_micros sample_minimums 2 full minus-x")

    _assert_stop(result, "report", "no arm labeled baseline")


def test_report_arm_lines_stop_when_no_arm_is_baseline():
    result = _run_bash(_FOLDED_MINIMUMS + "lsc_report_arm_lines sample_minimums 2 full minus-x")

    _assert_stop(result, "report", "no arm labeled baseline")


def test_report_arm_lines_stop_when_a_reference_arm_is_absent():
    result = _run_bash(_FOLDED_MINIMUMS + "lsc_report_arm_lines sample_minimums 2 baseline minus-x")

    _assert_stop(result, "report", "no arm labeled full, the reference of minus-x")
