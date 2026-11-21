"""Tests for _timing_split.py.

The table tests pin each pure function. TestPlannedPassesAgainstRealPytest runs real pytest on a throwaway project
with the argv plan_passes builds, which checks at run time the pytest and xdist option parsing those argvs rely on.
"""
from __future__ import annotations

import functools
import os
import signal
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import NamedTuple

import pytest
from _timing_split import (
    PARALLEL_PASS,
    SATURATES_CPU_MARKER,
    SERIAL_PASS,
    UNSPLIT_PASS,
    UNSPLIT_REASON_ARGUMENT_FILE,
    UNSPLIT_REASON_BARE_DOUBLE_DASH,
    UNSPLIT_REASON_CALLER_ONE_OR_FEWER_WORKERS,
    UNSPLIT_REASON_ENVIRONMENT_ONE_OR_FEWER_WORKERS,
    UNSPLIT_REASON_NO_MARKED_FILES,
    PassPlan,
    PytestPass,
    TimingMarkScan,
    merge_pass_exit_codes,
    one_or_fewer_workers_reason,
    plan_passes,
    scan_timing_marks,
    skips_serial_pass,
    split_caller_marker_expression,
)
from helpers import REPO_ROOT
from pytest import ExitCode

MARKED_TEST_TEXT = "import pytest\n\n\n@pytest.mark.timing\ndef test_marked():\n    pass\n"
UNMARKED_TEST_TEXT = "def test_unmarked():\n    pass\n"


class TestSplitCallerMarkerExpression:
    @pytest.mark.parametrize(
        ("caller_args", "expected_expression", "expected_remaining_args"),
        [
            pytest.param([], "", [], id="no-marker-option"),
            pytest.param(["-m", "slow"], "slow", [], id="separate-value"),
            pytest.param(["-mslow"], "slow", [], id="attached-value"),
            pytest.param(["-m=slow"], "slow", [], id="equals-value"),
            pytest.param(["-m", "a", "-k", "x", "-m", "b"], "b", ["-k", "x"], id="last-marker-wins-and-all-are-removed"),
            pytest.param(["-m", ""], "", [], id="empty-separate-value-is-no-expression"),
            pytest.param(["-m="], "", [], id="empty-equals-value-is-no-expression"),
            pytest.param(["-m", "slow", "-m", ""], "", [], id="a-later-empty-value-clears-the-expression"),
            pytest.param(["-m", " "], " ", [], id="blank-value-stays-an-expression"),
            pytest.param(["-x", "-m"], "", ["-x", "-m"], id="trailing-bare-marker-option-stays"),
            pytest.param(["-m", "-x"], "", ["-m", "-x"], id="marker-option-before-an-option-stays"),
            pytest.param(["-m", "-k", "foo"], "", ["-m", "-k", "foo"], id="marker-option-before-keyword-option-stays"),
            pytest.param(["-m", "-1"], "", ["-m", "-1"], id="negative-number-shaped-value-stays"),
            pytest.param(["-vm", "slow"], "", ["-vm", "slow"], id="short-flag-cluster-is-not-recognized"),
        ],
    )
    def test_removes_each_recognized_marker_option_and_returns_the_last_expression(
        self, caller_args, expected_expression, expected_remaining_args,
    ):
        assert split_caller_marker_expression(caller_args) == (expected_expression, expected_remaining_args)


class TestOneOrFewerWorkersReason:
    @pytest.mark.parametrize(
        ("caller_args", "auto_num_workers"),
        [
            pytest.param(["-n0"], None, id="attached-zero"),
            pytest.param(["-n", "0"], None, id="separate-zero"),
            pytest.param(["-n=0"], None, id="equals-zero"),
            pytest.param(["--numprocesses", "0"], None, id="long-separate-zero"),
            pytest.param(["--numprocesses=0"], None, id="long-equals-zero"),
            pytest.param(["-n", "00"], None, id="zero-with-leading-zero"),
            pytest.param(["-n=-1"], None, id="negative-equals-value"),
            pytest.param(["-n", "4", "-n0"], None, id="a-later-zero-wins"),
            pytest.param(["-n", "0"], "4", id="caller-zero-beats-environment"),
            pytest.param(["-n", "1"], None, id="separate-one"),
            pytest.param(["-n1"], None, id="attached-one"),
            pytest.param(["-n=1"], None, id="equals-one"),
            pytest.param(["--numprocesses", "1"], None, id="long-separate-one"),
            pytest.param(["--numprocesses=1"], None, id="long-equals-one"),
            pytest.param(["-n", "4", "-n1"], None, id="a-later-one-wins"),
            pytest.param(["-n", "1"], "4", id="caller-one-beats-environment"),
        ],
    )
    def test_names_the_callers_n_when_it_starts_one_worker_or_fewer(self, caller_args, auto_num_workers):
        assert (
            one_or_fewer_workers_reason(caller_args, auto_num_workers=auto_num_workers)
            == UNSPLIT_REASON_CALLER_ONE_OR_FEWER_WORKERS
        )

    @pytest.mark.parametrize(
        ("caller_args", "auto_num_workers"),
        [
            pytest.param([], "0", id="no-n-and-zero-environment"),
            pytest.param(["-n", "auto"], "0", id="auto-and-zero-environment"),
            pytest.param(["--numprocesses=logical"], "0", id="logical-and-zero-environment"),
            pytest.param([], "-1", id="negative-environment"),
            pytest.param([], "1", id="no-n-and-one-environment-worker"),
            pytest.param(["-n", "auto"], "1", id="auto-and-one-environment-worker"),
            pytest.param(["--numprocesses=logical"], "1", id="logical-and-one-environment-worker"),
        ],
    )
    def test_names_the_environment_when_it_decides_and_starts_one_worker_or_fewer(
        self, caller_args, auto_num_workers,
    ):
        assert (
            one_or_fewer_workers_reason(caller_args, auto_num_workers=auto_num_workers)
            == UNSPLIT_REASON_ENVIRONMENT_ONE_OR_FEWER_WORKERS
        )

    @pytest.mark.parametrize(
        ("caller_args", "auto_num_workers"),
        [
            pytest.param([], None, id="no-n-and-unset-environment"),
            pytest.param([], "2", id="no-n-and-two-environment-workers"),
            pytest.param([], "", id="empty-environment-counts-as-unset"),
            pytest.param([], "x", id="unparseable-environment-counts-as-unset"),
            pytest.param(["-n", "2"], None, id="two-workers-is-the-smallest-split-count"),
            pytest.param(["-n", "4"], None, id="positive-n"),
            pytest.param(["-n", "2"], "0", id="positive-n-beats-zero-environment"),
            pytest.param(["-n", "2"], "1", id="positive-n-beats-one-environment-worker"),
            pytest.param(["-n2"], None, id="attached-two"),
            pytest.param(["-n=2"], None, id="equals-two"),
            pytest.param(["--numprocesses", "2"], None, id="long-separate-two"),
            pytest.param(["--numprocesses=2"], None, id="long-equals-two"),
            pytest.param(["-n", "auto"], "2", id="auto-and-two-environment-workers"),
            pytest.param(["-n", "auto"], "4", id="auto-and-four-environment-workers"),
            pytest.param(["-n0", "-n", "4"], None, id="a-later-positive-wins"),
            pytest.param(["-n1", "-n", "2"], None, id="a-later-two-beats-an-earlier-one"),
            pytest.param(["-n"], None, id="trailing-bare-n"),
            pytest.param(["-n", "-1"], None, id="separated-negative-value-is-not-read"),
            pytest.param(["-n", "x"], None, id="unparseable-n"),
            pytest.param(["--numproc", "0"], None, id="abbreviated-long-option-is-not-recognized"),
            pytest.param(["-vn0"], None, id="short-flag-cluster-is-not-recognized"),
            pytest.param(["--numproc", "1"], None, id="abbreviated-long-option-with-one-is-not-recognized"),
        ],
    )
    def test_returns_none_when_two_workers_or_more_start_or_the_option_is_not_read(
        self, caller_args, auto_num_workers,
    ):
        assert one_or_fewer_workers_reason(caller_args, auto_num_workers=auto_num_workers) is None


def test_pyproject_registers_the_marker_the_serial_pass_deselects_by_name():
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    markers = pyproject["tool"]["pytest"]["ini_options"]["markers"]

    assert any(marker.startswith(f"{SATURATES_CPU_MARKER}:") for marker in markers), (
        f"pyproject.toml registers no {SATURATES_CPU_MARKER!r} marker; the serial pass deselects that marker by "
        "name, so a mismatch would let a local run start the CPU-saturating test"
    )


def _write_files(root: Path, files: dict[str, str]) -> None:
    for relative_path, text in files.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


class TestScanTimingMarks:
    @pytest.mark.parametrize(
        ("files", "targets", "caller_args", "expected_marked"),
        [
            pytest.param(
                {"t/test_a.py": MARKED_TEST_TEXT, "t/test_b.py": UNMARKED_TEST_TEXT},
                ["t"], [], ("t/test_a.py",),
                id="directory-with-one-marked-and-one-unmarked-file",
            ),
            pytest.param(
                {"t/x/y/test_a.py": MARKED_TEST_TEXT},
                ["t"], [], ("t/x/y/test_a.py",),
                id="marked-file-two-directories-deep",
            ),
            pytest.param(
                {"t/test_a.py": UNMARKED_TEST_TEXT, "t/b_test.py": UNMARKED_TEST_TEXT},
                ["t"], [], (),
                id="directory-with-no-mark-finds-no-marked-file",
            ),
            pytest.param(
                {"t/test_a.py": MARKED_TEST_TEXT, "t/test_b.py": UNMARKED_TEST_TEXT},
                ["t/test_a.py", "t/test_b.py"], [], ("t/test_a.py",),
                id="files-named-directly-are-marked-only-when-they-hold-the-mark",
            ),
            pytest.param(
                {"t/helper.py": MARKED_TEST_TEXT, "t/notes.txt": MARKED_TEST_TEXT, "t/test_a.py": UNMARKED_TEST_TEXT},
                ["t"], [], (),
                id="walked-files-outside-the-test-patterns-do-not-count",
            ),
            pytest.param(
                {"t/helper.py": MARKED_TEST_TEXT},
                ["t/helper.py"], [], ("t/helper.py",),
                id="file-named-directly-is-read-whatever-its-name",
            ),
            pytest.param({}, ["missing"], [], (), id="missing-target"),
            pytest.param(
                {"t/test_a.py": MARKED_TEST_TEXT},
                [], ["t/test_a.py::Class::test[a::b]"], ("t/test_a.py",),
                id="caller-path-with-a-node-id-suffix",
            ),
            pytest.param(
                {"sub/test_a.py": MARKED_TEST_TEXT},
                [], ["-k", "sub"], (),
                id="keyword-value-naming-a-directory-is-not-a-path",
            ),
            pytest.param(
                {"sub/test_a.py": MARKED_TEST_TEXT},
                [], ["sub"], ("sub/test_a.py",),
                id="bare-caller-argument-naming-a-directory-is-a-path",
            ),
            pytest.param(
                {"t/test_z.py": MARKED_TEST_TEXT, "t/a/test_m.py": MARKED_TEST_TEXT, "t/test_b.py": MARKED_TEST_TEXT},
                ["t"], [], ("t/a/test_m.py", "t/test_b.py", "t/test_z.py"),
                id="several-marked-files-come-back-sorted-not-in-walk-order",
            ),
            pytest.param(
                {"t/test_a.py": MARKED_TEST_TEXT},
                ["t"], ["t/test_a.py", "t"], ("t/test_a.py",),
                id="a-target-and-overlapping-caller-paths-list-a-file-once",
            ),
        ],
    )
    def test_lists_the_files_that_hold_the_timing_mark(
        self, tmp_path, files, targets, caller_args, expected_marked,
    ):
        _write_files(tmp_path, files)

        scan = scan_timing_marks(targets, caller_args, repo_root=tmp_path)

        assert scan == TimingMarkScan(expected_marked)

    def test_dangling_symlink_counts_as_marked_because_it_cannot_be_read(self, tmp_path):
        (tmp_path / "t").mkdir()
        (tmp_path / "t" / "test_dangling.py").symlink_to(tmp_path / "nowhere.py")

        scan = scan_timing_marks(["t"], [], repo_root=tmp_path)

        assert scan == TimingMarkScan(("t/test_dangling.py",))

    def test_directory_symlink_is_not_followed(self, tmp_path):
        _write_files(tmp_path, {"elsewhere/test_linked.py": MARKED_TEST_TEXT, "t/test_plain.py": UNMARKED_TEST_TEXT})
        (tmp_path / "t" / "link").symlink_to(tmp_path / "elsewhere", target_is_directory=True)

        scan = scan_timing_marks(["t"], [], repo_root=tmp_path)

        assert scan == TimingMarkScan(())

    @pytest.mark.skipif(os.geteuid() == 0, reason="root reads a directory whatever its mode")
    def test_unreadable_directory_contributes_nothing_while_its_readable_sibling_is_scanned(self, tmp_path):
        _write_files(tmp_path, {"t/locked/test_hidden.py": MARKED_TEST_TEXT, "t/test_visible.py": MARKED_TEST_TEXT})
        locked_directory = tmp_path / "t" / "locked"
        locked_directory.chmod(0o000)
        try:
            scan = scan_timing_marks(["t"], [], repo_root=tmp_path)
        finally:
            locked_directory.chmod(0o700)

        assert scan == TimingMarkScan(("t/test_visible.py",))

    def test_caller_path_outside_the_repo_root_is_skipped_without_raising(self, tmp_path):
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        _write_files(tmp_path, {"outside/test_o.py": MARKED_TEST_TEXT})

        scan = scan_timing_marks([], [str(tmp_path / "outside" / "test_o.py")], repo_root=repo_root)

        assert scan == TimingMarkScan(())


def _scan_that_fails_the_test() -> TimingMarkScan:
    raise AssertionError("the scan must not run for this plan")


def _scan_of(marked_files=("t/test_marked.py",)) -> TimingMarkScan:
    return TimingMarkScan(tuple(marked_files))


class TestPlanPassesUnsplit:
    @pytest.mark.parametrize(
        ("caller_args", "auto_num_workers", "expected_reason"),
        [
            pytest.param(
                ["@args.txt", "-n", "0"], None, UNSPLIT_REASON_ARGUMENT_FILE,
                id="argument-file-comes-before-the-caller-n-reason",
            ),
            pytest.param(
                ["-n", "0", "--", "tests/x.py"], None, UNSPLIT_REASON_BARE_DOUBLE_DASH,
                id="double-dash-comes-before-the-caller-n-reason",
            ),
            pytest.param(
                ["-k", "foo", "--", "some/path.py"], None, UNSPLIT_REASON_BARE_DOUBLE_DASH,
                id="double-dash-after-a-keyword-option",
            ),
            pytest.param(
                ["-m", "slow", "-k", "foo", "--", "tests/x.py"], None, UNSPLIT_REASON_BARE_DOUBLE_DASH,
                id="double-dash-keeps-the-callers-marker-option",
            ),
            pytest.param(["-n", "0"], None, UNSPLIT_REASON_CALLER_ONE_OR_FEWER_WORKERS, id="caller-n-zero"),
            pytest.param(["-n", "1"], None, UNSPLIT_REASON_CALLER_ONE_OR_FEWER_WORKERS, id="caller-n-one"),
            pytest.param([], "0", UNSPLIT_REASON_ENVIRONMENT_ONE_OR_FEWER_WORKERS, id="environment-workers-zero"),
            pytest.param([], "1", UNSPLIT_REASON_ENVIRONMENT_ONE_OR_FEWER_WORKERS, id="environment-workers-one"),
        ],
    )
    def test_argument_only_collapse_plans_one_pass_without_reading_any_file(
        self, caller_args, auto_num_workers, expected_reason,
    ):
        plan = plan_passes(
            caller_args, auto_num_workers=auto_num_workers, scan_selection=_scan_that_fails_the_test,
        )

        assert plan == PassPlan((PytestPass(UNSPLIT_PASS, (), list(caller_args)),), expected_reason)

    def test_selection_with_no_marked_file_plans_one_unsplit_pass(self):
        scan = _scan_of(marked_files=())

        plan = plan_passes(["-k", "foo"], auto_num_workers=None, scan_selection=lambda: scan)

        assert plan == PassPlan((PytestPass(UNSPLIT_PASS, (), ["-k", "foo"]),), UNSPLIT_REASON_NO_MARKED_FILES)


class TestPlanPassesSplit:
    @pytest.mark.parametrize(
        ("caller_args", "parallel_expression", "serial_expression", "remaining_args"),
        [
            pytest.param([], "not timing", "timing and not saturates_cpu", [], id="no-caller-arguments"),
            pytest.param(
                ["-m", "slow", "-k", "foo"],
                "(slow) and not timing", "(slow) and timing and not saturates_cpu", ["-k", "foo"],
                id="caller-marker-and-keyword-reach-both-passes",
            ),
            pytest.param(
                ["-m", "a or b"],
                "(a or b) and not timing", "(a or b) and timing and not saturates_cpu", [],
                id="caller-marker-expression-is-wrapped",
            ),
            pytest.param(
                ["-m", " "],
                "( ) and not timing", "( ) and timing and not saturates_cpu", [],
                id="blank-caller-marker-expression-stays-an-expression",
            ),
            pytest.param(
                ["-m", "saturates_cpu"],
                "(saturates_cpu) and not timing", "(saturates_cpu) and timing and not saturates_cpu", [],
                id="caller-marker-naming-the-excluded-marker-selects-nothing-in-either-pass",
            ),
            pytest.param(
                ["-n", "4"], "not timing", "timing and not saturates_cpu", ["-n", "4"],
                id="caller-n-reaches-the-parallel-pass-and-the-serial-pass-overrides-it",
            ),
        ],
    )
    def test_plans_the_parallel_pass_then_the_serial_pass_with_the_options_appended_last(
        self, caller_args, parallel_expression, serial_expression, remaining_args,
    ):
        plan = plan_passes(caller_args, auto_num_workers=None, scan_selection=_scan_of)

        parallel_options = ("-m", parallel_expression)
        serial_options = ("-m", serial_expression, "-n0")
        assert plan.unsplit_reason is None
        assert [planned_pass.name for planned_pass in plan.passes] == [PARALLEL_PASS, SERIAL_PASS]
        assert [planned_pass.added_options for planned_pass in plan.passes] == [parallel_options, serial_options]
        assert [planned_pass.pytest_args for planned_pass in plan.passes] == [
            [*remaining_args, *parallel_options],
            [*remaining_args, *serial_options],
        ]

    def test_default_pass_options_are_pinned_as_literals(self):
        plan = plan_passes([], auto_num_workers=None, scan_selection=_scan_of)

        assert [planned_pass.added_options for planned_pass in plan.passes] == [
            ("-m", "not timing"),
            ("-m", "timing and not saturates_cpu", "-n0"),
        ]


class TestSkipsSerialPass:
    @pytest.mark.parametrize(
        "parallel_exit_code",
        [
            pytest.param(ExitCode.INTERNAL_ERROR, id="internal-error"),
            pytest.param(ExitCode.USAGE_ERROR, id="usage-error"),
            pytest.param(-signal.SIGKILL, id="killed"),
            pytest.param(-signal.SIGINT, id="interrupted-by-signal"),
        ],
    )
    def test_skips_after_a_pytest_error_or_a_kill(self, parallel_exit_code):
        assert skips_serial_pass(parallel_exit_code) is True

    @pytest.mark.parametrize(
        "parallel_exit_code",
        [
            pytest.param(ExitCode.OK, id="ok"),
            pytest.param(ExitCode.TESTS_FAILED, id="tests-failed"),
            pytest.param(ExitCode.INTERRUPTED, id="interrupted"),
            pytest.param(ExitCode.NO_TESTS_COLLECTED, id="no-tests-collected"),
        ],
    )
    def test_runs_after_a_test_result(self, parallel_exit_code):
        assert skips_serial_pass(parallel_exit_code) is False


class TestMergePassExitCodes:
    @pytest.mark.parametrize(
        ("parallel_exit_code", "serial_exit_code", "expected"),
        [
            pytest.param(ExitCode.OK, ExitCode.OK, ExitCode.OK, id="both-ok"),
            pytest.param(ExitCode.OK, ExitCode.NO_TESTS_COLLECTED, ExitCode.OK, id="serial-collected-nothing"),
            pytest.param(ExitCode.NO_TESTS_COLLECTED, ExitCode.OK, ExitCode.OK, id="parallel-collected-nothing"),
            pytest.param(
                ExitCode.NO_TESTS_COLLECTED, ExitCode.NO_TESTS_COLLECTED, ExitCode.NO_TESTS_COLLECTED,
                id="both-collected-nothing",
            ),
            pytest.param(ExitCode.TESTS_FAILED, ExitCode.OK, ExitCode.TESTS_FAILED, id="parallel-failed-serial-ok"),
            pytest.param(ExitCode.OK, ExitCode.TESTS_FAILED, ExitCode.TESTS_FAILED, id="parallel-ok-serial-failed"),
            pytest.param(
                ExitCode.TESTS_FAILED, ExitCode.NO_TESTS_COLLECTED, ExitCode.TESTS_FAILED,
                id="parallel-failed-serial-collected-nothing",
            ),
            pytest.param(
                ExitCode.NO_TESTS_COLLECTED, ExitCode.TESTS_FAILED, ExitCode.TESTS_FAILED,
                id="parallel-collected-nothing-serial-failed",
            ),
            pytest.param(
                ExitCode.INTERRUPTED, ExitCode.TESTS_FAILED, ExitCode.INTERRUPTED,
                id="run-order-decides-not-an-interrupt",
            ),
            pytest.param(
                ExitCode.TESTS_FAILED, ExitCode.INTERNAL_ERROR, ExitCode.TESTS_FAILED,
                id="first-failing-pass-wins-over-a-later-error",
            ),
            pytest.param(ExitCode.USAGE_ERROR, ExitCode.USAGE_ERROR, ExitCode.USAGE_ERROR, id="both-usage-errors"),
            pytest.param(-signal.SIGKILL, ExitCode.OK, -signal.SIGKILL, id="killed-parallel-pass-is-a-failure"),
        ],
    )
    def test_first_failing_pass_wins_and_a_pass_that_collected_nothing_defers(
        self, parallel_exit_code, serial_exit_code, expected,
    ):
        merged = merge_pass_exit_codes([parallel_exit_code, serial_exit_code])

        assert merged == expected
        assert type(merged) is int

    @pytest.mark.parametrize(
        "exit_code",
        [ExitCode.OK, ExitCode.TESTS_FAILED, ExitCode.NO_TESTS_COLLECTED],
        ids=["ok", "tests-failed", "no-tests-collected"],
    )
    def test_a_single_pass_returns_its_own_code(self, exit_code):
        assert merge_pass_exit_codes([exit_code]) == exit_code

    def test_rejects_an_empty_list_of_codes(self):
        with pytest.raises(ValueError):
            merge_pass_exit_codes([])


PYTEST_INI = f"""\
[pytest]
addopts = -n auto -p no:cacheprovider
markers =
    timing
    slow
    a
    b
    {SATURATES_CPU_MARKER}
"""

# Names the ids file of a run that is not an xdist worker.
NO_WORKER_IDS_FILE_STEM = "no-xdist-worker"

# Writes each selected node ID, post-deselection, to a per-worker file under the directory the environment names.
# The hook runs after -m deselection (so the IDs are the selected tests in one format under any verbosity). Each xdist
# worker writes its own file, so the file count is the worker count, and a run without workers writes one file.
CONFTEST = f"""\
import os


def pytest_collection_finish(session):
    output_dir = os.environ.get("TIMING_SPLIT_COLLECTED_IDS_DIR")
    if output_dir:
        worker = os.environ.get("PYTEST_XDIST_WORKER", "{NO_WORKER_IDS_FILE_STEM}")
        with open(os.path.join(output_dir, f"{{worker}}.ids"), "w") as handle:
            handle.write("\\n".join(item.nodeid for item in session.items))
"""

PROJECT_MARKED_TESTS = f"""\
import os

import pytest


@pytest.mark.timing
def test_timing_serial():
    assert "PYTEST_XDIST_WORKER" not in os.environ


@pytest.mark.timing
@pytest.mark.slow
def test_timing_slow():
    assert "PYTEST_XDIST_WORKER" not in os.environ


def test_unmarked():
    pass


@pytest.mark.a
def test_a():
    pass


@pytest.mark.timing
@pytest.mark.{SATURATES_CPU_MARKER}
def test_saturates_cpu():
    pytest.fail("a split run must never start the CPU-saturating test")
"""

PROJECT_FAILING_TEST = """\
def test_plain_fails():
    assert False
"""

PROJECT_FIXED_TEST = """\
def test_plain_fails():
    pass
"""

# Replaces the ini's addopts, which carries -p no:cacheprovider, so --lf has a cache to read.
CACHE_ENABLED_OPTIONS = ["-o", "addopts=-n auto"]

PROJECT_PLAIN_TESTS = """\
import pytest


def test_plain_unmarked():
    pass


@pytest.mark.slow
def test_plain_slow():
    pass


@pytest.mark.b
def test_plain_b():
    pass
"""

MARKED = "tests/test_marked.py::"
PLAIN = "tests/test_plain.py::"
ALL_TESTS_BUT_THE_CPU_SATURATING_ONE = {
    f"{MARKED}test_timing_serial",
    f"{MARKED}test_timing_slow",
    f"{MARKED}test_unmarked",
    f"{MARKED}test_a",
    f"{PLAIN}test_plain_unmarked",
    f"{PLAIN}test_plain_slow",
    f"{PLAIN}test_plain_b",
}


class _PytestRun(NamedTuple):
    exit_code: int
    node_ids: set[str]
    ids_file_stems: set[str]
    output: str


class TestPlannedPassesAgainstRealPytest:
    @pytest.fixture
    def project(self, tmp_path: Path) -> Path:
        _write_files(
            tmp_path,
            {
                "pytest.ini": PYTEST_INI,
                "conftest.py": CONFTEST,
                "tests/test_marked.py": PROJECT_MARKED_TESTS,
                "tests/test_plain.py": PROJECT_PLAIN_TESTS,
            },
        )
        return tmp_path

    @staticmethod
    def _run_pytest(project: Path, argv: list[str]) -> _PytestRun:
        # xdist sets these in each worker, and the child must not see the ones of the worker running this test.
        environment = {
            name: value
            for name, value in os.environ.items()
            if name not in {"PYTEST_XDIST_WORKER", "PYTEST_XDIST_WORKER_COUNT", "PYTEST_XDIST_TESTRUNUID", "PYTEST_ADDOPTS"}
        }
        environment["PYTEST_XDIST_AUTO_NUM_WORKERS"] = "2"
        with tempfile.TemporaryDirectory(dir=project, prefix="collected-ids-") as ids_dir:
            environment["TIMING_SPLIT_COLLECTED_IDS_DIR"] = ids_dir
            completed = subprocess.run(
                [sys.executable, "-m", "pytest", "-c", str(project / "pytest.ini"), *argv],
                cwd=project, env=environment, capture_output=True, text=True, timeout=120, check=False,
            )
            node_ids: set[str] = set()
            ids_file_stems: set[str] = set()
            for ids_file in Path(ids_dir).glob("*.ids"):
                ids_file_stems.add(ids_file.stem)
                node_ids.update(line for line in ids_file.read_text().splitlines() if line)
        return _PytestRun(completed.returncode, node_ids, ids_file_stems, f"{completed.stdout}\n{completed.stderr}")

    @staticmethod
    def _plan(project: Path, caller_args: list[str]) -> PassPlan:
        return plan_passes(
            caller_args,
            auto_num_workers=None,
            scan_selection=functools.partial(scan_timing_marks, ["tests"], caller_args, repo_root=project),
        )

    def _collect_each_pass(self, project: Path, caller_args: list[str]) -> list[_PytestRun]:
        return [
            self._run_pytest(project, ["--collect-only", "tests", *planned_pass.pytest_args])
            for planned_pass in self._plan(project, caller_args).passes
        ]

    @pytest.mark.parametrize(
        ("caller_args", "expected_union"),
        [
            pytest.param([], ALL_TESTS_BUT_THE_CPU_SATURATING_ONE, id="no-caller-arguments"),
            pytest.param(
                ["-m", "slow"], {f"{PLAIN}test_plain_slow", f"{MARKED}test_timing_slow"}, id="caller-marker",
            ),
            pytest.param(
                ["-m", "a or b"], {f"{MARKED}test_a", f"{PLAIN}test_plain_b"}, id="caller-marker-expression",
            ),
            pytest.param(
                ["-vm", "slow"], ALL_TESTS_BUT_THE_CPU_SATURATING_ONE,
                id="marker-in-a-short-flag-cluster-widens-the-run",
            ),
            pytest.param(
                ["-m", "timing"], {f"{MARKED}test_timing_serial", f"{MARKED}test_timing_slow"},
                id="caller-marker-timing",
            ),
        ],
    )
    def test_the_passes_select_disjoint_tests_that_cover_the_callers_selection(
        self, project, caller_args, expected_union,
    ):
        parallel_run, serial_run = self._collect_each_pass(project, caller_args)

        for run in (parallel_run, serial_run):
            assert run.exit_code in (ExitCode.OK, ExitCode.NO_TESTS_COLLECTED), run.output
        assert parallel_run.node_ids.isdisjoint(serial_run.node_ids)
        assert parallel_run.node_ids | serial_run.node_ids == expected_union

    def test_a_caller_marker_naming_the_excluded_marker_selects_nothing_in_either_pass(self, project):
        runs = self._collect_each_pass(project, ["-m", SATURATES_CPU_MARKER])

        exit_codes = [run.exit_code for run in runs]
        assert exit_codes == [ExitCode.NO_TESTS_COLLECTED, ExitCode.NO_TESTS_COLLECTED], [run.output for run in runs]
        assert [run.node_ids for run in runs] == [set(), set()]
        assert merge_pass_exit_codes(exit_codes) == ExitCode.NO_TESTS_COLLECTED

    def test_a_pass_that_selects_nothing_exits_5_when_run_for_real_under_workers_and_serially(self, project):
        parallel_pass, serial_pass = self._plan(project, ["-n", "2", "-m", SATURATES_CPU_MARKER]).passes

        parallel_run = self._run_pytest(project, ["tests", *parallel_pass.pytest_args])
        serial_run = self._run_pytest(project, ["tests", *serial_pass.pytest_args])

        assert len(parallel_run.ids_file_stems) == 2 and NO_WORKER_IDS_FILE_STEM not in parallel_run.ids_file_stems
        assert serial_run.ids_file_stems == {NO_WORKER_IDS_FILE_STEM}
        assert [parallel_run.exit_code, serial_run.exit_code] == [
            ExitCode.NO_TESTS_COLLECTED, ExitCode.NO_TESTS_COLLECTED,
        ], [parallel_run.output, serial_run.output]
        assert parallel_run.node_ids == set() and serial_run.node_ids == set()

    def test_the_parallel_pass_runs_the_non_timing_tests_in_the_callers_number_of_workers(self, project):
        # Three workers differ from the two the environment sizes -n auto to, so only the caller's -n explains them.
        parallel_pass, _ = self._plan(project, ["-n", "3"]).passes

        run = self._run_pytest(project, ["tests", *parallel_pass.pytest_args])

        assert run.exit_code == ExitCode.OK, run.output
        assert len(run.ids_file_stems) == 3 and NO_WORKER_IDS_FILE_STEM not in run.ids_file_stems
        timing_test_ids = {f"{MARKED}test_timing_serial", f"{MARKED}test_timing_slow"}
        assert run.node_ids == ALL_TESTS_BUT_THE_CPU_SATURATING_ONE - timing_test_ids

    def test_last_failed_collects_nothing_in_the_serial_pass_while_a_non_timing_test_still_fails_in_a_file_without_timing_tests(
        self, project,
    ):
        _write_files(project, {"tests/test_failing.py": PROJECT_FAILING_TEST})
        parallel_pass, serial_pass = self._plan(project, []).passes
        failing_node_id = "tests/test_failing.py::test_plain_fails"

        first_run = self._run_pytest(project, ["tests", *parallel_pass.pytest_args, *CACHE_ENABLED_OPTIONS])
        parallel_rerun = self._run_pytest(
            project, ["tests", *parallel_pass.pytest_args, *CACHE_ENABLED_OPTIONS, "--lf"],
        )
        serial_rerun = self._run_pytest(project, ["tests", *serial_pass.pytest_args, *CACHE_ENABLED_OPTIONS, "--lf"])

        assert first_run.exit_code == ExitCode.TESTS_FAILED, first_run.output
        assert (parallel_rerun.exit_code, parallel_rerun.node_ids) == (ExitCode.TESTS_FAILED, {failing_node_id})
        assert (serial_rerun.exit_code, serial_rerun.node_ids) == (ExitCode.NO_TESTS_COLLECTED, set()), (
            serial_rerun.output
        )

    def test_last_failed_after_a_fix_runs_every_timing_test_in_the_serial_pass_because_the_parallel_pass_cleared_the_cache(
        self, project,
    ):
        _write_files(project, {"tests/test_failing.py": PROJECT_FAILING_TEST})
        parallel_pass, serial_pass = self._plan(project, []).passes
        fixed_node_id = "tests/test_failing.py::test_plain_fails"
        timing_test_ids = {f"{MARKED}test_timing_serial", f"{MARKED}test_timing_slow"}

        first_run = self._run_pytest(project, ["tests", *parallel_pass.pytest_args, *CACHE_ENABLED_OPTIONS])
        _write_files(project, {"tests/test_failing.py": PROJECT_FIXED_TEST})
        parallel_rerun = self._run_pytest(
            project, ["tests", *parallel_pass.pytest_args, *CACHE_ENABLED_OPTIONS, "--lf"],
        )
        serial_rerun = self._run_pytest(project, ["tests", *serial_pass.pytest_args, *CACHE_ENABLED_OPTIONS, "--lf"])

        assert first_run.exit_code == ExitCode.TESTS_FAILED, first_run.output
        assert (parallel_rerun.exit_code, parallel_rerun.node_ids) == (ExitCode.OK, {fixed_node_id}), (
            parallel_rerun.output
        )
        assert (serial_rerun.exit_code, serial_rerun.node_ids) == (ExitCode.OK, timing_test_ids), serial_rerun.output

    def test_a_caller_double_dash_runs_one_pass_that_collects_while_a_split_argv_would_be_a_usage_error(self, project):
        caller_args = ["--", "tests/test_plain.py"]
        unsplit_pass = self._plan(project, caller_args).passes[0]
        split_parallel_options = self._plan(project, []).passes[0].added_options

        unsplit_run = self._run_pytest(project, ["--collect-only", "tests", *unsplit_pass.pytest_args])
        split_shape_run = self._run_pytest(
            project, ["--collect-only", "tests", *caller_args, *split_parallel_options],
        )

        assert self._plan(project, caller_args) == PassPlan(
            (PytestPass(UNSPLIT_PASS, (), caller_args),), UNSPLIT_REASON_BARE_DOUBLE_DASH,
        )
        assert unsplit_run.exit_code == ExitCode.OK, unsplit_run.output
        assert split_shape_run.exit_code == ExitCode.USAGE_ERROR, split_shape_run.output

    @pytest.mark.parametrize(
        "caller_args",
        [pytest.param([], id="no-caller-arguments"), pytest.param(["-n", "2"], id="caller-n-overridden-by-the-serial-pass")],
    )
    def test_the_serial_pass_runs_without_xdist_workers_and_never_starts_the_cpu_saturating_test(
        self, project, caller_args,
    ):
        _, serial_pass = self._plan(project, caller_args).passes

        run = self._run_pytest(project, ["tests", *serial_pass.pytest_args])

        assert run.exit_code == ExitCode.OK, run.output

    def test_the_serial_pass_without_its_n0_runs_in_workers_and_fails_the_worker_assertion(self, project):
        _, serial_pass = self._plan(project, []).passes
        args_without_n0 = [arg for arg in serial_pass.pytest_args if arg != "-n0"]

        run = self._run_pytest(project, ["tests", *args_without_n0])

        assert run.exit_code == ExitCode.TESTS_FAILED, run.output
