# select-tests.py: run `timing`-marked tests serially

## Context

Goal: a local `select-tests.py` run executes `timing`-marked tests serially (`-n0`) and everything else in parallel under pytest-xdist, the same split CI uses, so a scoped local pass stops disagreeing with CI on timing-sensitive tests.

Ask: "let's do #1, that seems worthwhile" — the engineer's words as relayed by the prior session's handoff brief (`~/.claude/briefs/select-tests-serial-timing-task.md`), where "#1" is the brief's §1 goal restated above. Widened mid-planning with a constraint, in the engineer's words: "I am worried that running tests locally like CI does will lead to more load on the machine". After Verification step 2 failed its CPU rule, the engineer chose, in their selected label, "Drop the narrowing (Recommended)", and then said: "I think you should edit the plan file because this is it's not a tiny change, but it's large enough that I think a plan review makes sense."

`select-tests.py` picks the test files a diff touches and runs them in one pytest invocation under xdist (`main()` → `build_pytest_argv` → `run_pytest`, `claude/.claude/scripts/select-tests.py:1249-1435`). That invocation includes `timing`-marked tests. The marker's own definition (`pyproject.toml:34`) says to "run serially (-m timing -n0)". CI already splits them: `.github/workflows/tests.yml:222` runs `-m "not timing"` and `:227` runs `-m timing -n0`. Under xdist, `timing` tests flake from sibling-worker load; one such flake was fixed in PR #1539, but the local runner still exposes these tests to that load.

Decisions this plan settles:

- The split mechanism: two pytest invocations, or a lighter pytest/xdist primitive if one gives true serial isolation.
- How the two legs' exit codes merge into one exit status, including exit 5 (no tests collected) in one or both legs.
- How caller passthrough arguments interact with the added `-m`: a caller's `-m` combines rather than being overridden, a caller's `-k` applies to both legs, and what a caller's `-n` means for the serial leg.
- Whether the full-suite widening path gets the same split.

Out of the brief's scope from the start: a cold-stub prewarm guard in `evals/conftest.py`, pid-path quoting in `evals/test_replay_bench_launch.py`, refactoring the domain-mapping table or worker heuristics beyond the split, and changing `tests.yml`.

## Approach

`select-tests.py` splits a run into two pytest passes over the same resolved targets, matching `tests.yml`'s two steps with one named difference. First a parallel pass runs `-m "not timing"`. Then a serial pass collects the same selection and runs `-m "timing and not saturates_cpu" -n0`. The difference from CI is the `saturates_cpu` exclusion, which keeps the one `timing` test that starts a busy process per core in CI only. The serial pass runs after every parallel result except exit 3, exit 4 or a death by signal, and the run exits with one merged status. Tests in `test_pytest_collection_config.py` fail CI when pytest collects a `timing` test from a file the scan does not mark, or when the CPU-saturating test no longer carries `saturates_cpu`. A narrowing of the serial pass to the marked files, with one `--ignore` per unmarked test file, was built, measured and dropped (M8).

The run uses one unsplit pass instead, with the caller's arguments verbatim as today, in four cases:
- a caller argument is an `@file`;
- a caller argument is a bare `--`;
- the run would start one xdist worker or none;
- no selected file contains `mark.timing`.

The engineer's load concern (row 27) shapes four of these choices:
- the collapses skip a pass that would buy nothing, and the first three also skip the scan;
- the serial pass leaves out the one test that saturates every core;
- the skip rule starts no second pass after a pytest error or a kill;
- the guard runs its three existing collections once per run, in one test method, and adds one over only the CPU-saturating test's file (row 83).

Against today's single pass, a split run adds one pytest startup and one whole-selection collection, the serial pass's. That costs about 10.0 to 11.2 s of CPU on `claude/.claude/scripts/tests` and 21.8 to 25.2 s on the full suite (row 76, the session's unsaved record). The run's wall time also grows by the serial pass's whole run (row 14). No run compares a split run with `main`. The added cost is the collection row 76 measured, so no new measurement is planned.

Dropping the narrowing is not a load reduction for every scope. Per serial-pass collection, it raises CPU by about 4 s on a scoped `claude/.claude/scripts/tests` run and lowers it by 4.3 to 7.9 s on the full suite (row 76).

A new module, `claude/.claude/scripts/_timing_split.py`, holds the scan, the pass plan, the skip rule and the exit-code merge. `main()` runs the passes it plans. This plan calls the invocations "passes", the term README.md:570 already uses for CI's split. The Step 4 questions called them "legs". The plan cites `select-tests.py` by its line numbers at the merge base, 7ba14dba.

Alternatives weighed (M1, M8 and M12 hold the lighter-primitive checks):

- **One invocation with `--dist loadgroup` and an `xdist_group` on every `timing` test.** Rejected: the group runs on one worker while the other workers keep running, so the sibling-worker load stays (G2).
- **`-n0` for the whole selection.** Rejected: it runs serially, but it gives up parallelism for every non-`timing` test.
- **Deselecting through a pytest plugin instead of combining `-m`.** This means a `-p` module or a root `conftest.py` that adds a pass option and a `pytest_collection_modifyitems` hook. It would compose with every caller `-m` form. Rejected: it loads a new plugin into every split run, xdist workers included (row 20), only to cover `-m` forms no caller uses. Every form the token scan misses already leaves the split intact (row 9).
- **A prefilter that skips only the serial pass and keeps `-m "not timing"` on the parallel pass.** Rejected: a test the scan missed would then run in neither pass. An empty scan runs one unsplit pass instead, which turns a miss into today's behavior (row 31).
- **Narrowing the serial pass to the marked files with one `--ignore` per unmarked test file.** Built, measured and dropped (M8). On the full suite it cost more CPU than it saved (row 76), and the engineer chose to drop it (row 74).
- **Narrowing by passing the marked files as the serial pass's targets,** the session's description in row 40. Set aside, first for `--ignore` and then with all narrowing (Out of scope). An explicit file argument bypasses pytest's `python_files`, `norecursedirs` and `--ignore` filters (G8), so the plan would have to re-implement each one. Expanding a selected directory into files would also stop a caller's file from shadowing it, and a file named twice is collected twice.
- **Pruning the scan's walk with `pyproject.toml`'s `norecursedirs`.** Built, then removed (row 86). M9's guard checks only that the scan's list covers the files pytest collects `timing` tests from, so an extra marked file never fails it. The pruning saved only reads of files pytest skips. It cost a `tomllib` read with its own error handling, and a matcher that mirrored pytest's and was the only scan logic that could drop a file pytest collects.
- **Narrowing with `-k` or `--deselect`.** Rejected: both filter after collection (`_pytest/main.py:440-455`), so they save none of it. `--ignore-glob` matches path patterns, not file contents.
- **An AST pin on how the marker is applied.** Set aside for the collection-based guard (rows 44-45). The pin missed aliases, variable names and cross-file imports. The guard reads pytest's own collected IDs from collections its class already runs.
- **Treating every caller argument that does not start with `-` as a possible path that forces the split.** Rejected: `-n 4` and `-k foo` would then always pay for the serial pass, which works against the engineer's load concern (row 27). The scan reads only the caller arguments that name an existing path and are not a recognized `-k`, `-m` or `-n` value (row 32).
- **Inserting the pass options before the caller's arguments.** Rejected: pytest would then parse a caller's `-n` after the serial pass's `-n0`, and the caller's value would win (G2). The serial pass would have to remove it. Appending the options after the caller's arguments needs no removal (M3).
- **Splitting a run whose caller arguments hold a `--`, by moving every option ahead of the targets.** Set aside for the collapse the engineer chose (row 67). Appended pass options become paths after a caller's `--`, and options inserted before that `--` make pytest reject it (G4). Moving the caller's options out of the way would need pytest's whole option table, to tell which options take a value. It would also reorder `build_pytest_argv`'s targets-first argv for a form no in-repo caller uses (row 19).
- **Failing loudly on an unrecognized `-m` form.** Rejected: a token starting `-m` is never another option's value (G4), so only a short-flag cluster is ambiguous. Telling `-vm X` from `-kmatch` would need pytest's whole short-option table. A heuristic error would break `-kmatch`, which pytest accepts today. Row 9 records what a cluster does instead: the split stays intact and the run widens.
- **Collapsing on a bare `--pdb`.** Set aside. xdist runs a `--pdb` invocation with no workers when its `-n` is `auto` (`xdist/plugin.py:310-313`), so the split then runs two serial sessions. The results stay correct, and the cost is one extra collection. README.md:556 already tells `--pdb` users to pass `-n0`, which collapses.
- **Splitting a run with one worker.** The engineer first chose to collapse it (row 41), then to split it (rows 46 and 80), and finally to collapse it (row 85). One worker has no sibling workers for the serial pass to protect, so a split would pay a whole-selection collection for nothing (row 47).
- **A class-scoped fixture that shares the guard's collections among several test methods.** Set aside for one method (row 83). Under the ini's `-n auto`, such a fixture can run once in each worker that receives one of its tests, and each run repeats the three whole-suite collections.
- **Running the CPU-saturating test in the local serial pass.** The engineer chose to keep it CI-only (row 60). M12 holds the lighter-primitive checks.
- **Adding `-o tmp_path_retention_count=2` to the serial pass.** The engineer first chose this, then chose "Drop; document" (rows 43, 48). README names the loss instead (row 26).
- **Keeping the split inline in `select-tests.py`, tested in `test_select_tests.py`.** Rejected: both files are already over the repo's 1,000-line limit (row 22). A separate test file for an inline split would also need a second `importlib` loader for the hyphenated script.
- The engineer's answers set aside further options. One item per round:
  - rows 2-7, the Step 4 answers;
  - row 29;
  - row 42;
  - rows 62 and 64;
  - row 67;
  - row 74;
  - rows 80-82;
  - rows 83-85;
  - row 86.

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

  `skips_serial_pass(parallel_exit_code)` returns True for `ExitCode.INTERNAL_ERROR`, `ExitCode.USAGE_ERROR` and any negative code, which a death by signal gives. `main()` then starts no serial pass. Every other code, exit 2 included, still runs the serial pass (row 29). Row 14 records what that costs after a collection error.

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
  - An unsplit run prints one line before its pass, `select-tests: one pass, not split: <reason>`, and no summary line. The reason is one of `a caller argument starts with @`, `a caller argument is --`, `the caller's -n starts one or fewer workers`, `PYTEST_XDIST_AUTO_NUM_WORKERS sets one or fewer workers`, or `no selected file contains mark.timing`.
  - A split run prints a header before each pass, `select-tests: <name> pass: <options>`, with the options joined by `shlex.join`. With no caller `-m`, the headers read `select-tests: parallel pass: -m 'not timing'` and `select-tests: serial pass: -m 'timing and not saturates_cpu' -n0`.
  - After both passes it prints `select-tests: parallel pass exited <p> in <s>s, serial pass exited <q> in <t>s; exiting <merged>`. Each time is a `time.monotonic()` difference with one decimal. A reader who tails the output then sees the run's result and cost, not just the serial pass's summary.
  - After a skip it prints `select-tests: parallel pass exited <p> in <s>s; serial pass skipped; exiting <p>`.

  `record_selection` still writes one line before any pass and gains no field (row 16).

  anchors: row13, row16, row42
- **M6. Collapse when the caller's arguments cannot be split safely, or the run starts one worker or none.** `plan_passes` checks three cases before M7's, in this order:
  - A caller token starts with `@`. argparse expands that file (G4), where no scan here can see a `-m`, `-n` or `--` inside it.
  - A caller token is a bare `--`. A split pass appends its options after that `--`, where pytest reads them as paths and exits 4 (G4, row 71). The unsplit pass keeps today's argv, so a `-- <path>` form that runs today still runs.
  - `one_or_fewer_workers_reason` returns a reason.

  The first case that applies plans one unsplit pass with the caller's arguments verbatim. The `--` case reads only the caller's arguments. A bare `--` in `PYTEST_ADDOPTS` stays unseen, and it makes a split run fail instead of widening (row 73, Out of scope).

  `one_or_fewer_workers_reason(caller_args, *, auto_num_workers)` returns M5's unsplit reason when the run would start one xdist worker or none, and None otherwise. One worker has no sibling workers for the serial pass to protect, so a split would pay a whole-selection collection for nothing (row 85). `auto_num_workers` is the value of `PYTEST_XDIST_AUTO_NUM_WORKERS` in `size_result.env`, the environment pytest will see. It reuses M2's option scan:
  - It reads `-n X`, `-nX`, `-n=X`, `--numprocesses X` and `--numprocesses=X`, and the last occurrence wins (G2).
  - A caller value that parses as an integer of 1 or less returns the caller reason. xdist starts no workers for 0 or less and one worker for 1 (G2). It parses with `int()`, as xdist's `parse_numprocesses` does (`xdist/plugin.py:56-60`).
  - With no recognized `-n`, or one whose value is `auto` or `logical`, it reads `auto_num_workers` the same way (G2). A value of 1 or less returns the environment reason. An empty or unparseable value counts as unset, as in xdist.
  - Every other value returns None, an unparseable caller value included. pytest then reports the bad value itself.
  - It does not see a cluster such as `-vn0`, `-n` in `PYTEST_ADDOPTS`, `--pdb`, or a separated negative value such as `-n -1`, whose next token starts with `-`. Such a run splits, with both passes serial for a count of 0 or less. The results stay correct, at the cost of one extra collection.
  - Its environment reason can also be wrong in the other direction. With `-n 4` in `PYTEST_ADDOPTS` and `PYTEST_XDIST_AUTO_NUM_WORKERS` at 1, it returns that reason and the run collapses, though pytest parses the `-n 4` after the ini's `-n auto` (G3) and starts four workers. The collapsed run is today's single pass, so this is no regression.
  - `--dist no` is not a zero-worker form. xdist resets `dist` to `load` whenever `-n` resolves to a count above 0 (`xdist/plugin.py:318-320`), so `-n auto --dist no` starts workers and the split stays correct.
  - It does not read `--maxprocesses`. xdist ignores a value of 0 (`xdist/plugin.py:321-324`). A value of 1 caps the run at one worker, and a negative value starts none (G2), so such a run splits with one worker or none.
  - It does not see xdist's own CPU count, which decides when `PYTEST_XDIST_AUTO_NUM_WORKERS` is unparseable, or unset because the sizing could not read the load average (G2). On a one-CPU host such a run splits with one worker.

  A count of 1 or less reaches the function from three sources:
  - a caller's `-n`;
  - a caller's own `PYTEST_XDIST_AUTO_NUM_WORKERS`, which `pytest_subprocess_env` leaves as set when it is not empty;
  - `select-tests.py`'s own sizing on a one-CPU budget. `compute_worker_count` floors at `min(2, cpu_budget)` workers (`select-tests.py:1175`, `:1280-1284`), so it writes 1 only then, and never 0 (row 47).

  anchors: row27, row28, row47, row64, row65, row67, row68, row71, row73, row85
- **M7. Scan the selection, and collapse when nothing carries the mark.** `scan_timing_marks(target_paths, caller_args, *, repo_root)` returns a `TimingMarkScan` of the selection's marked files. A file is marked when its bytes contain `TIMING_MARK_TEXT` (`f"mark.{TIMING_MARKER}"`), or when it cannot be read.

  What it scans:
  - each resolved target, and each caller argument that names an existing path under `repo_root` (row 32);
  - a file named directly, read whatever its name, because pytest collects it whatever its name (G8);
  - a directory, walked into every subdirectory, reading only the files that match pytest's default `python_files` patterns `test_*.py` and `*_test.py` (`_pytest/python.py:85-88`), since `pyproject.toml` sets no `python_files`;
  - no path that does not exist, since pytest reports a missing path itself;
  - no caller path outside `repo_root`, which it skips without raising (row 32);
  - every matching file, with no early stop, since M9's guard compares the whole marked list with pytest's collection (row 33).

  The walk applies none of pytest's `norecursedirs` pruning (row 86). So a full-suite scan also reads files pytest never collects, such as a stale nested checkout under `claude/.claude/worktrees/`, which `test_pytest_collection_config.py:1-6` records. Such a file can only add a marked file:
  - M9's guard checks that `marked_files` covers the files pytest collects `timing` tests from, so an extra entry never fails it.
  - When an extra entry is a selection's only marked file, the run splits with no `timing` test to run. The serial pass then collects the whole selection, selects nothing and exits 5, and M4's merge returns the parallel pass's code.

  What it returns:
  - repo-relative POSIX paths, deduplicated and sorted;
  - paths built from the walk without resolving symlinks, which M9's guard compares with the file part of pytest's node IDs.

  `plan_passes` calls the scan only after M6's three cases decline, so an `@file`, `--` or one-worker-or-fewer run reads no file. When `marked_files` is empty, it plans one unsplit pass with the caller's arguments verbatim. It takes the scan as a zero-argument callable, because the other shapes each fail:
  - Passing a finished scan would read every selected file for those runs too.
  - Splitting `plan_passes` into an argument check and a scan check would move the case order into `main()`, where only the `main()` tests could pin it.

  No scan error drops a test from the run:
  - An unreadable file counts as marked, so it can only cause a split.
  - A file the scan misses, such as one under an unreadable or symlinked directory, matters only when its mark is the selection's only one. The run then collapses to today's single pass. A split run's serial pass collects the whole selection, missed files included (M8).

  anchors: row12, row27, row31, row32, row33, row36, row86
- **M8. The serial pass collects the whole selection.** It gets the same targets and caller arguments as the parallel pass, and only its `-m` and `-n0` select its tests, as CI's serial step does (`tests.yml:227`). So in a split run, every `timing` test pytest collects from the selection, but the `saturates_cpu` one (M12), runs in the serial pass, whichever file it is collected from, an imported marked test included (row 50). An unsplit run (M6, M7) runs such a test once, as today's run does: under xdist, or with no workers when the run starts none.

  A test that is `timing` only through its defining module's `pytestmark` is not `timing` in a module that imports it. pytest reads a module's `pytestmark` from the module it collects the item in, and a function's marks from the function itself (`_pytest/python.py:281-287`, `:1599`). So such a test runs in the parallel pass when collected from the importing module.

  An `--ignore` narrowing was measured and dropped (rows 74, 76). The other narrowings each fail:
  - `-k` and `--deselect` act after collection (`_pytest/main.py:440-455`), so they save none of it.
  - Explicit file targets bypass pytest's own collection filters (G8), so they need the caller-path rules row 40 names (Out of scope).
  - A plugin would load into every split run (row 20).

  anchors: row14, row50, row55, row74, row75, row76
- **M9. A collection-based guard backs the scan and M12's marker.** `TestTimingMarkerCoverageParity` (`claude/.claude/tests/test_pytest_collection_config.py:200-245`) collects `claude/.claude/` three times: with `-m "not timing"`, with `-m timing`, and unfiltered. One test method now runs those three collections over every `FULL_SUITE_TARGETS` root (rows 44 and 81), and scans the real tree with `scan_timing_marks(FULL_SUITE_TARGETS, [], repo_root=REPO_ROOT)`.

  Each collection goes through `_collected_node_ids`, which returns the node IDs with the exit code and asserts the exit code itself. It accepts exit 0 alone unless its caller passes other codes in `accepted_exit_codes`. Its failure message gives the exit code, pytest's stderr and the last `COLLECTION_FAILURE_STDOUT_TAIL_LINES` (40) stdout lines, because a failed collect-only prints its error after the node-ID listing.

  The method then makes three assertions, each with its own failure message:
  - the existing partition assertion, which must hold over the wider scope;
  - the `-m timing` IDs and the scan's `marked_files` are not empty, and every file holding a collected `timing` test is in `marked_files`;
  - at least one unfiltered ID sits under each root, so a root dropped from the collection fails instead of passing vacuously.

  One method runs the three collections once per run, where a class-scoped fixture shared by several methods could repeat them in each worker (row 83).

  A fourth collection, in its own test, backs M12's marker, not the scan. It shares no collection with the method above and collects only `CPU_SATURATING_TEST_FILE`, the CPU-saturating test's file, with `timing and not (<SERIAL_PASS_MARKER_EXPRESSION>)`, the tests that `-m timing` selects and the serial pass deselects (row 83). It passes `accepted_exit_codes=(ExitCode.OK, ExitCode.NO_TESTS_COLLECTED)`, so exit 5 reaches the test's own assertion. Its outcomes:
  - an exit other than 0 or 5 fails inside the helper with its collection-failure message, which a moved or renamed file gives as exit 4 (G4);
  - exit 5, which a collection that selects nothing returns (row 11), or exit 0 with IDs other than exactly `CPU_SATURATING_TEST_NODE_ID`, fails with a message that the CPU-saturating test lost its `saturates_cpu` mark, no longer carries `timing` beside it, or was renamed without the constant;
  - exit 0 with exactly that node ID passes.

  So CI fails when that test's `saturates_cpu` mark is missing, removed, or has replaced `timing` (M12), even when another test carries the mark. No assertion on the three whole-suite collections can see this, because a collected ID carries no marker.

  The guard fails CI on a file the scan does not mark, so no collapse runs a `timing` test under xdist only because its mark sits in another file. The stake is lower than under the dropped narrowing: such a file now at worst collapses a run to today's single pass (M7), and it drops no test. The guard still fails CI on it (row 81). Its properties:
  - It reads pytest's own collected IDs, so it catches every route by which a file without the mark text holds a `timing` test: an import, an alias, a conftest hook, or a `pytestmark`.
  - It calls the runner's own scan and expression constants rather than restating them.
  - Each of its three existing collections grows to the whole suite (rows 44-45, 54) and runs once per run. The fourth adds one subprocess over one file. Verification step 1 lists the guard's durations.

  anchors: row44, row45, row50, row53, row54, row60, row81, row83
- **M10. Tests.**
  - A new `test_timing_split.py` holds table tests for M1's skip rule and M2-M8. Its contract test runs real pytest on a throwaway project with the argv `plan_passes` builds. That checks G1-G4, rows 9 and 71, and M12's exclusion at run time, which no table test can.
  - New `main()` tests in `test_select_tests.py` cover every collapse reason, the skip rule, the merge order and a raising first pass. Two wiring tests run the real scan on a `tmp_path` repo root. A CI parity test maps each pass's options one-to-one onto a `tests.yml` step, after removing M12's one named exclusion.
  - Selection tests pin the new `CROSS_DOMAIN_EXCEPTIONS` row (row 53).
  - The existing `main()` tests that assert on calls patch the scan with a recording stub (row 21).
  - M9's guard extends the existing collection class.

  anchors: row21, row22, row24, row35, row53, row56, row67, row71
- **M11. Docs.** README.md gains the split's caller-facing contract, and CHANGELOG.md gains a `### Changed` bullet (row 23).

  anchors: row18, row19, row23, row26, row60, row67
- **M12. The serial pass leaves out the CPU-saturating test.** The one `timing` test that starts a busy process per core (row 51) gains a second marker, `saturates_cpu`. `pyproject.toml`'s `markers` list registers it, which `--strict-markers` requires (row 66). The serial pass's expression is `timing and not saturates_cpu`, or `(<caller>) and timing and not saturates_cpu` (M2). So a split run never runs that test, and CI's serial step, `-m timing -n0`, still does.
  - The parallel pass needs no change, since `not timing` already excludes the test.
  - An unsplit run adds no `-m`, so a `-n 0` run still runs the test, as today. A `-n 1` run also collapses, but runs the test in a worker, where it skips itself (row 51).
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
6. The engineer's answer on a caller's `-n <N>`. [engineer-verified: "Parallel leg only (Recommended)"] The session's description proposed the mechanism: the serial pass appends `-n0` last, with no `-n` parsing. [unverified] M3 grounds that mechanism on G2 and G3. Row 85 narrows this row: a caller `-n` of 1 or less runs one unsplit pass, so only a `-n` of 2 or more reaches the parallel pass alone. M6's `-n` parsing serves only the collapses in rows 28 and 85.
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
14. A split run adds one pytest startup and one collection of the whole selection, and its added wall time is the serial pass's whole run. [unverified: reasoning from the facts below] The facts:
    - pytest's `-m` deselects only after collection (`_pytest/mark/__init__.py:257-284`), so the serial pass collects every selected file (M8). [verified: read] Row 76 measures that collection on the full suite and on `claude/.claude/scripts/tests`.
    - Each xdist worker collects the whole selection (`xdist/dsession.py:274-293`), so the parallel pass already collects it at least twice, given `compute_worker_count`'s floor of 2 (`select-tests.py:1175`, `:1280-1284`). That is CPU work. [verified: reads]
    - The passes run back to back, so wall time grows by the serial pass's startup, its collection, and every selected `timing` test run one at a time. [unverified: reasoning]
    - Every `timing` test but one already runs inside a worker today, so it moves from the workers into one process: the same work at a lower peak, over a longer wall time. The exception is row 51's test, which skips under any worker. A split serial pass would newly run it, with one busy process per core for 300 shim runs. M12 leaves it out, so a split run adds no test that today's run skips. [verified: a Grep of every `*.py` file for `PYTEST_XDIST_WORKER`, `cpu_count(`, `worker_id`, `is_xdist`, `xdist_worker` and `workerinput` finds no other test that branches on running in a worker. The load outcome is reasoning.]

    A parallel pass that ends in a collection error, pytest exit 2, still runs the serial pass (M1, row 29). The serial pass re-collects the whole selection with no narrowing, so it fails the same way, at the cost of one more collection. [unverified: that xdist reports a collection error as exit 2 was not read or probed] Row 29's answer predates the narrowing (rows 39-40), when the serial pass also collected the whole selection.

    M5's summary line reports each pass's wall time on every run, and the PR body records the `/ready-for-review` run's (Verification step 4).
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
    - These patch it to return one marked file, and assert two calls: `test_git_diff_unavailable_falls_back_to_full_suite` (`:3145-3170`), `test_domain_selected_paths_are_passed_through_to_run_pytest` (`:3172-3196`), `test_computed_env_reaches_run_pytest_unchanged` (`:3495-3515`), and `test_called_before_run_pytest` (`:3842-3867`).
    - `test_argv_none_falls_back_to_sys_argv` (`:3259-3283`) patches it to return no marked file and keeps its single-call assertion.
    - `test_stderr_scope_matches_recorded_pytest_argv_across_containment_collisions` (`:3348-3373`) runs against the real `_REPO_ROOT`. It patches the scan too, so it does not depend on where marks sit in the tree today.

    Each test that asserts a split clears `PYTEST_XDIST_AUTO_NUM_WORKERS` and patches `_cpu_budget` to return 8. Otherwise a developer who set the variable to 0 or 1 would collapse the run under test (M6), because `main()` reads the caller's value through `pytest_subprocess_env(dict(os.environ), ...)` (`select-tests.py:1393-1395`). On a one-CPU host the sizing would write 1 and collapse it too (M6). [verified: reads of `pytest_subprocess_env` and `compute_worker_count`]

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
27. The engineer's concern, typed after the adversarial review: [engineer-verified: "I am worried that running tests locally like CI does will lead to more load on the machine"] It covers the extra load the split adds to a local run. Rows 14, 28-33, 39-49, 55, 74-77 and 80-86 weigh that load.
28. The engineer's answer on a caller's `-n 0`. [engineer-verified: "Collapse on -n0 (Recommended)"] It covers running one unsplit invocation, with the caller's arguments verbatim, when the caller's `-n` is 0. The session proposed the description: parse `-n0`, `-n 0` and `--numprocesses=0`, and send any other `-n` to the parallel pass only. [unverified] M6 adds `-n=0`, `--numprocesses 0`, last-wins (G2, G4), and xdist's integer reading (`xdist/plugin.py:56-60`). Approach records why a bare `--pdb` does not also collapse.
29. The engineer's answer on fail-fast flags. [engineer-verified: "Keep run-both (Recommended)"] It covers running the serial pass after a failed parallel pass even under `-x`, `--maxfail` or `--pdb`, with no fail-fast parsing. Row 42 narrows it: the serial pass is skipped after exit 3, exit 4 or a signal, which covers `--pdb` with workers (exit 4).
30. Hooks test modules import names from sibling test modules, for example `claude/.claude/hooks/tests/test_check_python_floor.py:33-35` and `test_continuity_glob_parity.py:25-28`. [verified: Grep] pytest collects a test function or class that one test module imports from another inside the importing module as well. [unverified: pytest's collection of imported names was not read] So a marked test can be collected in a file whose text has no mark. Row 50 records probes showing pytest does collect it there. That is why M9's guard checks the scan against pytest's collection, and why M7 falls back to the unsplit pass instead of dropping tests.
31. The engineer's answer on a prefilter. [engineer-verified: "Add prefilter (Recommended)"] It covers scanning the selection for `mark.timing` and skipping the serial pass when nothing matches. The session proposed the description [unverified]:
    - scan the resolved target files and skip the serial pass when none match;
    - add a test pinning that the marker is applied only as a literal in test files;
    - run the serial pass anyway when a caller passes path arguments the scan cannot see.

    M7 adopts the scan. M9's collection-based guard replaces the pin (row 44). The plan departs from the description in two places. First, a selection with no match runs one unsplit pass, as today, instead of the parallel pass alone. A miss then leaves a test running under xdist, never in neither pass (row 34). Second, M7 scans the caller arguments that name existing paths (row 32), instead of treating every caller path as unseen.
32. A caller argument is scanned when it does not start with `-` and names an existing path under `repo_root` once any `::` suffix is removed. [unverified: reasoning, as are the first three rules below] The other rules:
    - The scan skips every value M2's shared option scan recognizes for `-k`, `-m`, `-n` or `--numprocesses`. So the `foo` in `-k foo` never counts, even when a directory named `foo` exists. The arguments it reads hold no bare `--`, because `plan_passes` collapses such a run before it calls the scan (M6, M7).
    - Another option's value that names a path, such as `--ignore <dir>`, is scanned. At worst that splits a run that could have collapsed.
    - Some paths stay out of the scan's sight: module names under `--pyargs` and paths in `PYTEST_ADDOPTS`. For those, the verdict rests on the resolved targets, and a miss falls back to the unsplit pass.
    - A path outside `repo_root` after `os.path.normpath`, such as an absolute path elsewhere, is skipped without raising. `Path.relative_to` would raise `ValueError` on it. [unverified: a reviewer's probe] pytest still collects that path in both passes as an initial path, so a skip at worst collapses the run to today's single pass.
    - `run_pytest` runs pytest with `cwd=repo_root` (`select-tests.py:1322`, `:1435`), so a relative caller path resolves against `repo_root`. [verified: read]
33. The scan reads every test-pattern file under the scanned directories, with no early stop, because M9's guard needs the whole marked list. The four roots hold about 21 MB of `.py` files. [unverified: a reviewer's measurement] A full-suite run reads the test files among them once. [unverified: not timed] An early stop would help only `plan_passes`, and only on a run that then splits, where each pass's collection costs ten seconds of CPU or more (row 76). [unverified: reasoning]
34. CI's split is `-m "not timing"` (`tests.yml:222`) and `-m timing -n0` (`:227`), and it runs every `timing` test in the suite serially on every PR and main push, whatever `select-tests.py` runs locally. [verified: read] This plan mirrors that split, apart from M12's `saturates_cpu` exclusion, and leaves `tests.yml` unchanged (Out of scope). `docs/design-decisions/ci-stays-an-unconditional-full-suite-backstop.md` records why CI always runs the whole suite.
35. The engineer's answer on the CI parity test, now in M10, which the Ask did not call for. [engineer-verified: "Keep it (Recommended)"]
36. The engineer's answer on row 31's two departures from the prefilter description. [engineer-verified: "Accept both (Recommended)"]
37. The engineer's confirmation of the relayed Ask quote (row 25). [engineer-verified: "Yes, accurate"]
38. The engineer's answer on the ~600-line projected diff. [engineer-verified: "Proceed anyway"]
39. The engineer's answer on narrowing the serial pass. [engineer-verified: "Narrow, with guard (Recommended)"] It covers collecting, in the serial pass, only the selected files that contain `mark.timing`. Row 74 supersedes it on narrowing. M9 still holds the guard.
40. The session proposed the selected option's description [unverified]:
    - the serial pass targets only the marked files;
    - a collection-based test asserts that every collected `timing` test sits in a file containing the mark text, so an import or alias fails CI instead of being skipped;
    - the guard likely lives in `claude/.claude/tests/test_pytest_collection_config.py`.

    It reversed this plan's earlier rejection of narrowing. The plan adopts the guard (M9) and the narrowing, but not "targets only the marked files": M8 keeps the targets and skips each unmarked test file with `--ignore`. A model's later review found that explicit file targets need three extra rules: no narrowing when a caller argument names a path, the `python_files` patterns, and the `norecursedirs` pruning. [unverified: model output relayed by the session] `--ignore` needs none of them for correctness (G8). Row 74 supersedes this row on narrowing.
41. The engineer's first answer on the collapse threshold. [engineer-verified: "Collapse at ≤1 (Recommended)"] It covered collapsing any run whose effective worker count is 0 or 1. Row 46 superseded it, and row 85 supersedes both.
42. The engineer's answer on a parallel pass that exits 3, exits 4 or dies from a signal. [engineer-verified: "Skip on 3/4/signal (Recommended)"] It covers skipping the serial pass and returning that code. The question stated that row 29's run-both answer for exit 2 stands.
43. The engineer's first answer on `tmp_path` retention. [engineer-verified: "Add the option (Recommended)"] It covered adding `-o tmp_path_retention_count=2` to the serial pass. Row 48 supersedes it.
44. The engineer's answer on the guard's scope. [engineer-verified: "All four roots (Recommended)"]
45. The session proposed the selected option's description [unverified]: widen the existing timing collection in `TestTimingMarkerCoverageParity` to every `FULL_SUITE_TARGETS` root, and assert on the IDs it already collects. That adds no subprocess, but each of the test's three collections grows to the whole suite. The partition test's own assertion must still hold over the wider scope. M9 adopts it with one departure: the fourth collection, for M12's marker, adds one subprocess. Verification step 1 lists the guard's durations. The description's premise holds: `_collected_node_ids` collects `claude/.claude/` alone (`test_pytest_collection_config.py:209-229`). [verified: read]
46. The engineer's answer on the collapse threshold. [engineer-verified: "Effective 0 only (Recommended)"] Row 85 supersedes it.
47. The session proposed the selected option's description [unverified]: collapse only when the run has no workers. A run capped at one worker still splits, but the narrowed serial pass costs little, and every `timing` test runs truly serially. M6 adopted it, and row 85 supersedes it.

    Since row 74, the serial pass is not narrowed, so a one-worker split pays one collection of the whole selection, which row 76 measures. `compute_worker_count` sizes a run at no fewer than `min(2, cpu_budget)` workers (`select-tests.py:1175`, `:1280-1284`), so only a caller's `-n 1`, a `PYTEST_XDIST_AUTO_NUM_WORKERS=1`, or a one-CPU budget gives one worker. [verified: read] The engineer was asked again with that cost stated and chose to keep row 46's answer (row 80). A later answer collapses such a run (row 85).
48. The engineer's answer on `tmp_path` retention. [engineer-verified: "Drop; document (Recommended)"]
49. The session proposed the selected option's description [unverified]: no extra option, and the CI parity test needs no exception. README notes that a run where both passes fail may lose the parallel pass's tmp dirs. M11 adopts it, and row 26 states when the loss happens. The description's "needs no exception" concerns the dropped `tmp_path` option only. M12's `saturates_cpu` suffix, adopted later, is the parity test's one named exception (M10).
50. pytest collects an imported marked test under the importing file. An imported marked function, an imported marked class, and a subclass of an imported marked mixin are each collected there by `-m timing`, though that file lacks the text. [unverified: a model's probes with pytest 8.4.2 in `/tmp`, relayed by the session, not re-run] An AST pass found three `from X import` names starting `test_` or `Test` across the four roots, none of them marked. [unverified: a reviewer's count] So no such route exists in the tree today, and M9's guard fails CI if one appears.
51. `claude/.claude/scripts/tests/test_cursor_adapter_shim_hook_run.py:170-201` holds a `timing` test that skips whenever `PYTEST_XDIST_WORKER` is set, that is, under any xdist worker (`:174-176`). Otherwise it starts `os.cpu_count()` busy-spin processes, each living up to `CONTENTION_HOG_LIFETIME_SECONDS = 300` (`:51`), and runs the shim 300 times under them (`:191-197`). [verified: read] Today a `select-tests.py` run reaches it only when the caller's `-n` or `PYTEST_XDIST_AUTO_NUM_WORKERS` starts no workers, since every other run uses xdist. M12 keeps every split run from reaching it.
52. Exit 3 and exit 4 mark a pytest error rather than a test result. `--pdb` with workers is a usage error, exit 4 (`xdist/plugin.py:330-334`), as in today's single run. [verified: read] A malformed `-m` expression exits 3 under xdist and 4 under `-n0`. [unverified: a reviewer's probe] Either way, M1 skips a serial pass that would only repeat the error.
53. A change to `_timing_split.py` needs a `CROSS_DOMAIN_EXCEPTIONS` row that selects `test_pytest_collection_config.py`, because M9 makes that test import `_timing_split`. This plan adds that one row. `select-tests.py` declares by hand each test that imports a scripts module from another domain, as such a row (`:260-267`, `:969-973`). [verified: read] `test_select_tests.py` pins a row in three places [verified: reads]:
    - its constant in `_EXACT_MATCH_LITERAL_PATH_CONSTANTS` (`:2511-2516`), where an unregistered constant fails nothing [unverified: a reviewer's read];
    - a file target in `_FILE_TARGETS` (`:2565-2569`), where an unregistered file target fails `test_every_directory_target_exists_on_disk` (`:2826`) [unverified: a reviewer's read];
    - a selection test such as `test_skill_auxiliary_files_module_change_also_selects_skills_tests` (`:668-673`).

    Local runs of the guard have a limit. `_is_test_tree_packaging_change` already selects `claude/.claude/tests` for any change under `claude/.claude/hooks/tests` or `claude/.claude/scripts/tests` (`select-tests.py:669-675`), so a cross-file import added there runs the guard locally. [verified: read] A change under `evals` or `claude-skills` does not, and CI runs the guard on every PR (row 34).

    The same rule selects the guard when the CPU-saturating test's file changes, so that file needs no row or path constant of its own, and the guard holds its path as a literal (M9). `test_scripts_tests_dir_py_file_selects_claude_tests_dir` in `test_select_tests.py` pins that selection. [verified: reads of the rule's `CROSS_DOMAIN_EXCEPTIONS` entry, `(_is_test_tree_packaging_change, (CLAUDE_TESTS_DIR,))`, and of that test. Not confirmed at run time until the code-writer runs the selection tests.]
54. Each of the guard's three whole-suite collections keeps its 120-second timeout (`test_pytest_collection_config.py:226`) at whole-suite scope. [unverified: no whole-suite collection was timed] Each grows by 59 of 409 test-pattern files, about 17%. [unverified: a reviewer's count] The fourth collection, for M12's marker, covers only the CPU-saturating test's file (row 83), under the same timeout. Verification step 1 runs the test and lists its duration.
55. The dropped narrowing (M8) gave the serial pass's argv one `--ignore=<path>` per unmarked test file. That is about 342 values, roughly 24 KB, for the full suite and about 163 for `claude/.claude/scripts/tests`, against a 1,048,576-byte `ARG_MAX`. [unverified: reviewers' `grep` counts and `getconf ARG_MAX` output] The CPU cost grows with walked entries times `--ignore` values, not with the value count alone:
    - pytest's `pytest_ignore_collect` turns every `--ignore` value into an absolute path on each call, then searches that list (`_pytest/main.py:404-408`). [verified: read]
    - Collection calls that hook once per directory entry it walks (G8's `_pytest/main.py:523-544` and `_pytest/python.py:697-707`).
    - Each conversion of a relative value calls `os.getcwd()`. [unverified: two reviewers' reads and a cProfile run]
    - Estimated cost on a loaded macOS host: about 345k conversions, roughly 15 s of CPU, for a full-suite serial pass, and about 34k, roughly 1.4 s, for `scripts/tests`. [unverified: reviewers' entry counts and micro-benchmarks, not re-run]

    Row 76 records the measured net, and row 74 the drop of the narrowing.
56. A pytest that a test spawns inherits the test's environment, and xdist sets `PYTEST_XDIST_WORKER` in each worker process (`test_cursor_adapter_shim_hook_run.py:174`). [verified: the comment there was read. xdist's source was not.] So the contract test removes that variable from its child's environment before it checks that the serial pass sets none.
57. The projected diff is about 1,310 lines, about 60 above the ~1,250 row 69 accepted. Row 69 supersedes rows 38 and 58 for the size question. [unverified: an estimate] Row 78 supersedes this estimate. The growth came in two steps:
    - The `--` collapse, the first `pyproject.toml` error cases, the guard's fourth collection and the `saturates_cpu` cases took it from about 1,200 to about 1,260.
    - Round 4's fixes add about 50: the remaining `pyproject.toml` cases and the outside-path case, the guard's exit-5 routing and its shim-file and pruning assertions, and the scan that runs only after the argument-only collapses.
58. The engineer's answer on the ~1,100-line projected diff. [engineer-verified: "Proceed anyway"] Row 69 supersedes it.
59. The engineer's answer on the `--ignore` narrowing mechanism, which replaces row 40's description of passing only the marked files. [engineer-verified: "Accept --ignore (Recommended)"] Row 74 supersedes it.
60. The engineer's answer on what happens locally to the CPU-saturating `timing` test at `test_cursor_adapter_shim_hook_run.py:170-201` (row 51). [engineer-verified: "Keep it CI-only (Recommended)"]
61. The session proposed the selected option's description [unverified]:
    - add a registered marker, such as `saturates_cpu`, to that one test;
    - have the local serial pass add `and not saturates_cpu` to its `-m`, while CI's serial leg still runs it;
    - add `pyproject.toml`'s `markers` list (`:33-35`) and that test file to scope.

    M12 adopts it and settles the name `saturates_cpu`, after the property the test has rather than the policy applied to it.
62. The engineer's answer on `--ignore`'s per-entry cost (row 55). [engineer-verified: "Keep --ignore, measure (Recommended)"] Its measurement failed the decision rule (row 76), and row 74 supersedes it.
63. The session proposed the selected option's description [unverified]:
    - keep the accepted mechanism;
    - Verification runs two collect-only comparisons of the serial pass, with and without the `--ignore` tokens, on the full suite and on `scripts/tests`;
    - if narrowing does not save CPU at full-suite scale, the session comes back to the engineer before shipping.

    Verification step 2 adopted it and stated the decision rule. The session came back to the engineer when the rule failed (row 74).
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
72. Row 86 supersedes this row. The `tomllib` read of `norecursedirs` and its error handling were built for M7's pruning, then removed with it. The row records what that handling rested on. `tomllib` raises `TOMLDecodeError`, a `ValueError` subclass, on invalid TOML (`tomllib/_parser.py:71`). `tomllib.load` decodes the file's bytes with `bytes.decode` (`:136`), whose `UnicodeDecodeError` is also a `ValueError`. [verified: read of CPython 3.14's `tomllib/_parser.py`] So catching `OSError` and `ValueError` covers the read, decode and parse failures on which M7 prunes nothing. [unverified: reasoning] A deeply nested array makes `tomllib.load` raise `RecursionError`, which neither clause catches. [unverified: staff-backend-engineer's round-4 probe] Only a pathological file raises it, not an honest edit to `pyproject.toml`, so M7 leaves it uncaught.
73. A bare `--` in `PYTEST_ADDOPTS` reaches pytest ahead of the command line (G3), so every token after it is positional (G4), each pass's appended options included. With `PYTEST_ADDOPTS='--'`, today's argv `tests` passes, while the parallel pass's argv `tests -m 'not timing'` collects nothing and exits 5. [unverified: staff-backend-engineer's round-4 probe. The serial pass's argv was not probed.] The serial pass's options land after the same `--`, so it is expected to collect nothing too, and the merged exit is then 5. [unverified: reasoning] Such a run fails with a non-zero exit where today's passes, instead of widening.
74. The engineer's answer after Verification step 2's full-suite pair failed its CPU rule. [engineer-verified: "Drop the narrowing (Recommended)"] It covers dropping the `--ignore` narrowing, so the serial pass collects the whole selection (M8). It supersedes rows 39, 59 and 62 on whether the serial pass narrows. The question's text, the session's own, gave the failed rule and row 76's first full-suite pair. It said the selected counts matched and the `scripts/tests` scope improved. It set the amounts beside the serial pass's run time in row 77.
75. The session proposed the selected option's description [unverified]:
    - take the plan's fallback, where the serial pass collects the whole selection with `-m timing -n0`, as CI does;
    - remove the unmarked-file walk and its pruning code and tests, so the diff gets much smaller;
    - it needs code changes, a README and CHANGELOG update and another review round;
    - scoped runs lose a saving of about 4 s.

    The plan adopts it with three departures:
    - The serial pass keeps M12's `and not saturates_cpu` (row 60).
    - M7 at first kept its `norecursedirs` pruning, which "its pruning code" can be read to include (row 82). Row 86 removes the pruning, its `pyproject.toml` read and their tests, so this departure no longer stands. The unmarked-file listing and its tests also go, the `evals/fixtures` assertion among them.
    - The diff does not get much smaller (row 78).
76. Verification step 2's comparison ran four times on the committed tree, with the snippet that step holds in commit 59b17e2e. [unverified: the session's unsaved record of its own runs. The output was not saved, so these figures are the only record.]
    - Full suite: both runs of every sample exited 0 and selected 220 tests, of 41,515 collected unnarrowed and 12,144 narrowed.
    - Full-suite user+sys CPU, narrowed against unnarrowed, with the 1-minute load average:
      - first sample, load 18-31: 30.2 s against 25.2 s, +5.0 s;
      - repeat 1, load 11.4: 27.3 s against 23.0 s, +4.3 s;
      - repeat 2, load 13.4: 29.7 s against 21.8 s, +7.9 s;
      - repeat 3, load 18.8: 28.6 s against 22.9 s, +5.7 s.
    - `claude/.claude/scripts/tests`: the narrowed run was lower every time, 6.1-7.1 s against 10.0-11.2 s.

    So the full-suite pair failed the CPU rule in every sample. The likely cause is that about 342 `--ignore` values cost more in per-entry matching (row 55) than the skipped imports save at full-suite scale. [unverified: the session's reading, not profiled]
77. Verification step 1's first run used the committed tree, narrowing included. [verified: the session's run]
    - The 1-minute load average was about 54 on 16 logical cores.
    - The parallel pass failed 396 tests and errored 139, all in hook and shell test files this diff does not touch.
    - At the same load, the merge base failed 72 of those tests and the branch 64. So the failures track the load, not this change. [unverified: the session's reading of those counts]
    - The serial pass exited 0, with 207 passed, in 588 s.
    - The guard's six tests and 469 tests in `test_timing_split.py` and `test_select_tests.py` passed.

    The run therefore exited non-zero. Verification step 1 states why it cannot stand in for step 1's run.
78. The committed implementation's diff against `origin/main`, leaving out `.claude/plans/`, measured 1,636 changed lines. [unverified: the session's count] The drop was estimated to take it to about 1,600, about 350 above the ~1,250 that row 69 accepted and about 2% below the committed diff. Row 75's description proposed a "much smaller" diff. [unverified: an estimate. The two new files' working-tree line counts were read while the narrowing's removal was in progress. Each modified file's figure is its growth over its base length, from row 22 or the guard class's base span, plus estimated deletions.] After the drop and row 86's removal of the pruning, the working tree's diff against the merge base, leaving out `.claude/plans/`, measures 1,501 changed lines, the Projected diff line's figure. That is about 8% below the committed diff, about 100 below the ~1,600 that row 79 accepted, and about 250 above row 69's ~1,250. [unverified: the session's `git diff 7ba14dba14a612e4f888054d9924d17563252c0a --numstat` count, not re-run]
79. The engineer's answer to `/plan-review`'s size question, asked once more because row 75's description said the drop would make the diff "much smaller" and row 78 shows it does not. [engineer-verified: "Proceed anyway"] It covers proceeding with the dropped narrowing and the single PR at the projected diff of about 1,600 lines. Row 69's answer covered about 1,250.
80. The engineer's answer on the one-worker split, asked again after the narrowing's drop. [engineer-verified: "Keep it (Recommended)"] It covers keeping row 46's "Effective 0 only" now that a one-worker split pays a collection of the whole selection (row 47). The question's wording and its option descriptions were the session's own, and the question stated that cost. Row 85 supersedes it.
81. The engineer's answer on the guard's scope, asked again after the narrowing's drop. [engineer-verified: "Keep four roots (Recommended)"] It covers keeping rows 44 and 45's four-root guard now that a missed mark costs a collapse to one pass, not a dropped test. The question's wording and its option descriptions were the session's own. Row 83 supersedes it on the guard's structure only, and its four-root scope stands.
82. The engineer's answer on the scan's pruning, which row 75's description could be read to remove. [engineer-verified: "Keep the pruning (Recommended)"] It covers keeping M7's `norecursedirs` pruning. The question's wording and its option descriptions were the session's own. Row 86 supersedes it.
83. The engineer's answer on the guard's structure, asked after a plan-architect consult recommended folding it. [engineer-verified: "Fold into one method (Recommended)"] It covers removing the class-scoped fixture, so one test method runs the three whole-suite collections and the partition, scan-parity and root-coverage assertions. The `saturates_cpu` check runs its own collection over only `CPU_SATURATING_TEST_FILE`, with `timing and not (<SERIAL_PASS_MARKER_EXPRESSION>)`, and asserts exit 0 and the exact node ID. It supersedes row 81 on the guard's structure only, and row 81's four-root scope stands. The question's wording and its option descriptions were the session's own. The consult's reason, relayed by the session: under the ini's `-n auto`, a class-scoped fixture can run in several workers, each repeating the three whole-suite collections. [unverified: the consult's and the session's reading. xdist's fixture scoping was not read.]
84. The engineer's answer on Verification step 1's full-suite run. [engineer-verified: "Targeted run (Recommended)"] It covers replacing that run with a targeted `-n0 --durations=15` run of the guard and the two split test files on the final tree. The full-suite evidence and the failure procedure move to the one `/ready-for-review` run (Verification step 4). The question's wording and its option descriptions were the session's own. The session's reason: step 1's only output that `/ready-for-review`'s run does not also give was the informational `--durations=15`. [unverified: the session's reading] `/ready-for-review` runs CLAUDE.md's Commands inline (`ready-for-review/SKILL.md:64-66`), and for this diff `select-tests.py` selects the full suite, CLAUDE.md's first full-suite case. [verified: reads]
85. The engineer's answer on the one-worker split, asked a third time after the consult. [engineer-verified: "Collapse at one worker"] It covers running one unsplit pass, as with no workers, when the run's worker count is 1 or fewer. It supersedes rows 41, 46 and 80, and M6 adopts it. The question's wording and its option descriptions were the session's own. The session's reason: one worker has no sibling workers for the serial pass to protect, so the split buys nothing and pays a whole-selection collection (row 47). [unverified: the session's reading]
86. The engineer's answer on the scan's pruning, asked again after an adversarial review. [engineer-verified: "Remove the pruning (Recommended)"] It covers removing M7's `norecursedirs` pruning, so the scan walks every selected directory with no pruning. It supersedes row 82, row 72, row 75's second departure, and M7's pruning text. The question's wording and its option descriptions were the session's own. The review said the stated reasons for keeping the pruning no longer held, and the session's description said the diff would shrink by roughly 100 to 150 lines. The reason, the session's and the review's reading [unverified: not checked by a run]:
    - An over-inclusive scan costs at most one serial pass that selects nothing and exits 5, which M4's merge absorbs.
    - The pruning was the only scan logic that could wrongly drop a file pytest collects.

    The removal took out about 30 lines of scan code, `_timing_split.py`'s `tomllib` import, the nine `pyproject.toml` error-case tests, the table case that pruned `worktrees` and `fixtures/nested`, and the guard's test that pinned the pruning to the real `pyproject.toml`. [verified: reads of `_timing_split.py`, `test_timing_split.py` and `test_pytest_collection_config.py` on the working tree, which hold none of them. The line count is the review's, not recounted.]

## Critical files

Use one `code-writer` dispatch, because the test updates depend on the exact argument lists `_timing_split.py` builds, and one agent's self-review should see both. A later change to the code, such as the narrowing's removal (row 74), gets its own such dispatch. Each dispatch prompt states these rules:
- It runs no `select-tests.py` command, because this diff makes every one a full-suite run (Verification).
- It runs only `test_timing_split.py` and `test_select_tests.py`, each with `scripts/venv-run.sh pytest <file> -n0`. The `-n0` overrides the ini's `-n auto`, which xdist sizes from the CPU count rather than the load (G2, G3).
- It leaves `test_pytest_collection_config.py`, whose guard runs three whole-suite collections, to Verification step 1.
- It never runs `test_cursor_adapter_shim_hook_run.py`, where a `-n0` run starts the CPU-saturating test (row 51).
- Comments and docstrings state the one-line facts given below and cite no M or row label.
- Paths are repo-relative.

- `claude/.claude/scripts/_timing_split.py`: **create.**
  - The module docstring is one line: it plans the pytest passes for a selection, either the parallel and serial passes `tests.yml` runs or one unsplit pass.
  - Imports: `fnmatch`, `os`, `pathlib.Path`, `typing.NamedTuple`, `Callable`, `Iterable` and `Sequence` from `collections.abc`, and `from pytest import ExitCode` (row 18).
  - Public constants:
    - `TIMING_MARKER = "timing"` and `TIMING_MARK_TEXT = f"mark.{TIMING_MARKER}"`;
    - `XDIST_WORKER_ENV_VAR = "PYTEST_XDIST_AUTO_NUM_WORKERS"`, moved here from `select-tests.py:1170`;
    - `TEST_FILE_PATTERNS = ("test_*.py", "*_test.py")`, with a one-line comment: pytest's default `python_files`, which `pyproject.toml` does not override;
    - `SATURATES_CPU_MARKER = "saturates_cpu"`;
    - `PARALLEL_PASS_MARKER_EXPRESSION = f"not {TIMING_MARKER}"` and `SERIAL_PASS_MARKER_EXPRESSION = f"{TIMING_MARKER} and not {SATURATES_CPU_MARKER}"`. The serial one carries a one-line comment: CI's serial step runs `saturates_cpu` tests, and a local serial pass leaves them out because each starts one busy process per core.
    - the pass names `PARALLEL_PASS = "parallel"`, `SERIAL_PASS = "serial"` and `UNSPLIT_PASS = "unsplit"`;
    - five reason constants holding M5's unsplit reasons, the environment one built from `XDIST_WORKER_ENV_VAR`.

    Private constants hold `"-m"`, `"-n"`, `"--numprocesses"`, `"-k"`, `"-n0"` and `"--"`, and `_MIN_WORKERS_TO_SPLIT = 2`. That last one carries a one-line comment: one worker has no sibling workers for the serial pass to protect, so a split would pay a second whole-selection collection for nothing.
  - Three `NamedTuple`s:
    - `TimingMarkScan`: `marked_files: tuple[str, ...]`, holding sorted repo-relative POSIX paths.
    - `PytestPass`: `name: str`, `added_options: tuple[str, ...]` and `pytest_args: list[str]`. `pytest_args` holds the caller's remaining arguments, followed by the added options.
    - `PassPlan`: `passes: tuple[PytestPass, ...]` and `unsplit_reason: str | None`, which is None when the plan splits.
  - One private helper finds every occurrence of a value-taking option, in the forms G4 lists, with each occurrence's token span and value. M2, M6 and the caller-path probe share it. Its docstring states its precondition in one line: the arguments hold no bare `--`, because `plan_passes` collapses such a run before any caller of this helper reads them.
  - `split_caller_marker_expression(caller_args: list[str]) -> tuple[str, list[str]]` works per M2. Its docstring says it removes every recognized `-m` and returns the last one's expression, since pytest's `-m` is last-wins. A second sentence says an unrecognized form stays, and each pass's own `-m` overrides it.
  - `one_or_fewer_workers_reason(caller_args: list[str], *, auto_num_workers: str | None) -> str | None` works per M6, returning a reason when the count it reads is below `_MIN_WORKERS_TO_SPLIT`. Its docstring says it returns the reason the run would start one worker or none, that the last `-n` decides, read the way xdist reads it, and that `auto_num_workers` decides only when that `-n` is absent, `auto` or `logical`.
  - `scan_timing_marks(target_paths: Iterable[str], caller_args: Sequence[str], *, repo_root: Path) -> TimingMarkScan` works per M7.
    - A private helper returns the caller paths per row 32. It tests containment with `Path.is_relative_to` on the `os.path.normpath` of the joined path, not with `Path.relative_to`, which raises.
    - It walks with `os.walk` from `repo_root / path` into every subdirectory, with no pruning (row 86), and builds each returned path with `os.path.relpath(..., repo_root)`, never resolving a symlink.
    - Its docstring says an unreadable file counts as marked, and that a directory walk reads only files matching the test-file patterns and descends into every subdirectory, while a file named directly is read whatever its name.
  - `plan_passes(caller_args: list[str], *, auto_num_workers: str | None, scan_selection: Callable[[], TimingMarkScan]) -> PassPlan` checks four collapse cases, in this order:
    1. a caller token starts with `@`;
    2. a caller token equals `--`;
    3. `one_or_fewer_workers_reason` returns a reason;
    4. the `marked_files` of `scan_selection()` is empty.

    It calls `scan_selection` only when the first three decline (M7). The first case that applies plans one `UNSPLIT_PASS` with its reason, no added options, and the caller's arguments verbatim. Otherwise it plans the two passes per M2, M3 and M8, parallel first, each with its options appended after the caller's remaining arguments:
    - Parallel options are `("-m", <PARALLEL_PASS_MARKER_EXPRESSION, combined>)`. Combined means `(<caller>) and <expression>` when the caller has an expression.
    - Serial options are `("-m", <SERIAL_PASS_MARKER_EXPRESSION, combined>, "-n0")`.
    - The `--` check carries a one-line comment: pytest reads every token after a `--` as a path, so a split pass's appended options would become missing paths.
  - `skips_serial_pass(parallel_exit_code: int) -> bool` works per M1. Its docstring says exit 3, exit 4 and a death by signal are a pytest error or a kill, not a test result, so a second pass would only repeat it.
  - `merge_pass_exit_codes(exit_codes: Sequence[int]) -> int` works per M4, for one code or two. Its docstring says a pass that collected no tests defers to the other, and otherwise the first failing pass's code wins.
- `claude/.claude/scripts/select-tests.py`: **modify.**
  - Import `shlex` and `time`. Import `PARALLEL_PASS`, `XDIST_WORKER_ENV_VAR`, `PassPlan`, `PytestPass`, `merge_pass_exit_codes`, `plan_passes`, `scan_timing_marks` and `skips_serial_pass` from `_timing_split`, next to the other underscore-module imports (`:18-20`), and delete the definition at `:1170`. Callers reach each name through this module's globals, so `_mod.XDIST_WORKER_ENV_VAR` keeps resolving and tests can patch the functions.
  - Beside the cross-domain import declarations (`:260-267`), add `TIMING_SPLIT_MODULE = "claude/.claude/scripts/_timing_split.py"` and `PYTEST_COLLECTION_CONFIG_TEST_PATH = "claude/.claude/tests/test_pytest_collection_config.py"`, with a one-line comment in that block's style. Add the `CROSS_DOMAIN_EXCEPTIONS` row `(lambda p: p == TIMING_SPLIT_MODULE, (PYTEST_COLLECTION_CONFIG_TEST_PATH,))` next to `SKILL_AUXILIARY_FILES_MODULE`'s row at `:969` (row 53). `test_select_tests.py` registers both constants. Add no row or path constant for the CPU-saturating test's file, which `_is_test_tree_packaging_change`'s row already covers (row 53).
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
  - `one_or_fewer_workers_reason`:
    - The caller reason, for a count of 0 or less: `-n0`, `-n 0`, `-n=0`, `--numprocesses 0`, `--numprocesses=0`, `-n 00`, `-n=-1`, `-n 4 -n0`, and `-n 0` with `auto_num_workers="4"`.
    - The caller reason, for a count of 1: `-n 1`, `-n1`, `-n=1`, `--numprocesses 1`, `--numprocesses=1`, `-n 4 -n1`, and `-n 1` with `auto_num_workers="4"`.
    - The environment reason: no `-n`, `-n auto` and `--numprocesses=logical`, each with `auto_num_workers` set to `"0"` and to `"1"`, and no `-n` with `auto_num_workers="-1"`.
    - None, in three groups:
      - no `-n`, with `auto_num_workers` set to None, `"2"`, `""` or `"x"`;
      - a `-n` of 2 or more that wins: `-n 2`, `-n 4`, `-n 2` with `auto_num_workers` set to `"0"` and to `"1"`, `-n0 -n 4`, and `-n1 -n 2`;
      - a `-n` the scan does not read or cannot parse: a trailing bare `-n`, the separated `-n -1`, the unparseable `-n x`, `--numproc 0`, `--numproc 1`, and the cluster `-vn0`.
  - One test loads `pyproject.toml` with `tomllib` from `helpers.REPO_ROOT` and asserts that some `markers` entry starts with `f"{SATURATES_CPU_MARKER}:"`. Its failure message says the serial pass deselects that marker by name, so a mismatch would let a local run start the test.
  - `scan_timing_marks`, over `tmp_path` trees with `repo_root=tmp_path`. Each case asserts `marked_files`:
    - a directory with one marked and one unmarked test file;
    - a marked file two directories deep;
    - a directory with no mark, where neither test file is listed;
    - a marked file named directly, and an unmarked one, which is not listed;
    - a walked `helper.py` and a `notes.txt` that hold the text, neither of which counts;
    - a `helper.py` named directly that holds the text, which counts;
    - a missing target;
    - a caller argument naming a marked file with a `::Class::test[a::b]` suffix;
    - the caller arguments `-k sub`, where `sub` is an existing marked directory, which the scan skips, and a bare `sub`, which it scans;
    - a dangling `test_dangling.py` symlink, which counts as marked;
    - with `repo_root` set to a subdirectory of `tmp_path`, an absolute caller path to a marked file outside it, which the scan skips without raising, so `marked_files` is empty.
  - `plan_passes` unsplit cases. Each plans one `UNSPLIT_PASS` with the arguments verbatim. Every case but the last passes a `scan_selection` that fails the test when called, which shows that such a run reads no file:
    - `@args.txt -n 0` plans the `@` reason, which comes first;
    - `-n 0 -- tests/x.py` plans the `--` reason, which comes before the caller reason;
    - `-k foo -- some/path.py` and `-m slow -k foo -- tests/x.py` each plan the `--` reason, and the second keeps its `-m slow`;
    - `-n 0` and `-n 1` each plan the caller reason;
    - `auto_num_workers` set to `"0"` and to `"1"` each plan the environment reason;
    - a `scan_selection` returning no marked file plans the no-marks reason.
  - `plan_passes` split cases, each with a `scan_selection` returning one marked file:
    - The names come in the order `PARALLEL_PASS`, then `SERIAL_PASS`, and `unsplit_reason` is None.
    - With no caller arguments, the options are `("-m", "not timing")` and `("-m", "timing and not saturates_cpu", "-n0")`, written as literals so that a change to either constant fails here.
    - With `-m slow -k foo`, each pass's arguments are `-k foo` followed by its own options. The expressions are `(slow) and not timing` and `(slow) and timing and not saturates_cpu`.
    - With `-m "a or b"`, the expressions are `(a or b) and not timing` and `(a or b) and timing and not saturates_cpu`.
    - With `-m ' '`, the expressions are `( ) and not timing` and `( ) and timing and not saturates_cpu`.
    - With `-m saturates_cpu`, the expressions are `(saturates_cpu) and not timing` and `(saturates_cpu) and timing and not saturates_cpu`. The contract test shows that both select nothing.
    - With `-n 4`, the serial pass's `-n0` comes after the caller's `-n 4`, and the parallel pass keeps `-n 4`.
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
    - `tests/test_plain.py` holds an unmarked test, a `slow` test and a `b` test.
    - The project's `conftest.py` defines `pytest_collection_finish(session)`. When the environment names an output directory, each pytest process writes its `session.items` node IDs there, one per line, to its own `<pid>.ids` file, and the test reads their union. pytest calls that hook after `-m` deselection (`_pytest/main.py:816-823`), so the IDs are the selected tests in one format under any caller verbosity, `-vm slow`'s `-v` included.
    - The child environment drops `PYTEST_XDIST_WORKER`, `PYTEST_XDIST_WORKER_COUNT`, `PYTEST_XDIST_TESTRUNUID` and `PYTEST_ADDOPTS`, and sets `PYTEST_XDIST_AUTO_NUM_WORKERS=2` (row 56). So a child run without `-n0` starts two workers under the ini's `-n auto`.
    - Each pass's argv is the contract test's own options, then `tests`, then its `pytest_args` from `plan_passes(caller_args, auto_num_workers=None, scan_selection=functools.partial(scan_timing_marks, ["tests"], caller_args, repo_root=project))`. The contract test's options go first, so they never land after a caller `--`. A collect-only run's options are `--collect-only`. Every run sets the output-directory variable to a fresh temporary directory under the project.

    Its assertions:
    - For `[]`, `-m slow`, `-m "a or b"`, `-vm slow`, `-m timing` and `-m saturates_cpu`, a collect-only run of each pass exits 0 or 5. The two passes' node IDs are disjoint, and their union equals a literal expected set, which never holds the `saturates_cpu` test. Two sets need a note:
      - For `-vm slow`, the set is every other test, the widening row 9 records.
      - For `-m saturates_cpu`, both passes exit 5, the set is empty, and `merge_pass_exit_codes` of the two codes is 5. So even a caller `-m saturates_cpu` cannot reach the test in a split run (M12).
    - For the caller arguments `-- tests/test_plain.py`:
      - `plan_passes` plans one `UNSPLIT_PASS` whose `unsplit_reason` is the `--` reason constant and whose arguments equal the caller's. A collect-only run of that argv exits 0.
      - The control builds the argv a split would build under M3: the same caller arguments with the `added_options` of the `[]` case's parallel pass appended, `tests -- tests/test_plain.py -m 'not timing'`. Its collect-only run exits 4.
      - Together they pin the shape the collapse rests on (G4, row 71).
    - A real run of the serial pass exits 0 for `[]` and for `-n 2`, which shows its `-n0` starts no worker. A real run of the `[]` serial argv with its `-n0` token removed exits 1, which shows the worker assertion fails under workers.

    Its pytest startups were not recounted after the narrowing's removal, and the test was not re-timed. [unverified] Each case stays because it pins a different claim. Verification step 1 lists its duration.
- `claude/.claude/scripts/tests/test_select_tests.py`: **modify.**
  - Convert the tests row 21 lists. The shared edits:
    - Each patches `_mod.scan_timing_marks` with a recording stub of signature `(target_paths, caller_args, *, repo_root)`.
    - Each test that asserts a split clears `PYTEST_XDIST_AUTO_NUM_WORKERS` with `monkeypatch.delenv(..., raising=False)` and patches `_cpu_budget` to return 8 (row 21).
    - Each test that asserts a split switches to a list of calls and asserts that there are two.
    - Each call starts with the targets the test asserts today. The first call ends with `-m`, `not timing`, and the second with `-m`, `timing and not saturates_cpu`, `-n0`.

    What each test pins:
    - `test_git_diff_unavailable_falls_back_to_full_suite`: the full-suite split (row 7);
    - `test_domain_selected_paths_are_passed_through_to_run_pytest`: `-k foo` in both passes (row 8), and that the stub received `resolved_targets`, the passthrough list and `repo_root`;
    - `test_computed_env_reaches_run_pytest_unchanged`: both calls receive the sizing env;
    - `test_called_before_run_pytest`: the order `["record_selection", "run_pytest", "run_pytest"]`;
    - `test_argv_none_falls_back_to_sys_argv`: one call, with the stub returning no marked file;
    - `test_stderr_scope_matches_recorded_pytest_argv_across_containment_collisions`: each call's leading targets equal `expected_argv`, its `TICKET_REFERENCE_DISCIPLINE_TEST_PATH` exclusion holds for both calls, and the stderr scope line is built from `resolved_targets`.
  - Add `TestMainComposition` tests. Each clears `PYTEST_XDIST_AUTO_NUM_WORKERS` unless it sets it, patches `_cpu_budget` to return 8 unless it sets the budget itself, and matches a summary line's seconds with a regex:
    - A split whose fake returns `ExitCode.TESTS_FAILED`, then `ExitCode.INTERNAL_ERROR`: `main()` returns `TESTS_FAILED`, which pins the merge order. stderr holds both M5 headers, `select-tests: parallel pass: -m 'not timing'` and `select-tests: serial pass: -m 'timing and not saturates_cpu' -n0`, and the summary line names exit 1 and exit 3.
    - A parallel `NO_TESTS_COLLECTED`, then a serial `OK`: `main()` returns `OK`, and the summary line names 5, 0 and `exiting 0`.
    - Parametrized over `INTERNAL_ERROR`, `USAGE_ERROR` and `-signal.SIGKILL` from the parallel pass: one call, `main()` returns that code, and stderr holds the skip line.
    - A fake that raises `KeyboardInterrupt` on its first call: `main()` raises, the fake ran once, and no summary line prints.
    - Seven unsplit cases. Each makes one call, whose argv is the targets followed by the caller's arguments verbatim, prints its unsplit line, and prints no summary line. In the first six, the recording scan stub records no call:
      - `main(["-n", "0", "-k", "foo"])` and `main(["-n", "1", "-k", "foo"])`, each with marks;
      - `main(["-k", "foo"])` with `PYTEST_XDIST_AUTO_NUM_WORKERS` set to `0` and to `1`;
      - `main(["@args.txt"])`;
      - `main(["--", "some/path.py"])` with marks;
      - a stub returning no marked file.
    - A one-CPU budget, with `_cpu_budget` patched to return 1 and a load average of 0: `main([])` makes one call with the targets alone, records no scan call, and prints the environment reason's unsplit line, because the sizing writes 1 (M6).
    - Two wiring tests that leave the scan unpatched. Each sets `resolve_repo_root` to a `tmp_path` root, and `compute_changed_paths` to one path under `_mod.SCRIPTS_DIR`, which selects `_mod.SCRIPTS_TESTS_DIR`. With a marked `test_marked.py` and an unmarked `test_plain.py` there, `main([])` makes two calls, each the targets followed by its pass's options and nothing else. With `test_plain.py` alone, it makes one call and prints the no-marks line.
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
  - Load `select-tests.py` once at module level with `importlib.util.spec_from_file_location`, as `test_select_tests.py:30-32` does, to read `FULL_SUITE_TARGETS`. Import `scan_timing_marks`, `SERIAL_PASS_MARKER_EXPRESSION` and `TIMING_MARKER` from `_timing_split` by name, which `pyproject.toml:21`'s `pythonpath` allows, and `ExitCode` from `pytest`.
  - Three module constants:
    - `CPU_SATURATING_TEST_FILE` holds the literal repo-relative path `claude/.claude/scripts/tests/test_cursor_adapter_shim_hook_run.py`, with a one-line comment: a change to that file selects this guard through `select-tests.py`'s test-tree packaging row (row 53).
    - `CPU_SATURATING_TEST_NODE_ID` builds the test's exact node ID from it.
    - `COLLECTION_FAILURE_STDOUT_TAIL_LINES = 40`, with a one-line comment: a failed collect-only prints its error after the node-ID listing, so the stdout tail holds the error.
  - `_collected_node_ids(marker_expr, targets=FULL_SUITE_TARGETS, accepted_exit_codes=(ExitCode.OK,))` returns `(node_ids, exit_code)`. `targets` replaces the hard-coded `"claude/.claude/"`. The helper asserts that the exit code is in `accepted_exit_codes`, with a `collection failed (exit N)` message followed by pytest's stderr and the last `COLLECTION_FAILURE_STDOUT_TAIL_LINES` stdout lines.
  - The class has no fixture and no record type (row 83). The existing partition test becomes `test_the_timing_partition_sums_to_the_unfiltered_total_and_the_scan_matches_the_timing_files`. It runs the three whole-suite collections, each under the helper's exit-0 default, and scans the real tree. Its three assertions follow, in this order, per M9:
    - the partition, with its existing message;
    - the scan parity, whose failure message names each file. It says the scan decides from file text whether a selection holds `timing` tests, so the mark must sit in the file pytest collects the test from;
    - the root coverage, whose failure message names each root with no collected ID.
  - `test_the_serial_pass_expression_deselects_the_cpu_saturating_test` runs one collection over `[CPU_SATURATING_TEST_FILE]` with `f"{TIMING_MARKER} and not ({SERIAL_PASS_MARKER_EXPRESSION})"` and `accepted_exit_codes=(ExitCode.OK, ExitCode.NO_TESTS_COLLECTED)`. It passes when the collection exits 0 with IDs exactly `[CPU_SATURATING_TEST_NODE_ID]`.
    - Exit 5 or a different ID list fails with one message, which gives the exit code and the selected IDs: the test lost its `saturates_cpu` mark, no longer carries `timing` beside it, or was renamed, and a rename updates `CPU_SATURATING_TEST_NODE_ID` in the same change. Exit 5 takes this message, not the helper's, because a lost mark selects nothing (row 11).
    - Any other exit fails inside the helper with its collection-failure message.
  - The class docstring gains two sentences. The same collections pin that `select-tests.py`'s scan marks the files pytest collects `timing` tests from. A separate collection of the CPU-saturating test's file pins that the serial pass's expression deselects that test.
- `pyproject.toml`: **modify.** Add one `markers` entry after `timing`'s at `:34`: `"saturates_cpu: starts one busy process per CPU core, and is always applied together with timing. select-tests.py's serial pass deselects it, and CI's serial step runs it."`
- `claude/.claude/scripts/tests/test_cursor_adapter_shim_hook_run.py`: **modify.** Add `@pytest.mark.saturates_cpu` beside the `timing` mark at `:170`. The xdist skip at `:174-176` stays, because `pytest claude/.claude/` with the ini's `-n auto` still runs the test in a worker.
- `README.md`: **modify.**
  - At `:566`, replace "`select-tests.py` forwards it through to pytest." with a sentence saying that in a `select-tests.py` split run only the parallel pass honors `-n <N>`, pointing to the split-run list below.
  - After `:578`, add the lead sentence "`select-tests.py` splits a run into two pytest passes, as CI does:" and a list, one fact per item:
    - It runs a parallel pass for everything not marked `timing`, then a serial `-n0` pass for the `timing` tests.
    - The serial pass leaves out tests marked `saturates_cpu`, each of which starts one busy process per CPU core, and CI's serial step runs them:
      - A split run never runs them, so `-m saturates_cpu` selects nothing in a split run.
      - To run them locally, pass `-n 0 -m saturates_cpu`, which runs one unsplit pass, or run `scripts/venv-run.sh pytest <file> -m timing -n0`.
      - `-n 1` also runs one unsplit pass, but the one such test in the suite skips itself inside an xdist worker, so `-n 1 -m saturates_cpu` runs nothing, and `-n 0` is the way to run it.
    - The serial pass collects the whole selection and filters it with `-m`. Whether a selection holds `timing` tests is read from file text, so the mark must sit in the file pytest collects the test from, and `test_pytest_collection_config.py` fails CI otherwise.
    - In a split run, modes that list the collected tests, such as `--collect-only`/`--co` and `--fixtures-per-test`, print each pass's share, and the two shares together omit `saturates_cpu` tests. `--setup-plan` prints no setup-plan lines from the parallel pass, because xdist discards its workers' output. Modes that collect nothing, such as `--version`, `--help` and `--markers`, print the same output once per pass. Adding `-n 0` gives one complete listing.
    - It skips the serial pass when the parallel pass exits 3 or 4 or is killed by a signal.
    - It runs one unsplit pass instead, as before, when:
      - your `-n` is 1 or less, since one worker has no sibling workers for the serial pass to protect;
      - `PYTEST_XDIST_AUTO_NUM_WORKERS` is 1 or less, and your `-n`, if any, is `auto` or `logical`. When the variable is unset and the 1-minute load average is readable, `select-tests.py` sizes it from the CPU count and load, so a one-CPU machine runs one pass too (M6 names the unreadable case);
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
- `CHANGELOG.md`: **modify.** Add a bullet at the top of `## [Unreleased]`'s `### Changed` (`:7-9`). It says `select-tests.py` now runs `timing`-marked tests in a second, serial pytest pass that collects the selection and filters it with `-m`, as CI's split does, whenever the selection contains them. Two sub-bullets:
  - The caller `-m` and `-n` behavior; the four unsplit cases, a worker count of 1 or less, an `@file` argument, a bare `--`, and a selection with no `mark.timing`, with why one worker gets no split; the skip after exit 3, exit 4 or a signal; and the `saturates_cpu` test that only CI's serial step runs, citing README.md's Tests section. The worker-count case covers two of `_timing_split.py`'s five reason strings, the caller's `-n` and `PYTEST_XDIST_AUTO_NUM_WORKERS`.
  - **Migration:** a split run prints two pytest summaries and a closing stderr line, each pass writes report files once, and the interpreter must be able to import pytest.

**Reuse:**
- `build_pytest_argv` and `run_pytest` stay as each pass's argv builder and runner.
- `pytest.ExitCode` provides the exit-code names.
- `TestTimingMarkerCoverageParity._collected_node_ids` provides the guard's collection, and `scan_timing_marks` its rule.
- `ci_test_slice_job` (`helpers.py:2713`) and `_steps_running` (`test_select_tests.py:2690`) provide the CI parity data.
- The existing `pytest_subprocess_env` result serves every pass and supplies M6's worker count.

Projected diff: 1,501 lines for the whole branch against `origin/main`, measured on the working tree (row 78): 260 in `_timing_split.py`, 646 in `test_timing_split.py`, 73 in `select-tests.py`, 405 in `test_select_tests.py`, 85 in `test_pytest_collection_config.py`, 27 in README.md, 3 in CHANGELOG.md, and 1 each in `pyproject.toml` and `test_cursor_adapter_shim_hook_run.py`.

## Verification

Run every command from the worktree root. Each step names the question it answers and the result that changes the plan.

**Load (row 27).** Hold each full-suite run while the machine is overloaded, and bound the workers of every other test run. The diff edits `select-tests.py` and `pyproject.toml`, both `GLOBAL_TRIGGER_PATHS` members (`select-tests.py:558-562`), so every `select-tests.py` run selects the full suite. The flow has run it once so far, before the drop (row 77). Row 77 also records two comparison runs at the same load, one at the merge base and one on the branch. The rest of the flow runs the full suite locally once, in step 4's `/ready-for-review` (row 84), and step 4's failure procedure can add comparison runs if that run fails. `/ready-for-review` runs CLAUDE.md's Commands (`ready-for-review/SKILL.md:64`) and caches only its own passing run (`:61`).

The rules:
- Before each `/ready-for-review`, read the 1-minute load average and the logical core count with `scripts/venv-run.sh python3 -c "import os; print(os.getloadavg()[0], os.cpu_count())"`. When the load exceeds the core count, hold the run and tell the engineer both numbers. The sizing line prints the same `os.getloadavg()` figure (`select-tests.py:1394`, `:1418-1423`), but only once the run has started.
- Before step 1, take the same reading, and record it beside step 1's durations. Step 1's own session starts no workers, and the contract test's child runs start at most two each (Critical files), so the reading does not hold it.
- When the load stays above the core count, the engineer decides between three courses, and the session runs nothing at that load until they do:
  - a bounded wait, of a length they state;
  - an explicit run at the stated load, with step 4's failure procedure for any failure;
  - deferring to CI, which runs the whole suite on every PR (row 34). Deferral covers test results only. CI runs its two `pytest` steps directly (`tests.yml:222`, `:227`) and never runs `select-tests.py`, so step 4's split headers, summary line and the serial session's missing worker banner cannot be read off CI. The PR body then states that the split was not run end to end on the final tree. Row 77's run, the only end-to-end run so far, was on the tree before the narrowing's drop.
- After a `/code-review` fix, rerun only the test files that cover the fix, with `scripts/venv-run.sh pytest <files> -n0 -m 'not saturates_cpu'`, and leave the next full-suite run to `/ready-for-review`. The `-n0` overrides the ini's `-n auto`, which xdist sizes from the CPU count rather than the load (G2, G3). The `-m` keeps the CPU-saturating test out of a run with no workers (row 51).
- Each further `/ready-for-review` round after a tree change adds one full-suite run.
- `/code-review` runs no tests.
- Each `code-writer` dispatch runs no `select-tests.py` command, and it bounds its own test runs (Critical files).
- Step 2 runs nothing.

**Approvals.** The session runs each command below, and the engineer approves it at the permission prompt, or runs it in a terminal and hands back the output. The project allowlist (`.claude/settings.json:10-12`) covers the bare `select-tests.py` command that `/ready-for-review` runs, and no command below. The session reports a denial and does not retry it.
- the load reading before step 1 and before each `/ready-for-review`;
- step 1's targeted run;
- step 4's comparison runs or failure reruns, and its merge-base check, if any;
- step 3's `ruff` command, which `:10`'s bare `ruff check claude/.claude/` does not match;
- a `/code-review` fix's test-file rerun;
- step 4's `gh` lookups.

1. **Do the change's own tests pass, and what do the guard and the contract test cost?** Step 1 runs on the final tree, the commit that holds the code-writer's last change, with no other uncommitted change (row 84). Row 77's run, on the committed tree with the narrowing, cannot stand in for it. The drop changes the serial pass's argv, and row 77's passing evidence does not carry over to the tests the removal rewrote.

   Run `scripts/venv-run.sh pytest claude/.claude/tests/test_pytest_collection_config.py::TestTimingMarkerCoverageParity claude/.claude/scripts/tests/test_timing_split.py claude/.claude/scripts/tests/test_select_tests.py -n0 -m 'not saturates_cpu' --durations=15`. It runs the guard, the contract test, the table tests and the `main()` tests in one session with no workers of its own, with the same `-n0` and `-m` as a fix rerun (Load). Only the contract test's child runs can start workers, at most two each, because its child environment sets `PYTEST_XDIST_AUTO_NUM_WORKERS=2`.

   Confirm that it exits 0 and that the guard's tests pass within their 120-second per-collection timeouts (row 54). A failure here is in a test this diff adds or changes, so fix it and rerun step 1.

   Record these in the PR body, each informational:
   - the commit step 1 used, and the load reading taken before it;
   - the guard's and the contract test's durations from the `--durations=15` list, beside their 120-second per-run timeouts. A test missing from the list took less than its last entry, and the PR body records that bound instead.
2. **The dropped `--ignore` narrowing.** Not run again (rows 74 and 76). The PR body says the narrowing was built, measured and dropped, and gives row 76's figures as the session's unsaved record, since an earlier commit on the branch still carries the narrowing.
3. `scripts/venv-run.sh ruff check claude/.claude/ claude-skills/ plugins/ evals/`. The diff changes no shell file, so the shellcheck command does not apply.
4. **Does the split run end to end on the full suite?** Run `/code-review`, then `/ready-for-review` before handoff. `/ready-for-review` runs `select-tests.py` inline, which selects the full suite for this diff and exercises the split itself (row 84). Read four confirmations off that run, or off the run that wrote its verification cache on a cache hit, and fix any that fails before shipping:
   - stderr shows `running the full suite (global-trigger: ...)`, `select-tests: parallel pass: -m 'not timing'`, `select-tests: serial pass: -m 'timing and not saturates_cpu' -n0`, and the summary line;
   - the serial session prints no xdist worker banner;
   - `TestTimingMarkerCoverageParity`'s tests pass within their 120-second per-collection timeouts (row 54);
   - the run exits 0, or the failure procedure below leaves no node ID that fails on the branch and not at the merge base.

   The stderr lines and the missing worker banner do not depend on the load. The guard's tests depend on it only through their timeouts. The exit code does depend on it: row 77's run, at a load of about 54 on 16 cores, failed hundreds of tests in files this diff does not touch. The failure procedure's comparison makes the last confirmation reachable on such a machine.

   The PR body records, as informational, the run's sizing-line load average and worker count, beside both passes' wall seconds from its summary line. A run at a load several times the core count gets 2 workers (`compute_worker_count`, `select-tests.py:1280-1284`), so its times do not compare with a lightly loaded run's. When `PYTEST_XDIST_AUTO_NUM_WORKERS` is pinned, the sizing line prints the count without a load, and the load comes from the reading taken before the run.

   If the run fails, do not rerun it whole. Take the failing node IDs through one of these, in this order of preference:
   - Comparison: create a merge-base worktree, as the global CLAUDE.md's "Prove your change caused a failing check" rule says. Back to back, run the failing node IDs there and on the branch, each with `PYTEST_XDIST_AUTO_NUM_WORKERS` pinned to the worker count the run's sizing line printed, and with `-n0` instead for IDs from the serial pass. Compare the two failing sets. At the merge base, run only the IDs that exist there, and count each other ID as failing only on the branch.
   - Rerun: run the failing node IDs with `scripts/venv-run.sh pytest <node ids> -n0`, only once a fresh load reading is at or below the core count. Check each ID that fails again at the merge base, per the same rule.

   Only an ID that fails on the branch and not at the merge base goes to the engineer, with both results. Such an ID is in scope: fix it, rerun its node IDs, and leave the next full-suite run to the next `/ready-for-review` round. A test that passes alone goes to the engineer only when it is one of those, since it may fail CI's parallel leg too. An ID that fails at the merge base too marks pre-existing drift, outside this plan.

   The PR body also records CI's cost:
   - Once the PR's CI run finishes, the PR body records its parallel leg's wall time from `gh run view <run id> --json jobs`. Beside it go the last `main` run's, found with `gh run list --workflow tests.yml --branch main --limit 1`, and the job's `timeout-minutes: 30` (`tests.yml:43`).
   - The guard's widening (row 54) and the contract test both grow that leg, and the cap comment at `tests.yml:41-42` says "Re-derive this cap whenever the parallel pass grows". `tests.yml` stays unchanged (Out of scope), so the engineer decides whether the margin calls for re-deriving it.

## Out of scope

- `tests.yml` stays unchanged, since CI already splits (brief).
- The cold-stub prewarm guard in `evals/conftest.py`, the pid-path quoting in `evals/test_replay_bench_launch.py`, and refactors of the domain-mapping table or the worker heuristics (brief). The one rule-table row this plan adds declares the guard's new import (row 53).
- Recognizing the caller `-m` forms in row 9. Each already widens the run rather than breaking the split, and each would need its own machinery:
  - a cluster, pytest's whole short-option table;
  - a `-m` in `PYTEST_ADDOPTS`, shell-word parsing of the environment;
  - a negative-number value, argparse's negative-number rule in the shared scan, which only `-m -1` and `-n -1` would use.
- Reading `PYTEST_ADDOPTS`, `--pdb`, a separated negative `-n` value, a `--maxprocesses` of 1 or less, or xdist's own CPU count for M6's worker count. `PYTEST_ADDOPTS` would need the same shell-word parsing. A run with any of these forms splits with one worker or none, and a `-n` of 2 or more in `PYTEST_ADDOPTS` beside a `PYTEST_XDIST_AUTO_NUM_WORKERS` of 1 or less collapses to today's single pass (M6). The results stay correct either way.
- Reading a bare `--` in `PYTEST_ADDOPTS` for M6's `--` collapse. It is the one unread form that fails loudly instead of widening: each pass's appended options land after that `--`, and the run exits non-zero where today's passes (row 73). Reading it would need the same shell-word parsing.
- The serial pass is not narrowed, and these two variants stay unbuilt (M8 and rows 74 and 76 hold the history):
  - one `--ignore` per walked directory that holds no marked file, which cuts `--ignore`'s per-entry cost (row 55) but keeps its matching;
  - the marked files as explicit targets, which avoids that cost but needs the caller-path, `python_files` and `norecursedirs` rules row 40 names;
  - the reason for both: either variant would need its own measurement, as the dropped `--ignore` narrowing did.
- Merging per-session state across the two passes: report files (`--junitxml`), the `--lf` and `--sw` cache, and the `tmp_path` directories a run where both passes fail can lose (row 26). No in-repo caller passes such flags (row 19), and the engineer chose to document the loss (row 48).
- Recording the pass plan or the pass times in the selection log. The log records the selection decision, which the split does not change (row 16), and M5's summary line shows the times on every run.
- Running the guard locally for a change under `evals` or `claude-skills`. CI runs it on every PR (row 53).
- Splitting `select-tests.py` or `test_select_tests.py` under the 1,000-line limit (row 22). This plan grows them only by the wiring and test updates the split needs.
