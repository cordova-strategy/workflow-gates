# Sparse-findings remedy for the precision decision statistics (GH-1114, PR 2)

## Context

Goal: stop finding-free fixtures from entering the precision sign-flip test and fixture t-interval, by dropping them inside `precision_fixture_terms`, and pin that rule with tests. Whether the statistics then reach nominal rates in the sparse regime is not measured here.

Ask: "Let's do option 2" (the PR 2 follow-up to #1583), and, when asked how much PR 2 should cover, "Ask an architect". The scope below is the architect consult's recommendation, which is the session's proposal rather than the engineer's words.

#1565 added the decision statistics and #1583 added `calibrate`, which measures their false-adopt and power rates on synthetic data. `precision_fixture_terms` (`evals/review_bench/analysis.py:574`) keeps a fixture that has present defects but no finding in either arm, so it counts in the fixture count F and the mean totals. Its residual is exactly 0 and its `null_centered` value is the constant estimate + delta. When every finding sits in one fixture, the interval has zero width and the sign-flip p is 1, so the statistics never adopt. As more empty fixtures join a few informative ones, the plug-in constant dominates the flipped sums and the false-adopt rate is expected to leave its nominal level. The #1583 generator gives every arm at least one finding per fixture, so its rates do not describe this regime.

What this plan leaves to later PRs is in Out of scope.

Evidence from exploration, as evidence and not conclusions:
- `precision_fixture_terms` has no caller in `analysis.py` beyond its definition. Its other callers are `evals/review_bench/calibrate.py:453` and tests in `evals/test_review_bench_decision_statistics.py` and `evals/test_review_bench_calibrate.py`.
- `TestDegenerateTermsFromPrecisionCounts` in `evals/test_review_bench_calibrate.py` (around lines 360-413) pins the current degenerate behavior, including a zero-width interval, a constant `null_centered` and a sign-flip p of exactly 1.
- `review-ledger.sh render` printed no row for ledger row `7accfcdfc25a` (the zero-width guard test) on this branch.
- The docstring at `analysis.py:578-587` states the current rule, "stays in the fixture set", and has to change with the code.
- The row 26 algebra in `.claude/plans/decision-statistics-calibrate.md` was never run.
- The architect found that algebra's sign-flip claim wrong for m of 2 or more. That plan file is not edited here.

## Approach

`precision_fixture_terms` drops every fixture whose present defects carry no adjudicated finding in either `arm_x` or `arm_baseline`. The drop happens before any per-fixture sum or mean total is taken, so the returned terms are exactly those of a call on only the fixtures that carry findings. When fewer than two such fixtures remain, the function returns None, as it already does below two present fixtures. The tests that pinned the old keep-it-in-F behavior are rewritten or deleted to pin the new one. `analysis.py`'s row in the code-file-size exceptions table moves to the file's new line count.

Alternatives set aside:
- **Weight the plug-in by each fixture's finding volume** (row 26's second candidate in `.claude/plans/decision-statistics-calibrate.md`). An empty fixture's `null_centered` becomes 0, which the exact sign-flip ignores. The t-interval still keeps F − 1 degrees of freedom and the F(F − 1) divisor, though. The weighting also changes every non-empty fixture's `null_centered` whenever volumes differ, which moves the rates #1583's `calibrate` already measured.
- **Set only the empty fixtures' `null_centered` to 0.** It has the same t-interval gap.
- **Filter finding-free fixtures at each caller.** That would restate the membership rule in `calibrate.py` and again in the later `analyze` wiring. `precision_fixture_terms` already owns fixture-set membership through its absent-defect drop (`analysis.py:584`, `:590-594`).
- **A floor on fixtures with findings, alone.** It cannot bound the sign-flip's false-adopt rate, because every empty fixture's plug-in value is the same constant (Context). Out of scope records where a floor belongs.

### Assumption ledger

**Root:** `precision_fixture_terms` keeps a fixture with no adjudicated finding in either compared arm, which distorts the t-interval and the sign-flip test by the mechanism Context states (`analysis.py:585-586`, `:616-625`). This PR removes such fixtures from the terms. It changes no verdict the bench produces today, because `analyze` does not call the function (row 3).

**Givens:**
- G1. For m values with m up to `SIGN_FLIP_EXACT_MAX_FIXTURES` (20, `analysis.py:47`), the exact sign-flip test's smallest p-value is 1/2^m. Above that cap, `sign_flip_p_value` takes the Monte Carlo path, whose smallest p-value is 1/(resamples + 1) (`analysis.py:516`). Reason: the method imposes it, since the exact path divides a count of sign patterns by 2^count (`analysis.py:507-508`).
- G2. Test data and any recorded `calibrate` output are synthetic, with no per-project dimension. Reason: the repository `CLAUDE.md`'s "Redact private-project-identifying content" governs every artifact, and changing that rule is outside this plan.

**Mechanisms:**
- **M1.** Extend the fixture comprehension at `analysis.py:590-594`. A fixture is kept only when its present defects are non-empty and at least one of them has a nonzero `total_by_arm` entry for `arm_x` or `arm_baseline`. A nested predicate, such as `carries_a_finding(fixture_defect_ids)`, names that test. Rename `present_fixtures` to `fixtures_with_findings` at each use (`:590`, `:595`, `:600`, `:603`, `:613`, `:614`). Every line after the filter stays as it is, so the terms equal a call on only the kept fixtures' defects by construction.

  anchors: root, row1, row2
- **M2.** In the docstring, merge the two fixture bullets at `:584-586` into one and delete the zero-width bullet at `:587-588`. Prescribed bullet: `- A fixture with no present defect, or no adjudicated finding in arm_x or arm_baseline, is dropped from the fixture set, so it counts in neither the degrees of freedom nor the mean totals.`

  anchors: row1, row5
- **M3.** Tests in `evals/test_review_bench_decision_statistics.py`. `_exact_precision_terms` (`:523-549`) stays unchanged (row 13).
  - Replace `test_a_fixture_with_no_finding_in_either_arm_still_counts_as_a_fixture` (`:626-636`) with `test_a_fixture_with_no_finding_in_either_arm_is_dropped`. Parametrize it over two finding-free shapes for `d1`: all four counts 0, and findings only under a third arm key. Each case calls the function on `d1`, `d2` and `d3`, and asserts three things:
    - The call returns two residuals.
    - The call compares `==` to the call on `d2` and `d3`, the exact-equality pattern of `test_a_fixture_of_only_absent_defects_is_dropped_from_the_fixture_count` (`:662-676`). `FixtureTerms` equality covers the estimate, the residuals and `null_centered`. The residual count sets `fixture_t_interval`'s degrees of freedom (`analysis.py:632-635`).
    - The call's estimate, residuals and `null_centered` match, by `pytest.approx`, `_exact_precision_terms` called on the `d2` and `d3` counts alone.
  - Parametrize `test_a_fixture_with_no_finding_in_one_arm_beside_a_nonzero_pool_still_counts_as_a_fixture` (`:614-624`) over three kept shapes for `d1`, and rename it `test_a_fixture_with_a_finding_in_a_compared_arm_still_counts_as_a_fixture`. The shapes are findings in arm X only `(3, 4, 0, 0)`, findings in the baseline only `(0, 0, 3, 4)`, and findings in both arms that are all invalid `(0, 3, 0, 2)`. Its assertions stay as they are: three residuals, and an estimate and residuals that match the oracle.
  - Add `test_a_finding_free_defect_beside_one_with_findings_keeps_its_fixture`. Its counts put a defect `d0` with all four counts 0 ahead of `UNEQUAL_FIXTURES` (`:553`). `d0` takes `d1`'s cluster, as `:681` does for an absent defect. The call takes `list(counts)`, so that fixture's first defect is finding-free and its second carries findings. The test asserts three residuals, and an estimate and residuals that match `_exact_precision_terms` on all the counts. A predicate that reads all of a fixture's defects, or only its first, drops the fixture and fails the test.
  - Replace `test_every_finding_in_one_fixture_gives_zero_residuals_and_a_zero_width_interval` (`:638-647`) with `test_every_finding_in_one_fixture_gives_none`, on the same counts and clusters.

  anchors: row1, row2, row13, row14
- **M4.** In `evals/test_review_bench_calibrate.py`:
  - Delete `TestDegenerateTermsFromPrecisionCounts` (`:360-413`). All three of its cases put every finding in one fixture. That now gives None, an undefined replicate, which `test_missing_terms_are_undefined_and_not_adopted` (`:321-327`) already covers.
  - Add `test_a_p_value_equal_to_alpha_adopts_by_the_sign_flip` to `TestDecideReplicate` (`:303`), to keep the deleted class's p = alpha case (row 15). It calls `calibrate.decide_replicate` on `_terms(0.0, [0.01, -0.01] * 3, DELTA)` with `alphas=(0.025, 1 / 64, 0.0125)`. The six `null_centered` values are 0.06 and 0.04, all positive. It asserts `p_value == 1 / 64` and `sign_flip_adopts == (True, True, False)`.

  anchors: row4, row8, row15
- **M5.** In `code-file-size-exceptions.toml`, act on every line `test_code_file_sizes` prints for a file this branch changed, after Verification step 1's fetch and any merge. A line asks for one of three edits: write the printed ceiling, remove the row, or add a row (row 11). Edit no row for a file this branch did not change, such as `evals/run_review_bench.py` (row 12).
  - The expected line is for `evals/review_bench/analysis.py`, whose row is at `:496-497`. If the check prints no line for it, its count did not change and the row stays.
  - If `analysis.py` grows, take the check's third remedy and write the printed ceiling. Its first remedy would move the membership predicate out of `precision_fixture_terms`, the function that owns membership. Its second would split the file along the row's seam (Out of scope).
  - If the check prints an under-limit line for `evals/test_review_bench_calibrate.py`, remove that file's row (row 12).
  - `evals/test_review_bench_decision_statistics.py` has 848 lines and no row. M3 keeps it under 1,000 lines, so the check prints no line for it.

  anchors: row11, row12

**Rows:**
1. Dropping leaves the estimate, residuals, `null_centered` and degrees of freedom bit-identical to a call on only the m fixtures with findings. [verified: read of `analysis.py:354-359`, `:590-638`]
   - Estimate: a dropped fixture adds 0 to each of the four pooled sums, so `precision_x` and `precision_baseline` (`:611-612`) do not change.
   - Residuals and `null_centered`: the per-fixture and pooled sums are integer sums (`:598-605`), so summation order cannot change them. Floats first appear in the pooled precisions and the mean totals (`:611-614`). The mean totals divide by `len(fixtures_with_findings)`, which is m after the drop, as in the m-fixture call. `_fixture_groups` keeps first-appearance order (`:354-359`). So each kept fixture's float operations take the same operands in the same order, and the floats match exactly.
   - Degrees of freedom: `fixture_t_interval` takes them from `len(terms.residuals)` (`:632-635`). The sign-flip reads only `null_centered`.
2. "No finding in either arm" means zero total findings in both `arm_x` and `arm_baseline`. [verified: read of `analysis.py:598-612`, `evals/test_review_bench_decision_statistics.py:573-595` and `evals/test_review_bench_analysis.py:20-23`]
   - A fixture is kept when any one of its present defects carries a finding in a compared arm, because the sums at `analysis.py:598-605` are taken per fixture.
   - A single-defect fixture, which `_own_fixture_each` builds (`test_review_bench_analysis.py:20-23`), cannot tell that rule from one that reads all of a fixture's defects or only its first. So M3 adds a two-defect case.
   - A fixture with findings in one arm only stays in the set. Dropping it would remove its counts from that arm's pooled precision and break estimate = `precision_difference`, which `:588` of the test file asserts. Its residual is in general nonzero.
   - A finding under any other arm key does not keep a fixture, because only the two compared arms enter the sums (`analysis.py:598-608`).
   - A fixture whose findings are all invalid, with valid 0 and total above 0, stays in the set. The rule reads `total_by_arm`, not `valid_by_arm`. Dropping that fixture would remove its totals from the pooled denominators.
3. Nothing in `analysis.py` besides the definition calls `precision_fixture_terms`. The match at `:546` is a docstring mention inside `recall_fixture_terms`. The only non-test caller is `calibrate.py:453`. [verified: repo-wide Grep for `precision_fixture_terms`, this dispatch]
4. `calibrate.py` needs no edit, and its precision rows should not change. [verified: read, for the first three sub-bullets]
   - #1583's generator gives every fixture at least one finding per arm, as "1 + Poisson(expected volume)" (`calibrate.py:346-352`). So m = F on the existing regime.
   - `TestPlannedCellsReachTheirTrueDifference` (`test_review_bench_calibrate.py:677-690`) builds from that generator and is unaffected.
   - `decide_replicate`'s zero-width note (`calibrate.py:383-384`) still describes reachable terms. Kept fixtures whose per-arm precisions all equal their pools' give all-zero residuals.
   - That the output is byte-identical before and after is [unverified] until Verification step 3 runs.
5. No doc states the old rule, so `evals/README.md` is not edited. [verified: Grep of every `*.md` for fixture terms, `t-interval` and `sign-flip`, and a read of `evals/README.md:1174-1180`, this dispatch]
   - The only `evals/README.md` match is `:763`, the `calibrate` command's comment, which states no fixture rule.
   - `:1174-1180` describes `analyze`'s nulls and bootstrap drops, not fixture terms.
6. This edit changes the harness closure manifest hash, and that breaks nothing in the tree. [verified: reads, Grep and Glob, this dispatch]
   - `analysis.py` is a closure member (`test_review_bench_analysis.py:401-404`, `evals/README.md:1035`).
   - No test pins a literal hash. A Grep of `evals/` for a 64-hex-digit literal found none, and the closure tests compute the hash live.
   - No `conditions.json` or `results/baseline.json` exists under `evals/review_bench/`.
   - A smoke campaign run before this merges would fail `freeze`'s manifest precondition (`analysis.py:1255-1258`) and need a rerun. That is the intended invalidation. Whether any such campaign exists is [unverified].
7. Sibling audit: no other statistic has the plug-in shape this PR removes. [verified: read of `analysis.py:542-546`, `:567-570`, `:367-369`]
   - `recall_fixture_terms`' `null_centered` is exact, not a plug-in, and a fixture both arms miss is an observed difference of 0.
   - `bootstrap_interval_with_drops` resamples all F fixtures but fabricates no per-fixture value. Whether its own sparse-regime rates are nominal is [unverified] and not this PR's.
8. Deleting `TestDegenerateTermsFromPrecisionCounts` follows that class's own docstring, which says a change to how `precision_fixture_terms` treats finding-free fixtures "is expected to change these results" (`test_review_bench_calibrate.py:361-364`). [verified: read] Ledger row `7accfcdfc25a` (DEFER, zero-width guard test, from #1565) is unread, so this plan neither claims to close it nor depends on it. [unverified: the row's text] The one case the deletion would leave untested moves to `TestDecideReplicate` (row 15).
9. Whether the m-fixture statistics reach nominal false-adopt rates at small m is unmeasured. At m ≤ 5 the exact sign-flip cannot reach p ≤ 0.025, since 1/2^5 = 1/32 (G1). Measuring it belongs to the sparse sweep (Out of scope). [unverified]
10. The scope, the drop inside `precision_fixture_terms` with the exclusions Out of scope lists, is the recommendation of the architect consult that Context's Ask paragraph names. This dispatch re-derived that scope and endorses it. [unverified: the consult's recommendation, which is session content]
11. The code-file-size check fails on any file with a row whose line count differs from its ceiling, by even one line. [verified: reads of `claude/.claude/tests/code_file_size.py`, `claude/.claude/scripts/select-tests.py:202-208` and the table, and a Grep line count of `analysis.py`, this dispatch]
    - The rule is `evaluate` (`code_file_size.py:337-353`), which reports an over-ceiling or under-ceiling line.
    - The check also asks for a row added for a file over 1,000 lines that has none (`code_file_size.py:363-370`).
    - It asks for a row removed for a file at or under 1,000 lines that has one (`code_file_size.py:377-381`).
    - `select-tests.py` selects the check for a change to any tracked `.py` file.
    - The check counts working-tree files, so an unstaged edit counts (`code_file_size.py:171-181`).
    - `code-file-size-exceptions.toml:496-497` holds `analysis.py` at `ceiling = 1303`, its current line count. So M1 and M2 move it unless their net line change is 0.
    - The check's message says to merge `origin/main` and rerun before writing a printed value, because CI counts the branch merged with main (`code_file_size.py:53-56`).
12. At this branch's base, the check already fails on lines for files this branch does not change. [verified: Grep line counts of the three files named below against the table, this dispatch; the check itself was not run]
    - The branch head and the local `origin/main` ref both hold `f133812f` (a read of the worktree's git refs), so the unedited tree is the base.
    - Two such lines are for `evals/run_review_bench.py`, at 2421 lines against a ceiling of 2351 (`code-file-size-exceptions.toml:506-507`), and `evals/test_review_bench_mining.py`, at 6248 against 6217 (`:576-577`).
    - The full line set is whatever the check prints. Plan-review round 2 replayed the check's own functions read-only on `f133812f` and reported eleven lines: ten for files this branch does not change, and one for `evals/test_review_bench_calibrate.py`. [unverified: not rerun by this dispatch, which has no shell]
    - `evals/test_review_bench_calibrate.py` has 1007 lines and no row, a no-row line. M4 removes about 46 lines net, so the file falls under the 1,000-line limit and its line clears.
    - If a merge in Verification step 1 brought a row for that file, M4 instead turns the row into an under-limit line, which M5 removes.
    - This PR's required `tests` check stays red on the lines for unchanged files until a fix for main's lines merges (`code_file_size.py:91`).
13. Leaving `_exact_precision_terms` unchanged keeps the drop tests' oracle independent of the drop rule. [verified: read of `evals/test_review_bench_decision_statistics.py:523-549`]
    - It groups through a dict over `counts` and computes in `Fraction`s, so it shares no code with `precision_fixture_terms`.
    - Called on the kept subset, it checks the post-drop arithmetic. The `==` assertion cannot, because it compares production with production.
    - Set aside: a drop branch inside the oracle. It would restate the production rule inside the check of that rule, and no current input runs it (row 14). Making it run would need the randomized test to draw finding-free fixtures, which changes what seeds 0-4 draw.
14. No input of the randomized test's seeds 0-4 (`test_review_bench_decision_statistics.py:572-595`) holds a finding-free fixture, so the unchanged oracle still matches production there. [unverified: plan-review's replay of the seeds' draws, not rerun this dispatch] A seed that did hold one would fail Verification step 2 on residual count, not pass silently.
15. `decide_replicate`'s inclusive `p_value <= alpha` (`calibrate.py:394`) has one test at equality: the p = 1/64 case of `TestDegenerateTermsFromPrecisionCounts` (`test_review_bench_calibrate.py:400-406`). [verified: Grep of `evals/test_*.py` for `p_value` and `sign_flip_adopts`, and a read of `test_review_bench_calibrate.py:303-358`, this dispatch]
    - No `TestDecideReplicate` case gives a p-value equal to one of its alphas, 0.025 and 0.0125.
    - Six strictly positive `null_centered` values give p = 1/64 exactly on the exact path (G1). Flipping any one of M4's values lowers the sum by at least 0.08, far past the tie tolerance (`analysis.py:50-53`), so no other pattern ties.

## Critical files

- `evals/review_bench/analysis.py`: M1 and M2. Reuse `_fixture_groups` (`:354`) as it is.
- `evals/test_review_bench_decision_statistics.py`: M3.
  - Reuse `_precision_counts_by_defect` (`:510`), `_exact_precision_terms` (`:523`) unchanged, `UNEQUAL_FIXTURES` (`:553`), `_own_fixture_each` (imported at `:17`), the exact-equality pattern at `:662-676` and the shared-cluster pattern at `:681`.
  - Build the third-arm shape as an `analysis.DefectPrecisionCounts` directly, because `_precision_counts_by_defect` writes only `ARM_X` and `ARM_BASELINE`.
  - Name the third arm with a test-local constant, because `evals/review_bench/arms.py:15-16` defines only the two compared arms.
- `evals/test_review_bench_calibrate.py`: M4. Reuse `_terms` (`:42`) and `DELTA` (`:24`).
- `code-file-size-exceptions.toml` at the repository root: M5, on rows of files this branch changes, expected to be the `analysis.py` row alone.
- This plan file.

Dispatch split: one `code-writer` dispatch for all four files. The tests pin the rule that the code change states, and the table's value depends on the code change's final line count, so a split would restate that context in each prompt.

Projected diff: about 175 lines, made of about 32 in `analysis.py`, 2 in the table, about 77 in the decision-statistics tests, and about 66 in the calibrate tests (56 deleted, about 10 added).

## Verification

1. Before the `code-writer` dispatch, on the unedited tree:
   - Run `git fetch origin main`. If `origin/main` has moved past `f133812f`, merge it into the branch first, so every later step counts against the base CI uses (row 11).
   - Run `scripts/venv-run.sh pytest claude/.claude/tests/test_code_file_size.py::test_code_file_sizes` and keep every line it prints. The branch changes no code file yet, so this run is the merge-base reproduction that `CLAUDE.md`'s "Prove your change caused a failing check" bullet asks for. Its line set is whatever the check prints, with no fixed count expected (row 12).
   - Capture `calibrate`'s precision output: `scripts/venv-run.sh python3 evals/run_review_bench.py calibrate --metric precision --k 10 --fixtures 6 --fixtures 12 --replicates 200 --out evals/review_bench/.local/calibrate-precision-before.json`. If this capture is missed, run the same command from a merge-base worktree, made by the recipe in that same `CLAUDE.md` bullet, with `--out` naming this worktree's `.local/` path. It runs no model and spends nothing, and its output stays under the gitignored `evals/review_bench/.local/` (`.gitignore:48`).
2. Run the two commands below. Each passes as its item states:
   - `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py` passes, except for `test_code_file_sizes` lines that step 1 also printed for a file this branch did not change. Out of scope's first bullet governs those lines.
   - `scripts/venv-run.sh ruff check evals/` is clean.
3. After the edit, rerun step 1's `calibrate` command with `--out evals/review_bench/.local/calibrate-precision-after.json`. Then `cmp evals/review_bench/.local/calibrate-precision-before.json evals/review_bench/.local/calibrate-precision-after.json` prints nothing and exits 0.
   - This proves only that the no-drop path is unchanged, because the generator gives every fixture a finding in both arms (row 4).
   - Only M3's unit tests exercise the drop.
4. `git diff --stat --merge-base origin/main` lists no file besides the three `.py` files in Critical files, `code-file-size-exceptions.toml` and this plan file. It shows the plan file only once git tracks it, and the table only when M5 edited it. `git diff --merge-base origin/main -- code-file-size-exceptions.toml` changes only rows of files this branch changed.

## Out of scope

- **Main's failing size-check lines**, the lines the check prints for files this branch does not change (row 12). This branch edits no row for such a file. The check's did-not-change procedure owns them (`code_file_size.py:67-92`). Under it, the session reports every such line to the engineer. A separate `code-file-size row fix` PR from `origin/main`'s tip opens only on the engineer's go-ahead.
- **Splitting `evals/review_bench/analysis.py`** along its table row's seam (`code-file-size-exceptions.toml:499`).
- **The sparse generator and its sweep**, a `calibrate` parameter whose first m fixtures carry findings and the rest carry none in either arm. Design note for that PR: `calibrate.sign_flip_path`, `smallest_sign_flip_p_value` and `CalibrationConfig`'s alpha guard all key on the planned fixture count (`calibrate.py:83-92`, `:131-141`, `:247-253`). Once a replicate can hold finding-free fixtures, they need to key on the fixtures with findings.
- **Wiring the terms into `analyze`**, with its report, verdicts, floors and constants. Design note for that PR: after the drop, the exact sign-flip's smallest p-value is 1/2^m for m fixtures with findings (G1). So a floor must count fixtures with findings, not F.
- **Raising `SIGN_FLIP_EXACT_MAX_FIXTURES`** (`analysis.py:47`).
- **Editing `.claude/plans/decision-statistics-calibrate.md`**, including its row 26 algebra, which was never run.
