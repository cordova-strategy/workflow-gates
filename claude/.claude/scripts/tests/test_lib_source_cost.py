"""Subprocess tests for scripts/dev/lib-source-cost.sh, one case per script branch.

The arithmetic, span resolution and arm edits are pinned by the direct tests of
the sourceable lib beside it. These cases run the real script against a fixture
checkout reached through the working directory, plus one run against this
checkout that pins every cluster-file anchor at HEAD. The fixture functions are
synthetic: no case names a function of the real shell libraries.
"""
from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest
from helpers import REPO_ROOT, installed_locale_where

from .conftest import _clean_env, _git, _init_repo

_SCRIPT = REPO_ROOT / "scripts" / "dev" / "lib-source-cost.sh"
_REAL_CLUSTER_FILE = REPO_ROOT / "scripts" / "dev" / "lib-source-cost-clusters.psv"

# Hang backstop, not a performance bound.
_RUN_TIMEOUT_SECONDS = 120

_SIGNED_MS = re.compile(r"^[+-][0-9]+\.[0-9]{3}$")
_UNSIGNED_MS = re.compile(r"^[0-9]+\.[0-9]{3}$")
_FIXED_ARM_LABELS = ["total-deletion", "tail-cut", "control", "baseline", "dirname-fork", "param-expansion"]

_FIXTURE_SOURCING_LINE = '. "${BASH_SOURCE[0]%/*}/_config.sh" || return 1'
# Appended to the fixture's sourced file outside every span: the first source of a directory
# exits 0 and creates a marker, and every later source of that directory returns 1.
_GUARD_THAT_FAILS_ON_THE_SECOND_SOURCE = (
    'if [[ -e "${BASH_SOURCE[0]%/*}/marker" ]]; then return 1; fi; : > "${BASH_SOURCE[0]%/*}/marker"'
)


def _script_env(**overrides: str | None) -> dict[str, str]:
    """_clean_env without any inherited startup file, so one that prints cannot reach an exact-output assertion."""
    return _clean_env(**{"BASH_ENV": None, "ENV": None, **overrides})


def _run_script(
    checkout: Path, *args: str, env: dict[str, str] | None = None, stdin_text: str | None = None
) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(_SCRIPT), *args],
        cwd=checkout,
        env=_script_env() if env is None else env,
        input=stdin_text,
        capture_output=True,
        text=True,
        check=False,
        timeout=_RUN_TIMEOUT_SECONDS,
    )


def _install_dirname_stub(stub_dir: Path) -> Path:
    """A `dirname` in stub_dir that runs the real one, so the header names a path the test controls."""
    real_dirname = shutil.which("dirname")
    assert real_dirname is not None
    stub_dir.mkdir(parents=True)
    stub = stub_dir / "dirname"
    stub.write_text(f'#!/bin/sh\nexec {shlex.quote(real_dirname)} "$@"\n')
    stub.chmod(0o755)
    return stub


def _path_led_by(directory: Path) -> str:
    return f"{directory}{os.pathsep}{os.environ['PATH']}"


def _hooks_dir(checkout: Path) -> Path:
    return checkout / "claude" / ".claude" / "hooks"


def _make_fixture_checkout(
    root: Path,
    sourced_lines: list[str],
    sourced_by_it_lines: list[str],
    cluster_rows: list[str],
) -> Path:
    """A repository with no commit that holds the three measured files and a cluster file."""
    _init_repo(root)
    hooks_dir = _hooks_dir(root)
    hooks_dir.mkdir(parents=True, exist_ok=True)
    (hooks_dir / "_lib.sh").write_text("".join(f"{line}\n" for line in sourced_lines))
    (hooks_dir / "_config.sh").write_text("".join(f"{line}\n" for line in sourced_by_it_lines))
    (hooks_dir / "config-keys.psv").write_text("")
    cluster_file = root / "scripts" / "dev" / "lib-source-cost-clusters.psv"
    cluster_file.parent.mkdir(parents=True, exist_ok=True)
    cluster_file.write_text("".join(f"{line}\n" for line in ["# fixture clusters", *cluster_rows]))
    return root


_PLAIN_SOURCED_LINES = [
    "# fixture",
    _FIXTURE_SOURCING_LINE,
    "plain_one() {",
    "  :",
    "}",
]
_PLAIN_SOURCED_BY_IT_LINES = [
    "plain_two() {",
    "  :",
    "}",
]
_PLAIN_CLUSTER_ROWS = [
    "solo|_lib.sh|plain_one|plain_one",
    "other|_config.sh|plain_two|plain_two",
]


def _make_plain_fixture(root: Path, extra_sourced_lines: list[str] | None = None) -> Path:
    return _make_fixture_checkout(
        root,
        [*_PLAIN_SOURCED_LINES, *(extra_sourced_lines or [])],
        _PLAIN_SOURCED_BY_IT_LINES,
        _PLAIN_CLUSTER_ROWS,
    )


def _parse_report(stdout: str) -> list[tuple[str, dict[str, str]]]:
    """Each report line as its kind word and its key=value fields."""
    report = []
    for line in stdout.splitlines():
        kind, *fields = line.split(" ")
        report.append((kind, dict(field.split("=", 1) for field in fields)))
    return report


def _lines_of_kind(report: list[tuple[str, dict[str, str]]], kind: str) -> list[dict[str, str]]:
    return [fields for line_kind, fields in report if line_kind == kind]


def _arms_by_label(report: list[tuple[str, dict[str, str]]]) -> dict[str, dict[str, str]]:
    return {fields["label"]: fields for fields in _lines_of_kind(report, "arm")}


def _stop_lines(stderr: str, stage: str) -> list[str]:
    return [line for line in stderr.splitlines() if line.startswith(f"lib-source-cost: {stage}:")]


def _assert_arm_figures_well_formed(arm: dict[str, str], repetitions: int) -> None:
    """A format-envelope check: every time is milliseconds with three decimals, signed only for a cost or saving."""
    minimums = arm["mins_ms"].split(",")
    assert len(minimums) == repetitions, arm
    for minimum in minimums:
        assert _UNSIGNED_MS.match(minimum), arm
        # No sample outlives the subprocess timeout, so a larger value is a mis-scaled timestamp.
        assert float(minimum) < _RUN_TIMEOUT_SECONDS * 1000, arm
    for key in ("figure_ms", "spread_ms", "floor_ms"):
        if key in arm:
            assert _UNSIGNED_MS.match(arm[key]), arm
    for key in ("cost_ms", "saving_ms"):
        if key in arm:
            assert _SIGNED_MS.match(arm[key]), arm


def test_smoke_run_resolves_every_anchor_and_formats_every_figure():
    cluster_rows = [
        line
        for line in _REAL_CLUSTER_FILE.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    clusters_in_first_row_order = list(dict.fromkeys(row.split("|")[0] for row in cluster_rows))

    result = _run_script(REPO_ROOT, "--iterations", "1", "--repetitions", "2")

    assert result.returncode == 0, result.stderr
    assert len(result.stderr.splitlines()) == 2, result.stderr
    report = _parse_report(result.stdout)
    assert [kind for kind, _ in report if kind not in ("span", "arm")] == ["header", "noise-floor"]
    header = _lines_of_kind(report, "header")[0]
    assert header["iterations"] == "1"
    assert header["repetitions"] == "2"
    assert len(_lines_of_kind(report, "span")) == len(cluster_rows)
    arms = _lines_of_kind(report, "arm")
    assert [arm["label"] for arm in arms] == [
        "full",
        *(f"minus-{cluster}" for cluster in clusters_in_first_row_order),
        *_FIXED_ARM_LABELS,
    ]
    for arm in arms:
        _assert_arm_figures_well_formed(arm, repetitions=2)
    assert _UNSIGNED_MS.match(_lines_of_kind(report, "noise-floor")[0]["ms"])


def test_progress_line_marks_the_start_of_each_repetition_once(tmp_path):
    """At two iterations a line per round, or a wrong repetition number, would show here."""
    checkout = _make_plain_fixture(tmp_path / "checkout")

    result = _run_script(checkout, "--iterations", "2", "--repetitions", "2")

    assert result.returncode == 0, result.stderr
    assert result.stderr.splitlines() == [
        "lib-source-cost: repetition 1 of 2",
        "lib-source-cost: repetition 2 of 2",
    ]


def test_header_names_the_toolchain_and_dirname_and_reports_none_for_a_checkout_with_no_commit(tmp_path):
    checkout = _make_plain_fixture(tmp_path / "checkout")
    expected_bash_version = subprocess.run(
        ["bash", "-c", 'printf "%s" "$BASH_VERSION"'],
        env=_script_env(),
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    dirname_stub = _install_dirname_stub(tmp_path / "tools")

    result = _run_script(
        checkout,
        "--iterations",
        "1",
        "--repetitions",
        "2",
        env=_script_env(PATH=_path_led_by(dirname_stub.parent)),
    )

    assert result.returncode == 0, result.stderr
    header = _lines_of_kind(_parse_report(result.stdout), "header")[0]
    assert header["bash"] == expected_bash_version
    assert header["system"] == os.uname().sysname
    assert header["machine"] == os.uname().machine
    assert header["dirname"] == str(dirname_stub)
    assert header["commit"] == "none"


def test_timestamps_stay_integer_microseconds_under_a_comma_decimal_locale(tmp_path):
    comma_locale = installed_locale_where(
        "[[ $EPOCHREALTIME == *,* ]]",
        "unused",
        absent_message="no installed UTF-8 locale prints EPOCHREALTIME with a comma",
    )
    checkout = _make_plain_fixture(tmp_path / "checkout")

    result = _run_script(checkout, "--iterations", "1", "--repetitions", "2", env=_script_env(LC_ALL=comma_locale))

    assert result.returncode == 0, result.stderr
    for arm in _lines_of_kind(_parse_report(result.stdout), "arm"):
        _assert_arm_figures_well_formed(arm, repetitions=2)


# Fixture for the deterministic arm-content case. Line numbers are pinned by its span assertions.
# Each span holds a top-level marker write, so the log shows which spans a pass sourced.
_MARKED_SOURCED_LINES = [
    "_probe_dir=${BASH_SOURCE[0]%/*}; printf '%s %s\\n' \"$0\" \"${_probe_dir##*/}\" >> {log}",  # 1
    _FIXTURE_SOURCING_LINE,  # 2
    "split_alpha() {",  # 3
    "  :",  # 4
    "}",  # 5
    "printf '%s split-1\\n' \"$0\" >> {log}",  # 6
    "split_beta() (",  # 7
    "  :",  # 8
    ")",  # 9
    "",  # 10
    "keep_middle() {",  # 11
    "  :",  # 12
    "}",  # 13
    "",  # 14
    "split_gamma() {",  # 15
    "  :",  # 16
    "}",  # 17
    "printf '%s split-2\\n' \"$0\" >> {log}",  # 18
    "split_delta() {",  # 19
    "  :",  # 20
    "}",  # 21
    # Outside every span: edits the live file once the run has taken its snapshot.
    "echo 'echo live-edit >&2' >> {live_lib}",  # 22
]
_MARKED_SOURCED_BY_IT_LINES = [
    "_cfg_kept=1",  # 1
    "cfg_one() {",  # 2
    "  :",  # 3
    "}",  # 4
    "printf '%s cfg\\n' \"$0\" >> {log}",  # 5
    "cfg_two() {",  # 6
    "  :",  # 7
    "}",  # 8
]
_MARKED_CLUSTER_ROWS = [
    "split|_lib.sh|split_alpha|split_beta",
    "split|_lib.sh|split_gamma|split_delta",
    "cfg|_config.sh|cfg_one|cfg_two",
]
_MARKED_SPAN_LINES = [
    "span cluster=split file=_lib.sh lines=3-9 line_count=7 functions=2",
    "span cluster=split file=_lib.sh lines=15-21 line_count=7 functions=2",
    "span cluster=cfg file=_config.sh lines=2-8 line_count=7 functions=2",
]
_MARKED_ARM_LABELS = ["full", "minus-split", "minus-cfg", *_FIXED_ARM_LABELS]
# One entry per source pass of an arm that sources the fixture's sourced file, as "<label> <directory>":
# the lookup, the pre-flight, then rounds 0 to 3 rotated one arm per round over the nine-arm list.
# The floor gate sources the fixture's companion file once before them, under the script's own `$0`.
_SOURCE_PASSES = [
    "lookup lookup",
    "full 0", "minus-split 1", "minus-cfg 2", "total-deletion 3", "tail-cut 4", "control 5",
    "full 0", "minus-split 1", "minus-cfg 2", "total-deletion 3", "tail-cut 4", "control 5",
    "minus-split 1", "minus-cfg 2", "total-deletion 3", "tail-cut 4", "control 5", "full 0",
    "minus-cfg 2", "total-deletion 3", "tail-cut 4", "control 5", "full 0", "minus-split 1",
    "total-deletion 3", "tail-cut 4", "control 5", "full 0", "minus-split 1", "minus-cfg 2",
]
# The span markers a pass writes after its first line, in execution order: the sourced file
# sources its companion first. The tail cut moves every span behind a `return 0`, so it writes none.
_SPAN_MARKERS_BY_PASS_LABEL = {
    "lookup": ["cfg", "split-1", "split-2"],
    "full": ["cfg", "split-1", "split-2"],
    "control": ["cfg", "split-1", "split-2"],
    "minus-split": ["cfg"],
    "minus-cfg": ["split-1", "split-2"],
    "total-deletion": [],
    "tail-cut": [],
}


def _expected_source_log() -> list[str]:
    expected = [f"{_SCRIPT} cfg"]
    for source_pass in _SOURCE_PASSES:
        label = source_pass.rsplit(" ", 1)[0]
        expected.append(source_pass)
        expected.extend(f"{label} {marker}" for marker in _SPAN_MARKERS_BY_PASS_LABEL[label])
    return expected


def test_each_arm_sources_the_spans_it_keeps_in_rotated_order_from_one_snapshot(tmp_path):
    source_log = tmp_path / "source.log"
    scratch_parent = tmp_path / "scratch-parent"
    scratch_parent.mkdir()
    checkout_root = tmp_path / "checkout"
    live_lib = _hooks_dir(checkout_root) / "_lib.sh"
    placeholders = {"{log}": shlex.quote(str(source_log)), "{live_lib}": shlex.quote(str(live_lib))}

    def fill(lines: list[str]) -> list[str]:
        filled = []
        for line in lines:
            for placeholder, value in placeholders.items():
                line = line.replace(placeholder, value)
            filled.append(line)
        return filled

    checkout = _make_fixture_checkout(
        checkout_root, fill(_MARKED_SOURCED_LINES), fill(_MARKED_SOURCED_BY_IT_LINES), _MARKED_CLUSTER_ROWS
    )
    blob_before_the_run = _git(checkout, "hash-object", "--", str(live_lib)).strip()

    result = _run_script(
        checkout, "--iterations", "2", "--repetitions", "2", env=_script_env(TMPDIR=str(scratch_parent))
    )

    # The live-edit line appends a stderr write to the live file, and any arm built from the live
    # file would print it, which stops the pre-flight.
    assert result.returncode == 0, result.stderr
    assert _git(checkout, "hash-object", "--", str(live_lib)).strip() != blob_before_the_run
    report = _parse_report(result.stdout)
    arms = _arms_by_label(report)
    assert list(arms) == _MARKED_ARM_LABELS
    assert [line for line in result.stdout.splitlines() if line.startswith("span ")] == _MARKED_SPAN_LINES
    header = _lines_of_kind(report, "header")[0]
    assert header["lib_blob"] == blob_before_the_run
    assert header["config_blob"] == _git(checkout, "hash-object", "--", str(_hooks_dir(checkout) / "_config.sh")).strip()
    noise_floor = _lines_of_kind(report, "noise-floor")[0]["ms"]
    assert noise_floor == arms["baseline"]["spread_ms"]
    for label, arm in arms.items():
        if label != "baseline":
            assert float(noise_floor) <= float(arm["floor_ms"]), label
    assert list(scratch_parent.iterdir()) == []
    assert source_log.read_text().splitlines() == _expected_source_log()


# Fixture for the timing case: one planted sleep between the two functions of the only span.
_SLOW_SOURCED_LINES = [
    "# fixture",
    _FIXTURE_SOURCING_LINE,
    "slow_one() {",
    "  :",
    "}",
    "sleep 0.1",
    "slow_two() {",
    "  :",
    "}",
]


@pytest.mark.timing
def test_a_planted_sleep_inside_a_span_shows_as_a_positive_saving_in_milliseconds(tmp_path):
    """Bounds a planted cost, so run it serially: a red under `-n auto` is rerun with `-m timing -n0` before it counts.

    The saving must fall between half and ten times the planted 100 ms. That pins the timer's sign and its unit.
    """
    checkout = _make_fixture_checkout(
        tmp_path / "checkout", _SLOW_SOURCED_LINES, _PLAIN_SOURCED_BY_IT_LINES, ["slow|_lib.sh|slow_one|slow_two"]
    )

    result = _run_script(checkout, "--iterations", "2", "--repetitions", "2")

    assert result.returncode == 0, result.stderr
    arms = _arms_by_label(_parse_report(result.stdout))
    assert 50 < float(arms["minus-slow"]["saving_ms"]) < 1000


@pytest.mark.parametrize(
    ("failing_line", "child_report"),
    [
        ("return 1", "child stdout:\nchild stderr:\n"),
        ("echo noise >&2", "child stdout:\nchild stderr:\nnoise\n"),
        ("echo noise", "child stdout:\nnoise\nchild stderr:\n"),
    ],
    ids=["nonzero-status", "stderr-output", "stdout-output"],
)
def test_source_failure_stops_the_pre_flight_naming_the_arm_and_printing_its_output(
    tmp_path, failing_line, child_report
):
    scratch_parent = tmp_path / "scratch-parent"
    scratch_parent.mkdir()
    checkout = _make_plain_fixture(tmp_path / "checkout", [failing_line])

    result = _run_script(
        checkout, "--iterations", "1", "--repetitions", "2", env=_script_env(TMPDIR=str(scratch_parent))
    )

    assert result.returncode == 1
    assert result.stdout == ""
    stop_lines = _stop_lines(result.stderr, "pre-flight")
    assert len(stop_lines) == 1
    assert stop_lines[0].startswith("lib-source-cost: pre-flight: arm full:")
    assert child_report in result.stderr
    assert _stop_lines(result.stderr, "timed") == []
    assert list(scratch_parent.iterdir()) == []


def test_source_that_fails_only_on_a_later_pass_stops_the_first_timed_round(tmp_path):
    scratch_parent = tmp_path / "scratch-parent"
    scratch_parent.mkdir()
    checkout = _make_plain_fixture(tmp_path / "checkout", [_GUARD_THAT_FAILS_ON_THE_SECOND_SOURCE])

    result = _run_script(
        checkout, "--iterations", "1", "--repetitions", "2", env=_script_env(TMPDIR=str(scratch_parent))
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert _stop_lines(result.stderr, "pre-flight") == []
    stop_lines = _stop_lines(result.stderr, "timed")
    assert len(stop_lines) == 1
    assert stop_lines[0].startswith("lib-source-cost: timed: arm full, repetition 1, round 0:")
    assert list(scratch_parent.iterdir()) == []


def test_pre_flight_stops_on_the_first_arm_that_prints_an_error_though_its_source_exits_zero(tmp_path):
    """A kept line calling a deleted function prints `command not found`, and the harmless line after it keeps the status 0."""
    scratch_parent = tmp_path / "scratch-parent"
    scratch_parent.mkdir()
    checkout = _make_plain_fixture(tmp_path / "checkout", ["plain_one", ":"])

    result = _run_script(
        checkout, "--iterations", "1", "--repetitions", "2", env=_script_env(TMPDIR=str(scratch_parent))
    )

    assert result.returncode == 1
    assert result.stdout == ""
    stop_lines = _stop_lines(result.stderr, "pre-flight")
    assert stop_lines == ["lib-source-cost: pre-flight: arm minus-solo: exit status 0, output below"]
    assert "arm full" not in result.stderr
    assert _stop_lines(result.stderr, "timed") == []
    assert list(scratch_parent.iterdir()) == []


def test_every_child_bash_reads_stdin_from_dev_null(tmp_path):
    """Each source records any line it reads from stdin, and the script's own stdin carries one line."""
    stdin_log = tmp_path / "stdin.log"
    read_stdin_line = (
        "IFS= read -r -t 1 _stdin_line || true; "
        f'[[ -z ${{_stdin_line-}} ]] || echo "$0" >> {shlex.quote(str(stdin_log))}'
    )
    checkout = _make_plain_fixture(tmp_path / "checkout", [read_stdin_line])

    result = _run_script(checkout, "--iterations", "1", "--repetitions", "2", stdin_text="leaked line\n")

    assert result.returncode == 0, result.stderr
    assert not stdin_log.exists()


def test_no_child_bash_runs_the_inherited_bash_env_file(tmp_path):
    """BASH_ENV is sourced by the script's own startup and, unless the script unsets it, by every child bash."""
    startup_log = tmp_path / "startup.log"
    startup_file = tmp_path / "startup.sh"
    startup_file.write_text(f"echo started >> {shlex.quote(str(startup_log))}\n")
    checkout = _make_plain_fixture(tmp_path / "checkout")

    result = _run_script(
        checkout, "--iterations", "1", "--repetitions", "2", env=_script_env(BASH_ENV=str(startup_file))
    )

    assert result.returncode == 0, result.stderr
    assert startup_log.read_text().splitlines() == ["started"]


def test_checkout_under_a_directory_name_with_a_space_runs_to_a_report(tmp_path):
    checkout = _make_plain_fixture(tmp_path / "check out")

    result = _run_script(checkout, "--iterations", "1", "--repetitions", "2")

    assert result.returncode == 0, result.stderr
    assert _lines_of_kind(_parse_report(result.stdout), "arm")[0]["label"] == "full"


def test_floor_gate_stops_on_a_failed_source_of_the_checkouts_hook_config(tmp_path):
    marker = "stub floor gate was sourced"
    _init_repo(tmp_path)
    stub = _hooks_dir(tmp_path) / "_config.sh"
    stub.parent.mkdir(parents=True)
    stub.write_text(f"printf '%s' '{marker}' >&2\nreturn 1\n")

    result = _run_script(tmp_path)

    assert result.returncode == 1
    assert result.stderr == marker
    assert result.stdout == ""


@pytest.mark.parametrize("missing_file", ["_lib.sh", "config-keys.psv"])
def test_missing_measured_file_stops_at_the_input_stage_naming_it(tmp_path, missing_file):
    checkout = _make_plain_fixture(tmp_path / "checkout")
    (_hooks_dir(checkout) / missing_file).unlink()

    result = _run_script(checkout)

    assert result.returncode == 1
    assert result.stdout == ""
    stop_lines = _stop_lines(result.stderr, "input")
    assert len(stop_lines) == 1
    assert missing_file in stop_lines[0]


def test_spec_error_names_a_cluster_function_the_checkout_does_not_define(tmp_path):
    checkout = _make_fixture_checkout(
        tmp_path / "checkout",
        _PLAIN_SOURCED_LINES,
        _PLAIN_SOURCED_BY_IT_LINES,
        ["ghost|_lib.sh|undefined_anchor|undefined_anchor"],
    )

    result = _run_script(checkout)

    assert result.returncode == 1
    assert result.stdout == ""
    stop_lines = _stop_lines(result.stderr, "lookup")
    assert len(stop_lines) == 1
    assert "undefined_anchor" in stop_lines[0]


@pytest.mark.parametrize(
    "arguments",
    [
        ["--repetitions", "1"],
        ["--iterations", "0"],
        ["--iterations"],
        ["--unknown-flag"],
    ],
    ids=["single-repetition", "zero-iterations", "flag-without-value", "unknown-flag"],
)
def test_usage_error_exits_2_with_the_usage_line(tmp_path, arguments):
    checkout = _make_plain_fixture(tmp_path / "checkout")

    result = _run_script(checkout, *arguments)

    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr.startswith("usage: lib-source-cost.sh")
