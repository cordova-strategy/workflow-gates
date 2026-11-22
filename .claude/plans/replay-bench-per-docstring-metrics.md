# Add per-docstring secondary metrics to the replay bench

## Context

Goal: let the Python replay campaign tell "agents write longer docstrings" apart from "agents write docstrings more often", without changing the study's pre-set primary outcome or its 20% rule.

Ask: "for pure verbosity we can use a mechanical metric." — and, on whether words per new docstring sits beside the primary outcome, "Yes to number 2." — and, on the plan's remaining choices (no threshold on the new figures; start after the Python-prune PR merges), "Sure let's go with recommended" — and, on whether to add the share of new definitions that get a new docstring beside words per new docstring, the selected label "Yes, both figures (Recommended)".

Why now: the primary outcome, comment-plus-docstring words per added non-test code line, mixes how often an agent writes a docstring with how long each one is. The Python campaign (about 50 tasks, `--k 3`) is the study that decides whether the toolkit's prose or the model's habits drive verbose docstrings, and a pilot showed the toolkit arm writing fewer words, so the reading rule must be direction-aware before any campaign output is read. The Python-prune PR (#1562) merged as `f96c618a`, so this change can branch from `main` without conflicting with its record fields.

Intended outcome:

- The runner records, per run, four Python counts from which words per new docstring and the share of new definitions with a new docstring follow.
- `summarize` prints both figures as descriptive secondary figures over the primary's paired task set, with no threshold.
- `evals/README.md` documents both figures and a direction-aware reading rule.
- Existing task sets and campaign records stay readable and report the new figures as `not measured`.

## Approach

Each run, and each task mined from now on, records four Python counts per scope: new docstrings, the words in them, new definitions, and new definitions whose docstring is new. `summarize` turns the non-test counts into two descriptive figures, words per new docstring and the share of new definitions with a new docstring. It prints them after the existing secondary outcome, over the primary outcome's paired tasks, each with a `toolkit - bare` difference, a 95% bootstrap interval and its dropped-resample count, and no threshold. A run record or task set written before this change keeps its bytes and its task-set hash, and every figure it cannot supply prints `not measured`.

**What counts.** Both rules read only what `measure_diff` already receives: the added line numbers and the post-change file (row 16).

- A new docstring is a class or function docstring whose line range, as `mine_szz._docstring_lines_without_shared_code` trims it, is non-empty and made only of added lines.
  - A module docstring is not one (proposal (c), row 8).
  - A one-line docstring on its `def` line is not one, since its trimmed range is empty (proposal (b), row 7).
  - A docstring that gained lines inside an existing one is not one.
  - A docstring written whole onto an existing definition is one.
- A new definition is a class or function, methods and nested ones included, whose `def` or `class` line and the first line of its first body statement are both added lines. A signature edit changes only the first of those two lines, so it is not a new definition (row 20).
- A new docstring's words are the per-line counts `_comment_words` already computes for its lines, so the quote opener adds no word and a blank interior line adds nothing (rows 18, 19).

**Figures.** Both cover non-test files only. Both pool as the primary outcome does: a task's arm counts are its valid runs' means, and an arm's figure is a ratio of sums over the paired tasks (proposal (a), row 6).

- Words per new docstring: the sum of new-docstring words over the sum of new docstrings.
- Share of new definitions with a new docstring: the sum of new definitions whose docstring is new over the sum of new definitions. Its numerator counts those definitions, not proposal (a)'s new docstrings, so the share stays between 0 and 1. A docstring added to an existing definition still enters the first figure but cannot inflate this one (row 11).
- The difference statistic returns None for a resample in which either arm's denominator sums to zero. `analysis.bootstrap_interval_with_drops` drops and counts those resamples (proposal (d), row 9).

**Rewrites count as new.** The rules see added line numbers only, so a `-U0` replacement hunk reads the same as a pure insertion. Five edits therefore count as new, and the README names all five:

1. A one-line docstring on its own line, reworded, counts as a new docstring with all its words.
2. A signature edit made together with a reworded one-line docstring on its own line counts as a new documented definition and a new docstring.
3. A signature edit made together with an edit to the opener of a multi-line docstring, or to a first body line that is no docstring, counts as a new undocumented definition.
4. An edit to an existing one-line definition, such as a stub or a one-line class, counts as a new undocumented definition, because its `def` line and first body line are the same line.
5. A signature edit made together with a docstring or a statement inserted at the top of the body counts as a new definition, documented when the insertion is a docstring.

Excluding replacement hunks would need `parse_added_lines` to keep the old-side count. It would trade these false positives for false negatives, since a genuinely new function adjacent to an edited line may merge into one replacement hunk. No test pins that merge.

**Not measured.**

- An arm's figure and the difference print `not measured` when any valid run of a paired task lacks the counts, and the line says how many paired tasks lack them.
- The reference line prints `not measured` when a paired task's reference entry is present without the counts, and `n/a` when the reference is unavailable or lacks the task, because the `reference unavailable:` line already says why.
- Computing over only the runs that carry the counts would silently change which tasks a figure covers.
- A Python file the parser rejects adds zero counts, while the primary's code lines still include it. The README says so.

**Reading rule.** `evals/README.md` states it for these two figures only.

- A gap whose 95% interval covers zero is a null.
- Any other gap is read with its sign: toolkit below bare means the toolkit lowers the figure.
- An effect on only some tasks can read as a null, because the interval also carries task-to-task variation.
- The 20% rule stays the primary outcome's alone (row 25).

Rows 26 and 30 give the reason for the interval reading.

Alternatives set aside:

- A new definition as any definition whose `def` line is added, the exploration's proposal: it counts every signature edit. A task that threads a parameter through five documented functions and adds one documented function would read as one documented definition in six.
- A new definition as one whose whole span is added: a new function ending in a common line such as `return None` can lose that last line to the old function above it when git slides the inserted block (row 21).
- Passing pre-change bytes to `measure_diff` to match definitions by name: it widens the inputs of both callers, run capture and task mining (row 16), for a descriptive figure.
- Always emitting the counts, zeroed when unmeasured: every existing task set's hash would change, and `summarize` would then report no reference for any older campaign (row 12).
- A mean of per-task ratios: a task in which an arm wrote no new docstring has no ratio, which needs a second exclusion rule and gives each figure its own task set.
- The spread reading of the null clause, which compares a gap with a per-arm run-to-run spread figure (row 26).
- The `CommentMetrics.blocks` already held by every old run record and task set, which would give a docstring-block count and words per block on old campaigns with no hash change. A sectioned docstring splits into several blocks at its blank lines, so a structure change would mimic a length change, and the share figure needs definitions that blocks do not carry.
- Per-task lines for the new figures: about twice the paired-task count in further local output, for figures with no threshold.

**Assumption ledger**

**Root:** the primary outcome, comment-plus-docstring words per added non-test code line, rises both when an agent writes docstrings more often and when it writes longer ones, so the Python campaign cannot tell the two apart. Any figure added to separate them needs its reading fixed before campaign output is read.

**Givens:**
- G1. Run records and task sets written before this change lack the counts and cannot gain them. Reason: the counts need the whole post-change file, which a run does not keep (row 15), and recovering it takes a paid rerun outside this plan's reach.
- G2. The primary outcome, `paired_outcome`, the primary printout and the 20% rule stay as they are. Reason: the experiment's pre-registered design owns them (`.claude/plans/docstring-verbosity-experiment.md:108`, "fixed before any run"), and reopening it is a decision outside this plan.
- G3. CPython's `ast` positions decide which lines belong to a definition, and git's diff alignment decides which lines count as added. Reason: the interpreter and git impose both (rows 19, 21).

**Mechanisms:**
- **M1: `mine_szz._python_docstring_owners` returns each module, class and function node with its trimmed docstring range, or None for a node without one, and `_python_docstring_lines` flattens it.** `anchors: row17, row28, row29` One parse per file then serves both the line classes and the counts, and the docstring rule keeps one home.
  - Rejected, a second `ast.parse` and walk in `comment_metrics.py`: it restates the docstring rule and doubles a parse that `_python_docstring_lines`' own docstring says costs seconds on a multi-MB file.
  - Rejected, working from the flattened line set: it carries neither the owning node nor any definition without a docstring.
- **M2: `_classify_python` derives the four counts from the owners, the added line numbers and the word counts, and returns them on `FileClassification`.** `anchors: G3, row7, row8, row16, row18, row19, row20, row21`
- **M3: `CommentMetrics.python_definition_counts` defaults to None, `to_dict` omits it when None, `from_dict` reads it with `.get`, and `measure_diff` always sets it, zeroed per scope before tallying.** `anchors: G1, row12, row13, row14, row22` An unmeasured task set keeps its bytes and hash, and a measured empty change stays distinct from an unmeasured one.
- **M4: `summary._per_docstring_figure_lines` prints both figures after the existing secondary outcome and before `diagnostics per arm:`, reusing the primary's pooling helpers and `bootstrap_interval_with_drops`.** `anchors: G2, row5, row6, row9, row10, row11, row23, row24`
- **M5: `evals/README.md` defines both figures, their `n/a` and `not measured` cases and the direction-aware reading rule, beside the existing secondary outcome.** `anchors: row1, row2, row3, row25, row26, row27, row30`

**Assumption rows:**
1. [engineer-verified: "for pure verbosity we can use a mechanical metric."] The new figures are counts the classifier derives from the change, with no judge pass.
2. [engineer-verified: "Yes to number 2."] The engineer answered "number 2" of the session's numbered proposals, which concerned adding words per new docstring beside the primary outcome. The quote alone does not show whether that meant a descriptive secondary line or a line printed with the primary, so M4's placement is row 10's proposal. The primary outcome and its 20% rule stay unchanged.
3. [engineer-verified: "Sure let's go with recommended"] Asked about two of the session's proposals, the engineer accepted both: the new figures carry no 20% threshold and are reported descriptively, and the work starts after the Python-prune PR merged.
4. [verified: the session's git status, whose recent commits list `f96c618a replay bench python prune (#1562)`] The prune PR is on `main`, so this branch starts from `main`.
5. [engineer-verified: "Yes, both figures (Recommended)"] Asked whether to add the share of new definitions that get a new docstring beside words per new docstring, the engineer selected this label, which is the session's option. Both figures ship.
6. [unverified] Proposal (a), the session's: pool each figure as a ratio of sums, as the primary does (`summary.py:58-78`). Adopted, because a ratio of sums stays defined for a task in which an arm wrote no new docstring, where a per-task ratio is 0/0.
7. [unverified] Proposal (b), the session's: a one-line docstring on its `def` line is no new docstring. Adopted, because `_docstring_lines_without_shared_code` already drops a line shared with code (`mine_szz.py:101-109`), so the classifier counts that line as code (row 19).
8. [unverified] Proposal (c), the session's: module docstrings enter neither figure. Adopted: a module is no definition the share could pair it with, and leaving it out of words per new docstring keeps both figures about class and function docstrings.
9. [verified: `evals/review_bench/analysis.py:362-410`] `bootstrap_interval_with_drops` returns the interval and the dropped-resample count. It drops a resample whose statistic is None and returns no interval for fewer than two tasks or when every resample drops. `bootstrap_interval` is its interval alone, so `_interval_over_tasks` can delegate to a drop-returning helper and keep the same draws. Proposal (d), the session's, prints each difference with both.
10. [unverified] Proposal (e), the session's: the two figures are named additional secondary outcomes beside the existing secondary outcome.
11. [unverified] This plan's refinement of proposal (a): the share's numerator counts new definitions whose docstring is new, not new docstrings. Proposal (a)'s numerator would count a docstring added to an existing definition with no definition beside it in the denominator, so the share could pass 1.
12. [verified: `evals/replay_bench/campaign.py:65-66`; `evals/replay_bench/tasks.py:169-183`; `evals/replay_bench/summary.py:122-135`] `task_set_hash` hashes each task's `to_dict()`, which embeds `reference_metrics.to_dict()`, and `summarize` reports no reference when that hash differs from the manifest's. A key emitted for every task would change every existing task set's hash.
13. [verified: `evals/replay_bench/comment_metrics.py:379-390`; `evals/replay_bench/tasks.py:218-233`] `CommentMetrics.from_dict` reads every key by subscript, and `ReplayTask.from_dict` turns a KeyError or TypeError into a ValueError. A dict without the new key therefore needs `.get`.
14. [verified: `evals/replay_bench/summary.py:46-55,337-353`; `evals/replay_bench/records.py:45`] `summarize` reads a run's `metrics` by fixed keys, and a record keeps `metrics` as an unvalidated dict. An added key therefore breaks no reader. It must stay a sibling of `line_counts`, whose scopes `summary.py:341-342` iterate. [verified: as relayed] `smoke.py:76-77` reads the same way.
15. [verified: `evals/replay_bench/diffing.py:21`; `evals/replay_bench/records.py:109-119`] A run keeps its change as `git diff -U0` text, which holds no unchanged line, so the post-change file the counts need cannot be rebuilt from it. The experiment plan's row 157 "no rerun" premise therefore does not cover these figures.
16. [verified: `evals/replay_bench/comment_metrics.py:393-423`; as relayed, `diffing.py:64-90` and `tasks.py:762-785`] Run capture and task mining both call `measure_diff`, which receives the added line numbers and the post-change bytes but no pre-change bytes.
17. [verified: `evals/review_bench/mine_szz.py:101-141,157`] `_python_docstring_lines` parses once and counts attempts and failures on `stats`. It takes a docstring as the string-constant first statement of a module, class or function, and trims a first or last line shared with code. Its non-test callers are `comment_metrics.py:248` and `mine_szz.py:157`.
18. [verified: `evals/replay_bench/comment_metrics.py:246-295`] `_classify_python` tests for a blank line before a docstring line. `_comment_words` counts a docstring line's words after stripping the quote opener and keeps no entry for a blank line.
19. [verified: the exploration's run on Python 3.14, the repo floor, as relayed] A decorated function's or class's `lineno` is its `def` or `class` line. A sectioned docstring's range spans its blank interior lines. A one-line docstring on the `def` line gives an empty trimmed range.
20. [unverified] Feature and fix commits often edit an existing signature and leave the body alone, so a `def`-line-only rule would count those definitions as new.
21. [unverified] git can slide an inserted block by a line when the block's last line equals the line just above it, so a new function's last line can show as unchanged. A `def` line under a unique name and the line after it sit at the block's top and do not slide out of it for a body of two or more lines. `staff-backend-engineer` probed 11 shapes with the mining flags and saw no slide, and `staff-sdet` argues a one-line body could slide. One real-git test pins the one-line-body case under both flag sets (`tasks.py:69`, `diffing.py:21`), and the row stays unverified until it runs.
22. [verified: `evals/test_replay_bench_comment_metrics.py:527-529`] The empty-change test compares `measure_diff("", "", {})` with `CommentMetrics()`, so its expectation changes once `measure_diff` sets zeroed counts.
23. [verified: `evals/test_replay_bench_summary.py:20-33,70-72,804,832-834,1025`] The summary tests build metrics through `CommentMetrics()` and read a figure from the first line with a given prefix. They take arm diagnostics from every `"  toolkit: "` or `"  bare: "` line after `diagnostics per arm:`, and one asserts no line says `reference unavailable`. New lines therefore need three properties:

- prefixes no existing line uses;
- a position before `diagnostics per arm:`;
- no line saying `reference unavailable`.
24. [verified: `evals/replay_bench/summary.py:32-39,58-78,156-158,183-186,235-242`] Pooling another ratio needs a denominator parameter and a drop-returning interval, because of four facts:

- `_ArmCounts` names its denominator `code_lines`.
- `_mean_counts_per_run` always divides by code lines.
- `_arm_docstring_counts` holds the per-arm record filter.
- `_interval_over_tasks` calls `bootstrap_interval`.

Only `summary.py` references `_ArmCounts` and `_arm_docstring_counts`, the latter at `:328` and `:333`.
25. [verified: `evals/README.md:1509-1510`] The 20% rule calls a paired difference meaningful when the toolkit's figure is at least 20% above or below bare's. Adding the null-within-spread clause to the primary would set a second decision rule beside it, which G2 bars, so the new rule covers the new figures only.
26. [unverified] "A gap smaller than what run-to-run spread explains" reads as a 95% interval that covers zero. The architect made this choice under row 30's delegation, and the engineer did not choose it. [verified: `evals/review_bench/analysis.py:44-46,362-366`] The interval is two-sided 95%, from 10,000 seeded resamples. Reasons:
    - Each task's arm figure is a mean over its runs, so the bootstrap over tasks carries run-to-run variation.
    - `summarize` prints the interval anyway, so the rule needs no further figure.
    - The spread reading has no value for a run that wrote no new docstring.
    - The spread reading is a size threshold that never tightens with more tasks, and row 3 declined a threshold for these figures.
    - Cost: the interval also carries task-to-task variation, so a toolkit effect on only some tasks reads as a null. The rule therefore leans toward calling a gap null, and the README says so.
27. [verified: `.claude/plans/docstring-verbosity-experiment.md:108,439,718-729`; `evals/README.md:1535-1536`] The experiment plan pre-registered one docstring secondary outcome and kept every other figure out on the strength of its row 157. The README names that plan as the bench's design home.
28. [verified: Grep of `evals/` for `_python_docstring_lines`] Tests at `evals/test_review_bench_mining.py:1219-1255` pin `_python_docstring_lines`' results and its parse-failure counting.
29. [verified: `staff-sdet`'s in-process call of `select_pytest_targets`, as relayed; `claude/.claude/scripts/select-tests.py:709-711`] The plan's changed paths select `domain-selected` targets, not the full suite: the `evals/test_replay_bench*.py` and `evals/test_review_bench*.py` tests, three other evals tests, `claude/.claude/scripts/tests/test_select_tests.py` (from the `evals/replay_bench/` edits) and `claude-skills/skills/tests` (from the `evals/README.md` edit).
30. [engineer-verified: "Ask the architect I don’t know how to answer this"] Asked whether the null clause reads as an interval covering zero or as a gap below a run-to-run spread figure, the engineer left the choice to the architect. The quote covers only that delegation, and row 26 records the choice.
31. [engineer-verified: "Proceed anyway"] Asked whether to split a plan that projects about 480 changed lines against a 400-line threshold, the engineer selected this label. The plan ships as one PR.
32. [verified: the real-git known-gap tests in `evals/test_replay_bench_comment_metrics.py` run through `_measure_change`, which pin items 1, 2, 3 and 5 of Approach's "Rewrites count as new"; item 4, the one-line-definition case, is pinned by a unit-layer row] The plan accepts these as residuals and pins them as known gaps. A multi-line docstring with one changed line counts nothing, pinned by a unit-layer row.
33. [engineer-verified: "Follow the architect (Recommended)"] Asked about this round's two added test files and the diff growth from about 480 to about 650 lines, the engineer selected this label, which is the session's option, after asking "Does the architect agree or disagree?". The architect's recommendation, the session's relay of it, was to keep one PR at the larger size and drop both added test files, whose assertions compare a producer's key to the test's own literal. The end-to-end summary test covers key drift. The plan ships as one PR at about 600 lines, without those files.

## Critical files

Two `code-writer` dispatches, run in sequence because the second reads the record key the first writes. Both run Verification steps 1 and 2.

Dispatch 1, measurement:
- `evals/review_bench/mine_szz.py`: add `_python_docstring_owners(source, *, stats=None)`, moving today's `stats` increments, warning-silenced `ast.parse`, `split("\n")` and walk out of `_python_docstring_lines`. Each element pairs a module, class or function node with `_docstring_lines_without_shared_code`'s range, or None when the node has no docstring. It returns an empty list when the parse fails. `_python_docstring_lines` keeps its signature and results and becomes the union of the non-None ranges.
- `evals/replay_bench/comment_metrics.py`:
  - `PythonDefinitionCounts`, a frozen dataclass of four ints that default to 0: `new_docstrings`, `new_docstring_words`, `new_definitions`, `documented_new_definitions`.
  - `FileClassification.python_definition_counts`, defaulting to `PythonDefinitionCounts()`.
  - `_classify_python` calls `_python_docstring_owners` once, and never also calls `_python_docstring_lines`, so the parse attempt is counted once.
    - It derives the docstring line set from the owners and computes the words once.
    - It passes owners, added lines and words to a new `_python_definition_counts`, which applies Approach's two rules.
    - `_python_definition_counts` skips `ast.Module` as its own rule.
    - `tasks._base_density` also reaches this code through `classify_file` and discards the counts.
  - `CommentMetrics.python_definition_counts: dict[str, dict[str, int]] | None = None`, keyed by scope and then by the four field names. Its docstring gains one line: None means unmeasured, and `to_dict` then omits the key so the task set keeps its hash. `from_dict` reads the key with `.get`. When the key is present it reads both scopes and all four field names by subscript, with the names taken from `PythonDefinitionCounts`, so a malformed task set fails at read time as a `ValueError`.
  - `measure_diff` builds `CommentMetrics` with zeroed counts and adds each file's counts to its scope.
  - The comment at `:55-56` names `_python_docstring_owners`.
- `evals/test_review_bench_mining.py`: owners tests at the seam. The existing `_python_docstring_lines` tests pass unedited.
  - An undocumented function pairs with None.
  - A documented function pairs with its trimmed range.
  - A one-line docstring on its `def` line pairs with an empty range, distinct from None.
  - A module node is returned.
  - A parse failure returns `[]` and counts one attempt and one failure on `stats`.
- `evals/test_replay_bench_comment_metrics.py`, two layers:
  - Unit layer: one table-driven test over `classify_file` with explicit added-line sets, each case asserting the whole four-field tuple. A final assertion over every case checks `documented_new_definitions <= min(new_definitions, new_docstrings)`. The cases are:
    - a new function with a sectioned docstring, whose blank line adds no word;
    - a new function without a docstring;
    - a signature edit of a documented function, which counts nothing;
    - a decorator added to an existing function, which counts nothing;
    - a parameter added on a continuation line of a multi-line signature, which counts nothing;
    - a new function with a multi-line signature, which counts once;
    - a line added inside an existing docstring, which is no new docstring;
    - a docstring added whole to an existing function, which is a new docstring and no new definition;
    - a docstring added whole to an existing class, which is a new docstring and no new definition;
    - a one-line docstring on its `def` line, which is a new definition and no new docstring;
    - a multi-line docstring that starts on the `def` line, which counts a docstring whose first line adds no words;
    - a new module with a module docstring, which counts nothing;
    - a decorated new function, which counts once;
    - a new `async def` with a docstring, which counts once;
    - a method or inner function added to an existing class or function, which counts one definition;
    - a new class with a method, which counts two definitions;
    - an `ast.parse` rejection, which counts nothing.
  - Known-gap tests, named `..._a_known_gap` as the file's convention has it, pin Approach's rewrite residuals: items 1, 2, 3 and 5, each through real git, and item 4, the one-line-definition edit, at the unit layer.
  - Integration layer, real-git tests through `_measure_change`. The first pins that `measure_diff`:
    - feeds git's added lines into the rules;
    - assigns test-path files to test scope only;
    - sums across files;
    - counts a valid file beside a parser-rejected one.
  - The second integration test adds a function with a one-line body under both diff flag sets (`tasks.py:69`, `diffing.py:21`) and pins whatever git reports (row 21).
  - `test_an_empty_change_measures_to_all_zero` now expects a literal zeroed dict of both scopes and the four field names, not `CommentMetrics()` and not a call to the production zeroing code.
  - The round-trip test gains a populated case beside the existing zero-count fixture, showing the counts survive `from_dict`, `to_dict` and `json.dumps`.
  - A frozen-literal test holds a pre-change task dict copied from `main` and its `task_set_hash` captured once from `main`. It asserts `ReplayTask.from_dict(frozen).to_dict() == frozen` and the hash, and its docstring names the incident it prevents: every in-flight campaign refusing to resume on a changed `task_set_hash`.
  - A `from_dict` test shows a present key missing a scope or field raises `ValueError` through `ReplayTask.from_dict`.

Dispatch 2, summary and docs:
- `evals/replay_bench/summary.py`:
  - Rename `_ArmCounts.code_lines` to `denominator` at `:35`, `:39`, `:65`, `:73` and `:239`.
  - `_mean_counts_per_run` gains `run_denominator`, defaulting to `_run_code_lines`.
  - `_arm_docstring_counts` becomes `_arm_counts(task_records, arm_name, run_numerator, run_denominator=_run_code_lines)`, and the existing secondary outcome calls it.
  - `_interval_and_drops_over_tasks` wraps `analysis.bootstrap_interval_with_drops` with today's singleton cluster map, and `_interval_over_tasks` returns its interval.
  - A two-row figure table, with stems `words per new docstring` and `share of new definitions with a new docstring`, and `_per_docstring_figure_lines(block_records, paired_ids, reference)`. `summarize` calls it once after the existing secondary's per-task loop (`:331-335`) with `paired_ids` from `:317`.
  - Each figure prints a header line beginning `additional secondary outcome:`, then `  toolkit <stem>:`, `  bare <stem>:`, `  reference (the merged commits) <stem>:` and `  <stem>, toolkit - bare:`. A value prints as a number, `n/a` (no paired task, a zero pooled denominator, or an unavailable reference), or `not measured` with the count of paired tasks lacking the counts. The difference line appends the dropped-resample count.
  - The figure code reads the four field names from `PythonDefinitionCounts`, not from string literals.
- `evals/test_replay_bench_summary.py`:
  - `metrics()` gains `definitions=None`, a dict of non-test and test counts. None leaves the key out, as every existing caller expects. `reference_task` gains the same parameter.
  - Fixtures give the four fields distinct values and nonzero test-scope counts, so a field swap or a test-scope read fails. One fixture has more new docstrings than new definitions, so a numerator wired to docstrings would print a share above 1.
  - New tests:
    - each figure is a ratio of sums over per-run means;
    - the `toolkit - bare` sign is pinned with a literal, toolkit below bare printing a negative value;
    - an unpaired task and a no-code task enter neither figure, and a failed run (`metrics is None`) never makes a figure `not measured`;
    - one paired task with `k=2` in one arm, run 0 carrying the counts and run 1 not, prints `not measured` for that arm and its difference while the other arm keeps its figure;
    - the reference reads a task set carrying the counts, prints `not measured` for an entry without them, and prints `n/a` when the reference is unavailable or lacks the task;
    - an arm with no new docstring in any paired task prints `n/a`;
    - a two-task fixture with no new docstring in one arm prints a dropped-resample count between 2,000 and 3,000, parametrized over which arm is empty and over which figure, plus a drop-free fixture printing 0;
    - the primary outcome's lines, sliced from `primary outcome:` through the last `  excluded,` line, are non-empty and identical across two campaigns with the same words and code metrics, one carrying nonzero counts;
    - one end-to-end test builds a record and a task set, read back through `ReplayTask.from_dict`, from real `measure_diff(...).to_dict()` output and shows `summarize` prints a measured figure for the arms and the reference, so a key or scope drift between producer and reader fails.
  - The all-resamples-dropped message is unreachable with a real fixture, because a two-task resample equal to the original multiset has a defined statistic. The plan therefore prints the dropped-resample count and names no such message, and an undefined interval prints `n/a` as it does today.
- `evals/README.md`:
  - A paragraph after the secondary-outcome paragraph (`:1512-1520`). It defines both figures by Approach's rules and points to the primary's reading guide (`:1495-1507`) for pooling rather than restating it. It states the `n/a` and `not measured` cases, the interval and drop count, and that no threshold applies. It says "added or rewritten" and names all five rewrite residuals and the silent omission of parser-rejected files.
  - The reading rule as Approach words it: the null clause first, then the sign, then the caveat that an effect on only some tasks can read as a null, with a pointer to rows 26 and 30 left out of the README.
  - The sentence at `:1535-1536` also names `.claude/plans/replay-bench-per-docstring-metrics.md` as the design of these figures.

Reuse, not reimplement: `_docstring_lines_without_shared_code`, `_comment_words`, `_valid`, `_ratio_of_sums`, `_pooled_ratio`, `_number`, `analysis.bootstrap_interval_with_drops`, and the test helpers `_measure_change`, `metrics()`, `reference_task`, `Campaign` and `number_after`.

Consulted, not edited: `claude/.claude/scripts/select-tests.py`, `evals/replay_bench/tasks.py`, `evals/replay_bench/smoke.py`.

Projected diff: about 600 lines, up from the about 480 the engineer answered "Proceed anyway" to, after this round's added tests (row 33).

## Verification

1. `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py` passes. Its selection is the set row 29 names, including `claude-skills/skills/tests` for the README edit.
2. `scripts/venv-run.sh ruff check claude/.claude/ claude-skills/ plugins/ evals/` reports nothing.
3. `git diff main...HEAD -- evals/replay_bench/summary.py` changes no line inside `paired_outcome`, `run_spread` or the primary printout, which runs from the `primary outcome:` line through the `excluded,` loop. `git diff main...HEAD -- evals/test_replay_bench_summary.py` edits no existing test body. That diff check covers only those regions. The existing primary-outcome tests in step 1 guard the helper rename, since `_mean_counts_per_run`, `_ratio_of_sums` and `_reference_pooled_ratio` sit outside them.
4. Among Dispatch 1 and 2's new tests, three carry the constraints: the frozen-literal task dict and hash hold, so existing task-set hashes hold; the primary outcome's lines stay identical with and without the counts; and the mixed-run `k=2` fixture prints `not measured`.
5. No step runs `run`, `smoke` or `summarize` against `.local/`, so no paid run happens and no campaign figure or task ID enters the PR or this plan.

## Out of scope

- Running or summarizing the Python campaign, any paid run, and any judge pass. The campaign runs after this change merges, so the reading rule exists before its output.
- Re-mining the Python task set so the reference lines report the new figures. A task set mined before this change prints `not measured` there. A re-mined set has a new task-set hash, so re-mining is the operator's choice before the campaign's first block.
- Applying the reading rule to the primary outcome or to the existing secondary outcome. On the primary it would set a second decision rule beside the 20% rule (G2, row 25).
- Editing `.claude/plans/docstring-verbosity-experiment.md`. It is the merged record of the experiment's design, row 157 included, and this plan ships beside it as the record of this change (row 27).
- Docstring counts for languages other than Python, which the classifier gives no docstring class.
- `smoke` printing the new counts.
