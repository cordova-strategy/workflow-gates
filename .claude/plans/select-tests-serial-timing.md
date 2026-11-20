# select-tests.py: run `timing`-marked tests serially

## Context

Goal: a local `select-tests.py` run executes `timing`-marked tests serially (`-n0`) and everything else in parallel under pytest-xdist, the same split CI uses, so a scoped local pass stops disagreeing with CI on timing-sensitive tests.

Ask: "let's do #1, that seems worthwhile" — the engineer's words as relayed by the prior session's handoff brief (`~/.claude/briefs/select-tests-serial-timing-task.md`), where "#1" is the brief's §1 goal restated above. Widened mid-planning with a constraint, in the engineer's words: "I am worried that running tests locally like CI does will lead to more load on the machine".

`select-tests.py` picks the test files a diff touches and runs them in one pytest invocation under xdist (`main()` → `build_pytest_argv` → `run_pytest`, `claude/.claude/scripts/select-tests.py:1249-1435`). That invocation includes `timing`-marked tests. The marker's own definition (`pyproject.toml:34`) says to "run serially (-m timing -n0)". CI already splits them: `.github/workflows/tests.yml:222` runs `-m "not timing"` and `:227` runs `-m timing -n0`. Under xdist, `timing` tests flake from sibling-worker load; one such flake was fixed in PR #1539, but the local runner still exposes these tests to that load.

Decisions this plan settles:

- The split mechanism: two pytest invocations, or a lighter pytest/xdist primitive if one gives true serial isolation.
- How the two legs' exit codes merge into one exit status, including exit 5 (no tests collected) in one or both legs.
- How caller passthrough arguments interact with the added `-m`: a caller's `-m` combines rather than being overridden, a caller's `-k` applies to both legs, and what a caller's `-n` means for the serial leg.
- Whether the full-suite widening path gets the same split.

Out of the brief's scope from the start: a cold-stub prewarm guard in `evals/conftest.py`, pid-path quoting in `evals/test_replay_bench_launch.py`, refactoring the domain-mapping table or worker heuristics beyond the split, and changing `tests.yml`.

## Approach

`select-tests.py` splits a run into two pytest passes over the same resolved targets, matching `tests.yml`'s two steps with one named difference. First a parallel pass runs `-m "not timing"`. Then a serial pass runs `-m "timing and not saturates_cpu" -n0` and skips, with one `--ignore` each, the selected test files whose text lacks `mark.timing`. The difference from CI is the `saturates_cpu` exclusion, which keeps the one `timing` test that starts a busy process per core in CI only. The serial pass runs after every parallel result except exit 3, exit 4 or a death by signal, and the run exits with one merged status. A test in `test_pytest_collection_config.py` fails CI when pytest collects a `timing` test from a file the scan would skip, or when the CPU-saturating test no longer carries `saturates_cpu`.

The run uses one unsplit pass instead, with the caller's arguments verbatim as today, in four cases:
- a caller argument is an `@file`;
- a caller argument is a bare `--`;
- the run would start no xdist workers;
- no selected file contains `mark.timing`.

The engineer's load concern (row 27) shapes five of these choices:
- the collapses skip a pass that would buy nothing, and the first three also skip the scan;
- the narrowing limits the serial pass's collection to the marked files;
- the serial pass leaves out the one test that saturates every core;
- the skip rule starts no second pass after a pytest error or a kill;
- the guard reuses the collections its test already runs, and adds one over only the marked files.

A new module, `claude/.claude/scripts/_timing_split.py`, holds the scan, the pass plan, the skip rule and the exit-code merge. `main()` runs the passes it plans. This plan calls the invocations "passes", the term README.md:570 already uses for CI's split. The Step 4 questions called them "legs".

Alternatives weighed (M1, M8 and M12 hold the lighter-primitive checks):

- **One invocation with `--dist loadgroup` and an `xdist_group` on every `timing` test.** Rejected: the group runs on one worker while the other workers keep running, so the sibling-worker load stays (G2).
- **`-n0` for the whole selection.** Rejected: it runs serially, but it gives up parallelism for every non-`timing` test.
- **Deselecting through a pytest plugin instead of combining `-m`.** This means a `-p` module or a root `conftest.py` that adds a pass option and a `pytest_collection_modifyitems` hook. It would compose with every caller `-m` form. Rejected: it loads a new plugin into every split run, xdist workers included (row 20), only to cover `-m` forms no caller uses. Every form the token scan misses already leaves the split intact (row 9).
- **A prefilter that skips only the serial pass and keeps `-m "not timing"` on the parallel pass.** Rejected: a test the scan missed would then run in neither pass. An empty scan runs one unsplit pass instead, which turns a miss into today's behavior (row 31).
- **Narrowing by passing the marked files as the serial pass's targets,** the session's description in row 40. Set aside for `--ignore` (M8). An explicit file argument bypasses pytest's `python_files`, `norecursedirs` and `--ignore` filters (G8), so the plan would have to re-implement each one. Expanding a selected directory into files would also stop a caller's file from shadowing it, and a file named twice is collected twice. With `--ignore`, pytest still walks the targets itself, and a scan error only widens the serial pass.
- **Narrowing with `-k` or `--deselect`.** Rejected: both filter after collection (`_pytest/main.py:440-455`), so they save none of it. `--ignore-glob` matches path patterns, not file contents.
- **An AST pin on how the marker is applied.** Set aside for the collection-based guard (rows 44-45). The pin missed aliases, variable names and cross-file imports. The guard reads pytest's own collected IDs from a collection its test already runs.
- **Treating every caller argument that does not start with `-` as a possible path that forces the split.** Rejected: `-n 4` and `-k foo` would then always pay for the serial pass, which works against the engineer's load concern (row 27). The scan reads only the caller arguments that name an existing path and are not a recognized `-k`, `-m` or `-n` value (row 32).
- **Inserting the pass options before the caller's arguments.** Rejected: pytest would then parse a caller's `-n` after the serial pass's `-n0`, and the caller's value would win (G2). The serial pass would have to remove it. Appending the options after the caller's arguments needs no removal (M3).
- **Splitting a run whose caller arguments hold a `--`, by moving every option ahead of the targets.** Set aside for the collapse the engineer chose (row 67). Appended pass options become paths after a caller's `--`, and options inserted before that `--` make pytest reject it (G4). Moving the caller's options out of the way would need pytest's whole option table, to tell which options take a value. It would also reorder `build_pytest_argv`'s targets-first argv for a form no in-repo caller uses (row 19).
- **Failing loudly on an unrecognized `-m` form.** Rejected: a token starting `-m` is never another option's value (G4), so only a short-flag cluster is ambiguous. Telling `-vm X` from `-kmatch` would need pytest's whole short-option table. A heuristic error would break `-kmatch`, which pytest accepts today. Row 9 records what a cluster does instead: the split stays intact and the run widens.
- **Collapsing on a bare `--pdb`.** Set aside. xdist runs a `--pdb` invocation with no workers when its `-n` is `auto` (`xdist/plugin.py:310-313`), so the split then runs two serial sessions. The results stay correct, and the cost is one extra, narrowed collection. README.md:556 already tells `--pdb` users to pass `-n0`, which collapses.
- **Collapsing when the run has one worker.** The engineer first chose this, then chose "Effective 0 only" (rows 41, 46). A one-worker run still runs its `timing` tests inside a worker. The narrowed serial pass costs little.
- **Running the CPU-saturating test in the local serial pass.** The engineer chose to keep it CI-only (row 60). M12 holds the lighter-primitive checks.
- **Adding `-o tmp_path_retention_count=2` to the serial pass.** The engineer first chose this, then chose "Drop; document" (rows 43, 48). README names the loss instead (row 26).
- **Keeping the split inline in `select-tests.py`, tested in `test_select_tests.py`.** Rejected: both files are already over the repo's 1,000-line limit (row 22). A separate test file for an inline split would also need a second `importlib` loader for the hyphenated script.
- The engineer's answers set aside further options. One item per round:
  - rows 2-7, the Step 4 answers;
  - row 29;
  - row 42;
  - rows 62 and 64;
  - row 67.

### Assumption ledger

**Root:** `select-tests.py` runs every selected test in one xdist invocation (row 1). So `timing`-marked tests run under sibling-worker load that CI's serial step (`tests.yml:227`) never puts them under, and a scoped local pass can disagree with CI on them.

**Givens:**
- G1. pytest's `-m` is one `store` option with no long alias, so the last `-m` pytest parses wins (`_pytest/mark/__init__.py:112-120`). An empty value means no filter (`:258-259`). Its expression grammar accepts `(<expr>) and not <ident>` (`_pytest/mark/expression.py:5-8`). Reason: pytest owns its option and expression grammar.
- G2. xdist's `-n` is a `store` option (`xdist/plugin.py:70-77`), so the last `-n` wins. A count of 0 or less is the only serial mode, and it applies to a whole invocation. No `--dist` mode idles the other workers while a subset runs. `loadgroup` pins a group to one worker while the rest continue (`xdist/scheduler/loadgroup.py:10-13`, from the Step 3 evidence). How many workers a run starts:
  - `-n0` sets `dist = "no"` and starts none (`:326-328`).
  - With `-n auto` or `-n logical`, xdist reads `PYTEST_XDIST_AUTO_NUM_WORKERS` with `int()`. An empty or unparseable value falls through to a CPU count (`:15-24`, `:310-316`).
  - It builds its worker list as `["popen"] * n` (`:318-328`), so a count of 0 or less starts none. A negative `--maxprocesses` caps the count below 0 and also starts none (`:321-324`).
  - `--pdb` with `-n auto` starts none (`:310-313`). `--pdb` with workers is a usage error, exit 4 (`:330-334`).

  Reason: pytest-xdist owns its scheduling.
- G3. pytest assembles its arguments as the ini `addopts`, then `PYTEST_ADDOPTS`, then the command line (`_pytest/config/__init__.py:1386-1397`). So pytest parses a command-line option after `pyproject.toml:27`'s `-n auto` and after anything in `PYTEST_ADDOPTS`. Reason: pytest owns argument assembly.
- G4. CPython 3.14's `argparse.py` handles the short options. pytest's parser subclasses it (`_pytest/config/argparsing.py:423-438`).
  - `-m X`, `-mX` and `-m=X` all give `-m` the value `X` (`:2453-2456`, `:2500-2511`, `:2190-2192`).
  - It unpacks a short-flag cluster such as `-vm X` (`:2161-2187`).
  - Every token after a bare `--` is positional (`:2082-2085`). M3 builds a split pass's argv as the targets, then the caller's arguments, then the pass's options. A caller `--` therefore turns the pass's `-m` and its expression into two more paths, and pytest reports `file or directory not found: -m` (`_pytest/main.py:1058-1062`), a usage error, exit 4 (row 71).
  - pytest's `file_or_dir` positional takes `nargs="*"` (`_pytest/config/argparsing.py:129`). argparse drops a `--` only while it consumes that positional's group of tokens (`argparse.py:2240-2248`), and the positional is then spent (`argparse.py:2258`). So in an argv where an option follows the targets and a `--` follows that option, the `--` lands among the unrecognized arguments. That is the shape of a caller's own `-k p -- <path>`, and of pass options inserted before a caller `--`, which no split builds. pytest rejects any unrecognized argument that starts with `-` (`_pytest/config/argparsing.py:459-469`), a usage error, exit 4 (row 71).
  - It always reads a token starting `-m` as an option, never as another option's value (`:2434-2463`).
  - `--numprocesses` matches only when spelled in full, because pytest's parser sets `allow_abbrev=False` (`_pytest/config/argparsing.py:436`).
  - pytest's parser sets `fromfile_prefix_chars="@"` (`_pytest/config/argparsing.py:437`), so argparse replaces a token starting with `@` with the lines of the file it names.

  Reason: the standard library owns this grammar.
- G6. Other processes on the machine, such as concurrent runs from other worktrees, still load the serial pass. Reason: one run cannot control them. This plan removes only the run's own sibling workers.
- G8. pytest applies `--ignore` only while it walks a directory, and never to an initial path, one named on the command line (`_pytest/main.py:523-544`, `_pytest/python.py:697-707`). It turns each `--ignore` value into an absolute path from its own working directory (`_pytest/main.py:404-409`). A file it skips this way is never imported, because the check runs before `pytest_collect_file` (`_pytest/main.py:540-543`). An initial file path also bypasses `python_files` (`_pytest/python.py:185-191`). Reason: pytest owns collection.

**Mechanisms:**
- **M1. Two pytest invocations when the run splits, parallel first.** When no collapse case applies (M6, M7), `plan_passes` splits the run. `main()` runs the parallel pass, then the serial pass, over the same `resolved_targets` and with the same `size_result.env`. Two invocations are heavier than one, but each lighter primitive fails:
  - A `loadgroup` group leaves the other workers running (G2).
  - `-n0` for everything drops all parallelism.
  - No xdist mode idles workers within one session (G2).

  Parallel runs first, matching CI's step order. That way the load average is sampled just before the only pass that uses it (row 15).

  `skips_serial_pass(parallel_exit_code)` returns True for `ExitCode.INTERNAL_ERROR`, `ExitCode.USAGE_ERROR` and any negative code, which a death by signal gives. `main()` then starts no serial pass. Every other code, exit 2 included, still runs the serial pass (row 29).

  anchors: root, row1, row15, row29, row42, row52
- **M2. Recognize the caller's own `-m` and combine it.** `split_caller_marker_expression(caller_args)` returns the caller's expression and the arguments with every recognized `-m` removed. Its arguments never hold a bare `--`, because `plan_passes` collapses such a run first (M6). It reads these forms:
  - A bare `-m` takes the next token as its value when that token exists and does not start with `-`. Otherwise the `-m` stays in place. pytest then reports its own usage error (G4), except for a token shaped like a negative number, such as `-1`, which it takes as the value (row 9).
  - A token starting `-m=` takes the rest after the `=`.
  - Any other token starting `-m` takes the rest after the `-m`.
  - The last value is the caller's expression, as in pytest (G1).
  - Only the exact value `""` counts as no expression (G1). `-m ' '` stays an expression, so pytest rejects its wrapped form instead of silently deselecting every test.
  - Row 9's forms stay in place, and each pass's own `-m` overrides them.

  Each pass then uses `(<caller>) and not timing` or `(<caller>) and timing and not saturates_cpu` (M12), or the bare pass expression when the caller has none. The lighter alternatives fail:
  - Leaving the caller's `-m` in place lets the pass's later `-m` silently drop it (G1).
  - Letting it disable the split is the answer the engineer rejected (row 2).

  Neither M2 nor M7 moves or drops a caller path in argv, so the deliberate shadowing that `test_select_tests.py:2296-2300` pins still stands.

  anchors: row2, row3, row9, row10
- **M3. Each pass's options go at the end.** `plan_passes` appends each split pass's options after the caller's remaining arguments. pytest therefore parses them after `addopts` and `PYTEST_ADDOPTS` (G3) and after any caller `-n <N>`, so the serial pass's `-n0` wins (G2). The parallel pass keeps the caller's `-n <N>`. A split pass's arguments never hold a `--`, because a caller `--` collapses the run (M6).

  anchors: row6, row67
- **M4. Merge the exit codes. A pass that collected nothing defers to the other.** `merge_pass_exit_codes(exit_codes)` takes the codes of the passes that ran, in run order, and drops every `ExitCode.NO_TESTS_COLLECTED`.
  - If no code remains, it returns `NO_TESTS_COLLECTED`.
  - Otherwise it returns the first code that is not `ExitCode.OK`, taking the parallel pass first.
  - If every remaining code is `OK`, it returns `OK`.
  - An empty list raises `ValueError`, since every plan runs at least one pass.
  - A skipped serial pass contributes no code, so the parallel pass's code is the result.
  - A negative returncode from a pass killed by a signal counts as a failure.
  - It returns a plain `int`.
  - Exit 2 ranks like any other failure, by run order alone, because under xdist an ordinary failure under `-x` also exits 2 (row 17).

  anchors: row4, row5, row11, row17, row29, row42
- **M5. Stderr and the selection log.** The existing scope and sizing lines print once, unchanged.
  - An unsplit run prints one line before its pass, `select-tests: one pass, not split: <reason>`, and no summary line. The reason is one of `a caller argument starts with @`, `a caller argument is --`, `the caller's -n is 0 or less`, `PYTEST_XDIST_AUTO_NUM_WORKERS is 0 or less`, or `no selected file contains mark.timing`.
  - A split run prints a header before each pass, `select-tests: <name> pass: <options>`, with the options joined by `shlex.join`. The serial header adds the number of files it skips. With no caller `-m`, the headers read `select-tests: parallel pass: -m 'not timing'` and `select-tests: serial pass: -m 'timing and not saturates_cpu' -n0; skipping unmarked test files: <n>`.
  - After both passes it prints `select-tests: parallel pass exited <p> in <s>s, serial pass exited <q> in <t>s; exiting <merged>`. Each time is a `time.monotonic()` difference with one decimal. A reader who tails the output then sees the run's result and cost, not just the serial pass's summary.
  - After a skip it prints `select-tests: parallel pass exited <p> in <s>s; serial pass skipped; exiting <p>`.

  `record_selection` still writes one line before any pass and gains no field (row 16).

  anchors: row13, row16, row42
- **M6. Collapse when the caller's arguments cannot be split safely, or the run starts no workers.** `plan_passes` checks three cases before M7's, in this order:
  - A caller token starts with `@`. argparse expands that file (G4), where no scan here can see a `-m`, `-n` or `--` inside it.
  - A caller token is a bare `--`. A split pass appends its options after that `--`, where pytest reads them as paths and exits 4 (G4, row 71). The unsplit pass keeps today's argv, so a `-- <path>` form that runs today still runs.
  - `no_workers_reason` returns a reason.

  The first case that applies plans one unsplit pass with the caller's arguments verbatim. The `--` case reads only the caller's arguments. A bare `--` in `PYTEST_ADDOPTS` stays unseen, and it makes a split run fail instead of widening (row 73, Out of scope).

  `no_workers_reason(caller_args, *, auto_num_workers)` returns M5's unsplit reason when the run would start no xdist workers, and None otherwise. `auto_num_workers` is the value of `PYTEST_XDIST_AUTO_NUM_WORKERS` in `size_result.env`, the environment pytest will see. It reuses M2's option scan:
  - It reads `-n X`, `-nX`, `-n=X`, `--numprocesses X` and `--numprocesses=X`, and the last occurrence wins (G2).
  - A caller value that parses as an integer of 0 or less returns the caller reason, since xdist starts no workers for either (G2). It parses with `int()`, as xdist's `parse_numprocesses` does (`xdist/plugin.py:56-60`).
  - With no recognized `-n`, or one whose value is `auto` or `logical`, it reads `auto_num_workers` the same way (G2). A value of 0 or less returns the environment reason. An empty or unparseable value counts as unset, as in xdist.
  - Every other value returns None, an unparseable caller value included. pytest then reports the bad value itself.
  - It does not see a cluster such as `-vn0`, `-n` in `PYTEST_ADDOPTS`, `--pdb`, or a separated negative value such as `-n -1`, whose next token starts with `-`. Such a run splits with both passes serial. The results stay correct, at the cost of one extra collection.
  - It does not read `--maxprocesses`. xdist ignores a value of 0, and a positive value leaves at least one worker (`xdist/plugin.py:321-324`). A negative value starts none (G2), so such a run also splits with both passes serial.

  `select-tests.py`'s own sizing never writes 0, because `compute_worker_count` floors at one worker (`select-tests.py:1268-1284`), so only a caller's own setting starts no workers.

  anchors: row27, row28, row41, row46, row47, row64, row65, row67, row68, row71, row73
- **M7. Scan the selection, and collapse when nothing carries the mark.** `scan_timing_marks(target_paths, caller_args, *, repo_root)` returns a `TimingMarkScan` of the selection's marked files and its unmarked test files. Two rules classify a file:
  - It is marked when its bytes contain `TIMING_MARK_TEXT` (`f"mark.{TIMING_MARKER}"`), or when it cannot be read.
  - It is an unmarked test file when the scan found it by walking a directory, it is not marked, and it matches pytest's default `python_files` patterns `test_*.py` and `*_test.py` (`_pytest/python.py:85-88`). `pyproject.toml` sets no `python_files`.

  What it scans:
  - each resolved target, and each caller argument that names an existing path under `repo_root` (row 32);
  - a file named directly, read whatever its name, because pytest collects it whatever its name (G8);
  - a directory, walked, reading only the files that match the two patterns;
  - no subdirectory that matches a `norecursedirs` pattern in `repo_root`'s `pyproject.toml`. It matches as pytest's `fnmatch_ex` does (`_pytest/pathlib.py:446-452`): a pattern without `/` against the directory's name, and a pattern with `/` against its absolute path with `*/` prefixed. So `evals/fixtures` matches `<repo_root>/evals/fixtures`. A scanned path itself is never pruned, as pytest never prunes an initial path.
  - no path that does not exist, since pytest reports a missing path itself;
  - no caller path outside `repo_root`, which it skips without raising (row 32);
  - every matching file, with no early stop, since M8 needs the whole unmarked list (row 33).

  What it returns:
  - repo-relative POSIX paths, deduplicated and sorted;
  - paths built from the walk without resolving symlinks, so they match the paths pytest builds from the same working directory (G8).

  `plan_passes` calls the scan only after M6's three cases decline, so an `@file`, `--` or no-worker run reads no file. It therefore takes the scan as a zero-argument callable. Passing a finished scan would read every selected file for those runs too. Splitting `plan_passes` into an argument check and a scan check would move the case order into `main()`, where only the `main()` tests could pin it. When `marked_files` is empty, `plan_passes` plans one unsplit pass with the caller's arguments verbatim.

  Every scan error widens the run:
  - An unreadable file counts as marked. It is never skipped, and it can only cause a split.
  - A file the scan misses, such as one under an unreadable or symlinked directory, is never skipped. The serial pass collects it as today. If its mark is the only one, the run at worst collapses to today's single pass.
  - A `pyproject.toml` that is missing, whose read raises `OSError`, whose decode or parse raises `ValueError`, or whose `tool.pytest.ini_options.norecursedirs` path lacks a step or holds a value of the wrong type prunes nothing (row 72). The scan then reads more files instead of raising. A `RecursionError` from a pathologically nested file is not caught (row 72).

  anchors: row12, row27, row31, row32, row33, row36, row72
- **M8. Narrow the serial pass with `--ignore`.** `plan_passes` gives the serial pass one `--ignore=<path>` for each of the scan's unmarked test files, after its `-m` and `-n0`, at the end of its arguments (M3). pytest still walks the targets itself and skips each listed file before importing it (G8). The parallel pass is not narrowed, because a marked file can hold unmarked tests.
  - The caller's own paths stay initial paths, which `--ignore` never touches (G8). The plan adds no path, so the shadowing at `test_select_tests.py:2296-2300` and pytest's duplicate handling stay as today. So this narrowing needs none of the caller-path rules that explicit file targets would (row 40).
  - A file the scan fails to list is collected as today, so a scan error widens the serial pass and never drops a test from it.
  - The one exception is a `timing` test collected from a file whose own text lacks the mark, such as a marked test imported from another module (row 50). The serial pass skips that file and the parallel pass deselects the test, so a local run runs it in neither pass. M9's guard fails CI on it.

  Each lighter primitive fails:
  - `-k` and `--deselect` act after collection (`_pytest/main.py:440-455`), so they save none of it.
  - Explicit file targets bypass pytest's own collection filters (G8).
  - A plugin would load into every split run (row 20).

  The cost is one argv token per unmarked file, plus per-entry work that grows with walked entries times `--ignore` values (row 55). Whether the narrowing still saves CPU at full-suite scale is unmeasured. Verification step 2 measures it and stops for the engineer if it does not (rows 62-63).

  anchors: row14, row39, row40, row50, row55, row62, row63
- **M9. A collection-based guard backs the narrowing and M12's marker.** `TestTimingMarkerCoverageParity` (`claude/.claude/tests/test_pytest_collection_config.py:200-245`) collects the suite three times: with `-m "not timing"`, with `-m timing`, and unfiltered. It now collects every `FULL_SUITE_TARGETS` root instead of `claude/.claude/` alone. Its test adds these assertions on the IDs it already collects and on one scan of the real tree:
  - the `-m timing` IDs are not empty;
  - `scan_timing_marks(FULL_SUITE_TARGETS, [], repo_root=REPO_ROOT).marked_files` is not empty;
  - every file that holds a collected `timing` test is in that `marked_files`;
  - the unfiltered IDs hold at least one ID under each `FULL_SUITE_TARGETS` root, so a root dropped from the collection fails instead of passing vacuously;
  - `evals/fixtures/temp-project/tests/test_calculator.py`, a real test file under a pruned directory, is in neither of the scan's lists;
  - no path in either list has a `worktrees` segment.

  The last two pin M7's pruning to the real `pyproject.toml`, whose `norecursedirs` holds `worktrees` and `evals/fixtures` (`pyproject.toml:40-45`).

  A fourth collection runs after those assertions, over only the files that hold a `-m timing` ID, so pytest never receives an empty target list. It collects `timing and not (<SERIAL_PASS_MARKER_EXPRESSION>)`, the tests that `-m timing` selects and the serial pass deselects. Its outcomes:
  - exit 0 with an ID from `test_cursor_adapter_shim_hook_run.py` passes;
  - exit 5, which a collection that selects nothing returns (row 11), or exit 0 with no ID from that file, fails with a message that the CPU-saturating test has lost its `saturates_cpu` mark or no longer carries `timing` beside it;
  - any other exit fails as a collection failure, with the generic message.

  So CI fails when that test's `saturates_cpu` mark is missing, removed, or has replaced `timing` (M12), even when another test carries the mark. No assertion on the three whole-suite collections can see this, because a collected ID carries no marker.

  M8's narrowing depends on the guard. M7's collapse is fail-safe without it. The guard's other properties:
  - It reads pytest's own collected IDs, so it catches every route by which a file without the mark text holds a `timing` test: an import, an alias, a conftest hook, or a `pytestmark`.
  - It calls the runner's own scan and expression constants rather than restating them.
  - Each of its three existing collections grows to the whole suite (rows 44-45, 54). The fourth adds one subprocess, bounded by the 67 marked files (row 12), and the PR body states its share of the guard's collection work (Verification step 2).
  - Its existing partition assertion must hold over the wider scope.

  anchors: row44, row45, row50, row53, row54, row60
- **M10. Tests.**
  - A new `test_timing_split.py` holds table tests for M1's skip rule and M2-M8. Its contract test runs real pytest on a throwaway project with the argv `plan_passes` builds. That checks G1-G4, G8, rows 9 and 71, and M12's exclusion at run time, which no table test can.
  - New `main()` tests in `test_select_tests.py` cover every collapse reason, the skip rule, the merge order and a raising first pass. Two wiring tests run the real scan on a `tmp_path` repo root. A CI parity test maps each pass's options one-to-one onto a `tests.yml` step, after removing M12's one named exclusion.
  - Selection tests pin the new `CROSS_DOMAIN_EXCEPTIONS` row (row 53).
  - The existing `main()` tests that assert on calls patch the scan with a recording stub (row 21).
  - M9's guard extends the existing collection test.

  anchors: row21, row22, row24, row35, row53, row56, row67, row71
- **M11. Docs.** README.md gains the split's caller-facing contract, and CHANGELOG.md gains a `### Changed` bullet (row 23).

  anchors: row18, row19, row23, row26, row60, row67
- **M12. The serial pass leaves out the CPU-saturating test.** The one `timing` test that starts a busy process per core (row 51) gains a second marker, `saturates_cpu`. `pyproject.toml`'s `markers` list registers it, which `--strict-markers` requires (row 66). The serial pass's expression is `timing and not saturates_cpu`, or `(<caller>) and timing and not saturates_cpu` (M2). So a split run never runs that test, and CI's serial step, `-m timing -n0`, still does.
  - The parallel pass needs no change, since `not timing` already excludes the test.
  - An unsplit run adds no `-m`, so a `-n 0` run still runs the test, as today.
  - M9's guard, its partition assertion and the contract test still hold, because the test stays `timing` and sits in a file whose text holds `mark.timing`.
  - The marker is always applied together with `timing`, and its registered text says so. A `saturates_cpu` test without `timing` would run in the parallel pass under xdist, locally and in CI (`tests.yml:222`).
  - M9's fourth collection fails CI when the CPU-saturating test no longer carries the marker beside `timing`.
  - The CI parity test names the exclusion as the one intended difference from `tests.yml` (M10).
  - A table test pins that `pyproject.toml` registers the marker name `_timing_split.py` uses, so a typo in the constant cannot silently disable the exclusion. `--strict-markers` already catches a typo in the decorator.
  - A split run never runs the test, under any `-m` that pytest accepts and any `-k`. A caller `-m saturates_cpu` therefore collects nothing in either pass and exits 5. README names the local routes, an unsplit `-n 0` run or a direct `pytest -m timing -n0` (M11).

  Each lighter primitive fails:
  - A pass-added `-k "not <name>"` would override a caller's `-k`, because `-k` is also a last-wins `store` option (`_pytest/mark/__init__.py:93-96`).
  - A `--deselect <node id>` or a `-k` would name another domain's test inside `_timing_split.py` and go silently dead on a rename.
  - A skip inside the test keyed on CI's `CI` environment variable would also hide it from a deliberate local `pytest -m timing -n0`.

  anchors: row27, row51, row60, row61, row66

**Rows:**
1. `main()` makes one `run_pytest` call (`select-tests.py:1434-1435`). `build_pytest_argv` returns the resolved targets followed by the passthrough arguments, unchanged (`:1249-1255`). Nothing inspects the passthrough today. [verified: read]
2. The engineer's answer on a caller's `-m`. [engineer-verified: "Combine (Recommended)"] It covers combining the caller's `-m` with each pass's marker, so that neither overrides the other.
3. The session proposed the selected option's description: detect `-m X` / `-mX`, remove it, and run `(X) and not timing`, then `(X) and timing -n0`. [unverified] This plan adopts that description. It adds three cases that follow from G1 and G4: `-m=X`, the last of several `-m`s winning, and an empty value counting as none.
4. The engineer's answer on merging exit codes. [engineer-verified: "Run both, worst wins (Recommended)"] It covers always running both passes and letting the worse code decide the result. Row 42 narrows it: the serial pass is skipped after exit 3, exit 4 or a signal.
5. The session proposed the selected option's description. Exit 5 counts as success when the other pass ran tests, and both at 5 returns 5. Otherwise the parallel pass's failure code wins, then the serial pass's. [unverified] pytest's `ExitCode` (`_pytest/config/__init__.py:92-111`) ranks no failure code above another. M4 therefore takes the description's order as what "worst" means.
6. The engineer's answer on a caller's `-n <N>`. [engineer-verified: "Parallel leg only (Recommended)"] The session's description proposed the mechanism: the serial pass appends `-n0` last, with no `-n` parsing. [unverified] M3 grounds that mechanism on G2 and G3. M6's `-n` parsing serves only the collapse in row 28.
7. The engineer's answer on the full-suite path. [engineer-verified: "Same split (Recommended)"] M1 covers it with no extra branch, since the full-suite and domain-selected paths already reach the same call (`select-tests.py:1398-1435`).
8. A caller's `-k` applies to both passes. [unverified: from the prior session's agent-authored brief, not an engineer answer] It follows from forwarding the caller's remaining arguments to both passes.
9. M2 does not recognize these caller `-m` forms:
   - a `-m` inside a short-flag cluster such as `-vm X` (G4);
   - a `-m` in `PYTEST_ADDOPTS` or in an ini `addopts`;
   - a bare `-m` followed by a token shaped like a negative number, such as `-m -1`, which pytest takes as the expression `-1`. [unverified: a reviewer's probe with pytest 8.4.2, not re-run]

   For each form, the split stays intact, and only the caller's narrowing is lost, which widens the run. [verified: G1, G3 and G4 reads. The outcome is reasoning from them.]
   - pytest parses each form before the pass's own `-m` (G3, G4), so the pass's expression wins. The parallel pass never runs a `timing` test, and the serial pass runs every `timing` test in the selection but the `saturates_cpu` one (M12).
   - To recognize a cluster, the scan would need pytest's whole short-option table, so it could tell `-vm X` from `-kmatch`.
   - A `-m` inside an `@file` no longer reaches this row, because an `@file` collapses the run (M6).

   Wrapping can also re-balance an expression pytest would reject. `slow) or (plain` becomes `(slow) or (plain) and not timing`, which parses. [unverified: a reviewer's probe, not re-run] Only a caller expression with a `)` before its `(` hits this, and M2 does not check the balance.
10. A caller token starting `-m` can only be pytest's `-m`, since M2 reads only arguments that hold no bare `--` (M6). M2's scan therefore cannot mistake another option's value for it. [verified: G4]
11. A pass that collects nothing exits 5, under xdist as well as under `-n0`. [verified: `_pytest/main.py:345-348`. `xdist/dsession.py:291` sets `testscollected` from the workers' collection.] A `--collect-only` run returns from the run loop before any test runs (`_pytest/main.py:362-363`), so one that selects nothing exits 5 too, as a reviewer's probe of M9's fourth collection showed. [verified: read. The probe was not re-run.] When both passes collect nothing, M4 returns 5, the same code today's single run returns for that selection.
12. 172 `mark.timing` marks sit in 67 files: 39 under `claude/.claude/hooks/tests`, 19 under `claude/.claude/scripts/tests`, and 9 under `evals`. [verified: Step 3 exploration count] 171 of them are `@pytest.mark.timing` decorators, and one is the class-level `pytestmark = pytest.mark.timing` at `claude/.claude/hooks/tests/test_require_plan_review.py:2080`. [verified: a Grep for that `pytestmark` form found only `:2080`. The 171 is staff-backend-engineer's round-4 recount.] A Grep for `add_marker\(|getattr\(pytest\.mark|mark\.timing` across every `*.py` file finds the same 172 hits in the same 67 files, every one of them a `test_*.py`. So no `add_marker` or `getattr(pytest.mark` call exists today. [verified: Grep] Selections under `claude-skills/` or `plugins/` therefore collapse to one unsplit pass (M7).
13. Python's `sys.stderr` is line-buffered. A header printed before `subprocess.run` therefore reaches the terminal ahead of the child's output. [unverified: CPython's documented 3.9+ behavior, not read here]
14. A split run's added collection is bounded by the marked files, and its added wall time by the serial pass's whole run. [unverified: reasoning from the facts below] The facts:
    - The split adds one pytest startup, one directory walk, and one collection of the selected files that contain `mark.timing` (M8). In the three marked directories, 39 of 157 `.py` files are marked in `claude/.claude/hooks/tests`, 19 of 204 in `claude/.claude/scripts/tests`, and 9 of 78 in `evals`. [unverified: a reviewer's count]
    - pytest's `-m` deselects only after collection (`_pytest/mark/__init__.py:257-284`), so without M8 the serial pass would collect every selected file. [verified: read]
    - Each xdist worker collects the whole selection (`xdist/dsession.py:274-293`), so the parallel pass already collects it at least twice, given `compute_worker_count`'s floor of 2 (`select-tests.py:1175`, `:1280-1284`). That is CPU work. [verified: reads]
    - The passes run back to back, so wall time grows by the serial pass's startup, its collection, and every selected `timing` test run one at a time. [unverified: reasoning]
    - Every `timing` test but one already runs inside a worker today, so it moves from the workers into one process: the same work at a lower peak, over a longer wall time. The exception is row 51's test, which skips under any worker. A split serial pass would newly run it, with one busy process per core for 300 shim runs. M12 leaves it out, so a split run adds no test that today's run skips. [verified: a Grep of every `*.py` file for `PYTEST_XDIST_WORKER`, `cpu_count(`, `worker_id`, `is_xdist`, `xdist_worker` and `workerinput` finds no other test that branches on running in a worker. The load outcome is reasoning.]
    - `--ignore` adds per-entry work during the serial pass's walk (row 55).
    - A reviewer's single sample on a heavily loaded machine put one unnarrowed serial collection of `claude/.claude/scripts/tests` at tens of seconds of CPU time. [unverified: not re-run]

    Verification step 2 measures the narrowing's net CPU, step 1's `--durations=15` lists the serial pass's slowest tests, and M5's summary line reports each pass's wall time on every run.
15. `PYTEST_XDIST_AUTO_NUM_WORKERS` affects only `-n auto` and `-n logical` (`xdist/plugin.py:310-316`). Passing the same `size_result.env` to the serial pass therefore changes nothing there. Sizing is computed once, before the parallel pass, so the stderr line and the selection log share one decision. `test_computed_worker_sizing_reaches_the_persisted_log_matching_stderr` (`test_select_tests.py:3517-3538`) pins that. [verified: reads]
16. `record_selection` logs the selection decision before pytest runs (`select-tests.py:1396`), and `test_called_before_run_pytest` pins that order (`test_select_tests.py:3842-3867`). The split changes neither the selection nor the sizing, so the record needs no per-pass field. [verified: reads]
17. A terminal Ctrl-C stops the run before the serial pass starts. `subprocess.run` kills the child and re-raises `KeyboardInterrupt` (`subprocess.py:572` in the venv's CPython 3.14), so `main()` never reaches the second call. [verified: read] The terminal delivers SIGINT to the parent as well as to pytest; that is standard job control. [unverified: not read] A signal delivered only to pytest behaves differently:
    - A kill by signal gives a negative returncode, and M1's skip rule starts no serial pass (row 42).
    - A SIGINT delivered only to pytest makes it exit 2, and the serial pass then runs (row 29). [unverified: a reviewer's reading]
    - Under xdist, `-x` and `--maxfail` exit 2 on an ordinary failure, while `-n0 -x` exits 1. [unverified: a reviewer's probe]

    No code therefore marks an interrupt, so M4 and README describe the merge by run order alone.
18. `select-tests.py` now imports `pytest`, through `_timing_split`'s import of `pytest.ExitCode` (`pytest/__init__.py:15,108`), so `pytest` becomes a runtime import of its own interpreter. [verified: reads, as are the first two items]
    - Every documented invocation is `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py` (CLAUDE.md "Commands"; README.md:575), and that venv carries pytest 8.4.2 (Step 3).
    - `_resolve_pytest_executable` (`select-tests.py:1258-1265`) falls back to a `pytest` on PATH, which let the script run under an interpreter without pytest. Such an interpreter now fails at import.
    - CLAUDE.md's discriminator-literal rule calls for the named constant instead of a raw `5` and `0`.
    - README.md says the interpreter must be able to import pytest (M11).
19. No in-repo caller passes arguments to `select-tests.py`. [verified: a Grep for `select-tests\.py \S` outside `.claude/plans/` finds only the `-k bar` fixture at `test_select_tests.py:3276`] Each pass writes a caller's report-file flag such as `--junitxml`, so the serial pass's file replaces the parallel pass's. README.md and CHANGELOG.md say so.
20. A plugin's hooks would run on xdist workers, where collection happens. [unverified: xdist's plugin propagation was not read] Only the rejected plugin alternative depends on this row. pytest imports `-p` plugins after it applies `pythonpath` (`_pytest/config/__init__.py:1404-1405`), so importability was not why that alternative was rejected.
21. Most `main()` tests use a fake `repo_root` (`test_select_tests.py:3146`, `:3173`, `:3263`, `:3386`, `:3847`). Under it no target exists, so the real scan finds no mark and `main()` would plan one unsplit pass. [verified: reads. The outcome is reasoning from M7's skip rule.] The tests that assert on calls therefore patch `_mod.scan_timing_marks` with a recording stub of signature `(target_paths, caller_args, *, repo_root)`, so they do not depend on that fact [verified: reads of `test_select_tests.py`]:
    - These patch it to return one marked file and no unmarked file, and assert two calls: `test_git_diff_unavailable_falls_back_to_full_suite` (`:3145-3170`), `test_domain_selected_paths_are_passed_through_to_run_pytest` (`:3172-3196`), `test_computed_env_reaches_run_pytest_unchanged` (`:3495-3515`), and `test_called_before_run_pytest` (`:3842-3867`).
    - `test_argv_none_falls_back_to_sys_argv` (`:3259-3283`) patches it to return no marked file and keeps its single-call assertion.
    - `test_stderr_scope_matches_recorded_pytest_argv_across_containment_collisions` (`:3348-3373`) runs against the real `_REPO_ROOT`. It patches the scan too, so it does not depend on where marks sit in the tree today.

    Each test that asserts a split clears `PYTEST_XDIST_AUTO_NUM_WORKERS`. Otherwise a developer who set it to 0 would collapse the run under test (M6), because `main()` reads the caller's value through `pytest_subprocess_env(dict(os.environ), ...)` (`select-tests.py:1393-1395`). [verified: read]

    Two kinds of fake assert nothing about calls and work unchanged: the lambdas that return 0 (`:3294`, `:3306`, `:3391`, `:3420`, `:3892`) and the fakes that raise in the empty-selection tests (`:3214-3215`, `:3246-3247`).
22. `select-tests.py` is 1,440 lines and `test_select_tests.py` is 3,898. `docs/design-decisions/code-file-line-limit.md:19` sets a 1,000-line limit for production and test files alike, and no test enforces it yet. [verified: reads. A Grep found no enforcing test.] `select-tests.py` already imports underscore modules from its own directory (`:18-20`). Tests import those modules by name through `pyproject.toml:21`'s `pythonpath`, as `claude-skills/skills/tests/test_skill_citation_grammar.py:12` does. The blanket rule at `select-tests.py:734` selects `claude/.claude/scripts/tests/` for any change under `claude/.claude/scripts/`, so it selects the new module's tests. [verified: reads]
23. The docs this plan edits read as follows. [verified: reads]
    - README.md:556 tells `--pdb` users to pass `-n0`.
    - README.md:562-565 document `PYTEST_XDIST_AUTO_NUM_WORKERS` as the way to cap workers.
    - README.md:566 says `select-tests.py` forwards `-n <N>` to pytest.
    - README.md:570 calls CI's two invocations the parallel and serial passes.
    - README.md:572-578 introduce `select-tests.py`.
    - CHANGELOG.md's `## [Unreleased]` opens with `### Changed` at `:7`. Earlier `select-tests.py` behavior changes are bullets there (`:291`, `:425`, `:580`, `:626`).
24. `test_full_suite_targets_equal_the_roots_of_every_ci_pytest_and_lint_step` (`test_select_tests.py:2772-2775`) already pins `select-tests.py` against `tests.yml` through `ci_test_slice_job` (`claude/.claude/tests/helpers.py:2713-2715`). `TestPytestTwoPassSplit` (`claude/.claude/tests/test_ci_path_filter.py:251-264`) pins CI's own split. [verified: reads]
25. The Ask is "let's do #1, that seems worthwhile". [unverified: relayed by the prior session's brief, not said this session]
26. `tmp_path_retention_policy = "failed"` and `tmp_path_retention_count = 1` (`pyproject.toml:31-32`) govern the `tmp_path` directories. A session that passes removes its own base directory when it finishes (`_pytest/tmpdir.py:279-297`). At exit, each session that created a base directory removes every numbered one but the newest `keep` (`_pytest/pathlib.py:344-353`, `:377-404`). [verified: reads] So a failing parallel pass's directory survives a serial pass that passes or never uses `tmp_path`. It is lost in two cases [verified: reasoning from those reads]:
    - the serial pass also fails after using `tmp_path`;
    - any other pytest session for the same user exits. Today's single run is exposed to this one as well.

    README.md names the loss (row 48).
27. The engineer's concern, typed after the adversarial review: [engineer-verified: "I am worried that running tests locally like CI does will lead to more load on the machine"] It covers the extra load the split adds to a local run. Rows 14, 28-33 and 39-49 weigh that load.
28. The engineer's answer on a caller's `-n 0`. [engineer-verified: "Collapse on -n0 (Recommended)"] It covers running one unsplit invocation, with the caller's arguments verbatim, when the caller's `-n` is 0. The session proposed the description: parse `-n0`, `-n 0` and `--numprocesses=0`, and send any other `-n` to the parallel pass only. [unverified] M6 adds `-n=0`, `--numprocesses 0`, last-wins (G2, G4), and xdist's integer reading (`xdist/plugin.py:56-60`). Approach records why a bare `--pdb` does not also collapse.
29. The engineer's answer on fail-fast flags. [engineer-verified: "Keep run-both (Recommended)"] It covers running the serial pass after a failed parallel pass even under `-x`, `--maxfail` or `--pdb`, with no fail-fast parsing. Row 42 narrows it: the serial pass is skipped after exit 3, exit 4 or a signal, which covers `--pdb` with workers (exit 4).
30. Hooks test modules import names from sibling test modules, for example `claude/.claude/hooks/tests/test_check_python_floor.py:33-35` and `test_continuity_glob_parity.py:25-28`. [verified: Grep] pytest collects a test function or class that one test module imports from another inside the importing module as well. [unverified: pytest's collection of imported names was not read] So a marked test can be collected in a file whose text has no mark. Row 50 records probes showing pytest does collect it there. That is why M8's narrowing needs M9's guard, and why M7 falls back to the unsplit pass instead of dropping tests.
31. The engineer's answer on a prefilter. [engineer-verified: "Add prefilter (Recommended)"] It covers scanning the selection for `mark.timing` and skipping the serial pass when nothing matches. The session proposed the description [unverified]:
    - scan the resolved target files and skip the serial pass when none match;
    - add a test pinning that the marker is applied only as a literal in test files;
    - run the serial pass anyway when a caller passes path arguments the scan cannot see.

    M7 adopts the scan. M9's collection-based guard replaces the pin (row 44). The plan departs from the description in two places. First, a selection with no match runs one unsplit pass, as today, instead of the parallel pass alone. A miss then leaves a test running under xdist, never in neither pass (row 34). Second, M7 scans the caller arguments that name existing paths (row 32), instead of treating every caller path as unseen.
32. A caller argument is scanned when it does not start with `-` and names an existing path under `repo_root` once any `::` suffix is removed. [unverified: reasoning, as are the first three rules below] The other rules:
    - The scan skips every value M2's shared option scan recognizes for `-k`, `-m`, `-n` or `--numprocesses`. So the `foo` in `-k foo` never counts, even when a directory named `foo` exists. The arguments it reads hold no bare `--`, because `plan_passes` collapses such a run before it calls the scan (M6, M7).
    - Another option's value that names a path, such as `--ignore <dir>`, is scanned. At worst that splits a run that could have collapsed.
    - Some paths stay out of the scan's sight: module names under `--pyargs` and paths in `PYTEST_ADDOPTS`. For those, the verdict rests on the resolved targets, and a miss falls back to the unsplit pass.
    - A path outside `repo_root` after `os.path.normpath`, such as an absolute path elsewhere, is skipped without raising. `Path.relative_to` would raise `ValueError` on it. [unverified: a reviewer's probe] pytest still collects that path in both passes as an initial path, so a skip at worst collapses the run to today's single pass or widens the serial pass.
    - `run_pytest` runs pytest with `cwd=repo_root` (`select-tests.py:1322`, `:1435`), so a relative caller path resolves against `repo_root`. [verified: read]
33. The scan reads every test-pattern file under the scanned directories, with no early stop, because M8 needs the whole unmarked list. The four roots hold about 21 MB of `.py` files. [unverified: a reviewer's measurement] A full-suite run reads the test files among them once. [unverified: not timed]
34. CI's split is `-m "not timing"` (`tests.yml:222`) and `-m timing -n0` (`:227`), and it runs every `timing` test in the suite serially on every PR and main push, whatever `select-tests.py` runs locally. [verified: read] This plan mirrors that split, apart from M12's `saturates_cpu` exclusion, and leaves `tests.yml` unchanged (Out of scope). `docs/design-decisions/ci-stays-an-unconditional-full-suite-backstop.md` records why CI always runs the whole suite.
35. The engineer's answer on the CI parity test, now in M10, which the Ask did not call for. [engineer-verified: "Keep it (Recommended)"]
36. The engineer's answer on row 31's two departures from the prefilter description. [engineer-verified: "Accept both (Recommended)"]
37. The engineer's confirmation of the relayed Ask quote (row 25). [engineer-verified: "Yes, accurate"]
38. The engineer's answer on the ~600-line projected diff. [engineer-verified: "Proceed anyway"]
39. The engineer's answer on narrowing the serial pass. [engineer-verified: "Narrow, with guard (Recommended)"] It covers collecting, in the serial pass, only the selected files that contain `mark.timing`.
40. The session proposed the selected option's description [unverified]:
    - the serial pass targets only the marked files;
    - a collection-based test asserts that every collected `timing` test sits in a file containing the mark text, so an import or alias fails CI instead of being skipped;
    - the guard likely lives in `claude/.claude/tests/test_pytest_collection_config.py`.

    It reversed this plan's earlier rejection of narrowing. The plan adopts the guard (M9) and the narrowing, but not "targets only the marked files": M8 keeps the targets and skips each unmarked test file with `--ignore`. A model's later review found that explicit file targets need three extra rules: no narrowing when a caller argument names a path, the `python_files` patterns, and the `norecursedirs` pruning. [unverified: model output relayed by the session] `--ignore` needs none of them for correctness (G8, M8).
41. The engineer's first answer on the collapse threshold. [engineer-verified: "Collapse at ≤1 (Recommended)"] It covered collapsing any run whose effective worker count is 0 or 1. Row 46 supersedes it.
42. The engineer's answer on a parallel pass that exits 3, exits 4 or dies from a signal. [engineer-verified: "Skip on 3/4/signal (Recommended)"] It covers skipping the serial pass and returning that code. The question stated that row 29's run-both answer for exit 2 stands.
43. The engineer's first answer on `tmp_path` retention. [engineer-verified: "Add the option (Recommended)"] It covered adding `-o tmp_path_retention_count=2` to the serial pass. Row 48 supersedes it.
44. The engineer's answer on the guard's scope. [engineer-verified: "All four roots (Recommended)"]
45. The session proposed the selected option's description [unverified]: widen the existing timing collection in `TestTimingMarkerCoverageParity` to every `FULL_SUITE_TARGETS` root, and assert on the IDs it already collects. That adds no subprocess, but each of the test's three collections grows to the whole suite. The partition test's own assertion must still hold over the wider scope. M9 adopts it with one departure: the fourth collection, for M12's marker, adds one subprocess. The PR body states that collection's share of the guard's collection work (Verification step 2). The description's premise holds: `_collected_node_ids` collects `claude/.claude/` alone (`test_pytest_collection_config.py:209-229`). [verified: read]
46. The engineer's answer on the collapse threshold. [engineer-verified: "Effective 0 only (Recommended)"]
47. The session proposed the selected option's description [unverified]: collapse only when the run has no workers. A run capped at one worker still splits, but the narrowed serial pass costs little, and every `timing` test runs truly serially. M6 adopts it.
48. The engineer's answer on `tmp_path` retention. [engineer-verified: "Drop; document (Recommended)"]
49. The session proposed the selected option's description [unverified]: no extra option, and the CI parity test needs no exception. README notes that a run where both passes fail may lose the parallel pass's tmp dirs. M11 adopts it, and row 26 states when the loss happens. The description's "needs no exception" concerns the dropped `tmp_path` option only. M12's `saturates_cpu` suffix, adopted later, is the parity test's one named exception (M10).
50. pytest collects an imported marked test under the importing file. An imported marked function, an imported marked class, and a subclass of an imported marked mixin are each collected there by `-m timing`, though that file lacks the text. [unverified: a model's probes with pytest 8.4.2 in `/tmp`, relayed by the session, not re-run] An AST pass found three `from X import` names starting `test_` or `Test` across the four roots, none of them marked. [unverified: a reviewer's count] So no such route exists in the tree today, and M9's guard fails CI if one appears.
51. `claude/.claude/scripts/tests/test_cursor_adapter_shim_hook_run.py:170-201` holds a `timing` test that skips whenever `PYTEST_XDIST_WORKER` is set, that is, under any xdist worker (`:174-176`). Otherwise it starts `os.cpu_count()` busy-spin processes, each living up to `CONTENTION_HOG_LIFETIME_SECONDS = 300` (`:51`), and runs the shim 300 times under them (`:191-197`). [verified: read] Today a `select-tests.py` run reaches it only when the caller's `-n` or `PYTEST_XDIST_AUTO_NUM_WORKERS` starts no workers, since every other run uses xdist. M12 keeps every split run from reaching it.
52. Exit 3 and exit 4 mark a pytest error rather than a test result. `--pdb` with workers is a usage error, exit 4 (`xdist/plugin.py:330-334`), as in today's single run. [verified: read] A malformed `-m` expression exits 3 under xdist and 4 under `-n0`. [unverified: a reviewer's probe] Either way, M1 skips a serial pass that would only repeat the error.
53. A change to `_timing_split.py` needs a `CROSS_DOMAIN_EXCEPTIONS` row that selects `test_pytest_collection_config.py`, because M9 makes that test import `_timing_split`. `select-tests.py` declares by hand each test that imports a scripts module from another domain, as such a row (`:260-267`, `:969-973`). [verified: read] `test_select_tests.py` pins a row in three places [verified: reads]:
    - its constant in `_EXACT_MATCH_LITERAL_PATH_CONSTANTS` (`:2511-2516`), where an unregistered constant fails nothing [unverified: a reviewer's read];
    - a file target in `_FILE_TARGETS` (`:2565-2569`), where an unregistered file target fails `test_every_directory_target_exists_on_disk` (`:2826`) [unverified: a reviewer's read];
    - a selection test such as `test_skill_auxiliary_files_module_change_also_selects_skills_tests` (`:668-673`).

    Local runs of the guard have a limit. `_is_test_tree_packaging_change` already selects `claude/.claude/tests` for any change under `claude/.claude/hooks/tests` or `claude/.claude/scripts/tests` (`select-tests.py:669-675`), so a cross-file import added there runs the guard locally. [verified: read] A change under `evals` or `claude-skills` does not, and CI runs the guard on every PR (row 34).
54. Each of the guard's three whole-suite collections keeps its 120-second timeout (`test_pytest_collection_config.py:226`) at whole-suite scope. [unverified: no whole-suite collection was timed] Each grows by 59 of 409 test-pattern files, about 17%. [unverified: a reviewer's count] The fourth collection, for M12's marker, covers only the 67 files that hold `timing` tests (row 12), under the same timeout. Verification step 1 runs the test and lists its duration.
55. The serial pass's argv gains one `--ignore=<path>` per unmarked test file. That is about 342 values, roughly 24 KB, for the full suite and about 163 for `claude/.claude/scripts/tests`, against a 1,048,576-byte `ARG_MAX`. [unverified: reviewers' `grep` counts and `getconf ARG_MAX` output] The CPU cost grows with walked entries times `--ignore` values, not with the value count alone:
    - pytest's `pytest_ignore_collect` turns every `--ignore` value into an absolute path on each call, then searches that list (`_pytest/main.py:404-408`). [verified: read]
    - Collection calls that hook once per directory entry it walks (G8's `_pytest/main.py:523-544` and `_pytest/python.py:697-707`).
    - Each conversion of a relative value calls `os.getcwd()`. [unverified: two reviewers' reads and a cProfile run]
    - Estimated cost on a loaded macOS host: about 345k conversions, roughly 15 s of CPU, for a full-suite serial pass, and about 34k, roughly 1.4 s, for `scripts/tests`. [unverified: reviewers' entry counts and micro-benchmarks, not re-run]

    Whether that beats the imports the narrowing avoids at full-suite scale is unmeasured. Verification step 2 decides it (rows 62-63).
56. A pytest that a test spawns inherits the test's environment, and xdist sets `PYTEST_XDIST_WORKER` in each worker process (`test_cursor_adapter_shim_hook_run.py:174`). [verified: the comment there was read. xdist's source was not.] So the contract test removes that variable from its child's environment before it checks that the serial pass sets none.
57. The projected diff is about 1,310 lines, about 60 above the ~1,250 row 69 accepted. Row 69 supersedes rows 38 and 58 for the size question. [unverified: an estimate] The growth came in two steps:
    - The `--` collapse, the first `pyproject.toml` error cases, the guard's fourth collection and the `saturates_cpu` cases took it from about 1,200 to about 1,260.
    - Round 4's fixes add about 50: the remaining `pyproject.toml` cases and the outside-path case, the guard's exit-5 routing and its shim-file and pruning assertions, and the scan that runs only after the argument-only collapses.
58. The engineer's answer on the ~1,100-line projected diff. [engineer-verified: "Proceed anyway"] Row 69 supersedes it.
59. The engineer's answer on the `--ignore` narrowing mechanism, which replaces row 40's description of passing only the marked files. [engineer-verified: "Accept --ignore (Recommended)"]
60. The engineer's answer on what happens locally to the CPU-saturating `timing` test at `test_cursor_adapter_shim_hook_run.py:170-201` (row 51). [engineer-verified: "Keep it CI-only (Recommended)"]
61. The session proposed the selected option's description [unverified]:
    - add a registered marker, such as `saturates_cpu`, to that one test;
    - have the local serial pass add `and not saturates_cpu` to its `-m`, while CI's serial leg still runs it;
    - add `pyproject.toml`'s `markers` list (`:33-35`) and that test file to scope.

    M12 adopts it and settles the name `saturates_cpu`, after the property the test has rather than the policy applied to it.
62. The engineer's answer on `--ignore`'s per-entry cost (row 55). [engineer-verified: "Keep --ignore, measure (Recommended)"]
63. The session proposed the selected option's description [unverified]:
    - keep the accepted mechanism;
    - Verification runs two collect-only comparisons of the serial pass, with and without the `--ignore` tokens, on the full suite and on `scripts/tests`;
    - if narrowing does not save CPU at full-suite scale, the session comes back to the engineer before shipping.

    Verification step 2 adopts it and states the decision rule.
64. The engineer's answer on the `@file` collapse (M6). [engineer-verified: "Keep the collapse (Recommended)"]
65. The session proposed the selected option's description [unverified]: one unsplit pass, as today, whenever an `@file` is passed. No in-repo caller uses `@file`s, which row 19's Grep backs.
66. `addopts` carries `--strict-markers` (`pyproject.toml:27`), and `test_addopts_contains_xdist_auto_and_strict_markers` pins it (`claude/.claude/tests/test_pytest_collection_config.py:151-163`). So an unregistered marker fails collection, and M12's marker needs its `markers` entry. [verified: reads]
67. The engineer's answer on a caller `--`, asked after the round-3 backend review found that pytest exits 4 when a split pass's options and a caller `--` share one argv (row 71 lists the shapes). [engineer-verified: "Collapse on -- (Recommended)"]
68. The session proposed the selected option's description [unverified]: a bare `--` among the caller's arguments collapses the run to one unsplit pass with the caller's arguments verbatim, as the `@file` collapse does (row 64). So a `-- path` form that works today still works.
69. The engineer's answer on the projected diff of about 1,250 lines, after the round-3 additions. It supersedes row 58 for the size question. [engineer-verified: "Proceed anyway"]
70. Before row 69's answer, plan-architect (MODE=consult) recommended one PR. Its stated reason was that every cut that leaves `main` coherent still has a PR over 400 lines, and that `select-tests.py` and `pyproject.toml` are global triggers, so a split doubles the full-suite runs. [unverified: the consult's estimates, not counted code]
71. A caller `--` reaches pytest as follows, with pytest 8.4.2 and CPython 3.14.10. [verified: re-run in round 4 by staff-backend-engineer]
    - `tests -- tests/test_plain.py`, today's argv for `select-tests.py -- tests/test_plain.py`, exits 0.
    - `tests -k p -- tests/test_plain.py` and `tests -n0 --`, today's argvs for a caller option before a `--`, already exit 4. The collapse keeps them verbatim, so they still exit 4, as today.
    - Pass options inserted before the `--`, as in `tests -m 'not timing' --` and `tests -m 'not timing' -- tests/test_plain.py`, exit 4 with `unrecognized arguments`. No split builds this shape (M3).

    The argv a split pass would build under M3 appends the pass's options after the caller's arguments: `tests -- tests/test_plain.py -m 'not timing'`. pytest's parser reads `-m` and `not timing` as two more paths and drops the expression. [unverified: staff-sdet's round-4 probe with pytest's own `Parser`, not a full run] Collection then fails on the missing path `-m` (`_pytest/main.py:1058-1062`), a usage error, exit 4. [unverified: reasoning from that read] The contract test runs this argv and today's at run time (M10). G4's reads explain every shape here.
72. `tomllib` raises `TOMLDecodeError`, a `ValueError` subclass, on invalid TOML (`tomllib/_parser.py:71`). `tomllib.load` decodes the file's bytes with `bytes.decode` (`:136`), whose `UnicodeDecodeError` is also a `ValueError`. [verified: read of CPython 3.14's `tomllib/_parser.py`] So catching `OSError` and `ValueError` covers the read, decode and parse failures M7 widens on. [unverified: reasoning] A deeply nested array makes `tomllib.load` raise `RecursionError`, which neither clause catches. [unverified: staff-backend-engineer's round-4 probe] Only a pathological file raises it, not an honest edit to `pyproject.toml`, so M7 leaves it uncaught.
73. A bare `--` in `PYTEST_ADDOPTS` reaches pytest ahead of the command line (G3), so every token after it is positional (G4), each pass's appended options included. With `PYTEST_ADDOPTS='--'`, today's argv `tests` passes, while the parallel pass's argv `tests -m 'not timing'` collects nothing and exits 5. [unverified: staff-backend-engineer's round-4 probe. The serial pass's argv was not probed.] The serial pass's options land after the same `--`, so it is expected to collect nothing too, and the merged exit is then 5. [unverified: reasoning] Such a run fails with a non-zero exit where today's passes, instead of widening.

## Critical files

Use one `code-writer` dispatch, because the test updates depend on the exact argument lists `_timing_split.py` builds, and one agent's self-review should see both. The dispatch prompt states these rules:
- It runs no `select-tests.py` command, because this diff makes every one a full-suite run (Verification).
- It runs only `test_timing_split.py` and `test_select_tests.py`, each with `scripts/venv-run.sh pytest <file> -n0`. The `-n0` overrides the ini's `-n auto`, which xdist sizes from the CPU count rather than the load (G2, G3).
- It leaves `test_pytest_collection_config.py`, whose guard runs three whole-suite collections and a fourth, to Verification step 1.
- It never runs `test_cursor_adapter_shim_hook_run.py`, where a `-n0` run starts the CPU-saturating test (row 51).
- Comments and docstrings state the one-line facts given below and cite no M or row label.
- Paths are repo-relative.

- `claude/.claude/scripts/_timing_split.py`: **create.**
  - The module docstring is one line: it plans the pytest passes for a selection, either the parallel and serial passes `tests.yml` runs or one unsplit pass.
  - Imports: `fnmatch`, `os`, `tomllib`, `pathlib.Path`, `typing.NamedTuple`, `Callable`, `Iterable` and `Sequence` from `collections.abc`, and `from pytest import ExitCode` (row 18).
  - Public constants:
    - `TIMING_MARKER = "timing"` and `TIMING_MARK_TEXT = f"mark.{TIMING_MARKER}"`;
    - `XDIST_WORKER_ENV_VAR = "PYTEST_XDIST_AUTO_NUM_WORKERS"`, moved here from `select-tests.py:1170`;
    - `TEST_FILE_PATTERNS = ("test_*.py", "*_test.py")`, with a one-line comment: pytest's default `python_files`, which `pyproject.toml` does not override;
    - `SATURATES_CPU_MARKER = "saturates_cpu"`;
    - `PARALLEL_PASS_MARKER_EXPRESSION = f"not {TIMING_MARKER}"` and `SERIAL_PASS_MARKER_EXPRESSION = f"{TIMING_MARKER} and not {SATURATES_CPU_MARKER}"`. The serial one carries a one-line comment: CI's serial step runs `saturates_cpu` tests, and a local serial pass leaves them out because each starts one busy process per core.
    - the pass names `PARALLEL_PASS = "parallel"`, `SERIAL_PASS = "serial"` and `UNSPLIT_PASS = "unsplit"`;
    - five reason constants holding M5's unsplit reasons, the environment one built from `XDIST_WORKER_ENV_VAR`.

    Private constants hold `"-m"`, `"-n"`, `"--numprocesses"`, `"-k"`, `"-n0"`, `"--ignore="` and `"--"`.
  - Three `NamedTuple`s:
    - `TimingMarkScan`: `marked_files: tuple[str, ...]` and `unmarked_test_files: tuple[str, ...]`, each holding sorted repo-relative POSIX paths.
    - `PytestPass`: `name: str`, `added_options: tuple[str, ...]`, `ignored_paths: tuple[str, ...]` and `pytest_args: list[str]`. `pytest_args` holds the caller's remaining arguments, followed by the added options and one `--ignore=<path>` per ignored path.
    - `PassPlan`: `passes: tuple[PytestPass, ...]` and `unsplit_reason: str | None`, which is None when the plan splits.
  - One private helper finds every occurrence of a value-taking option, in the forms G4 lists, with each occurrence's token span and value. M2, M6 and the caller-path probe share it. Its docstring states its precondition in one line: the arguments hold no bare `--`, because `plan_passes` collapses such a run before any caller of this helper reads them.
  - `split_caller_marker_expression(caller_args: list[str]) -> tuple[str, list[str]]` works per M2. Its docstring says it removes every recognized `-m` and returns the last one's expression, since pytest's `-m` is last-wins. A second sentence says an unrecognized form stays, and each pass's own `-m` overrides it.
  - `no_workers_reason(caller_args: list[str], *, auto_num_workers: str | None) -> str | None` works per M6. Its docstring says the last `-n` decides, read the way xdist reads it, and `auto_num_workers` decides only when that `-n` is absent, `auto` or `logical`.
  - `scan_timing_marks(target_paths: Iterable[str], caller_args: Sequence[str], *, repo_root: Path) -> TimingMarkScan` works per M7.
    - A private helper returns the caller paths per row 32. It tests containment with `Path.is_relative_to` on the `os.path.normpath` of the joined path, not with `Path.relative_to`, which raises.
    - A private helper reads `norecursedirs` from `repo_root / "pyproject.toml"` with `tomllib`. It returns `()` when any of these holds (row 72):
      - the file is missing;
      - reading it raises `OSError`;
      - decoding or parsing it raises `ValueError`, which covers `UnicodeDecodeError` and `TOMLDecodeError`;
      - a step on the `tool.pytest.ini_options` path is missing or not a table;
      - the key is missing;
      - the value is not a list of strings, including a list with one non-string element.
    - The pattern matcher receives each walked directory's absolute, unresolved path. It carries a one-line comment: it mirrors pytest's `fnmatch_ex`, which matches a pattern without `/` against the directory name, and one with `/` against the absolute path with `*/` prefixed.
    - It walks with `os.walk` from `repo_root / path` and builds each returned path with `os.path.relpath(..., repo_root)`, never resolving a symlink.
    - Its docstring says an unreadable file counts as marked, and only a file found by walking a directory can be an unmarked test file.
  - `plan_passes(caller_args: list[str], *, auto_num_workers: str | None, scan_selection: Callable[[], TimingMarkScan]) -> PassPlan` checks four collapse cases, in this order:
    1. a caller token starts with `@`;
    2. a caller token equals `--`;
    3. `no_workers_reason` returns a reason;
    4. the `marked_files` of `scan_selection()` is empty.

    It calls `scan_selection` only when the first three decline (M7). The first case that applies plans one `UNSPLIT_PASS` with its reason, no added options, no ignored paths, and the caller's arguments verbatim. Otherwise it plans the two passes per M2, M3 and M8, parallel first, each with its options appended after the caller's remaining arguments:
    - Parallel options are `("-m", <PARALLEL_PASS_MARKER_EXPRESSION, combined>)`, with no ignored paths. Combined means `(<caller>) and <expression>` when the caller has an expression.
    - Serial options are `("-m", <SERIAL_PASS_MARKER_EXPRESSION, combined>, "-n0")`, and its ignored paths are the scan's `unmarked_test_files`.
    - The `--` check carries a one-line comment: pytest reads every token after a `--` as a path, so a split pass's appended options would become missing paths.
  - `skips_serial_pass(parallel_exit_code: int) -> bool` works per M1. Its docstring says exit 3, exit 4 and a death by signal are a pytest error or a kill, not a test result, so a second pass would only repeat it.
  - `merge_pass_exit_codes(exit_codes: Sequence[int]) -> int` works per M4, for one code or two. Its docstring says a pass that collected no tests defers to the other, and otherwise the first failing pass's code wins.
- `claude/.claude/scripts/select-tests.py`: **modify.**
  - Import `shlex` and `time`. Import `XDIST_WORKER_ENV_VAR`, `PassPlan`, `merge_pass_exit_codes`, `plan_passes`, `scan_timing_marks` and `skips_serial_pass` from `_timing_split`, next to the other underscore-module imports (`:18-20`), and delete the definition at `:1170`. Callers reach each name through this module's globals, so `_mod.XDIST_WORKER_ENV_VAR` keeps resolving and tests can patch the functions.
  - Beside the cross-domain import declarations (`:260-267`), add `TIMING_SPLIT_MODULE = "claude/.claude/scripts/_timing_split.py"` and `PYTEST_COLLECTION_CONFIG_TEST_PATH = "claude/.claude/tests/test_pytest_collection_config.py"`, with a one-line comment in that block's style. Add the `CROSS_DOMAIN_EXCEPTIONS` row `(lambda p: p == TIMING_SPLIT_MODULE, (PYTEST_COLLECTION_CONFIG_TEST_PATH,))` next to `SKILL_AUXILIARY_FILES_MODULE`'s row at `:969` (row 53). `test_select_tests.py` registers both constants.
  - Add `run_pass_plan(pass_plan: PassPlan, resolved_targets: list[str], *, repo_root: Path, env: dict[str, str]) -> int` after `run_pytest`. It prints M5's lines and runs each planned pass through `run_pytest(build_pytest_argv(resolved_targets, planned_pass.pytest_args, repo_root=repo_root), cwd=repo_root, env=env)`. It times each pass with `time.monotonic()`, applies `skips_serial_pass` after the parallel pass, and returns `merge_pass_exit_codes` of the codes it collected.
  - Replace the single call at `:1434-1435` with two steps:
    1. `pass_plan = plan_passes(passthrough_args, auto_num_workers=size_result.env.get(XDIST_WORKER_ENV_VAR), scan_selection=lambda: scan_timing_marks(resolved_targets, passthrough_args, repo_root=repo_root))`.
    2. `return run_pass_plan(pass_plan, resolved_targets, repo_root=repo_root, env=size_result.env)`.

    The comment at `:1431-1433` moves with the `build_pytest_argv` call.
  - Leave these unchanged: `build_pytest_argv`, `run_pytest`, `pytest_subprocess_env`, `record_selection`, the early return at `:1404-1406`, and the existing stderr lines.
- `claude/.claude/scripts/tests/test_timing_split.py`: **create.** It imports `_timing_split` by name (row 22). Each table case is a row with an id in a parametrized test, not a new test class.
  - `split_caller_marker_expression`, asserting the expression and the remaining arguments:
    - no `-m`;
    - `-m slow`, `-mslow` and `-m=slow`;
    - several `-m`s, where the last wins and all are removed;
    - `-m ""`, `-m=` and `-m slow -m ""`, each counting as no expression;
    - `-m ' '`, which stays an expression;
    - a trailing bare `-m`, `-m -x`, `-m -k foo` and `-m -1`, where the `-m` stays;
    - `-vm slow`, which stays because the scan does not recognize the form.
  - `no_workers_reason`:
    - The caller reason: `-n0`, `-n 0`, `-n=0`, `--numprocesses 0`, `--numprocesses=0`, `-n 00`, `-n=-1`, `-n 4 -n0`, and `-n 0` with `auto_num_workers="4"`.
    - The environment reason: no `-n`, `-n auto` and `--numprocesses=logical` with `auto_num_workers="0"`, and no `-n` with `auto_num_workers="-1"`.
    - None, in three groups:
      - no `-n`, with `auto_num_workers` set to None, `"1"`, `""` or `"x"`;
      - a positive or later `-n` that wins: `-n 4`, `-n 2` with `auto_num_workers="0"`, and `-n0 -n 4`;
      - a `-n` the scan does not read or cannot parse: a trailing bare `-n`, the separated `-n -1`, the unparseable `-n x`, `--numproc 0`, and the cluster `-vn0`.
  - One test loads `pyproject.toml` with `tomllib` from `helpers.REPO_ROOT` and asserts that some `markers` entry starts with `f"{SATURATES_CPU_MARKER}:"`. Its failure message says the serial pass deselects that marker by name, so a mismatch would let a local run start the test.
  - `scan_timing_marks`, over `tmp_path` trees with `repo_root=tmp_path`. Each case asserts both tuples:
    - a directory with one marked and one unmarked test file;
    - a marked file two directories deep;
    - a directory with no mark, where both test files are unmarked;
    - a marked file named directly, and an unmarked one, which is not listed as unmarked;
    - a walked `helper.py` and a `notes.txt` that hold the text, neither of which counts;
    - a `helper.py` named directly that holds the text, which counts;
    - a missing target;
    - a caller argument naming a marked file with a `::Class::test[a::b]` suffix;
    - the caller arguments `-k sub`, where `sub` is an existing marked directory, which the scan skips, and a bare `sub`, which it scans;
    - a dangling `test_dangling.py` symlink, which counts as marked;
    - with `repo_root` set to a subdirectory of `tmp_path`, an absolute caller path to a marked file outside it, which the scan skips without raising, so both tuples are empty;
    - a `pyproject.toml` whose `norecursedirs` holds `worktrees` and `fixtures/nested`. It prunes a marked `worktrees/test_x.py` and a marked `fixtures/nested/test_y.py` below the scanned directory, but not a scanned path named `worktrees` itself.
  - `scan_timing_marks` over one tree with a marked `worktrees/test_x.py`, parametrized over a `pyproject.toml` that prunes nothing. Each case asserts that the scan does not raise and that `worktrees/test_x.py` counts as marked:
    - a directory named `pyproject.toml`;
    - text that is not valid TOML;
    - bytes that are not valid UTF-8;
    - valid TOML with no `tool.pytest` table;
    - `tool.pytest` set to a string;
    - `tool.pytest.ini_options` set to an integer;
    - an `ini_options` table with no `norecursedirs` key;
    - `norecursedirs = 5`;
    - `norecursedirs = ["worktrees", 5]`, which pins that a list with a non-string element prunes nothing, not even its string patterns.
  - `plan_passes` unsplit cases. Each plans one `UNSPLIT_PASS` with the arguments verbatim and no ignored paths. Every case but the last passes a `scan_selection` that fails the test when called, which shows that such a run reads no file:
    - `@args.txt -n 0` plans the `@` reason, which comes first;
    - `-n 0 -- tests/x.py` plans the `--` reason, which comes before the caller reason;
    - `-k foo -- some/path.py` and `-m slow -k foo -- tests/x.py` each plan the `--` reason, and the second keeps its `-m slow`;
    - `-n 0` plans the caller reason;
    - `auto_num_workers="0"` plans the environment reason;
    - a `scan_selection` returning no marked file plans the no-marks reason.
  - `plan_passes` split cases, each with a `scan_selection` returning one marked file:
    - The names come in the order `PARALLEL_PASS`, then `SERIAL_PASS`, and `unsplit_reason` is None.
    - With no caller arguments, the options are `("-m", "not timing")` and `("-m", "timing and not saturates_cpu", "-n0")`, written as literals so that a change to either constant fails here.
    - With `-m slow -k foo`, each pass's arguments are `-k foo` followed by its own options. The expressions are `(slow) and not timing` and `(slow) and timing and not saturates_cpu`.
    - With `-m "a or b"`, the expressions are `(a or b) and not timing` and `(a or b) and timing and not saturates_cpu`.
    - With `-m ' '`, the expressions are `( ) and not timing` and `( ) and timing and not saturates_cpu`.
    - With `-m saturates_cpu`, the expressions are `(saturates_cpu) and not timing` and `(saturates_cpu) and timing and not saturates_cpu`. The contract test shows that both select nothing.
    - With `-n 4`, the serial pass's `-n0` comes after the caller's `-n 4`, and the parallel pass keeps `-n 4`.
    - With two unmarked files in the scan, the serial pass's arguments end with its options and then two `--ignore=` tokens, and the parallel pass carries none.
  - `skips_serial_pass`: True for `INTERNAL_ERROR`, `USAGE_ERROR`, `-signal.SIGKILL` and `-signal.SIGINT`; False for `OK`, `TESTS_FAILED`, `INTERRUPTED` and `NO_TESTS_COLLECTED`.
  - `merge_pass_exit_codes`, with `ExitCode` members. Each two-code case gives the parallel code, then the serial code, then the result:
    - `OK`, `OK`: `OK`.
    - `OK`, `NO_TESTS_COLLECTED`: `OK`, and the same with the codes swapped.
    - `NO_TESTS_COLLECTED` for both: `NO_TESTS_COLLECTED`.
    - `TESTS_FAILED` with `OK` or `NO_TESTS_COLLECTED`, in either position: `TESTS_FAILED`.
    - `INTERRUPTED`, `TESTS_FAILED`: `INTERRUPTED`, under an id that names run order, not an interrupt.
    - `TESTS_FAILED`, `INTERNAL_ERROR`: `TESTS_FAILED`.
    - `USAGE_ERROR` for both: `USAGE_ERROR`.
    - `-signal.SIGKILL`, `OK`: `-signal.SIGKILL`.
    - The single codes `[OK]`, `[TESTS_FAILED]` and `[NO_TESTS_COLLECTED]` each return themselves.
    - `[]` raises `ValueError`.
  - One contract test runs real pytest through `subprocess.run([sys.executable, "-m", "pytest", ...], timeout=120)`, as `test_pytest_collection_config.py` does. Its setup:
    - A `tmp_path` project holds a `pytest.ini` with `addopts = -n auto -p no:cacheprovider` and the markers `timing`, `slow`, `a`, `b` and `SATURATES_CPU_MARKER`. Every run passes `-c` with that file and `cwd` at the project.
    - `tests/test_marked.py` holds a `timing` test, a `timing` and `slow` test, an unmarked test, an `a` test, and a `timing` and `saturates_cpu` test whose body calls `pytest.fail`. Each other `timing` test asserts `"PYTEST_XDIST_WORKER" not in os.environ`.
    - `tests/test_plain.py` holds an unmarked test, a `slow` test and a `b` test, and it creates a sentinel file when imported.
    - The project's `conftest.py` defines `pytest_collection_finish(session)`. When the environment names an output file, it writes each `session.items` node ID there, one per line. pytest calls that hook after `-m` deselection (`_pytest/main.py:816-823`), so the IDs are the selected tests in one format under any caller verbosity, `-vm slow`'s `-v` included.
    - The child environment drops `PYTEST_XDIST_WORKER`, `PYTEST_XDIST_WORKER_COUNT`, `PYTEST_XDIST_TESTRUNUID` and `PYTEST_ADDOPTS`, and sets `PYTEST_XDIST_AUTO_NUM_WORKERS=2` (row 56).
    - Each pass's argv is the contract test's own options, then `tests`, then its `pytest_args` from `plan_passes(caller_args, auto_num_workers=None, scan_selection=functools.partial(scan_timing_marks, ["tests"], caller_args, repo_root=project))`. The contract test's options go first, so they never land after a caller `--`. A collect-only run's options are `--collect-only`, and it sets the output-file variable.

    Its assertions:
    - For `[]`, `-m slow`, `-m "a or b"`, `-vm slow`, `-m timing` and `-m saturates_cpu`, a collect-only run of each pass exits 0 or 5. The two passes' node IDs are disjoint, and their union equals a literal expected set, which never holds the `saturates_cpu` test. Two sets need a note:
      - For `-vm slow`, the set is every other test, the widening row 9 records.
      - For `-m saturates_cpu`, both passes exit 5, the set is empty, and `merge_pass_exit_codes` of the two codes is 5. So even a caller `-m saturates_cpu` cannot reach the test in a split run (M12).
    - For the caller arguments `-- tests/test_plain.py`:
      - `plan_passes` plans one `UNSPLIT_PASS` whose `unsplit_reason` is the `--` reason constant and whose arguments equal the caller's. A collect-only run of that argv exits 0.
      - The control builds the argv a split would build under M3: the same caller arguments with the `added_options` of the `[]` case's parallel pass appended, `tests -- tests/test_plain.py -m 'not timing'`. Its collect-only run exits 4.
      - Together they pin the shape the collapse rests on (G4, row 71).
    - For `[]`, the serial pass's collection runs first, with no sentinel present, and leaves none behind. The parallel pass's collection then creates it. That shows the serial pass's `--ignore` paths match the paths pytest builds, and that the sentinel works.
    - A real run of the serial pass exits 0 for `[]` and for `-n 2`, which shows its `-n0` starts no worker. A real run of the `[]` serial argv with its `-n0` token removed exits 1, which shows the worker assertion fails under workers.

    This is about seventeen pytest startups, several seconds of CPU. [unverified: not timed] Each case stays because it pins a different claim. Verification step 1 lists its duration.
- `claude/.claude/scripts/tests/test_select_tests.py`: **modify.**
  - Convert the tests row 21 lists. The shared edits:
    - Each patches `_mod.scan_timing_marks` with a recording stub of signature `(target_paths, caller_args, *, repo_root)`.
    - Each test that asserts a split clears `PYTEST_XDIST_AUTO_NUM_WORKERS` with `monkeypatch.delenv(..., raising=False)`.
    - Each test that asserts a split switches to a list of calls and asserts that there are two.
    - Each call starts with the targets the test asserts today. The first call ends with `-m`, `not timing`, and the second with `-m`, `timing and not saturates_cpu`, `-n0`.

    What each test pins:
    - `test_git_diff_unavailable_falls_back_to_full_suite`: the full-suite split (row 7);
    - `test_domain_selected_paths_are_passed_through_to_run_pytest`: `-k foo` in both passes (row 8), and that the stub received `resolved_targets`, the passthrough list and `repo_root`;
    - `test_computed_env_reaches_run_pytest_unchanged`: both calls receive the sizing env;
    - `test_called_before_run_pytest`: the order `["record_selection", "run_pytest", "run_pytest"]`;
    - `test_argv_none_falls_back_to_sys_argv`: one call, with the stub returning no marked file;
    - `test_stderr_scope_matches_recorded_pytest_argv_across_containment_collisions`: each call's leading targets equal `expected_argv`, its `TICKET_REFERENCE_DISCIPLINE_TEST_PATH` exclusion holds for both calls, and the stderr scope line is built from `resolved_targets`.
  - Add `TestMainComposition` tests. Each clears `PYTEST_XDIST_AUTO_NUM_WORKERS` unless it sets it, and each matches a summary line's seconds with a regex:
    - A split whose fake returns `ExitCode.TESTS_FAILED`, then `ExitCode.INTERNAL_ERROR`: `main()` returns `TESTS_FAILED`, which pins the merge order. With a stub returning one unmarked file, stderr holds both M5 headers, the serial one ending `skipping unmarked test files: 1`, and the summary line names exit 1 and exit 3.
    - A parallel `NO_TESTS_COLLECTED`, then a serial `OK`: `main()` returns `OK`, and the summary line names 5, 0 and `exiting 0`.
    - Parametrized over `INTERNAL_ERROR`, `USAGE_ERROR` and `-signal.SIGKILL` from the parallel pass: one call, `main()` returns that code, and stderr holds the skip line.
    - A fake that raises `KeyboardInterrupt` on its first call: `main()` raises, the fake ran once, and no summary line prints.
    - Five unsplit cases. Each makes one call, whose argv is the targets followed by the caller's arguments verbatim, prints its unsplit line, and prints no summary line. In the first four, the recording scan stub records no call:
      - `main(["-n", "0", "-k", "foo"])` with marks;
      - `main(["-k", "foo"])` with `PYTEST_XDIST_AUTO_NUM_WORKERS=0` set;
      - `main(["@args.txt"])`;
      - `main(["--", "some/path.py"])` with marks;
      - a stub returning no marked file.
    - Two wiring tests that leave the scan unpatched. Each sets `resolve_repo_root` to a `tmp_path` root, and `compute_changed_paths` to one path under `_mod.SCRIPTS_DIR`, which selects `_mod.SCRIPTS_TESTS_DIR`. With a marked `test_marked.py` and an unmarked `test_plain.py` there, `main([])` makes two calls, and only the second ends with `--ignore=claude/.claude/scripts/tests/test_plain.py`. With `test_plain.py` alone, it makes one call and prints the no-marks line.
  - Pin the new `CROSS_DOMAIN_EXCEPTIONS` row (row 53) with three edits:
    - add `_mod.TIMING_SPLIT_MODULE` to `_EXACT_MATCH_LITERAL_PATH_CONSTANTS` (`:2516`);
    - add `_mod.PYTEST_COLLECTION_CONFIG_TEST_PATH` to `_FILE_TARGETS` (`:2569`), so the on-disk checks treat it as a file;
    - after `test_skill_auxiliary_files_module_change_also_selects_skills_tests` (`:668-673`), add a test that `_mod.select_pytest_targets([_mod.TIMING_SPLIT_MODULE])` is not a full-suite result and that its targets include `_mod.PYTEST_COLLECTION_CONFIG_TEST_PATH` and `_mod.SCRIPTS_TESTS_DIR`.
  - After `TestRuleTablePathFidelity`, add a CI parity class. It reuses `_steps_running`, `_CI_PYTEST_COMMAND` (`:2672`) and `ci_test_slice_job`.
    - A helper takes the `pytest` steps and the passes and returns every mismatch. First it strips one named suffix, `f" and not {SATURATES_CPU_MARKER}"`, from the serial pass's `-m` value, and reports a serial pass whose value lacks it. Then a pass's `added_options` match a step when they appear in it as a contiguous run of `shlex.split` tokens. Every pass must match exactly one step, and every step exactly one pass.
    - The suffix is a test-module constant with a one-line comment: it is the one intended difference from `tests.yml`, because CI alone runs `saturates_cpu` tests.
    - The live test feeds it `tests.yml`'s steps and the passes of `plan_passes([], auto_num_workers=None, scan_selection=lambda: <a scan with one marked file>)`, and expects no mismatch. Its failure message says `select-tests.py`'s pass options and `tests.yml`'s `pytest` steps are two copies of one split, which change together apart from the named suffix.
    - Seeded controls expect a mismatch for a serial step without `-n0`, for a parallel step whose `-m` reads `"not timing and not slow"`, for one step holding both passes' options, and for a serial pass whose `-m` reads `timing and not slow`.
- `claude/.claude/tests/test_pytest_collection_config.py`: **modify** `TestTimingMarkerCoverageParity` (`:200-245`) per M9.
  - Load `select-tests.py` once at module level with `importlib.util.spec_from_file_location`, as `test_select_tests.py:30-32` does, to read `FULL_SUITE_TARGETS`. Import `scan_timing_marks`, `SERIAL_PASS_MARKER_EXPRESSION` and `TIMING_MARKER` from `_timing_split` by name, which `pyproject.toml:21`'s `pythonpath` allows.
  - `_collected_node_ids` gains a `targets` parameter, which defaults to every `FULL_SUITE_TARGETS` root in place of `"claude/.claude/"`.
  - `test_not_timing_plus_timing_selection_equals_unfiltered_total` keeps its assertions and adds M9's after them, in the same method, so no collection runs twice. The containment assertion's failure message names each file. It says the serial pass skips a test file whose text lacks the mark, so the mark must sit in the file pytest collects the test from.
  - The root-coverage assertion's failure message names each root with no collected ID.
  - The two pruning assertions' failure messages name each offending path and say the scan must prune what `pyproject.toml`'s `norecursedirs` prunes.
  - The fourth collection runs after the assertion that the `-m timing` IDs are not empty, with `targets` set to the sorted files of those IDs. It stays out of the existing `returncode == 0` loop (`:236-239`). It collects `f"{TIMING_MARKER} and not ({SERIAL_PASS_MARKER_EXPRESSION})"` and checks the result in this order:
    1. An exit other than 0 or 5 fails with the loop's generic `collection failed (exit N)` message.
    2. Exit 5, or no ID from `claude/.claude/scripts/tests/test_cursor_adapter_shim_hook_run.py`, fails with a message saying the serial pass's expression no longer deselects that file's CPU-saturating test, so the test has lost its `saturates_cpu` mark or no longer carries `timing` beside it.
  - The class docstring gains two sentences. The `timing` collection also pins that `select-tests.py`'s scan marks every file pytest collects a `timing` test from. A fourth collection pins that the serial pass's expression deselects the CPU-saturating `timing` test.
- `pyproject.toml`: **modify.** Add one `markers` entry after `timing`'s at `:34`: `"saturates_cpu: starts one busy process per CPU core, and is always applied together with timing. select-tests.py's serial pass deselects it, and CI's serial step runs it."`
- `claude/.claude/scripts/tests/test_cursor_adapter_shim_hook_run.py`: **modify.** Add `@pytest.mark.saturates_cpu` beside the `timing` mark at `:170`. The xdist skip at `:174-176` stays, because `pytest claude/.claude/` with the ini's `-n auto` still runs the test in a worker.
- `README.md`: **modify.**
  - At `:566`, replace "`select-tests.py` forwards it through to pytest." with a sentence saying it forwards `-n <N>` to its parallel pass only.
  - After `:578`, add a lead sentence and a list, one fact per item:
    - It runs a parallel pass for everything not marked `timing`, then a serial `-n0` pass for the `timing` tests, as CI does.
    - The serial pass leaves out tests marked `saturates_cpu`, each of which starts one busy process per CPU core, and CI's serial step runs them:
      - A split run never runs them, so `-m saturates_cpu` without `-n 0` selects nothing.
      - To run them locally, pass `-n 0 -m saturates_cpu`, which runs one unsplit pass, or run `scripts/venv-run.sh pytest <file> -m timing -n0`.
    - The serial pass skips every selected test file whose text lacks `mark.timing`. The mark must therefore sit in the file pytest collects the test from, and `test_pytest_collection_config.py` fails CI otherwise.
    - It skips the serial pass when the parallel pass exits 3 or 4 or is killed by a signal.
    - It runs one unsplit pass instead, as before, when:
      - you pass `-n 0`;
      - `PYTEST_XDIST_AUTO_NUM_WORKERS` is 0 or less, and your `-n`, if any, is `auto` or `logical`;
      - an argument starts with `@`;
      - an argument is a bare `--`;
      - neither a selected file nor a path you pass contains `mark.timing`.
    - Your arguments reach both passes, and the serial pass's `-n0` overrides your `-n`.
    - A `-m` you pass combines as `(<expr>) and not timing` and `(<expr>) and timing and not saturates_cpu`. A `-m` inside a flag cluster such as `-vm`, or in `PYTEST_ADDOPTS`, is not recognized, and each pass's own `-m` overrides it.
    - It does not read `PYTEST_ADDOPTS` or `--pdb` when it decides whether to split.
    - It exits with the first non-zero code, the parallel pass's first. A pass that collected no tests, exit 5, defers to the other unless both did.
    - Each pass writes report files such as `--junitxml` once, so the serial pass's file replaces the parallel pass's (row 19).
    - A run where both passes fail may lose the parallel pass's `tmp_path` directories (row 26).
    - The serial pass removes only this run's own sibling-worker load, not load from other processes on the machine (G6).
    - The interpreter that runs it must be able to import pytest (row 18).
- `CHANGELOG.md`: **modify.** Add a bullet at the top of `## [Unreleased]`'s `### Changed` (`:7-9`). It says `select-tests.py` now runs `timing`-marked tests in a second, serial pytest pass over only the files that carry the mark, as CI does, whenever the selection contains them. Two sub-bullets:
  - The caller `-m` and `-n` behavior, the five unsplit cases, the skip after exit 3, exit 4 or a signal, and the `saturates_cpu` test that only CI's serial step runs, citing README.md's Tests section.
  - **Migration:** a split run prints two pytest summaries and a closing stderr line, each pass writes report files once, and the interpreter must be able to import pytest.

**Reuse:**
- `build_pytest_argv` and `run_pytest` stay as each pass's argv builder and runner.
- `pytest.ExitCode` provides the exit-code names.
- `TestTimingMarkerCoverageParity._collected_node_ids` provides the guard's collection, and `scan_timing_marks` its rule.
- `ci_test_slice_job` (`helpers.py:2713`) and `_steps_running` (`test_select_tests.py:2690`) provide the CI parity data.
- The existing `pytest_subprocess_env` result serves every pass and supplies M6's worker count.

Projected diff: ~1,310 lines, about 275 in `_timing_split.py`, 545 in `test_timing_split.py`, 70 in `select-tests.py`, 315 in `test_select_tests.py`, 70 in `test_pytest_collection_config.py`, 26 in README.md, 10 in CHANGELOG.md, and 1 each in `pyproject.toml` and `test_cursor_adapter_shim_hook_run.py`.

## Verification

Run every command from the worktree root. Each step names the question it answers and the result that changes the plan.

**Load (row 27).** Hold each full-suite run while the machine is overloaded, and bound the workers of every other test run. The diff edits `select-tests.py` and `pyproject.toml`, both `GLOBAL_TRIGGER_PATHS` members (`select-tests.py:558-562`), so every `select-tests.py` run selects the full suite. The flow runs the full suite locally twice:
- in step 1;
- in step 4's `/ready-for-review`, which runs CLAUDE.md's Commands (`ready-for-review/SKILL.md:64`) and caches only its own passing run (`:61`), so step 1 cannot stand in for it.

The rules:
- Before step 1 and before each `/ready-for-review`, read the 1-minute load average and the logical core count with `scripts/venv-run.sh python3 -c "import os; print(os.getloadavg()[0], os.cpu_count())"`. When the load exceeds the core count, hold the run and tell the engineer both numbers. The sizing line prints the same `os.getloadavg()` figure (`select-tests.py:1394`, `:1418-1423`), but only once the run has started.
- After a `/code-review` fix, rerun only the test files that cover the fix, with `scripts/venv-run.sh pytest <files> -n0 -m 'not saturates_cpu'`, and leave the next full-suite run to `/ready-for-review`. The `-n0` overrides the ini's `-n auto`, which xdist sizes from the CPU count rather than the load (G2, G3). The `-m` keeps the CPU-saturating test out of a run with no workers (row 51).
- Each further `/ready-for-review` round after a tree change adds one full-suite run.
- `/code-review` runs no tests.
- The `code-writer` dispatch runs no `select-tests.py` command, and it bounds its own test runs (Critical files).
- Step 2 only collects.

**Approvals.** The session runs each command below, and the engineer approves it at the permission prompt, or runs it in a terminal and hands back the output. The project allowlist (`.claude/settings.json:10-12`) covers the bare `select-tests.py` command that `/ready-for-review` runs, and no command below. The session reports a denial and does not retry it.
- the load reading before step 1 and before each `/ready-for-review`;
- step 1, for its `--durations=15`;
- step 1's failure reruns and merge-base check, if any;
- step 2, a heredoc;
- step 3's `ruff` command, which `:10`'s bare `ruff check claude/.claude/` does not match;
- a `/code-review` fix's test-file rerun;
- step 4's `gh` lookups.

No PR opens until the engineer has run or approved step 2. A stop under step 2's rule also holds the PR until the engineer decides (row 62).

1. **Does the change pass, does the split run end to end, and what does each pass cost?** Once the load reading allows it, run `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py --durations=15`, and confirm five things, fixing any that fails before shipping:
   - stderr shows `running the full suite (global-trigger: ...)`, both pass headers, and the summary line;
   - the serial header's count of skipped files is above zero;
   - the serial session prints no xdist worker banner;
   - `test_not_timing_plus_timing_selection_equals_unfiltered_total` passes within its 120-second timeouts (row 54);
   - the run exits 0.

   `select-tests.py` itself selects the full suite for this diff, which is CLAUDE.md's first full-suite case. The run includes the contract test, the `main()` tests and M9's guard, and it exercises the split itself. `--durations=15` reaches both passes (row 8), so each pass prints its own 15 slowest entries.

   Record these in the PR body, each informational:
   - both passes' wall seconds from the summary line;
   - the serial pass's slowest entries, which show what the `timing` tests cost one at a time, with the `saturates_cpu` test deselected;
   - the guard test's and the contract test's durations from the parallel pass's list, beside their 120-second per-run timeouts. A test missing from the list took less than its last entry, and the PR body records that bound instead.

   If the run fails, do not rerun it:
   - Rerun only the failing node IDs, with `scripts/venv-run.sh pytest <node ids> -n0`.
   - When the run's sizing line, `(1-minute load average <x>)`, or a fresh load reading exceeds the logical core count, hold that rerun until a fresh reading is at or below the core count. A failure under that load may be the load's, not the change's, so the rerun comes before any merge-base check.
   - A test that passes alone goes to the engineer with both results, since it may fail CI's parallel leg too.
   - A test that fails again is checked at the merge-base, per the global CLAUDE.md's "Prove your change caused a failing check" rule. Failing there too marks pre-existing drift, outside this plan. Failing only here puts it in scope: fix it, rerun its node IDs, and leave the next full-suite run to `/ready-for-review`.
2. **Does the `--ignore` narrowing save CPU without dropping a test?** (rows 55, 62-63) Run it after step 1, so that both runs of each pair find warm bytecode caches. The snippet collects the serial pass's argv with `--collect-only -q`, with and without its `--ignore` tokens, on the full suite and on `claude/.claude/scripts/tests`. It prints no argv, since the full-suite one holds about 342 `--ignore` values. In place of the node-ID list, it prints pytest's closing collect-only line, `<selected>/<collected> tests collected (<deselected> deselected)`, or `<n> tests collected` when nothing is deselected (`_pytest/terminal.py:1432-1448`).

   ```bash
   scripts/venv-run.sh python3 - <<'EOF'
   import resource
   import subprocess
   import sys
   import time
   from functools import partial
   from pathlib import Path

   sys.path.insert(0, "claude/.claude/scripts")
   from _timing_split import SERIAL_PASS, plan_passes, scan_timing_marks


   def children_cpu_seconds():
       usage = resource.getrusage(resource.RUSAGE_CHILDREN)
       return usage.ru_utime + usage.ru_stime


   def closing_line(stdout):
       non_blank_lines = [line for line in stdout.splitlines() if line.strip()]
       return non_blank_lines[-1] if non_blank_lines else "(no output)"


   scopes = {"full suite": ["claude/.claude/", "claude-skills/", "plugins/", "evals/"], "scripts/tests": ["claude/.claude/scripts/tests"]}
   for scope, targets in scopes.items():
       plan = plan_passes([], auto_num_workers=None, scan_selection=partial(scan_timing_marks, targets, [], repo_root=Path.cwd()))
       serial = next(p for p in plan.passes if p.name == SERIAL_PASS)
       narrowed = [sys.executable, "-m", "pytest", *targets, *serial.pytest_args, "--collect-only", "-q"]
       unnarrowed = [token for token in narrowed if not token.startswith("--ignore=")]
       for label, argv in (("unnarrowed", unnarrowed), ("narrowed", narrowed)):
           cpu_start, wall_start = children_cpu_seconds(), time.monotonic()
           completed = subprocess.run(argv, stdout=subprocess.PIPE, text=True)
           wall_seconds = time.monotonic() - wall_start
           cpu_seconds = children_cpu_seconds() - cpu_start
           print(f"{scope} {label}: exit {completed.returncode}, {wall_seconds:.1f}s real, {cpu_seconds:.1f}s user+sys; {closing_line(completed.stdout)}", flush=True)
   EOF
   ```

   - The decision rule has three parts, and the full-suite pair must meet all of them:
     - both runs exit 0;
     - both report the same selected count, the first number on the closing line;
     - the narrowed run's user-plus-sys figure is below the unnarrowed one's.

     Otherwise stop, and take all four lines to the engineer before shipping (row 62). A non-zero exit or a count mismatch means the narrowing broke the collection or dropped a test.
   - The `scripts/tests` pair is informational, for the PR body.
   - The PR body also states the guard's fourth collection's share of the guard's collection CPU as at most N ÷ (3U + N). N is the full-suite narrowed figure, which bounds the fourth collection from above, because that run collects the same marked files plus a directory walk and the `--ignore` cost. U is the full-suite unnarrowed figure, which approximates each of the guard's three whole-suite collections (row 45).
   - Each figure is a single sample, the cheaper choice under row 27. The PR body says so.
3. `scripts/venv-run.sh ruff check claude/.claude/ claude-skills/ plugins/ evals/`. The diff changes no shell file, so the shellcheck command does not apply.
4. Run `/code-review`, then `/ready-for-review` before handoff.
   - Once the PR's CI run finishes, the PR body records its parallel leg's wall time from `gh run view <run id> --json jobs`. Beside it go the last `main` run's, found with `gh run list --workflow tests.yml --branch main --limit 1`, and the job's `timeout-minutes: 30` (`tests.yml:43`).
   - The guard's widening (row 54) and the contract test both grow that leg, and the cap comment at `tests.yml:41-42` says "Re-derive this cap whenever the parallel pass grows". `tests.yml` stays unchanged (Out of scope), so the engineer decides whether the margin calls for re-deriving it.

## Out of scope

- `tests.yml` stays unchanged, since CI already splits (brief).
- The cold-stub prewarm guard in `evals/conftest.py`, the pid-path quoting in `evals/test_replay_bench_launch.py`, and refactors of the domain-mapping table or the worker heuristics (brief). The one rule-table row this plan adds declares the guard's new import (row 53).
- Recognizing the caller `-m` forms in row 9. Each already widens the run rather than breaking the split, and each would need its own machinery:
  - a cluster, pytest's whole short-option table;
  - a `-m` in `PYTEST_ADDOPTS`, shell-word parsing of the environment;
  - a negative-number value, argparse's negative-number rule in the shared scan, which only `-m -1` and `-n -1` would use.
- Reading `PYTEST_ADDOPTS`, `--pdb`, a separated negative `-n` value or a negative `--maxprocesses` for M6's worker count. `PYTEST_ADDOPTS` would need the same shell-word parsing, and a run with any of these forms splits with both passes serial, which stays correct.
- Reading a bare `--` in `PYTEST_ADDOPTS` for M6's `--` collapse. It is the one unread form that fails loudly instead of widening: each pass's appended options land after that `--`, and the run exits non-zero where today's passes (row 73). Reading it would need the same shell-word parsing.
- Cutting `--ignore`'s per-entry cost, for example with one `--ignore` for a walked directory that holds no marked file. The engineer chose to keep `--ignore` and measure (row 62), and Verification step 2 stops for a decision if the narrowing loses.
- Merging per-session state across the two passes: report files (`--junitxml`), the `--lf` and `--sw` cache, and the `tmp_path` directories a run where both passes fail can lose (row 26). No in-repo caller passes such flags (row 19), and the engineer chose to document the loss (row 48).
- Dropping an unmarked file named directly from the serial pass's targets. `--ignore` cannot skip a path named on the command line (G8), so this would need a separate target list per pass. Such a file costs one module import. This is the one point where the plan takes the simpler option over the cheaper one.
- Recording the pass plan or the pass times in the selection log. The log records the selection decision, which the split does not change (row 16), and M5's summary line shows the times on every run.
- Running the guard locally for a change under `evals` or `claude-skills`. CI runs it on every PR (row 53).
- Splitting `select-tests.py` or `test_select_tests.py` under the 1,000-line limit (row 22). This plan grows them only by the wiring and test updates the split needs.
