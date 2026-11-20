"""Pins pytest's collection config against two failure modes surfaced by a
stale linked worktree nested at claude/.claude/worktrees/<branch>: a full
repo checkout under the collection root breaks collection outright (it
carries evals/fixtures/temp-project/tests/test_calculator.py, which fails to
import), and .gitignore excluding claude/.claude/worktrees/ does nothing to
stop pytest from walking into it — gitignore does not scope collection.

Run with: pytest claude/.claude/
"""

from __future__ import annotations

import ast
import importlib.util
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
from _timing_split import SERIAL_PASS_MARKER_EXPRESSION, TIMING_MARKER, TimingMarkScan, scan_timing_marks
from helpers import REPO_ROOT
from pytest import ExitCode

_SELECT_TESTS_SCRIPT = REPO_ROOT / "claude" / ".claude" / "scripts" / "select-tests.py"
_select_tests_spec = importlib.util.spec_from_file_location("select_tests", _SELECT_TESTS_SCRIPT)
_select_tests = importlib.util.module_from_spec(_select_tests_spec)
_select_tests_spec.loader.exec_module(_select_tests)
FULL_SUITE_TARGETS = _select_tests.FULL_SUITE_TARGETS

CPU_SATURATING_TEST_FILE = _select_tests.CPU_SATURATING_SHIM_TEST_PATH
CPU_SATURATING_TEST_NODE_ID = (
    f"{CPU_SATURATING_TEST_FILE}::TestShimHookRun::"
    "test_a_hook_that_prints_a_deny_and_exits_at_once_denies_every_time_under_cpu_contention"
)
# A real test file under a directory that norecursedirs prunes, so the scan must list it as neither marked nor unmarked.
PRUNED_FIXTURE_TEST_FILE = "evals/fixtures/temp-project/tests/test_calculator.py"
# A failed collect-only prints its error after the node-ID listing, so the stdout tail holds the error and the head is noise.
COLLECTION_FAILURE_STDOUT_TAIL_LINES = 40


@dataclass(frozen=True)
class _TimingCollections:
    """The collect-only results the timing-marker parity tests share."""

    not_timing_ids: list[str]
    timing_ids: list[str]
    all_ids: list[str]
    timing_files: list[str]
    scan: TimingMarkScan
    serial_deselected_ids: list[str]
    serial_deselected_result: subprocess.CompletedProcess | None


class TestNestedWorktreeExcludedFromCollection:
    """Regression test for the stale claude/.claude/worktrees/handoff-scratch
    checkout that made `pytest claude/.claude/` abort collection entirely
    with `ModuleNotFoundError: No module named 'calculator'` from
    evals/fixtures/temp-project/tests/test_calculator.py."""

    def test_seeded_nested_worktree_contributes_no_collected_tests(self):
        # No -n0 here: xdist's own pytest_configure() unconditionally skips
        # itself on --collect-only regardless of -n, so this collect-only
        # run was never going to spawn workers even with -n auto in addopts.
        #
        # pid-suffixed so concurrent `pytest claude/.claude/` invocations
        # against this checkout (routine in this repo's multi-worktree
        # workflow) don't race on the same leaf directory; self-cleaned
        # up front so a leftover from a prior interrupted run under the
        # same pid doesn't turn every subsequent run into a hard failure.
        fake_worktree = REPO_ROOT / "claude" / ".claude" / "worktrees" / f"pytest-collection-regression-fixture-{os.getpid()}"
        if fake_worktree.exists():
            shutil.rmtree(fake_worktree)
        fake_worktree_tests = fake_worktree / "sub" / "tests"
        fake_worktree_tests.mkdir(parents=True)
        (fake_worktree_tests / "test_should_never_collect.py").write_text(
            "import this_module_does_not_exist\n\n\ndef test_x():\n    assert True\n"
        )
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "claude/.claude/", "--collect-only", "-q", "--rootdir", str(REPO_ROOT)],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=120,
            )
        finally:
            shutil.rmtree(fake_worktree)

        assert result.returncode == 0, (
            f"collection failed with the fake nested worktree present "
            f"(exit {result.returncode}):\n{result.stdout}\n{result.stderr}"
        )

        # Parse collected node ids rather than substring-matching raw stdout:
        # `-q --collect-only` prints one "path::test" line per collected
        # test plus a trailing summary line with no "::" in it, so filtering
        # on "::" isolates node ids from the summary before checking each
        # one's file-path component for a "worktrees" path segment.
        collected_paths_under_worktrees = [
            line
            for line in result.stdout.splitlines()
            if "::" in line and "worktrees" in Path(line.split("::", 1)[0]).parts
        ]
        assert not collected_paths_under_worktrees, (
            f"collected node id(s) reference a path under a worktrees/ directory — "
            f"norecursedirs is not excluding nested worktree checkouts: "
            f"{collected_paths_under_worktrees}"
        )


class TestNorecursedirsDefaultsPreserved:
    """pytest's norecursedirs ini option REPLACES the built-in default list
    rather than extending it — setting norecursedirs = ["worktrees"] alone
    silently drops ".*" and re-exposes hidden directories to collection.
    This pins the configured list as a superset of pytest's own defaults,
    reading the default from pytest itself rather than a second hardcoded
    copy that could drift from the installed version."""

    def test_configured_norecursedirs_is_superset_of_pytest_defaults(self):
        # No public pytest API exposes the built-in norecursedirs default as
        # of pytest 8.4.2 (checked dir(_pytest.main) and Parser's public
        # surface) — Parser._inidict is the only source, and it already
        # raises PytestDeprecationWarning for private-attribute access.
        # Accepted trade-off: switch to a public accessor if pytest ever
        # adds one.
        import _pytest.main as pytest_main
        from _pytest.config.argparsing import Parser

        parser = Parser()
        pytest_main.pytest_addoption(parser)
        pytest_defaults = set(parser._inidict["norecursedirs"][2])
        assert pytest_defaults, "could not introspect pytest's default norecursedirs — pytest internals moved"

        import tomllib

        with (REPO_ROOT / "pyproject.toml").open("rb") as f:
            config = tomllib.load(f)
        configured = set(config["tool"]["pytest"]["ini_options"]["norecursedirs"])

        missing = pytest_defaults - configured
        assert not missing, (
            f"pyproject.toml's norecursedirs dropped pytest default(s) {missing} — "
            f"norecursedirs replaces rather than extends the built-in list, so every "
            f"default must be restated alongside any repo-specific addition"
        )
        assert "worktrees" in configured, "norecursedirs no longer excludes nested worktree checkouts"

    def test_configured_norecursedirs_excludes_the_evals_fixtures_sample_project(self):
        import tomllib

        with (REPO_ROOT / "pyproject.toml").open("rb") as f:
            config = tomllib.load(f)
        configured = set(config["tool"]["pytest"]["ini_options"]["norecursedirs"])

        assert "evals/fixtures" in configured, "norecursedirs no longer excludes the evals sample project"


class TestPythonpathIncludesScriptsDir:
    """Pins that claude/.claude/scripts is on pytest's pythonpath, so
    `from transcript_analysis.corpus import ...`-style imports resolve
    without each test file inserting the directory itself."""

    def test_pythonpath_contains_scripts_dir(self):
        import tomllib

        with (REPO_ROOT / "pyproject.toml").open("rb") as f:
            config = tomllib.load(f)
        pythonpath = config["tool"]["pytest"]["ini_options"]["pythonpath"]

        assert "claude/.claude/scripts" in pythonpath, (
            "pythonpath dropped claude/.claude/scripts — the transcript_analysis "
            "package (and any test importing it directly) would no longer resolve"
        )


class TestAddoptsConfiguresXdistAndStrictMarkers:
    """Pins that pyproject.toml's addopts actually carries -n auto and
    --strict-markers, and that --strict-markers really enforces what it's
    there for — a typo'd marker name failing collection."""

    def test_addopts_contains_xdist_auto_and_strict_markers(self):
        import tomllib

        with (REPO_ROOT / "pyproject.toml").open("rb") as f:
            config = tomllib.load(f)
        addopts = config["tool"]["pytest"]["ini_options"]["addopts"]

        assert "-n" in addopts, "addopts dropped -n — pytest-xdist parallelization is no longer configured"
        assert "auto" in addopts, "addopts dropped auto — -n is no longer paired with an auto-detected worker count"
        assert "--strict-markers" in addopts, (
            "addopts dropped --strict-markers — a typo'd marker name would silently "
            "collect unfiltered instead of failing collection"
        )

    def test_strict_markers_rejects_unregistered_marker(self, tmp_path: Path):
        bogus_marker_test = tmp_path / "test_bogus_marker.py"
        bogus_marker_test.write_text(
            "import pytest\n\n\n"
            "@pytest.mark.definitely_not_a_real_marker\n"
            "def test_x():\n"
            "    assert True\n"
        )
        result = subprocess.run(
            [
                sys.executable, "-m", "pytest", str(bogus_marker_test),
                "--collect-only", "-q",
                # -c forces the repo's own pyproject.toml to load — --rootdir alone
                # doesn't, since config-file discovery walks up from the common
                # ancestor of cwd and the test path, which excludes REPO_ROOT here.
                "-c", str(REPO_ROOT / "pyproject.toml"),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode != 0, (
            f"expected --strict-markers to fail collection on an unregistered marker, "
            f"but exit was 0:\n{result.stdout}\n{result.stderr}"
        )
        # Matches just the marker name, not pytest's full diagnostic wording —
        # that wording is an internal message, not a documented API, and isn't
        # guaranteed stable across the pytest==8.* pin range.
        assert "definitely_not_a_real_marker" in result.stdout, (
            f"expected pytest's --strict-markers error message to name the bogus marker, "
            f"got:\n{result.stdout}\n{result.stderr}"
        )


class TestTimingMarkerCoverageParity:
    """Pins that `-m "not timing"` and `-m timing` are a complementary
    partition of the full collected suite: neither invocation errors out
    (returncode asserted below) and pytest's own mark-filtering isn't
    silently broken. This does NOT catch a test losing its `timing` marker
    — `not timing` and `timing` are complementary by construction, so a
    test moving between the two buckets leaves their sum unchanged
    regardless.

    The `timing` collection also pins that select-tests.py's scan marks every file pytest collects a `timing` test
    from. A fourth collection pins that the serial pass's expression deselects the CPU-saturating `timing` test.
    One class-scoped fixture runs all four collections for the tests below."""

    @staticmethod
    def _collected_node_ids(
        marker_expr: str | None, targets: tuple[str, ...] | list[str] = FULL_SUITE_TARGETS,
    ) -> tuple[list[str], subprocess.CompletedProcess]:
        # -n0: unnecessary defensive redundancy, not a requirement — xdist's
        # own pytest_configure() unconditionally skips itself on
        # --collect-only regardless of -n, so this collect-only run was
        # never going to spawn workers even without it.
        args = [
            sys.executable, "-m", "pytest", *targets,
            "--collect-only", "-q", "-n0", "--rootdir", str(REPO_ROOT),
        ]
        if marker_expr is not None:
            args += ["-m", marker_expr]
        result = subprocess.run(
            args,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        node_ids = [line for line in result.stdout.splitlines() if "::" in line]
        return node_ids, result

    @pytest.fixture(scope="class")
    def collections(self) -> _TimingCollections:
        # Under xdist this fixture runs once in each worker that receives one of its requesting tests.
        not_timing_ids, not_timing_result = self._collected_node_ids("not timing")
        timing_ids, timing_result = self._collected_node_ids("timing")
        all_ids, all_result = self._collected_node_ids(None)
        for result in (not_timing_result, timing_result, all_result):
            stdout_tail = "\n".join(result.stdout.splitlines()[-COLLECTION_FAILURE_STDOUT_TAIL_LINES:])
            assert result.returncode == 0, (
                f"collection failed (exit {result.returncode}); stderr:\n{result.stderr}\n"
                f"last {COLLECTION_FAILURE_STDOUT_TAIL_LINES} stdout lines:\n{stdout_tail}"
            )

        timing_files = sorted({node_id.split("::", 1)[0] for node_id in timing_ids})
        # An empty target list would make pytest collect the whole rootdir, so the subset run needs a guard.
        serial_deselected_ids, serial_deselected_result = (
            self._collected_node_ids(f"{TIMING_MARKER} and not ({SERIAL_PASS_MARKER_EXPRESSION})", timing_files)
            if timing_files
            else ([], None)
        )
        return _TimingCollections(
            not_timing_ids=not_timing_ids,
            timing_ids=timing_ids,
            all_ids=all_ids,
            timing_files=timing_files,
            scan=scan_timing_marks(FULL_SUITE_TARGETS, [], repo_root=REPO_ROOT),
            serial_deselected_ids=serial_deselected_ids,
            serial_deselected_result=serial_deselected_result,
        )

    def test_not_timing_and_timing_selections_sum_to_the_unfiltered_total(self, collections):
        assert len(collections.not_timing_ids) + len(collections.timing_ids) == len(collections.all_ids), (
            f'-m "not timing" selected {len(collections.not_timing_ids)}, -m timing selected '
            f"{len(collections.timing_ids)}, but the unfiltered run collected {len(collections.all_ids)} — "
            "pytest's mark-filtering disagrees with itself across these three invocations"
        )

    def test_the_scan_marks_every_file_pytest_collects_a_timing_test_from(self, collections):
        assert collections.timing_ids, "-m timing collected no test, so the scan check below would pass vacuously"
        assert collections.scan.marked_files, "the scan found no file holding the timing mark text in the real tree"

        unmarked_timing_files = sorted(set(collections.timing_files) - set(collections.scan.marked_files))

        assert not unmarked_timing_files, (
            f"pytest collects a timing test from {unmarked_timing_files}, whose text lacks the mark; the serial pass "
            "skips a test file whose text lacks the mark, so the mark must sit in the file pytest collects the test from"
        )

    def test_the_unfiltered_collection_holds_a_test_under_every_full_suite_root(self, collections):
        roots_without_ids = [
            root for root in FULL_SUITE_TARGETS if not any(node_id.startswith(root) for node_id in collections.all_ids)
        ]

        assert not roots_without_ids, f"the unfiltered collection holds no test ID under {roots_without_ids}"

    def test_the_scan_prunes_the_evals_fixtures_sample_project_as_pytest_does(self, collections):
        assert (REPO_ROOT / PRUNED_FIXTURE_TEST_FILE).is_file(), f"{PRUNED_FIXTURE_TEST_FILE} no longer exists"

        scanned_files = [*collections.scan.marked_files, *collections.scan.unmarked_test_files]

        assert PRUNED_FIXTURE_TEST_FILE not in scanned_files, (
            f"the scan lists {PRUNED_FIXTURE_TEST_FILE}; it must prune what pyproject.toml's norecursedirs prunes"
        )

    def test_the_serial_pass_expression_deselects_the_cpu_saturating_test(self, collections):
        assert collections.serial_deselected_result is not None, (
            "-m timing collected no test, so the serial expression had no file to collect from"
        )
        serial_deselected_result = collections.serial_deselected_result
        assert serial_deselected_result.returncode in (ExitCode.OK, ExitCode.NO_TESTS_COLLECTED), (
            f"collection failed (exit {serial_deselected_result.returncode}):\n"
            f"{serial_deselected_result.stdout}\n{serial_deselected_result.stderr}"
        )

        assert serial_deselected_result.returncode == ExitCode.OK and CPU_SATURATING_TEST_NODE_ID in (
            collections.serial_deselected_ids
        ), (
            f"the serial pass's expression does not deselect {CPU_SATURATING_TEST_NODE_ID}. Either the test lost its "
            "saturates_cpu mark or no longer carries timing beside it, or the test or its class was renamed: "
            "update CPU_SATURATING_TEST_NODE_ID in the same change as the rename."
        )

    def test_scan_prunes_a_worktrees_directory_as_the_real_norecursedirs_does(self, tmp_path):
        shutil.copy(REPO_ROOT / "pyproject.toml", tmp_path / "pyproject.toml")
        marked_test_text = f"@pytest.mark.{TIMING_MARKER}\ndef test_x():\n    pass\n"
        for relative_path in ("worktrees/test_x.py", "kept/test_x.py"):
            (tmp_path / relative_path).parent.mkdir(parents=True)
            (tmp_path / relative_path).write_text(marked_test_text)

        scan = scan_timing_marks(["."], [], repo_root=tmp_path)

        assert scan == TimingMarkScan(("kept/test_x.py",), ()), (
            f"the scan must list kept/test_x.py and prune worktrees/test_x.py as pyproject.toml's norecursedirs does, "
            f"got {scan}"
        )


class TestConftestModuleNamesAreUnique:
    """Two sibling test trees each carry a conftest.py: claude/.claude/hooks/tests/
    and claude/.claude/scripts/tests/. Without a package identity, pytest's
    prepend import mode names both `conftest` and evicts the previous one
    from sys.modules before loading the next, so that slot is
    last-writer-wins. A test file's own `from .conftest import X` is an
    ordinary Python import that reads whatever sits in that slot. The
    __init__.py markers under claude/.claude/hooks/ and claude/.claude/scripts/
    give each tree a dotted name so both coexist. The package root is
    asserted as well as the name, because a tree missing only its domain
    marker (e.g. claude/.claude/hooks/__init__.py, keeping
    claude/.claude/hooks/tests/__init__.py) still produces a dotted name,
    just one level shallower than intended."""

    @staticmethod
    def _resolve(conftest_path: Path) -> tuple[Path, str]:
        """Resolve pkg_root/module_name the way pytest's own prepend-mode
        conftest loader would, including its fallback for an unpackaged
        path.

        No public pytest API exposes this resolution as of pytest 8.4.2 —
        hand-reimplementing the __init__.py walk instead of calling
        resolve_pkg_root_and_module_name would drift from pytest's own rule
        as its algorithm evolves. Accepted trade-off, matching the
        precedent at TestNorecursedirsDefaultsPreserved above: switch to a
        public accessor if pytest ever adds one.
        """
        # requirements-dev.txt pins pytest==8.*, which permits an automatic minor bump.
        # An ImportError here means such a bump renamed or removed this private
        # symbol, not that the module-naming invariant broke.
        from _pytest.pathlib import CouldNotResolvePathError, resolve_pkg_root_and_module_name

        try:
            return resolve_pkg_root_and_module_name(conftest_path, consider_namespace_packages=False)
        except CouldNotResolvePathError:
            # Mirrors import_path's own fallback for a path belonging to no
            # package at all (_pytest/pathlib.py's import_path).
            return conftest_path.parent, conftest_path.stem

    @staticmethod
    def _tracked_conftest_paths() -> list[Path]:
        out = subprocess.run(
            ["git", "ls-files", "-z", "--", "*conftest.py"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        return [REPO_ROOT / p for p in out.split("\0") if p]

    def test_every_tracked_conftest_resolves_to_a_pairwise_unique_module_name(self):
        conftest_paths = self._tracked_conftest_paths()
        assert conftest_paths, "no conftest.py tracked in the repo — did the git ls-files glob break?"

        resolved = {conftest_path: self._resolve(conftest_path) for conftest_path in conftest_paths}

        module_names = [module_name for _, module_name in resolved.values()]
        duplicate_names = {name for name in module_names if module_names.count(name) > 1}
        assert not duplicate_names, (
            f"conftest.py files resolve to duplicate module name(s) {duplicate_names} — "
            "pytest's prepend import mode gives both the same name and evicts one from "
            "sys.modules before loading the other, so a `from .conftest import X` in one "
            f"test tree can silently read the other tree's conftest instead: {resolved}"
        )

        claude_root = REPO_ROOT / "claude" / ".claude"
        for conftest_path, (pkg_root, module_name) in resolved.items():
            if claude_root not in conftest_path.parents:
                continue
            domain = conftest_path.parent.parent.name
            needed = f"claude/.claude/{domain}/__init__.py and claude/.claude/{domain}/tests/__init__.py"
            assert "." in module_name, (
                f"{conftest_path} resolved to bare module name {module_name!r} — add {needed}"
            )
            assert pkg_root == claude_root, (
                f"{conftest_path} resolved pkg_root {pkg_root}, expected {claude_root} — add {needed}"
            )

    def test_resolution_fallback_matches_pytests_own_unpackaged_path_handling(self, tmp_path: Path):
        """Unit test of `_resolve`'s own CouldNotResolvePathError fallback
        branch, exercised against a synthetic unpackaged path rather than
        the live tree — after the __init__.py markers land, every tracked
        conftest.py resolves via resolve_package_path and never trips this
        branch, so the assertion above gives it no coverage."""
        unpackaged_conftest = tmp_path / "conftest.py"
        unpackaged_conftest.write_text("")

        assert self._resolve(unpackaged_conftest) == (tmp_path, "conftest")


class TestMultiArgCollectionSpansTestDomains:
    """Reproduces the trigger shape directly, independent of
    TestConftestModuleNamesAreUnique's naming-invariant check above: two
    initial path arguments whose conftests both preload before either test
    module is imported, so the second argument's conftest evicts the
    first's from sys.modules and whichever module is named last wins,
    order-dependent. A future pytest release could change the naming rule
    the other class targets while still preserving this order-dependent
    eviction behavior, and only this class would catch that regression."""

    @pytest.mark.parametrize(
        "first, second",
        [
            (
                "claude/.claude/scripts/tests/test_token_analyzer.py",
                "claude/.claude/hooks/tests/test_require_routing_read.py",
            ),
            (
                "claude/.claude/hooks/tests/test_require_routing_read.py",
                "claude/.claude/scripts/tests/test_token_analyzer.py",
            ),
        ],
    )
    def test_collection_succeeds_regardless_of_argument_order(self, first: str, second: str):
        # Both orders: the victim is whichever argument's conftest loads
        # first, since the later argument's conftest evicts it from
        # sys.modules before that module ever imports.
        result = subprocess.run(
            [sys.executable, "-m", "pytest", first, second, "--collect-only", "-q", "--rootdir", str(REPO_ROOT)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, (
            f"collection failed for argument order ({first}, {second}) "
            f"(exit {result.returncode}):\n{result.stdout}\n{result.stderr}"
        )


class TestDirectoryPlusContainedFileCollectionPremise:
    """Pins the pytest collection premise select-tests.py's
    resolve_target_paths exists to route around: passing a directory and a
    file inside it as two initial pytest arguments makes pytest collect
    nothing from the directory, not merely less of it. Verified at pytest
    8.4.2 in this project's venv (_pytest/main.py:964-976, :916). The file
    argument's matching walk populates the shared collection cache for the
    enclosing directory node, so genitems() later sees duplicate=True for
    that directory and returns without yielding anything.

    requirements-dev.txt pins pytest==8.*, not a patch version, so a fresh
    install can land a different 8.x whose collection semantics differ from
    what this test was written against — see the assertion message below
    for how to read a red result here.
    """

    @staticmethod
    def _collected_node_ids(tmp_path: Path, *extra_args: str) -> list[str]:
        # No -n0 here: xdist's own pytest_configure() unconditionally skips
        # itself on --collect-only regardless of -n (see
        # TestNestedWorktreeExcludedFromCollection above).
        result = subprocess.run(
            [
                sys.executable, "-m", "pytest", str(tmp_path), *extra_args,
                "--collect-only", "-q", "--rootdir", str(tmp_path),
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, (
            f"collection failed (exit {result.returncode}):\n{result.stdout}\n{result.stderr}"
        )
        return [line for line in result.stdout.splitlines() if "::" in line]

    def test_directory_plus_contained_file_drops_the_directorys_other_tests(self, tmp_path: Path):
        (tmp_path / "test_a.py").write_text("def test_a_case():\n    assert True\n")
        (tmp_path / "test_b.py").write_text("def test_b_case():\n    assert True\n")

        directory_only = self._collected_node_ids(tmp_path)
        directory_plus_contained_file = self._collected_node_ids(tmp_path, str(tmp_path / "test_b.py"))

        assert set(directory_only) == {"test_a.py::test_a_case", "test_b.py::test_b_case"}
        assert set(directory_plus_contained_file) == {"test_b.py::test_b_case"}, (
            "expected the directory argument to contribute zero tests once a file "
            "inside it was also passed as an initial argument, with test_a.py's test "
            "fully absent. A red result here means an upstream pytest release changed "
            "this collection-cache behavior, not that resolve_target_paths' own dedup "
            "(select-tests.py) broke. That function stays correct either way, since "
            "it only decides what to drop, not what pytest does with what's left."
        )


class TestNoBareSameDirectorySiblingImports:
    """TestConftestModuleNamesAreUnique above only covers conftest.py's own
    module-naming collision. A test-local helper module like
    test_agent_roster.py hits the identical prepend-mode sys.path bug through
    an ordinary bare sibling import, whether `from test_agent_roster import X`
    or `import test_agent_roster` followed by attribute access, rather than
    pytest's own conftest loader, per CLAUDE.md's "audit structural siblings
    before scoping a fix narrowly" principle. This walks every tracked test
    file's AST rather than grepping for import lines, since a regex can't
    distinguish `from test_agent_roster import X` (breaks once
    claude/.claude/hooks/tests/ is no longer inserted directly onto
    sys.path) from `from .test_agent_roster import X` (an ordinary
    package-relative import that keeps working) or from a module of that
    name imported from an unrelated package. A future contributor
    copy-pasting a test file and reintroducing a bare
    `from test_agent_roster import X` or `import test_agent_roster` instead
    of the package-relative form would trip this check. Scanned trees with
    no __init__.py of their own (claude/.claude/tests/) are exempt, since
    they're never given a package identity and a bare same-directory import
    there stays correct rather than latent."""

    @staticmethod
    def _tracked_test_tree_paths() -> list[Path]:
        out = subprocess.run(
            [
                "git", "ls-files", "-z", "--",
                "claude/.claude/hooks/tests/*.py",
                "claude/.claude/scripts/tests/*.py",
                "claude/.claude/tests/*.py",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        return [REPO_ROOT / p for p in out.split("\0") if p]

    def test_no_bare_import_resolves_to_a_same_directory_sibling_module(self):
        tracked_paths = self._tracked_test_tree_paths()
        assert tracked_paths, (
            "no tracked .py files under hooks/tests or scripts/tests — did the git ls-files glob break?"
        )

        sibling_stems_by_dir: dict[Path, set[str]] = {}
        for path in tracked_paths:
            sibling_stems_by_dir.setdefault(path.parent, set()).add(path.stem)

        violations = []
        for path in tracked_paths:
            # A directory with no __init__.py (claude/.claude/tests/ stays
            # unpackaged — see .claude/rules/test-tree-packaging.md)
            # is never handed a package identity, so pytest's prepend import
            # mode keeps inserting it directly onto sys.path and a bare
            # same-directory import there stays correct rather than latent.
            if not (path.parent / "__init__.py").exists():
                continue
            sibling_stems = sibling_stems_by_dir[path.parent] - {path.stem}
            tree = ast.parse(path.read_text(), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module in sibling_stems:
                    violations.append(
                        f"{path.relative_to(REPO_ROOT)}:{node.lineno}: "
                        f"`from {node.module} import ...` is a bare import of a same-directory "
                        f"sibling module — use `from .{node.module} import ...` instead"
                    )
                elif isinstance(node, ast.Import):
                    # ast.Import has no `level` attribute — that concept is
                    # ImportFrom-only — so the sibling-stem match alone
                    # identifies the bare-import case here.
                    for alias in node.names:
                        if alias.name in sibling_stems:
                            violations.append(
                                f"{path.relative_to(REPO_ROOT)}:{node.lineno}: "
                                f"`import {alias.name}` is a bare import of a same-directory "
                                f"sibling module — use `from . import {alias.name}` instead"
                            )

        assert not violations, (
            "bare same-directory sibling import(s) found — these break once __init__.py "
            "markers stop hooks/tests/ or scripts/tests/ being inserted directly onto "
            "sys.path under pytest's prepend import mode:\n" + "\n".join(violations)
        )
