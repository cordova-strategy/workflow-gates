# Benchmark the cost of sourcing `_lib.sh`

## Context

Add a checked-in benchmark script that measures what sourcing `claude/.claude/hooks/_lib.sh` costs a hook today, what each candidate cluster of it contributes, and what a tail cut would save.

Ask: issue #1433 ("Benchmark the parse cost of sourcing _lib.sh, per cluster and for a tail cut"), invoked as "/plan-it 1433". Cluster set: "measure every row except command parsing/redaction" — accepted via label "All non-core rows (Recommended)". Recording results: "post the #1117 comment only once you say yes" — accepted via label "Post after you approve (Recommended)". Cluster data file: "Accept the PSV file (Recommended)". Test depth: "I'm inclined to do deterministic tests and a sourceable lib." Span lookup: "bash's own `declare -F` (with `extdebug`) supplies each start line; the closer rule stays for end lines" — accepted via label "Text rule plus declare -F (Recommended)".

Why now: #1117 reopens the decomposition of `_lib.sh`, which has grown to 6,233 lines (`wc -l` at `dd60e672`) and sources the 1,337-line `_config.sh`. The two prior cost records were taken on a much smaller file and are not comparable with each other: `.claude/plans/hook-bootstrap-cost.md:11-22` gives a marginal cost from an interleaved ABAB harness, and `docs/config-file.md` gives whole-process timing. The harness behind the first record was never checked in (`git grep -n EPOCHREALTIME` finds it only in `.claude/plans/`). #1117's gate for moving any cluster needs a measured saving per cluster against a noise floor, and #1435 and #1436 take their before and after numbers from this script.

Intended outcome: one script under repo-root `scripts/` that reruns on any checkout, a test for it, and a results comment on #1117 giving each cluster's saving, the total, the tail-cut saving, the `dirname` comparison, and the noise floor. A saving below the noise floor is no performance case.

## Approach

Add `scripts/dev/lib-source-cost.sh`, a bash benchmark, and `scripts/dev/_lib-source-cost-lib.sh`, a sourceable lib holding the benchmark's testable logic. The script copies `_lib.sh`, `_config.sh` and `config-keys.psv` into one scratch directory per arm, edits each copy for its arm, and times a fresh `bash -c '. <file>'` for every arm in one rotated round-robin `EPOCHREALTIME` loop. It reads the clusters from `scripts/dev/lib-source-cost-clusters.psv` as function-name spans resolved at run time, so it reruns unchanged as line numbers drift and fails closed when an anchor disappears.

**Where inputs come from.** The script measures the checkout it runs in:

- It finds the checkout root with `git rev-parse --show-toplevel`, run in the working directory (row 16).
- It reads all four data files under that root: `claude/.claude/hooks/_lib.sh`, `claude/.claude/hooks/_config.sh`, `claude/.claude/hooks/config-keys.psv` and `scripts/dev/lib-source-cost-clusters.psv`.
- It finds only its lib beside itself, because the lib is part of the tool, not of the measured tree.

So a PR that moves a cluster measures its own PSV rows against its own `_lib.sh`, and a test aims the real script at a fixture checkout through the working directory alone.

**Arms**, in the order the loop lists them. Every arm is a fresh child `"$BASH" -c '. "$1"' <label> <arm-dir>/<entry>`, so the arms differ only in what the child sources:

1. `full` sources an unedited copy of `_lib.sh`, which sources the copied `_config.sh` beside it (row 6). It reports its cost over `baseline`.
2. `minus-<cluster>`, one per cluster in the order of its first PSV row, sources copies with that cluster's spans deleted from each file they lie in. For `config-writer` only `_config.sh` changes. Each reports its saving against `full`.
3. `total-deletion` deletes every span from both files and reports its saving against `full`. It is measured rather than summed, so any interaction between clusters shows.
4. `tail-cut` moves each file's spans, in file order, to that file's end behind a bare top-level `return 0`, as #1433 Scope item 4 words it. It moves the same set `total-deletion` deletes, so the gap between those two rows prices reading bytes bash no longer parses (row 21). It reports its saving against `full`.
5. `control` sources a second byte-identical copy of `full`'s three files and reports its saving against `full`. Its row is the realized error of a comparison between two heavy arms.
6. `baseline` sources an empty file. Its spread is the noise floor (row 1).
7. `dirname-fork` sources a one-line file that assigns `"$(dirname "${BASH_SOURCE[0]}")"` to a variable. It reports its cost over `baseline`.
8. `param-expansion` sources a one-line file that assigns `"${BASH_SOURCE[0]%/*}"` instead. It reports its saving against `dirname-fork`, the per-site figure #1435 needs.

The lib writes both one-line files from quoted heredocs, so the literal `$(...)` needs no SC2016 suppression. At `dd60e672` the list holds 14 arms.

**Predecessors.** The Harness's rotation runs each arm right after its list predecessor, wrapping from the last arm to the first. The exception is the one round in A where the arm runs first, when it follows the arm two places before it (row 43). So the list order fixes each comparison's predecessor class: heavy for an arm that sources `_lib.sh`, light otherwise.

- `full` follows `param-expansion`, a light arm.
- Every `minus-*`, `total-deletion`, `tail-cut` and `control` arm follows a heavy arm. So `control`'s saving measures, beside noise, the predecessor offset that every saving against `full` carries.
- `baseline` follows `control`, a heavy arm.
- `dirname-fork` and `param-expansion` follow light arms, so `param-expansion`'s saving compares like with like.
- `full`'s and `dirname-fork`'s costs over `baseline` carry a light-arm predecessor offset that no arm measures. Placing `baseline` after `control` puts that offset on `full`'s cost of tens of milliseconds rather than on the `dirname` saving near 1 ms (row 44).

**Cluster spans.** The PSV's grammar:

- Each row is `cluster|file|first_function|last_function`.
- `file` is `_lib.sh` or `_config.sh`.
- No whitespace surrounds a `|`.
- `#` lines and blank lines are skipped, following `config-keys.psv:7-11`.

A cluster with several rows is non-contiguous. The rows at `dd60e672` (rows 11, 33):

| cluster | file | first function | last function | resolved lines |
|---|---|---|---|---|
| resume-context | `_lib.sh` | `_lib_resume_context_tmpdir_root` | `_lib_sanitize_for_terminal` | 5848-6233 |
| plugin-reconcile | `_lib.sh` | `_lib_validate_plugin_id` | `_lib_missing_plugin_ids_for_content` | 4338-4525 |
| worktree-lock | `_lib.sh` | `_lib_worktree_lock_pid` | `_lib_worktree_collision_guard` | 3904-4316 |
| review-pr | `_lib.sh` | `_lib_review_pr_marker_repo_hash` | `_lib_review_pr_marker_repo_hash` | 669-673 |
| review-pr | `_lib.sh` | `_lib_review_pr_completion_marker_fields` | `_lib_review_pr_completion_marker_fields` | 769-783 |
| review-pr | `_lib.sh` | `_lib_review_pr_artifact_path` | `_lib_review_pr_provenance_field` | 860-903 |
| review-pr | `_lib.sh` | `_lib_review_pr_worktree_name_prefix` | `_lib_review_pr_reviewer_findings_dir` | 939-1004 |
| reviewer-round | `_lib.sh` | `_lib_reviewer_round_state_cap` | `_lib_round_consult_gate_disabled` | 5213-5502 |
| push-parser | `_lib.sh` | `_lib_git_push_word_is_computed` | `_lib_push_protected_branches` | 2113-2451 |
| config-writer | `_config.sh` | `_config_quote_value_for_write` | `_config_scaffold` | 1078-1337 |

Span resolution rules:

- A definition line reads exactly `<name>() {` or `<name>() (`.
- A span starts at its first function's definition line, as bash reports it (rows 29-31).
- A span ends at its last function's closer, the first later line reading exactly `}` for a brace body or `)` for a subshell body (row 10).
- The comment block above each span's first function stays, so each saving slightly understates a real move.

How the lookup child runs:

- It sets `shopt -s extdebug`, sources its copy, and runs `declare -F` on every anchor, which prints each one's start line and source file.
- It is `"$BASH"`, the interpreter that already passed the floor gate, so the copied `_config.sh` clears its own floor check.
- It sources only the copy of `_lib.sh`, which sources the copy of `_config.sh` beside it, so one child reports both files' anchors (row 6).
- It sources a dedicated `lookup` copy that no arm times, so a stray file the source writes cannot reach an arm's directory.
- Its `$0` is `lookup`.
- It ignores the source's exit status and output. The pre-flight judges source health once per arm, naming the arm.
- It runs only after `bash -n` passes on both copies, because a source with a syntax error defines only the functions above the error and shows no cause (row 42).

Bash keeps only the last definition of a name, so `declare -F` cannot see a duplicate (row 32). The text rule therefore stays as a cross-check on every start line.

The script validates every row and resolves every span before it builds any arm. It stops on any of these, naming the PSV line and any function involved:

- Row parse, stage `cluster-file`:
  - a field count other than four, or an empty field;
  - a `file` value other than the two names;
  - a cluster label outside `[a-z0-9-]+`.
- Syntax, stage `syntax`, before the lookup: `bash -n` fails on the `lookup` copy of `_lib.sh` or `_config.sh`. The stop names the file rather than a PSV line and prints bash's message, which carries the line number.
- Lookup, stage `lookup`:
  - an anchor bash does not define after the source;
  - an anchor bash reports from the other file.
- Span, stage `span`:
  - zero or several definition lines for an anchor;
  - a definition line other than the one bash reported;
  - a last function defined before its first;
  - no closer after the last function's definition;
  - a definition line strictly between the last function's definition and its closer, which means the closer rule overran;
  - two spans in one file sharing a line, which covers overlap, nesting and a repeated row, naming both PSV lines.

Arm directories are named by 0-based index in the arm list and the lookup copy `lookup`, so no PSV value reaches a path. A renamed or deleted anchor function fails the script and its smoke test, and the fix is that PSV row. #1436, which moves resume-context out of `_lib.sh`, deletes that row in its own PR.

**Arm edits** use bash line arrays in the lib: `mapfile` the copied file, then write the kept lines to a new file with `printf '%s\n'`. They use no `sed -i`, `head` or `tail` form. CI tests only Linux (row 34), so a GNU-only form would pass CI and fail on the macOS run that produces #1117's figures.

An arm edits only a file that holds its spans and copies its other files unchanged. `printf '%s\n'` adds a newline to a last line that lacks one and writes one byte for an empty file (row 41), so every fixture file ends in a newline. The `baseline` arm's empty file is written, not edited.

**Harness.**

- Defaults are 200 iterations and 3 repetitions (row 1), overridable with `--iterations N` and `--repetitions N`.
- Each value must be a positive decimal integer with no leading zero, and repetitions must be at least 2 so the noise floor has a spread. Anything else, including an unknown flag or a flag with no value, exits 2 with the usage line on stderr.
- A run has iterations × repetitions rounds. Rounds count from 0 across the whole run and repetitions from 1, so round k belongs to repetition `k div iterations + 1`.
- Round k times every arm once, starting at index `k mod A` of the A-arm list and wrapping. Every arm therefore takes every position, and drift slower than one round reaches every arm alike.
- Timestamps are `${EPOCHREALTIME//[!0-9]/}`, integer microseconds whatever the locale's decimal separator.
- The script unsets `BASH_ENV` before its first child, so a contributor's value is not sourced into every child (row 23).
- The lib folds each timed sample into its arm's minimum for that round's repetition. An arm's figure is the smallest of those minimums, and its spread is the largest minus the smallest.
- The noise floor is `baseline`'s spread, as #1433 defines it (row 1).
- Each compared row's applied floor is the largest of the noise floor, the arm's spread and its reference arm's spread. A delta whose absolute value is under the applied floor is below the floor.
- One progress line goes to stderr at the start of each repetition.
- Run time is about arms × iterations × repetitions × the cost of one child, plus one untimed pass. At defaults that is 14 × 200 × 3 = 8,400 timed children. The platform review measured per-source minima of about 25 ms for `baseline` and 60-70 ms per heavy arm on a heavily loaded machine. At those minima a default run takes about 8 minutes, a lower bound for that load. The usage line carries the formula.

**Correctness checks**, in run order. Past the gate, every stop prints a line to stderr starting `lib-source-cost: <stage>:` and exits 1. Stdout stays empty on a stop, because the report prints only after the last round.

1. Source the checkout's `_config.sh` as the floor gate (rows 15, 24):
   - Only `set -euo pipefail` and `checkout_root=$(git rev-parse --show-toplevel) || exit 1` precede it.
   - All three lines parse on bash 3.2 (row 35).
   - The source line carries a `# shellcheck source=` directive and `|| exit 1` (row 36).
   - A below-floor bash therefore stops with `_config.sh`'s fix text before anything is timed.
   - The children run `"$BASH"`, the same interpreter, so they clear the floor too.
   - The script calls no function `_config.sh` defines.
2. Source the lib from the script's own directory, then `cd` to the root, then validate the flags. Everything bash-4+ runs from here on.
3. Validate the cluster file, check both files' syntax, run the lookup and resolve the spans, with the stops listed under Cluster spans.
4. Run a pre-flight (stage `pre-flight`) that sources every arm once, untimed and in list order. It requires exit 0 with empty stdout and stderr.
   - The empty-output rule catches a top-level call into a deleted function (row 9), which bash reports on stderr while the source still exits 0.
   - A closer found too early leaves the rest of its function in the kept text of its `minus-<cluster>` arm and of `total-deletion`. A parse error there makes that source exit non-zero with bash's message (row 42), so the pre-flight catches whatever `bash -n` on those files would.
   - A failure names the arm and prints the child's stderr.
5. Check every timed child's exit status (stage `timed`). A non-zero status stops the run naming the arm, repetition and round, so a failure that appears only on a later source is never timed (row 1, #1433 Scope item 5).

The scratch root is one `mktemp -d "${TMPDIR:-/tmp}/lib-source-cost.XXXXXX"`, removed by the script's single `EXIT` trap. It is the only path the script deletes, and it never comes from input.

**Report**, plain text on stdout, printed after the last round:

- Each line is a kind word followed by space-separated `key=value` fields, and no value holds a space.
- Every time is in milliseconds with exactly three decimals.
- A cost or saving always carries a sign, `+0.000` for zero. Every other time is unsigned.

The four kinds of line:

- `header`, with these keys in order:
  - `bash=` is `$BASH_VERSION`.
  - `system=` and `machine=` are `uname -s` and `uname -m`.
  - `dirname=` is the `dirname` the PATH resolves, the one the `dirname-fork` arm priced.
  - `commit=` is `git describe --always --dirty`, or `none` when that fails.
  - `lib_blob=` and `config_blob=`, then `iterations=` and `repetitions=`.
  - The line carries no hostname or load average. The `dirname=` path is its one machine-specific value.
- `span`, one per PSV row in PSV order: `cluster=`, `file=`, `lines=<start>-<end>`, `line_count=`, and `functions=`, the number of definition lines inside the span. A function added inside a span shows as a changed count in a rerun.
- `arm`, one per arm in list order: `label=`, `mins_ms=` (the per-repetition minimums, comma-separated), `figure_ms=` and `spread_ms=`. Every arm but `baseline` then adds:
  - `ref=`;
  - `cost_ms=` for `full` and `dirname-fork`, or `saving_ms=` for every other arm;
  - `floor_ms=`, the applied floor;
  - `floor_from=`, naming whichever of `baseline`, the arm and its reference has the spread equal to the applied floor, taking the first in that order on a tie;
  - `verdict=above` or `verdict=below`.
- `noise-floor`: `ms=`, `baseline`'s spread.

A cost is the arm's figure minus its reference's. A saving is the reference's figure minus the arm's. The blob ids are `git hash-object` of the two files measured. They survive a squash merge, which the branch commit does not. They need no commit, so they work in a fixture checkout (row 38). The script exits 0 after the report and never judges a saving itself.

**Reading a before/after pair.** #1435 and #1436 take their before and after from two runs that no loop interleaves, so a machine-state shift between the runs would read as a saving. The script header states this reading rule:

- Compare `full`'s `cost_ms` across the two runs, never its `figure_ms`.
- Count the change as a saving only when it exceeds the larger of the two `full` rows' `floor_ms`.
- The before run's row for the same change, `minus-<cluster>` or `param-expansion`, is the interleaved estimate of it. When the cross-run change misses that estimate by more than the same floor, machine state moved between the runs, so cite the interleaved row.

**Function names stay out of code.** Neither the script, the lib nor either test file names a `_lib.sh` or `_config.sh` function on a non-comment line, docstrings included. No identifier in them contains `_lib_` or `_config_`, so none can match a function name at its right edge. The tests take anchors and labels from the PSV or use synthetic names.

**Why a PSV file rather than an array in the script.** `test_shell_lib_function_liveness.py` counts any mention of a `_lib.sh` or `_config.sh` function on a non-comment line of a tracked shell or `.py` file as a reference (row 13). The 18 anchor names written into the script would keep those functions alive in that tripwire after their last real caller went.

**The lib**, `scripts/dev/_lib-source-cost-lib.sh`, holds every part of the benchmark a fixed input can test (rows 27, 28, 39). Its functions share the prefix `lsc_`:

- the flag-value check;
- cluster-file parsing and row validation;
- the start-line lookup and span resolution, with every stop above;
- the arm edits and the two one-line `dirname` files, each written for its label;
- the arm list, its rotation for round k, and each arm's reference and cost-or-saving kind;
- the round-to-repetition mapping, and the fold of each timed sample into its arm's per-repetition minimum;
- the figure, spread, delta, applied floor and verdict arithmetic, and millisecond formatting;
- `span` and `arm` line formatting.

The script keeps flag parsing, the gate, the scratch root, copying, the pre-flight, the timing loop, progress lines and the `header` and `noise-floor` lines.

**Lib tests**, `claude/.claude/scripts/tests/test_lib_source_cost_lib.py`. Each case sources the lib under `set -euo pipefail` in `bash -c`, as `test_worktree_lib.py:42-62` does, and feeds it fixed input. None times anything. The lib's path is built from `helpers`' `REPO_ROOT` (row 14). The tests' shared `bash -c` helper also drops `BASH_ENV` and `ENV` through `_clean_env`, so an inherited startup file that prints cannot reach an exact-output assertion.

- Flag values: `0`, `01`, `x` and an empty value fail, and `1` fails only as a repetition count.
- Cluster-file parsing: a valid file with a comment, a blank line and a non-contiguous cluster yields its rows in order. One invalid row per parse stop (three fields, five fields, an empty field, an unknown `file`, a bad label) returns 1 with `cluster-file` and the line number on stderr.
- Lookup, on a synthetic `_lib.sh` that sources a synthetic `_config.sh`:
  - each anchor's start line and file;
  - a name defined twice reports its later line (row 32);
  - a source that returns 1 after defining every anchor still resolves;
  - an undefined anchor, and an anchor in the other file, each stop with `lookup`;
  - a syntax error after the first anchor, in either file, stops with `syntax` naming that file, and no `lookup` line follows.
- Span resolution, on a synthetic file of a few dozen lines holding a two-span cluster and a `(` body: exact ranges, line counts and definition counts, plus one case per `span` stop.
- Arm edits: the exact output of deleting a non-contiguous cluster, and of the tail cut, whose `return 0` precedes the moved spans in file order. The exact text of both one-line `dirname` files, and the empty bytes of `baseline`'s file, each written by the lib's light-arm writer.
- Light arms, executed. The test has the lib's writer produce each of the three light-arm files, `baseline`'s included, then sources each one in a child bash.
  - The child's PATH leads with a `dirname` stub that logs each call and then runs the real `dirname`.
  - The log records one call for `dirname-fork` and none for `param-expansion` or `baseline`.
  - `dirname-fork` and `param-expansion` leave the same value in the variable they assign, the arm file's directory, and `baseline` leaves it unset.
- Arithmetic:
  - millisecond formatting of -848, -1000, 0, 1 and 123456 microseconds, signed and unsigned;
  - the sign of a cost and of a saving;
  - an applied floor set once by each of its three sources, and a tie;
  - the verdict for a delta below, equal to and above the floor, negative deltas included.
- The arm list for a two-cluster file, its rotation at rounds 0, 1 and A, and the reference of every fixed arm.
- The fold, at 2 iterations and 2 repetitions. One arm's samples of 900 and 700 microseconds in rounds 0 and 1 and 800 and 850 in rounds 2 and 3 give minimums 700 and 800 and a spread of 100. A fold that never resets would read 700 and 700, and one keyed by `k mod repetitions` would read 800 and 700.
- The exact `span` and `arm` lines for fixed inputs.

**Script tests**, `claude/.claude/scripts/tests/test_lib_source_cost.py`, one case per script branch:

- Each run invokes the real script by a path built from `helpers`' `REPO_ROOT`, so `TestCrossDomainReadCompleteness` sees it (row 14).
- Each run passes an environment built by `_clean_env`:
  - It drops an inherited `GIT_DIR`, so the script cannot be aimed at another checkout (row 18).
  - It also drops `BASH_ENV` and `ENV`, so an inherited startup file that prints cannot reach an exact-output assertion.
  - A case that wants a startup file sets its own.
- A fixture checkout is `_init_repo` on a temp directory, which makes no commit (`conftest.py:1730`). It holds a synthetic `_lib.sh` that sources a synthetic `_config.sh` and an empty `config-keys.psv`, all under `claude/.claude/hooks/`, plus a synthetic PSV under `scripts/dev/`.
- The plain fixture holds one function in each measured file, each in its own cluster: `solo` in `_lib.sh` and `other` in `_config.sh`.
- No script case covers the `config-keys.psv` copy into the arm directories, and the lib tests' copy cases do. Sourcing reads no file (row 9), so an omitted copy changes no figure today. The copy stays because row 6 puts all three files in every arm directory.
- Synthetic files keep every case but the smoke run independent of the real files' size and floor check.

Cases:

1. Smoke, run from `REPO_ROOT` with `--iterations 1 --repetitions 2`. It expects:
   - exit 0, and stderr of exactly two lines, one progress line per repetition;
   - a `header` line carrying `iterations=1` and `repetitions=2`;
   - one `span` line per PSV row, one `arm` line per label in list order, and a `noise-floor` line;
   - every `cost_ms` and `saving_ms` value matching `^[+-][0-9]+\.[0-9]{3}$`;
   - every other `_ms` value, and the `noise-floor` line's `ms` value, matching the same form without the sign, with `mins_ms` first split on commas into exactly two values.

   This is the single pin that every anchor resolves at HEAD, and any `_lib.sh` edit selects it (row 14).
2. Planted cost, marked `timing` because it bounds a measured saving (rows 22, 34). Its docstring says that a red under `-n auto` is rerun with `-m timing -n0` before it counts. Its fixture:
   - The PSV lists one `_lib.sh` cluster `slow`, spanning two functions.
   - The `_lib.sh` holds a top-level `sleep 0.1` between those two functions, inside the span.

   It runs with `--iterations 2 --repetitions 2`. It expects exit 0 and a `minus-slow` saving above 50 ms and below 1,000 ms, which is half and ten times the planted 100 ms. The bounds pin the timer's sign and its unit.
3. Source failure, over four lines appended to the fixture's `_lib.sh`, outside every span. Three run as one parametrized case and the guard runs as its own case, all with `--iterations 1 --repetitions 2`. Each sets a per-test `TMPDIR` and expects exit 1, empty stdout and that directory empty after exit:
   - `return 1`: a stderr line starting `lib-source-cost: pre-flight:` names `full`, and no line starts `lib-source-cost: timed:`;
   - a write to stderr: the same expectation;
   - a write to stdout: the same expectation, where the empty stdout also pins that the pre-flight captures the child's stdout;
   - a guard that returns 1 when a marker file exists in `${BASH_SOURCE[0]%/*}`, and otherwise creates that file as its last command.

   The guard's pre-flight source therefore ends 0, and a later timed source returns 1. The case expects a stderr line starting `lib-source-cost: timed: arm full, repetition 1, round 0:` and no `pre-flight:` line.

   The lookup ignores source health and runs on its own copy, so none of the four stops there.
4. Floor gate: a fixture whose only file is a stub `_config.sh` that prints a marker to stderr and returns 1, as `test_bash_floor.py:461-505` does for other scripts. It expects exit 1, stderr exactly the marker, and empty stdout, on any host bash.
5. Spec error: the fixture PSV names a function the fixture never defines. It expects exit 1, a stderr line starting `lib-source-cost: lookup:` naming that function, and empty stdout. Only the fixture's PSV holds that name, so the case also pins that the PSV is read from the checkout root.
6. Usage, parametrized over four rows: `--repetitions 1`, `--iterations 0`, `--iterations` with no value, and an unknown flag. Each exits 2 with empty stdout and a stderr that starts with the usage line.
7. Arm contents, on a fixture whose spans hold top-level marker writes and no sleeps. It runs with `--iterations 2 --repetitions 2` and `TMPDIR` set to an empty per-test directory. Its fixture:
   - The PSV lists a two-span `_lib.sh` cluster `split` before a one-span `_config.sh` cluster `cfg`, and one span ends in a `(` body.
   - Each span holds a top-level line that appends `$0` and a span marker to a log file. The log sits in the test's temp directory, outside the per-test `TMPDIR`.
   - The `_lib.sh` opens with a line, outside every span, that appends `$0` and the last component of `${BASH_SOURCE[0]%/*}` to the log.
   - The `_lib.sh` ends with a line, outside every span, that appends a stderr write to the live `_lib.sh` itself.

   The arm list is `full`, `minus-split`, `minus-cfg`, `total-deletion`, `tail-cut`, `control`, `baseline`, `dirname-fork` and `param-expansion`, in directories `0` to `8`. The case expects:
   - exit 0, because an arm built from the live file would print the appended stderr write and stop the pre-flight;
   - the live `_lib.sh`'s blob changed by the run, and `lib_blob` equal to the blob before it;
   - `config_blob` equal to `git hash-object` of the fixture's `_config.sh`, in a fixture with no commit;
   - the arm labels in list order and the three `span` lines exactly;
   - the `noise-floor` line's `ms` equal to `baseline`'s `spread_ms` and no greater than any other arm's `floor_ms`;
   - the per-test `TMPDIR` empty after exit;
   - the log equal to the expected log:
     - The floor gate's own entry comes first.
     - Each source pass below follows, each entry followed by the markers its spans wrote.
     - The block shows one source pass per row: the lookup, the pre-flight, then rounds 0 to 3.
     - The test writes the passes out rather than deriving them from the lib's rotation.
     - `full`, `control` and the lookup write every marker.
     - `minus-split` and `minus-cfg` write only the markers of the spans they keep.
     - `total-deletion` and `tail-cut` write none.

   ```text
   lookup lookup
   full 0, minus-split 1, minus-cfg 2, total-deletion 3, tail-cut 4, control 5
   full 0, minus-split 1, minus-cfg 2, total-deletion 3, tail-cut 4, control 5
   minus-split 1, minus-cfg 2, total-deletion 3, tail-cut 4, control 5, full 0
   minus-cfg 2, total-deletion 3, tail-cut 4, control 5, full 0, minus-split 1
   total-deletion 3, tail-cut 4, control 5, full 0, minus-split 1, minus-cfg 2
   ```

   The log pins the rotation, `control`'s own copy, the separate `lookup` copy, and which spans each arm removes or moves. The `dirname` arms write no log entry, so the lib tests pin them.
8. Progress lines, on the plain fixture with `--iterations 2 --repetitions 2`. Stderr is exactly `lib-source-cost: repetition 1 of 2` and `lib-source-cost: repetition 2 of 2`, so a line per round or a wrong repetition number would show.
9. Header, on the plain fixture with `--iterations 1 --repetitions 2` and a `dirname` stub that runs the real one first on the PATH. The header's `bash`, `system` and `machine` equal what the test computes independently, `dirname` is the stub's absolute path, and `commit` is `none` because the fixture has no commit.
10. Comma-decimal locale, on the plain fixture with `--iterations 1 --repetitions 2`, `LC_ALL` set to an installed UTF-8 locale that prints `EPOCHREALTIME` with a comma. Every arm's figures keep the same millisecond format as in Case 1. The case fails under `CI` when no such locale is installed and skips otherwise.
11. Inherited `BASH_ENV`, on the plain fixture with `--iterations 1 --repetitions 2`. `BASH_ENV` names a file that appends a line to a log, and the case expects the log to hold exactly one line, the script's own startup. The children that execute the file are the lookup, the pre-flight and the timed children, and none of them adds a line. Row 23 is verified for `bash -c` only, so that the script file's own startup reads `BASH_ENV` rests on this case.
12. Child stdin, on the plain fixture with `--iterations 1 --repetitions 2`. The script's own stdin carries one line, and a line appended to the fixture's `_lib.sh` records any line a source reads from stdin. The case expects exit 0 and no record, which pins that every child reads `/dev/null`.
13. Checkout path with a space, on the plain fixture under a directory named `check out`, with `--iterations 1 --repetitions 2`. The case expects exit 0 and a first `arm` line labeled `full`.
14. Missing measured file, parametrized over `_lib.sh` and `config-keys.psv` removed from the plain fixture, with default flags. The case expects exit 1, empty stdout and one stderr line starting `lib-source-cost: input:` that names the missing file.
15. Pre-flight output with a zero status, on the plain fixture with `--iterations 1 --repetitions 2` and a per-test `TMPDIR`. Two lines are appended to `_lib.sh`: a call to the function the `minus-solo` arm deletes, then a harmless line. The case expects:
    - exit 1 and empty stdout;
    - the single stop line `lib-source-cost: pre-flight: arm minus-solo: exit status 0, output below`;
    - no `timed:` line;
    - the `TMPDIR` empty after exit.

Every run shares one timeout, a module constant of 120 s, whose comment calls it a hang backstop.

- The smoke run starts about 45 child bashes: one lookup, two `bash -n`, 14 pre-flight and 28 timed. At up to the 70 ms per-source minimum the platform review measured under heavy load, that is about 3 s.
- The planted-cost run starts 43 child bashes: one lookup, two `bash -n`, 8 pre-flight and 32 timed. That is about 3 s at the same per-source minimum. It also sleeps 1.1 s, which is 0.1 s in each of 11 sources that keep the span: the lookup, 2 pre-flight sources and 8 timed ones, from `full` and `control` over four rounds. It is the slowest case, at about 4.1 s.
- The margin of at least 29-fold over the 120 s timeout covers a loaded `-n auto` full-suite run.

**Posting.** After the branch passes review, the session runs the script with defaults from the worktree root as a background Bash call. A foreground call's timeout can kill a run of several minutes. The session checks Verification step 6's relations, then shows the engineer the output. Only on the engineer's yes does it post a #1117 comment (rows 3, 4). The comment gives:

- each cluster's saving with its `floor_ms`, `floor_from` and verdict;
- the total, the tail-cut saving and the `dirname` comparison, each with the same three fields;
- the `control` row, the noise floor and the header line;
- that a saving below its applied floor, or a negative one, is no performance case;
- when Verification step 6.3's rerun still misses, the run's order term and every saving against `full` it marks as no case;
- that `full`'s and `dirname-fork`'s costs over `baseline` carry a predecessor offset no arm measures, as Predecessors states;
- a pointer to the script header's before/after rule for #1435 and #1436.

**Alternatives set aside.**

- Hardcoded line ranges: they drift with every `_lib.sh` edit, and #1435 and #1436 rerun the script across exactly such edits.
- Timing `. _lib.sh` repeatedly inside one long-lived shell: a hook pays one fresh process's source. #1433 also prices the source "against a baseline that does not source it" with an exit status per timed source, which only a child process has.
- Pairwise ABAB runs per comparison: each pair repeats the `full` arm for no gain, while one round-robin loop interleaves every arm with every other.
- Lighter timing primitives, all rejected:
  - The bash `time` keyword resolves at best 1 ms (row 20), too coarse for a `dirname` delta near 1 ms.
  - `hyperfine` is a new dependency, and it times arms in sequential blocks, which `hook-bootstrap-cost.md:155` records as untrustworthy at a 1 ms delta (row 19).
  - A Python `perf_counter_ns` harness departs from #1433's prescribed `EPOCHREALTIME` design and puts a heavier spawner into every sample.
- Lighter homes for the cluster list, both rejected:
  - An inline bash array defeats the liveness tripwire (row 13).
  - Whole-line `#` rows parsed out of the script's own source avoid the tripwire, but make the script read its own comments as data.
- Lighter test seams than a lib, both rejected:
  - Subprocess cases alone: a timing run's figures vary, so no case can assert the arithmetic, the span ranges or the edits.
  - Regex-extracting functions from the script at test time: `shell-script-conventions.md:53-56` forbids it (row 39).
- One start-line source instead of two, both rejected:
  - The text rule alone passes a definition-shaped line bash never runs, and a later redefinition in another form.
  - `declare -F` alone sees only a name's last definition (row 32) and gives no end line.
- `sed` or `head` span edits: `sed -i` and `head -n -N` differ between BSD and GNU, and only Linux runs in CI (row 34).
- Integer-microsecond report fields with no formatter: they remove the signed-formatting hazard, but #1117 reads milliseconds, and the lib tests pin the formatter.
- `bash -n` on every arm file: a closer found too early breaks the kept text the pre-flight sources, so its only unique catch is a syntax error confined to the tail cut's moved region. One `bash -n` stage, on the two measured files before the lookup, is enough.
- Placing `control` right before `full`, so `full` also follows a heavy arm. No saving against `full` would then carry the offset `control` measures, so step 6.3's discount would charge savings for an offset they lack. `full` would also still follow a light arm in the one round in A it runs first.
- A second, light control arm to measure the light-arm offset: it adds an arm to every round, while placing `baseline` after `control` already keeps that offset off the `dirname` saving.
- An environment-variable override of the hooks directory as the test seam: it adds a test-only knob, while reading every data file from the working directory's root (row 16) already lets the test aim the real script at a fixture.
- Top-level `scripts/`: that directory holds tools CI and the documented commands run, and `scripts/dev/` holds the one manual diagnostic (row 17). Both satisfy #1433's "repo-root `scripts/`, not `claude/.claude/scripts/`".

**Assumption ledger**

**Root:** #1117's gate for moving any `_lib.sh` cluster needs a measured per-cluster saving against a noise floor. No checked-in harness can measure one on today's 6,233-line `_lib.sh`, or rerun for #1435's and #1436's before/after numbers.

**Givens** (fixed, beyond this plan's reach):

- Each hook is a fresh bash process that sources `_lib.sh` once. *Reason: harness-owned, already recorded as a given at `.claude/plans/hook-bootstrap-cost.md:81`.*
- The bash floor is 5.2, and `_config.sh:40-68` returns 1 below it. *Reason: README § "Requirements" and `_config.sh:26-28` set it, and changing it is a decision outside this plan.*
- Which functions belong to which cluster is #1117's call, and this plan measures #1117's rows as the dispatch relayed them. *Reason: #1117 owns the decomposition.*

| # | Assumption | Tag |
|---|---|---|
| 1 | #1433 prescribes the interleaved ABAB `EPOCHREALTIME` harness with 200 iterations per arm, 3 repetitions and the min statistic. It defines the noise floor as the spread of the baseline arm's three per-repetition minimums. Its arms are full against baseline, per-cluster deletion, a tail cut behind `return 0`, and `dirname` against parameter expansion. It requires every timed source to exit 0 | `[verified: #1433 "Scope" items 2-5, relayed verbatim in the dispatch]` |
| 2 | The benchmark measures every #1117 row except command parsing/redaction | `[engineer-verified: "All non-core rows (Recommended)"]` |
| 3 | Results go on #1117 only after the engineer approves them | `[engineer-verified: "Post after you approve (Recommended)"]` |
| 4 | The posting step follows implementation: the session runs the script, shows the output, posts only after a yes, and changes no repository file | `[unverified]` — the dispatching session's description under row 3's label, not the engineer's words |
| 5 | A non-contiguous cluster is deleted as a list of function spans, and the tail-cut arm moves the same set the deletion arms remove | `[unverified]` — the dispatching session's question and option wording, adopted here as design |
| 6 | `_lib.sh` sources `_config.sh` from `_lib.sh`'s own directory and returns 1 if that fails, and `_config.sh` builds `_CONFIG_SCHEMA_FILE` from its own directory, so each arm directory must hold all three files | `[verified: _lib.sh:25-27, _config.sh:115]` |
| 7 | On a bash below 5.2, `_config.sh` returns 1 and `_lib.sh` propagates it, so a below-floor child exits 1: the failure path a naive run would time | `[verified: _config.sh:26-68, _lib.sh:25-27]` |
| 8 | The only source-time loop reads `_LIB_REVIEW_ONLY_AGENTS` and sits outside every span; the nearest span starts at `:5213` | `[verified: _lib.sh:5165-5213]` |
| 9 | No top-level statement in `_lib.sh` or `_config.sh` calls a span function, and sourcing either file reads no environment variable or file and prints nothing | `[verified: the platform review's top-level enumeration of both files and its sourcing run, Answers Q1 and Q4]` |
| 10 | `_lib.sh` has 167 column-0 function definitions: 163 `name() {` and 4 `name() (` (`:325`, `:4338`, `:4371`, `:5994`). It has 163 column-0 `}` lines and no heredoc, only herestrings | `[verified: Grep counts on _lib.sh at dd60e672]` |
| 11 | Every anchor in the span table exists at `dd60e672`: resume-context `:5848`-`:6221` (file tail), plugin-reconcile `:4338`-`:4463`, worktree-lock `:3904`-`:4209`, review-pr `:669`, `:769`, `:860`-`:884` and `:939`-`:1001`, reviewer-round `:5213`-`:5489`, push-parser `:2113`-`:2427`, and config-writer `_config.sh:1078`-`:1249` (definition lines) | `[verified: definition-line Grep of _lib.sh and _config.sh]` |
| 12 | The review-pr spans skip four interleaved functions, at `:706`, `:797`, `:816` and `:843`. They also skip the globals at `:905-932`. `_lib_valid_session_id_component` reads one of those globals. `_LIB_SIZE_THRESHOLD_BYTES` (`:4319`) and `_LIB_REVIEWER_ROUND_STATE_CAP` (`:5200`) sit above their spans' first functions and stay | `[verified: _lib.sh:895-942, :917-923 comment, :4318-4338, :5193-5213]` |
| 13 | The liveness tripwire's corpus is every tracked shell file plus every tracked `.py` file, with whole-line comments dropped, so a function name on a code line or in a docstring counts as a reference. A tracked `.psv` whose first line is not a shebang is outside that corpus | `[verified: test_shell_lib_function_liveness.py:1-48, :107-133; scripts/list-shell-files.sh:26-51]` |
| 14 | `select-tests.py` maps a path under `scripts/` to the hooks and scripts tests, a `.sh` under `claude/.claude/hooks/` to the scripts tests, and `config-keys.psv` to the scripts tests. So every file either new test reads selects both, and `TestCrossDomainReadCompleteness` passes with no rule change | `[verified: select-tests.py:640-641, :1023, :1050, :1058; test_select_tests.py:372-397; the sdet review's select_pytest_targets run per path]` |
| 15 | Scripts that source `_config.sh` directly do it under a `# shellcheck source=` directive with an `\|\| exit` guard | `[verified: install.sh:29-30; claude/.claude/scripts/config-get.sh:38-39]` |
| 16 | Two of the three repo-root scripts resolve the checkout from the working directory with `git rev-parse --show-toplevel` | `[verified: scripts/list-shell-files.sh:18, scripts/dev/fork-topology-probe.sh:15]` |
| 17 | `scripts/dev/` holds only `fork-topology-probe.sh`, a manual diagnostic with no test, and no doc mentions anything under `scripts/dev/` | `[verified: Grep for scripts/dev outside .claude/plans/ finds only the probe and test_select_tests.py:1519]` |
| 18 | The scripts-tests `conftest.py` provides `_init_repo`, `_clean_env` and `_git`, imported relatively. `_clean_env` drops inherited `GIT_DIR`, `GIT_WORK_TREE`, `GIT_COMMON_DIR` and `GIT_INDEX_FILE`, and takes overrides | `[verified: conftest.py:100-111, :114, :1729; test_venv_run.py:35]` |
| 19 | Sequential-block timing proved untrustworthy at a 1 ms delta for the prior record | `[verified: .claude/plans/hook-bootstrap-cost.md:155]` |
| 20 | bash's `TIMEFORMAT` prints at most three fractional digits | `[unverified]` — supports a rejection only |
| 21 | bash reads a sourced file whole before parsing it command by command, so a top-level `return 0` saves parsing but not reading | `[unverified]` — the reason #1433 prices the tail cut separately; the tail-cut arm measures it, and no design choice depends on it |
| 22 | The `timing` pytest marker is for a test that asserts a wall-clock bound or needs serial isolation | `[verified: pyproject.toml:31]` |
| 23 | A non-interactive `bash -c` sources `$BASH_ENV` when it is set | `[verified: the platform review's run of BASH_ENV=<file> bash -c 'echo body', Answers Q1]` |
| 24 | `_config.sh` sources cleanly under the script's `set -euo pipefail` | `[unverified]` — `config-get.sh` runs `-uo pipefail` and `install.sh` runs `-e`, never both. The platform review's run confirmed it on bash 5.3.20 only. The smoke test settles it on CI's 5.2, and the fallback is sourcing it before `set` |
| 25 | The change adds `scripts/dev/lib-source-cost-clusters.psv` beside the script, a file #1433 does not name | `[engineer-verified: "Accept the PSV file (Recommended)"]` |
| 26 | The plan stays one PR at its projected diff of about 420 changed lines | `[engineer-verified: "Proceed anyway"]` — superseded by row 40, which answers the later projection |
| 27 | The change adds a sourceable lib beside the script and deterministic tests for it | `[engineer-verified: "I'm inclined to do deterministic tests and a sourceable lib."]` |
| 28 | The lib holds the flag-value check, cluster-file parsing, span resolution, the arm edits, the arm list with its rotation and references, the per-repetition minimum fold, the arithmetic and the line formatting. The tests are fixed-input lib tests, one subprocess case that plants a cost inside a known span, one that logs which spans each arm sources, the real-file smoke run as the single anchor-resolution pin, and failure and spec-error cases on small synthetic fixtures | `[unverified]` — the dispatching session's reading of row 27, adopted here as design; not the engineer's words |
| 29 | Span lookup combines the text rule with bash's `declare -F` | `[engineer-verified: "Text rule plus declare -F (Recommended)"]` |
| 30 | `declare -F` under `extdebug` supplies each start line, and the closer rule stays for end lines, guarded by the overlap and overrun stops and the pre-flight | `[unverified]` — the dispatching session's description under row 29's label, not the engineer's words. That description named a `bash -n` check on the arm files, which the pre-flight replaces (row 42) |
| 31 | Under `shopt -s extdebug`, `declare -F <name>` after sourcing `_lib.sh` prints the name, its definition line and the file path. For `_lib_validate_plugin_id` and `_lib_sanitize_for_terminal` it printed 4338 and 6221, matching the definition-line Grep. For all 18 anchors it printed row 11's definition lines, with the `_config.sh` path for both `_config.sh` anchors | `[verified: the dispatching session's run of bash -c 'shopt -s extdebug; . claude/.claude/hooks/_lib.sh; declare -F ...' in this worktree, for two anchors; the platform review's run of all 18 on bash 5.3.20, round 2 Answers Q2]` |
| 32 | Bash keeps one definition per name, the last one it ran, so `declare -F` reports a redefinition's line and cannot see the earlier definition. A source that returns 1 after defining every anchor still resolves them all | `[verified: the platform review's synthetic-file run on bash 5.3.20, round 2 Answers Q2]` — the lib tests settle it on CI's 5.2 |
| 33 | The closer rule resolves the ten rows to the span table's resolved lines, 1,746 `_lib.sh` lines in all. Every arm built from those spans parses under `bash -n` and sources with status 0 and empty output | `[verified: the platform review's resolution and build run, Answers Q1]` |
| 34 | CI runs only on `ubuntu-24.04`. It runs a parallel leg under `-m "not timing"` and a serial leg under `-m timing -n0` | `[verified: .github/workflows/tests.yml:28 per the platform review; :33-38 and :221-227 read this session]` |
| 35 | In a file that sources `_config.sh`, the code above the floor check must parse on bash 3.2 | `[verified: .claude/rules/shell-floor.md:14]` |
| 36 | A `# shellcheck source=` directive resolves relative to the sourcing script's own directory | `[verified: .shellcheckrc:21 source-path=SCRIPTDIR; config-get.sh:38's ../hooks/_config.sh form]` |
| 37 | The prior record prices `$(dirname "$0")` against parameter expansion at a 1.01 ms min and a 1.15 ms median | `[verified: .claude/plans/hook-bootstrap-cost.md:17]` |
| 38 | `git hash-object <path>` prints a file's blob id in a repository with no commit | `[unverified]` — the arm-contents case checks `lib_blob` and `config_blob` in a fixture with no commit, so it settles this |
| 39 | Pure bash in a `.sh` file goes into a sourceable `_<topic>-lib.sh`, unit-tested by sourcing it, and the subprocess test keeps one case per branch | `[verified: claude/.claude/rules/shell-script-conventions.md:53-56, whose paths: cover `**/*.sh`; .claude/rules/bash-unit-test-seams.md:21 for the name form]` |
| 40 | The plan stays one PR at its projected diff of about 1,200 changed lines | `[engineer-verified: "Proceed anyway"]` — the second such answer, given for this projection |
| 41 | `mapfile` then `printf '%s\n'` rewrites a newline-terminated file byte for byte. It adds a newline to a last line that lacks one and turns an empty file into one byte | `[verified: the platform review's runs on the real _lib.sh and _config.sh and on synthetic files, bash 5.3.20, round 2 Answers Q2]` |
| 42 | A syntax error stops a sourced file at that line. Before any top-level `return 0` the source exits non-zero with bash's message on stderr. After one it exits 0 with empty stderr, while `bash -n` still fails. A lookup child sourcing such a file defines only the functions above the error and shows no cause | `[verified: the test review's runs (round 2 R4) and the platform review's run (round 2 R2), on bash 5.3.20]` |
| 43 | Under the rotation, an arm follows its list predecessor in every round but the one in A where it runs first, and there it follows the arm two places before it | `[verified: the platform review's simulation of 14 arms over 600 rounds, round 2 R1: 557 or 558 rounds after the list predecessor]` |
| 44 | A light arm's predecessor offset, if one exists, is small beside `full`'s cost, which the platform review's minima put at tens of milliseconds | `[unverified]` — the reason `baseline` follows `control`; no arm measures that offset |

**Mechanisms:**

- A bash script in `scripts/dev/` that reads every data file from the checkout root and gates on that checkout's `_config.sh` floor check, with only bash-3.2-parseable lines above the gate. `anchors: root, row7, row15, row16, row17, row24, row35, row36`
- A sourceable lib beside the script holding everything a fixed input can test. `anchors: row27, row28, row39`
- Cluster spans in a PSV under the checkout root, anchored by function name and resolved at run time. `anchors: row2, row5, row11, row13, row25`
- Start lines from `declare -F` under `extdebug`, cross-checked by the text rule, end lines from the closer rule, `bash -n` on both measured files before the lookup, and the span stops. `anchors: row10, row29, row30, row31, row32, row33, row42`
- Arm edits in bash line arrays, applied only to files that hold the arm's spans. `anchors: row34, row41`
- One scratch directory per arm plus a `lookup` copy, each holding all three files. `anchors: row6`
- The arm list, each arm's reference, the `control` arm, and the list order's predecessor classes with `baseline` after `control`. `anchors: row1, row2, row5, row12, row21, row43, row44`
- One rotated round-robin timing loop, with the lib folding samples into per-repetition minimums. `anchors: row1, row19, row28`
- The noise floor and each row's applied floor. `anchors: row1`
- The pre-flight's exit-and-output check, which also catches a closer found too early, and the per-timed-source exit check, with the lookup leaving source health to the pre-flight. `anchors: row1, row7, row8, row9, row42`
- The key-value report with blob ids, printed only after the last round. `anchors: root, row1, row38`
- The before/after reading rule in the script header. `anchors: root`
- Fixed-input lib tests, and script cases on synthetic fixtures plus one real-file smoke run. `anchors: row13, row14, row16, row18, row27, row28, row39`
- The planted-cost case under the `timing` marker. `anchors: row18, row22, row34`
- The arm-contents case, which logs each source's label, directory and span markers. `anchors: row18, row38`
- Sanity relations checked before posting, with one rerun and an order-term discount when `control` or a negative saving misses. `anchors: row1, row21, row37, row43`
- Posting to #1117 gated on the engineer's yes, from a background run. `anchors: row3, row4`
- **Over-powered-primitive check on the timing mechanism:** the `time` keyword (1 ms resolution), `hyperfine` (new dependency, sequential blocks) and a Python `perf_counter_ns` harness (departs from the prescribed design, heavier spawner) each fail on the ground given in the Approach. `anchors: row1, row19, row20`
- **Over-powered-primitive check on the PSV file and the fixture checkout:** an inline array (defeats the tripwire), self-parsed comment rows (comments read as data) and an environment-variable hooks-directory override (a test-only knob the working-directory rule makes unnecessary) each fail on the ground given in the Approach. `anchors: row13, row16`
- **Over-powered-primitive check on the lib:** subprocess cases alone (nondeterministic figures) and regex-extracting functions from the script (forbidden) each fail on the ground given in the Approach. `anchors: row39`
- **Over-powered-primitive check on the `declare -F` lookup,** which adds one child process to the text rule: the text rule alone and `declare -F` alone each fail on the ground given in the Approach. `anchors: row29, row32`

## Critical files

**Two sequenced `code-writer` dispatches.** The script calls the lib's functions as the first dispatch names them, so the first dispatch's output is the second's input. The two file sets do not overlap. Both dispatches read this plan for the shared report grammar, stop texts and arm list.

Both prompts also carry two warnings:

- A test function named after its module, such as `test_lib_*`, contains `_lib_` and can match a real function in the liveness test. So no test function name contains `_lib_` or `_config_`, as Function names stay out of code requires.
- `scripts/list-shell-files.sh` lists only tracked and staged files, and a dispatch does not stage. So each dispatch lints its own files by path.

1. Lib dispatch: `scripts/dev/_lib-source-cost-lib.sh` and `claude/.claude/scripts/tests/test_lib_source_cost_lib.py`. It verifies with `scripts/venv-run.sh pytest claude/.claude/scripts/tests/test_lib_source_cost_lib.py`, `scripts/venv-run.sh shellcheck scripts/dev/_lib-source-cost-lib.sh` and `scripts/venv-run.sh ruff check claude/.claude/scripts/tests/test_lib_source_cost_lib.py`.
2. Script dispatch, after the first returns: `scripts/dev/lib-source-cost.sh`, `scripts/dev/lib-source-cost-clusters.psv` and `claude/.claude/scripts/tests/test_lib_source_cost.py`. It calls the lib as written and edits neither lib file. A lib gap it finds goes back to the parent session rather than into the lib. It verifies with `scripts/venv-run.sh pytest claude/.claude/scripts/tests/test_lib_source_cost.py`, Verification step 2, `scripts/venv-run.sh shellcheck scripts/dev/lib-source-cost.sh` and `scripts/venv-run.sh ruff check claude/.claude/scripts/tests/test_lib_source_cost.py`.

**Files to create:**

- `scripts/dev/_lib-source-cost-lib.sh`: the lib in the Approach. Its header and file mode follow `claude/.claude/scripts/_worktree-lib.sh`: a shebang, a one-line purpose, and that `lib-source-cost.sh` sources it and nothing runs it directly.
- `scripts/dev/lib-source-cost.sh`: the benchmark in the Approach, committed executable. Its header comment states, one fact per line:
  - its purpose;
  - the usage line, with both flags, their defaults and the run-time formula;
  - that it measures the checkout it runs in, including its cluster file;
  - the three lines of the before/after reading rule.
- `scripts/dev/lib-source-cost-clusters.psv`: the ten rows of the span table, under a `#` header. Its first line must not be a shebang (row 13). The header states, one fact per line:
  - the row grammar;
  - that a span runs from the first function's definition line through the last function's closer;
  - that several rows make a non-contiguous cluster;
  - that a renamed function stops the script until its row is updated.
- `claude/.claude/scripts/tests/test_lib_source_cost_lib.py`: the lib tests in the Approach.
- `claude/.claude/scripts/tests/test_lib_source_cost.py`: the script cases in the Approach.

**Reuse:**

- `_config.sh`'s floor gate, sourced the way `install.sh:29-30` and `claude/.claude/scripts/config-get.sh:38-39` source it.
- `claude/.claude/scripts/cleanup-merged-branches.sh:177-178`'s script-relative lib source and its `# shellcheck source=` directive.
- `claude/.claude/hooks/tests/test_shell_lib_function_liveness.py:142-149`, which already asks a child bash which functions a sourced lib defines.
- `claude/.claude/scripts/tests/test_worktree_lib.py:42-62`'s way of sourcing a lib under `set -euo pipefail` in `bash -c`.
- `conftest.py`'s `_init_repo` (`:1729`) and `_clean_env` (`:103`), imported relatively as `test_venv_run.py:35` does. `helpers`' `REPO_ROOT`, imported as `test_shell_lib_function_liveness.py:62` does.
- `claude/.claude/hooks/tests/test_bash_floor.py:461-505`'s stub `_config.sh`, for the floor-gate case.
- `config-keys.psv:7-11`'s row grammar for the PSV.

**No edit needed:**

- `select-tests.py` and `test_select_tests.py`: existing rules already select both new test files (row 14).
- `test_shell_lib_function_liveness.py`: the PSV design and the naming rule leave its corpus unaffected.
- `scripts/list-shell-files.sh`: it discovers the two new `.sh` files itself once they are staged.

Only the two test files land under `claude/`, so they are the only new files stowed to every consumer, where they are inert. The script, lib and PSV never install, and the script writes and deletes only its own `mktemp -d` directory.

Projected diff: about 1,350 lines (lib about 345, script about 195, PSV about 30, lib tests about 440, script tests about 335). Row 26 answered the earlier projection of about 420 lines, and row 40 answered a projection of about 1,200. `/plan-review` asks the size question once per plan, so the later growth to about 1,350 was not put to the engineer again.

## Verification

Run from the worktree root. First stage the five new files by path with `git add`. `scripts/list-shell-files.sh` lists only tracked and staged files, and `test_shellcheck.py`, `test_shell_dialect.py`, the liveness test and step 3 all discover files through it, so on unstaged files they pass without checking them.

1. `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py`. For a `scripts/` change it selects the hooks and scripts test domains (`select-tests.py:1050`). Those hold both new test files, `test_shellcheck.py`, `test_shell_dialect.py`, `test_shell_lib_function_liveness.py` and `test_select_tests.py`. This run includes the planted-cost case under `-n auto`, so a red there is rerun with step 2 before it counts.
2. `scripts/venv-run.sh pytest claude/.claude/scripts/tests/test_lib_source_cost.py -m timing -n0`, which runs the planted-cost case serially, as CI's timing leg does (row 34).
3. Run `scripts/list-shell-files.sh | xargs -0 scripts/venv-run.sh shellcheck`. Discovery picks up the staged script and lib. The script's directives use the script-relative form `config-get.sh:38` uses (row 36): `# shellcheck source=../../claude/.claude/hooks/_config.sh` and `# shellcheck source=_lib-source-cost-lib.sh`.
4. `scripts/venv-run.sh ruff check claude/.claude/ claude-skills/ plugins/ evals/`.
5. `/code-review` before the commit.
6. A manual full run:
   1. Run `scripts/dev/lib-source-cost.sh` with defaults in the background. Expect exit 0, one progress line per repetition on stderr, and a complete report on stdout.
   2. Compare every `span` line's `lines=` with the span table's resolved lines, allowing for any `_lib.sh` edit since `dd60e672`.
   3. Confirm these relations before showing the figures to anyone:
      - `control`'s verdict is `below`.
      - No saving is below minus its `floor_ms`. Removing code cannot slow a source, so such a row is an order or load artifact, like a `control` miss.
      - `full`'s `cost_ms` is positive, with verdict `above`.
      - `total-deletion`'s saving is at least each `minus-*` saving, less the larger of the two rows' `floor_ms`.
      - `tail-cut`'s saving lies between 0 and `total-deletion`'s, within their floors (row 21).
      - `param-expansion`'s saving is positive and of the order of the 1.01 ms min recorded for the same construct written with `$0` (row 37). That cost does not depend on `_lib.sh`'s size, so the record is comparable.

      If either of the first two relations fails, rerun once and use the rerun. The list order, not chance, fixes each arm's predecessor (Predecessors), so a miss that survives one rerun is likely structural and would survive more. If either still fails:
      - The run's order term is the largest of `control`'s absolute saving and the magnitude of every saving against `full` that lies below minus its floor.
      - The posting reports that term and marks every saving against `full` that does not exceed it as no case. The discount errs against moving a cluster.

      No prior record is a reference for `full`'s cost, since Context notes both were taken on a much smaller `_lib.sh`.
   4. Where a below-floor bash exists (macOS `/bin/bash` is 3.2), `/bin/bash scripts/dev/lib-source-cost.sh` must exit 1 with `_config.sh`'s floor text and empty stdout.
7. Write the comment to a body file, show the engineer that file, and post to #1117 with `gh issue comment 1117 --body-file <file>` only after their yes.
   - The file posted is the exact file the engineer was shown.
   - The engineer reads the header's `dirname=` and `commit=` values before saying yes, because the script prints both as they resolve locally.

   The figures are synthetic-loop timings of this repo's own code, which root `CLAUDE.md` places outside the provenance class: "Content derived only from this repo's own history, from public sources, or from synthetic fixtures is not in this class". The comment carries no machine state beyond the header's bash version, system, machine, `dirname` and `commit=`.

## Out of scope

- Moving, splitting or tail-cutting any cluster in the real `_lib.sh` or `_config.sh`, and replacing the two `dirname` forks. #1117, #1436 and #1435 own those, and this plan only measures them.
- The command parsing, quote-masking and credential redaction row. #1117 keeps it in core, and the engineer chose "All non-core rows (Recommended)".
- A wall-clock bound on any real-file figure. No latency budget exists to assert against (`.claude/plans/lib-sh-perf-audit.md:114`). The planted-cost case bounds only costs and savings it planted, and it carries the `timing` marker because such tests flake under contention (`pyproject.toml:31`).
- Pricing #1117's `_LIB_CORE_ONLY` guard form separately from the bare `return 0`. The guard adds one `[ -n ]` test, and #1433 prices the bare form.
- Deleting each span's leading comment block. Leaving it in makes the savings understate a real move slightly, which errs against moving a cluster.
- Balancing each arm's predecessor with a Williams-design order or a seeded shuffle. Rotation balances position, the list order decides which comparisons share a predecessor class, and `control` measures the offset the savings against `full` carry.
- A pointer to the script from README or `docs/`. No doc mentions anything under `scripts/dev/`, and the existing probe sets that precedent. The header comment is the usage doc, and #1435 and #1436 cite the path directly.
- `plugins/skill-management/hooks/_lib.sh`, a separate file that sources nothing.
- Running the children under a different bash from the one running the script, and keeping the scratch copies after a run.
- A script-level count of `dirname` calls per light arm. The script's wiring of the three light arms is pinned only by the smoke run's exit status and report format, and the lib test pins the arm files' content.
