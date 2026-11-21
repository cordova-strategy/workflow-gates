# Review-bench decision statistics and calibration tooling

## Context

Goal: give the review benchmark the small-sample decision statistics and the calibration tool that the agreed decision rule needs, as tooling only, with no change to any verdict the benchmark can produce today.

Ask: "yes begin" — the engineer's answer to the session's question "shall I begin PR 1?", where PR 1 was the architect's first step: new statistic functions in `evals/review_bench/analysis.py`, a `calibrate` subcommand, tests and a README line, changing no verdict.

The review benchmark (`evals/review_bench/`) decides whether a capacity-aware read rule may replace "read every changed file fully" for reviewer agents. Its interval for the recall difference is a percentile cluster bootstrap. Synthetic simulations run in this session, using no model, showed that statistic falsely adopts a rule that is 5 percentage points worse more often than its nominal 2.5%, at 15 to 40 fixtures. A sign-flip test on per-fixture differences and a per-fixture linearized t-interval held nearer the nominal rate, and the same holds for pooled precision, a ratio. The decision rule built on them (margins, floors, two error-budget slots, a ledger) lands in a later PR whose constants depend on calibration runs this PR makes possible. The decision record is `~/.local/state/gh1114-src/decision-record-2026-11-20.md`, and the simulation drafts `gh1114-sim3.py` and `gh1114-sim4.py` sit in the same directory. The drafts live outside the repo; port them, do not copy.

Scope: new stdlib-only decision functions in `analysis.py` (sign-flip test on per-fixture differences, per-fixture linearized pooled-precision difference with a t-interval and a sign-flip test), a parameterized `calibrate` subcommand that imports those production functions and runs synthetic scenarios, tests, and a README usage line. Not in this PR: the ledger, gate logic, constants changes, the case study, the skill, any edit to `.claude/plans/measure-review-quality.md`.

## Approach

Add standard-library-only decision statistics to `evals/review_bench/analysis.py` that nothing in `analyze` calls yet. Add a `calibrate` subcommand whose new module, `evals/review_bench/calibrate.py`, feeds synthetic per-defect counts through those production functions and prints false-adopt and power rates. Recall and pooled precision are both treated as a ratio of per-fixture sums and linearized per fixture. That one shape feeds two statistics:
- a t-interval, using an exact Student t quantile for integer degrees of freedom;
- a one-sided sign-flip test of H0 "difference = −delta", exact by meet-in-the-middle enumeration up to 20 fixtures and a seeded Monte Carlo above that.

No existing verdict, constant, report field or `analyze` path changes (M6). Rows marked **(sizing)** say how this PR moves the pilot's smoke campaign and freeze.

Alternatives weighed:
- **The new functions in a new `review_bench/decision_statistics.py` that `analysis.py` does not import yet.** It would leave the closure hash unchanged in this PR, but PR 2 changes the hash anyway when `analyze` starts calling them (row 7). It would also split these statistics from `analysis.py`, whose charter covers them, and from the fixture-grouping helper they share with the bootstrap.
- **Equal weight per fixture for recall**, the mean of each fixture's mean difference. It is simpler. But when fixtures hold unequal defect counts it estimates a different quantity than the existing defect-weighted recall difference, so delta would change meaning (row 11).
- **Plug-in centering for recall too** (`residual + estimate + delta`, as precision uses). Recall has an exactly H0-centered per-fixture value, so the plug-in only adds approximation.
- **The t quantile by other means.** See M2's over-powered check.
- **Calibrate on raw arrays, as the drafts do.** It would measure a copy of the statistics, not the functions PR 2 gates on.
- **The calibrate CLI test in `evals/test_review_bench_cli.py`.** That file is 7,124 lines and its docstring lists the subcommands it covers. `cmd_calibrate` is a thin adapter over `calibrate.py`, so its test sits with calibrate's own (row 19).

### Assumption ledger

**Root:** The bench's only decision statistic, a percentile cluster bootstrap, falsely adopts a rule 5 points worse more often than its nominal 2.5% at 15 to 40 fixtures (Context). PR 2 cannot set the decision rule's constants until the agreed replacement statistics exist, along with a tool that calibrates their error rates on synthetic data. Adding them must change no verdict the bench produces today.

**Givens:**
- G1. The bench's statistics use the standard library only. Reason: a numerical dependency needs the engineer's named-package confirmation under `CLAUDE.md`'s Safety rules, a decision outside this plan, and `analysis.py:1-3` states the constraint (row 4).

The frozen-conditions design is a condition the plan could change and deliberately does not: `freeze` and `analyze` hash `analysis.py` and every first-party module it imports (rows 6 and 7). `bootstrap_interval`'s signature and draws are another: `evals/replay_bench/summary.py:180` relies on them (row 9). Out of scope lists both.

**Mechanisms:**
- **M1.** Add constants after `BOOTSTRAP_SEED` (`analysis.py:46`): `SIGN_FLIP_EXACT_MAX_FIXTURES = 20`, `SIGN_FLIP_RESAMPLES = 100_000`, `SIGN_FLIP_SEED = 0`, and `_SIGN_FLIP_TIE_TOLERANCE = 1e-9`. The tolerance is a fraction of the sum of the values' magnitudes. Its one-line comment: a sign pattern whose sum ties the observed sum in exact arithmetic counts as at least as extreme despite float rounding. The comment adds that a value below about 5e-10 of the sum of magnitudes also counts as a tie, which is harmless for rate-valued inputs.

  anchors: row2, row8
- **M2.** `student_t_upper_quantile(df: int, upper_tail: float) -> float` returns t with P(T_df > t) = upper_tail. It accepts integer df >= 1 and 0 < upper_tail < 0.5, and raises ValueError otherwise.
  - A private `_student_t_central_probability(t, df)` gives P(|T| < t) by the finite trigonometric series for integer df, with θ = atan(t / √df):
    - df = 1: 2θ/π.
    - Even df: sin θ · Σ c_j cos^(2j) θ for j = 0 … df/2 − 1, with c_0 = 1 and c_j = c_(j−1) · (2j − 1)/(2j).
    - Odd df ≥ 3: (2/π) · (θ + sin θ cos θ · Σ d_j cos^(2j) θ) for j = 0 … (df − 3)/2, with d_0 = 1 and d_j = d_(j−1) · 2j/(2j + 1).
  - The quantile brackets t by doubling from 1, then bisects to float resolution. Both loops are bounded: a tail whose 1 − 2·alpha rounds to 1.0 raises ValueError.

  Over-powered check. Hand-rolled numerics in a standard-library-only module are the heavier choice. Each lighter primitive fails:
  - **The standard library's `statistics`:** it has no t distribution (row 5).
  - **Sign-flip only, no t-interval:** the agreed design reports the t-interval beside the sign-flip (row 2), and calibrate must compare the two for precision (row 3).
  - **A table of critical values:** alpha is a calibrate parameter and df follows the fixture grid, so any table is incomplete. Each entry is also a literal that needs a source.
  - **`NormalDist` plus a Cornish–Fisher correction:** it is approximate, about 0.003 low at df 4 and one-sided 0.0125 by the architect's hand calculation. It also carries four coefficient polynomials that need their own citation.
  - **The draft's regularized incomplete beta by continued fraction** (`gh1114-sim3.py:28-79`): it serves real-valued df, which never occurs here (df = fixtures − 1). It costs an iteration cap, a convergence tolerance and an underflow guard to justify.

  anchors: row2, row3, row4, row5, row12
- **M3.** `sign_flip_p_value(values, *, resamples=SIGN_FLIP_RESAMPLES, seed=SIGN_FLIP_SEED) -> float` returns the one-sided p-value for H0 "values are symmetric about 0" against a positive mean.
  - The statistic is the plain sum (row 8).
  - A sign pattern counts when its flipped sum is at least the observed sum minus the M1 tolerance.
  - Empty `values` and any non-finite value raise ValueError, so both paths behave alike. A NaN would otherwise make the Monte Carlo path adopt.
  - Up to `SIGN_FLIP_EXACT_MAX_FIXTURES` values the test is exact, with p = count / 2^F. It meets in the middle: enumerate each half's partial sums, sort one half, and count each other-half sum's qualifying partners with `bisect`. At F = 20 that is 2,048 sums and 1,024 bisections. A direct loop over 2^20 patterns is about 21 million additions per call, too slow for thousands of calibrate replicates.
  - Above that count it uses `random.Random(seed)`. Each flip draws one `getrandbits(F)`, whose bits set the signs in the order of `values`. p = (1 + count) / (resamples + 1), so p is never 0.
  - The exact path does not use `seed`.

  anchors: row2, row8, row20
- **M4.** `FixtureTerms` is a frozen dataclass of `estimate: float`, `residuals: tuple[float, ...]` and `null_centered: tuple[float, ...]`, one tuple entry per fixture. Two builders make it, in the verdict functions' parameter order: `recall_fixture_terms(recall_counts_by_defect, defect_ids, arm_baseline, arm_x, *, cluster_by_defect, delta=DELTA)` and `precision_fixture_terms(precision_counts_by_defect, defect_ids, arm_baseline, arm_x, *, cluster_by_defect, delta=DELTA)`. Each returns None with fewer than two fixtures, the bootstrap's bar.
  - Fixtures come from a new `_fixture_groups(defect_ids, cluster_by_defect) -> list[list[str]]`. It is the grouping at `analysis.py:365-368`, moved unchanged. `bootstrap_interval_with_drops` calls it, so the bootstrap's draws do not change (row 9).
  - Recall: for fixture f, S_f is the sum over its defects of `detection_rate(arm_x) − detection_rate(arm_baseline)`, and n_f is its defect count. n̄ = D / F.
    - `estimate` = ΣS / Σn, which equals `recall_difference(…, arm_x, arm_baseline)`.
    - `residuals` = (S_f − estimate · n_f) / n̄.
    - `null_centered` = (S_f + delta · n_f) / n̄, the exactly H0-centered value. With one defect per fixture it is the per-defect difference plus delta, the drafts' value.
  - Precision: for each fixture and arm, sum `valid_by_arm` and `total_by_arm` over its defects. Skip a defect ID absent from the counts, as `pooled_precision` does (row 13). A fixture left with no present defect is dropped before F is counted, so it does not enter F, the degrees of freedom or the mean totals. Return None when either arm's total is 0.
    - p_a = Σv_a / Σt_a and t̄_a = Σt_a / F for each arm a.
    - `estimate` = p_x − p_baseline, which equals `precision_difference`.
    - `residuals` = (v_x,f − p_x · t_x,f) / t̄_x − (v_b,f − p_b · t_b,f) / t̄_b.
    - `null_centered` = residual + estimate + delta, the drafts' plug-in.

  anchors: root, row9, row10, row11, row13
- **M5.** `fixture_t_interval(terms, *, alpha_one_sided=ALPHA_ONE_SIDED) -> tuple[float, float]` returns estimate ± `student_t_upper_quantile(F − 1, alpha_one_sided)` · √(Σ residual² / (F (F − 1))). It is the two-sided 1 − 2α interval, matching how the bootstrap's `confidence` default pairs with `ALPHA_ONE_SIDED` (`analysis.py:350`). A lower limit above −delta is therefore the one-sided test at α.

  anchors: row2, row10
- **M6.** No existing behavior changes. Besides the additions, `analysis.py` changes in two places:
  - M4's helper extraction.
  - The module docstring's parenthetical list of standard-library modules (`:2-3`), which M3's `bisect` would make stale. Drop the list and keep "Standard library only ... no numerical dependency".

  `analyze`, the verdict functions, `DELTA`, `ALPHA_ONE_SIDED` and every report field stay as they are.

  anchors: root, row1, row9
- **M7.** Add `evals/review_bench/calibrate.py`. Only `run_review_bench.py`'s handler imports it, so it stays outside the closure (row 6).
  - `CalibrationConfig` holds the metric (`recall` or `precision`), delta, alphas, fixture counts, k, harm (`normal` or `concentrated`), over-cap share, replicates, seed, workers and flips. It validates on construction and raises ValueError naming the field:
    - fixture counts >= 2;
    - 0 < alpha < 0.5;
    - 0 < delta < 1;
    - 0 < share <= 1;
    - k, replicates, workers and flips positive.

    Delta, alphas and flips default to `analysis.DELTA`, `(analysis.ALPHA_ONE_SIDED,)` and `analysis.SIGN_FLIP_RESAMPLES`.
  - A cell is one fixture count and one true gate-level difference: −delta for the false-adopt rate, then 0 for power.
    - In each replicate the first `max(1, floor(share · F + 0.5))` fixtures are acted on. The rule changes arm X only there; every other fixture's arm X equals its baseline.
    - The harm shift is solved per cell by bisection over 100,000 seeded draws. The acted fixtures' expected difference is set to target · F / acted, which makes the gate-level expectation the target. The draw-count constant's comment states its Monte Carlo error.
    - Every cell's shift is solved and checked before the first replicate runs. A target the bounded rates cannot reach raises ValueError naming the cell.
  - The generators port `gh1114-sim3.py`'s `recall_replicate` (`:129-141`) and `precision_replicate` (`:191-203`), one defect per fixture.
    - Precision's finding volume scales with K·λ, which is the draft's 10·λ at K = 10.
    - Normal harm is clip(p1 + shift + noise).
    - Concentrated harm drops 10% of acted fixtures to max(0, p1 − 0.5) and gives the rest normal harm, for both metrics. The draft modeled it for recall only.
    - Binomial counts may use `random.binomialvariate` (row 21).
    - Each scenario parameter is a named module constant with a one-line comment (row 14).
  - Each replicate builds `DefectRecallCounts` or `DefectPrecisionCounts` and a cluster map with one fixture key per defect. It then calls M4's builder, M5 once per alpha, and M3 on `null_centered` with `resamples=flips` and the default production seed.
    - The t-interval adopts when its lower limit is above −delta. The sign-flip adopts when p <= alpha.
    - A None from M4 counts as not adopted and as undefined. The per-replicate decision, from the terms to the adopt flags per alpha, is its own function, so tests can drive it with hand-built terms.
  - Each replicate seeds `random.Random` with a string built from the run seed, the cell's parameters and the replicate index, so output is the same for any worker count. Workers = 1 runs in process. Workers > 1 maps a top-level worker function over plain-tuple jobs with `concurrent.futures.ProcessPoolExecutor`, in job order.
  - A row holds metric, k, harm, over_cap_share, acted_fixtures, fixtures, true_difference, delta, replicates, undefined_replicates, flips, seed, the sign-flip path used (exact or Monte Carlo) and the Python version. It also holds, per alpha, `{alpha, t_interval_adopt_rate, sign_flip_adopt_rate}`.
    - Rows carry no worker count and no timing, so output is byte-identical across worker counts. Per-cell wall-clock time goes to stderr.
    - Each row prints as one JSON line when its cell finishes.
    - With an output path, the whole JSON array is rewritten after each row by writing a temporary file in the same directory and replacing the target with it, creating the parent directory first, so an interrupted sweep keeps its finished cells.

  Over-powered check. A process pool is heavier than one loop. Each lighter primitive fails:
  - **A single process:** above 20 fixtures each replicate draws 100,000 sign patterns in pure Python. A scratch port measured 0.16 s per replicate at 21 fixtures and 0.40 s at 40, so one 4,000-replicate cell takes about 11 to 27 minutes serial, and a sweep of several cells runs for hours (row 20).
  - **Raising the exact cap to about 30:** it would make those cells cheap, at about 23 ms per exact call at 30 fixtures. The agreed design says about 20 (row 2), so PR 2 decides it.
  - **Several operator-launched processes over slices of the grid:** merging rows and keeping seeds disjoint falls on the operator, and one command no longer reproduces a sweep.
  - **A thread pool, the review_bench precedent** (`runner.py:1795-1799`): the work is CPU-bound, so the GIL serializes it.

  anchors: row3, row6, row14, row15, row20
- **M8.** Changes to `evals/run_review_bench.py`:
  - `cmd_calibrate(args)` imports `review_bench.calibrate` inside the function, as every handler does (row 18). It builds the config and solves every cell's shift. On a ValueError it prints the message to stderr, prints no row, writes no `--out` file and returns 2; otherwise it runs the sweep and returns 0.
  - `build_parser` registers `calibrate` after `freeze`, with these flags:
    - `--metric`: required, with choices.
    - `--fixtures`: required, repeatable, int.
    - `--k`: required, `_positive_int`, as `analyze` and `freeze` require it (`:2223`, `:2252`).
    - `--alpha`: repeatable.
    - `--delta`.
    - `--harm`: choices, default normal.
    - `--over-cap-share`: default 1.0.
    - `--replicates`: `_positive_int`, default 4000.
    - `--seed`: default 0.
    - `--workers`: `_positive_int`, default 1.
    - `--flips`: `_positive_int`.
    - `--out`: default none.

    A flag whose default is an `analysis` constant defaults to None in the parser, so `build_parser` imports nothing, and the config fills it in. The 4000-replicate default gets a one-line comment: it puts the Monte Carlo standard error of a 2.5% rate near 0.0025.
  - The module docstring's subcommand list (`:2-5`) gains `calibrate`.

  anchors: row1, row16, row18
- **M9.** `evals/README.md`'s "Usage" block under "Review bench" gains one comment line and one command after the `analyze` example (`:755-757`). The comment says the command simulates the decision statistics' false-adopt and power rates on synthetic data, with no model and no spend.

  anchors: row16

**Rows:**
1. The Ask. [engineer-verified: "yes begin"] The quote covers none of PR 2's constants, ledger or gate logic.
2. The agreed recall statistic is a sign-flip test on per-fixture differences with a frozen seed. It enumerates exactly up to about 20 fixtures and otherwise uses at least 100,000 flips. A cluster t-interval is reported beside it. [verified: `~/.local/state/gh1114-src/decision-record-2026-11-20.md` § "The design as agreed"] That file is the session's summary of the approvals it quotes. It is not the engineer's words in this session. The plan reads "about 20" as at most 20 and keeps the threshold a named constant. [unverified: reading]
3. Precision is linearized per fixture, not bootstrapped. It needs its own simulation before freeze. Its 10-point delta is a PR 2 constants change. [verified: decision record § "The design as agreed"; Context's Scope] Calibrate therefore takes delta as a parameter. It defaults to `DELTA`, which `analysis.py:43` applies to both metrics. [verified: read]
4. `analysis.py` is standard library only, and `random.Random(seed)` is its existing seeded-RNG form (`:371`). [verified: `analysis.py:1-3`, `:15-25`]
5. The standard library has no Student t distribution. [verified for Python 3.12: `/usr/lib/python3.12/statistics.py` defines only `StatisticsError` and `NormalDist` as classes] CI and the README floor are Python 3.14 (`.github/workflows/tests.yml:115`, `pyproject.toml:3`, `README.md:116`). That 3.14's `statistics` still lacks one is [verified: the worktree's `python3` is 3.14.10 and its `statistics` exports `NormalDist` and no t distribution].
6. **(sizing)** The harness closure is a static import walk from `review_bench.runner`, `.adjudicate` and `.analysis`. It excludes `run_review_bench.py` (`analysis.py:700`, `:749-771`). The frozen fields are the closure plus the arm directories, judge agents, `defects.json` and prompt templates (`:852-876`). A module none of the three roots imports, such as `calibrate.py`, changes no frozen field, so later calibrate edits never move a freeze. [verified: reads]
7. **(sizing)** Run the pilot's smoke campaign and freeze after PR 2 merges, so smoke's model cost is paid once. This PR edits `analysis.py`, so it changes the closure manifest hash. `freeze` refuses unless that hash equals the last passing smoke campaign's (`analysis.py:1015-1018`), so a smoke campaign run before this PR merges cannot feed `freeze` after it. PR 2 edits `analysis.py` again. No committed freeze exists for this PR to invalidate. [verified: Glob finds no `evals/review_bench/**/conditions*.json`; `run_review_bench.py:47` makes `evals/review_bench/conditions.json` the default path; `.gitignore:48` ignores only `.local/`] Whether an uncommitted `conditions.json` sits in another checkout is [unverified].
8. The draft's sign-flip divides by √(Σu²), computed once from the unflipped values (`gh1114-sim3.py:85-96`). That denominator is the same for every sign pattern, so it changes no p-value, and the port uses the plain sum. [verified: read] A per-pattern studentized statistic would give the same p-values too, because with Σu² fixed the t statistic increases with the sum. [unverified: the architect's algebra]
9. `evals/replay_bench/summary.py:180` calls `analysis.bootstrap_interval`. [verified: read] `TestFixtureClusterBootstrap` (`evals/test_review_bench_analysis.py:1197`) pins the draws that M4's extraction must keep. [verified: Grep]
10. The precision residuals and plug-in centering port `gh1114-sim3.py:204-215`, and the t-interval's √(Σe² / (F (F − 1))) is at `:213`. The residuals sum to zero by construction. [verified: read]
11. The existing recall is the defect-weighted mean of per-defect detection rates (`analysis.py:131-140`, `:418-425`). [verified: read] The agreed "per-fixture differences" has two readings when fixtures hold unequal defect counts. The plan reads it as each fixture's linearized contribution to the existing defect-weighted difference. That reading keeps delta's meaning and matches the drafts exactly at one defect per fixture. [unverified: reading; the decision record does not say]
12. The architect checked M2's series by hand against the closed-form CDFs for df = 1 to 4. The tests pin df 1 and 2 against closed-form quantiles and df 3 against its closed-form CDF. [verified analytically for df 4 and 5 by a reviewer this session; larger df rest on the recursion and the independent check planned in Dispatch 1. The source is Abramowitz and Stegun 26.7.3–26.7.4, whose equation numbers were not re-read]
13. `pooled_precision` skips a defect ID absent from the counts (`analysis.py:198-200`), and `precision_difference` is None when either arm has no finding (`:428-436`). [verified: read]
14. The ported scenario parameters are synthetic design choices: baseline recall rate Beta(0.8, 0.8), defect noise SD 0.1, 10% concentrated drops of 0.5, precision mean 0.6 with concentration 6, finding volume Gamma(2, 2), and precision noise SD 0.05. That none was drawn from a private corpus is [unverified]. The reviewer confirms this before they ship in a public file.
15. The repo's precedent for CPU-bound parallelism is `ProcessPoolExecutor` (`run_skill_evals.py:45`, `:1162`), and its tests check the math apart from the pool (`claude-skills/skills/tests/test_trigger_detector.py:911`). [verified: Grep] Python 3.14 defaults to the forkserver start method on Linux, so the worker must be a top-level function taking picklable arguments. [verified: a scratch run on the worktree's Python 3.14.10 showed forkserver as the default, and a top-level worker over plain-tuple jobs gave pool output equal to serial output]
16. `evals/README.md:10-37` keeps the harness out of CI because of the cost of `claude -p`, while its `evals/test_*.py` unit tests run in CI. The "Usage" block (`:722-758`) is the only place subcommands are listed with commands. [verified: reads; Grep of `docs/`, `README.md` and `evals/*.md` for `snapshot-arms`] `run_review_bench.py:2-5` lists the subcommands. [verified: read]
17. `select-tests.py` maps `evals/review_bench/**` and `evals/test_review_bench*.py` to every evals test target (`:79-81`, `:709-723`, `:752`), so it needs no edit. [verified: read]
18. All 35 `from review_bench import` lines in `run_review_bench.py` sit inside functions, and none is at module level. `cmd_snapshot_arms` (`:1125-1135`) is the smallest handler. CLI tests build the parser and call the handler directly (`evals/test_review_bench_cli.py:219-225`). [verified: Grep and reads]
19. Each `evals/test_review_bench_<area>.py` covers one module or area: adjudicate, analysis, cli, fixtures, mining, runner. [verified: Glob] `calibrate.py` therefore gets its own test file.
20. Runtime: a scratch port of the plan's `getrandbits` Monte Carlo path took 0.16 s at 21 fixtures, 0.31 s at 30 and 0.40 s at 40 per 100,000-flip call. The exact path took 1 ms at 20 fixtures, 4 ms at 26 and 23 ms at 30. [verified: a reviewer's scratch timings on this machine this session, not the production code] Verification step 5 records the real timings.
21. Python 3.14 is the floor (row 5), so `random.binomialvariate` is available. [verified: it exists in the worktree's Python 3.14.10]
22. The architect chose these defaults with no engineer quote behind them [unverified]:
    - M7's acted-fixture semantics;
    - concentrated harm for precision;
    - the K·λ finding volume;
    - the 4,000-replicate default;
    - the tie tolerance;
    - the test-file placement.
23. This plan stays one PR at a `Projected diff:` of about 1,100 lines. The engineer answered "Proceed anyway" [engineer-verified: "Proceed anyway"] to plan-review's question "Split into smaller PRs now, or proceed?". That question was asked when the projection was about 900 lines. The projection is now about 1,100 lines, so the answer was given at the smaller size. Whether the answer still covers the larger size is unsettled [unverified: the engineer answered at about 900 lines].

## Critical files

Two `code-writer` dispatches run in sequence, because Dispatch 2's module calls Dispatch 1's functions. Their file sets are disjoint. The session runs `/code-review` and commits after each dispatch. Line numbers are base lines.

**Before Dispatch 1:** commit this plan (plan-it Step 7).

**Dispatch 1: the statistics.** Verify with `scripts/venv-run.sh pytest evals/test_review_bench_analysis.py` and `scripts/venv-run.sh ruff check evals/review_bench/analysis.py evals/test_review_bench_analysis.py`.
- `evals/review_bench/analysis.py`: M1 to M6.
  - Put the new functions in a new section after the bootstrap section (`:330-398`) and before "Verdicts" (`:401`).
  - Reuse `DefectRecallCounts.detection_rate` (`:87`), `DELTA` and `ALPHA_ONE_SIDED` (`:43-44`), and the moved `_fixture_groups`.
- `evals/test_review_bench_analysis.py`: add new classes and edit no existing test.
  - `student_t_upper_quantile`:
    - df 1 equals tan(π(½ − α)), and df 2 equals (1 − 2α) / √(2α(1 − α)), for α 0.025 and 0.0125.
    - At df 3, the closed-form CDF ½ + (1/π)(atan(t/√3) + (t/√3)/(1 + t²/3)) of the returned t is 1 − α.
    - At df 10,000 it is within 1e-3 of `NormalDist().inv_cdf(1 − α)`.
    - Pins at α 0.025: df 4 → 2.776445, 9 → 2.262157, 19 → 2.093024, 29 → 2.045230, 39 → 2.022691. Pin df 4 → 3.495406 at α 0.0125. The implementer re-derives each value with the integration check below and cites the table in the test.
    - An independent check that P(|T| < t) equals numerical integration of the density, built from `math.lgamma` in the test, for every df from 4 to 40 and both alphas.
    - It decreases as df rises.
    - df 0, df 2.5, `True`, tail 0, tail 0.5 and a NaN tail raise ValueError, and so does a tail whose 1 − 2α rounds to 1.0.
  - `sign_flip_p_value`:
    - `[1, 2, 3]` gives 1/8, and `[1, -1, 2]` gives 3/8.
    - `[0.1, 0.2, -0.3]` gives 5/8. That count includes the two sign patterns that tie the observed sum only in exact arithmetic.
    - The exact path equals an oracle written in the test that counts in exact integers (values scaled to a lattice, subset-sum DP), over seeded lattice vectors with repeats, for every F from 1 to 20 including 13, 16, 17 and 20. A float oracle needs the same tolerance and so proves nothing about ties.
    - The Monte Carlo path runs on 14 values of 1 and 10 of −1, with 20,000 resamples. Its p is within four standard errors of the binomial tail Σ_(b≥14) C(24, b) / 2^24, computed with `math.comb`. A second call gives the same p. F = 20 gives an identical p under two seeds. An all-positive 24-value vector gives p == 1 / (resamples + 1).
    - Empty input, and a NaN or infinite value on either path, raise ValueError.
  - `recall_fixture_terms`:
    - Over fixtures of 1, 2 and 3 defects, `estimate` equals `recall_difference(…, ARM_X, ARM_BASELINE)` and the residuals sum to 0.
    - `null_centered` matches hand-computed values on fixtures of mixed defect counts (n̄ ≠ 1) with delta ≠ 0. Estimate equality uses `approx`, since the two computations differ in the last ulp.
    - With one defect per fixture, `null_centered` is each per-defect difference plus delta.
    - One fixture gives None.
  - `precision_fixture_terms`:
    - A hand case with unequal precisions and unequal totals per arm, three fixtures (arm X valid/total, baseline valid/total): (3/4, 1/5), (1/6, 2/2), (4/4, 2/3). A reviewer's Fraction computation gives estimate 1/14 and residuals 591/980, −201/245 and 213/980. The test re-derives them with `Fraction` before pinning them. A two-fixture case with equal precisions and equal totals would be degenerate: a wrong centering or a mixed-up baseline term would pass it.
    - A property test over seeded random counts: the residuals sum to 0.
    - `estimate` equals `precision_difference`.
    - An arm with no finding gives None.
    - A defect ID absent from the counts is skipped, and a fixture left with no present defect is dropped from F.
  - `fixture_t_interval`: residuals (1, −1, 2, −2) with estimate 0.5 give 0.5 ± `student_t_upper_quantile(3, α)` · √(10/12).

**Dispatch 2: calibrate.** Verify with `scripts/venv-run.sh pytest evals/test_review_bench_calibrate.py` and `scripts/venv-run.sh ruff check evals/review_bench/calibrate.py evals/run_review_bench.py evals/test_review_bench_calibrate.py`.
- New `evals/review_bench/calibrate.py` (M7). Port the drafts' generators and shift solvers; do not copy their script structure.
- `evals/run_review_bench.py` (M8).
- `evals/README.md` (M9).
- New `evals/test_review_bench_calibrate.py`. Every sweep in it is tiny and runs with workers 1:
  - The generator exposes its per-fixture sampling, and a test checks that its mean acted difference equals target · F / acted within Monte Carlo error, for each metric and harm at share 1.0 and 0.5. The solver's draw count is a parameter, so CI uses a small one. Cells just reachable (share 0.2 at 20 fixtures) and just unreachable (share 0.1) pin the boundary, and an unreachable cell raises ValueError naming it before any replicate runs.
  - The per-replicate decision function, driven by hand-built terms: all fixtures far above −delta adopt under both statistics, all far below adopt under neither, and a zero-finding arm is undefined and not adopted. It pins `p <= alpha` at alpha 1/64 with 6 all-positive fixtures, and shows 5 fixtures can never adopt at 0.025 (the minimum p is 1/32).
  - A recall sweep at 6 fixtures and 3 replicates gives two rows, true difference −delta then 0, with `acted_fixtures` set. Running the same config twice gives identical rows.
  - A precision sweep with concentrated harm and share 0.5 runs.
  - 21 fixtures with 200 flips and 2 replicates take the Monte Carlo path.
  - The worker function and one job survive a `pickle` round trip. Running a sweep's jobs in reversed order gives each job the same result, and a 6-fixture, 2-replicate sweep with workers 2 equals workers 1.
  - `build_parser().parse_args(["calibrate", …])` followed by `cmd_calibrate` returns 0, and its stdout JSON lines equal the `--out` file's array. `--over-cap-share 0` returns 2 with a message naming the field. A sweep over two fixture counts whose second cell is unreachable returns 2 with no row printed and no `--out` file written.
  - Config validation, one parametrized case per rule at its boundary: share 1.0 passes while 0 and above 1 fail, alpha 0.5 fails, one fixture fails, and each positive-int field fails at 0. Omitted delta, alphas and flips resolve to the `analysis` constants in the row.
  - A positive control in one test shows `"evals/review_bench/analysis.py"` is a key of `analysis.compute_harness_closure()` while `"evals/review_bench/calibrate.py"` is not. The keys are repo-relative strings, so a Path-typed probe would pass vacuously.

This change only reads `evals/replay_bench/summary.py`, `evals/test_review_bench_cli.py` and `claude/.claude/scripts/select-tests.py` (rows 9, 17, 19).

Projected diff: about 1,100 lines. That is about 215 in `analysis.py`, 290 in `calibrate.py`, 75 in `run_review_bench.py`, 2 in the README, 290 in the analysis tests and 230 in the calibrate tests.

## Verification

1. Scoped suite: `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py` passes. It selects every evals test target for this diff (row 17).
2. Lint: `scripts/venv-run.sh ruff check evals/` is clean.
3. No verdict changes:
   - `git diff --numstat origin/main...HEAD -- evals/test_review_bench_analysis.py` shows 0 deleted lines, and the existing tests pass in step 1.
   - In `git diff origin/main...HEAD -- evals/review_bench/analysis.py`, every hunk outside the new constants and new section is the `_fixture_groups` move or the docstring line.
   - `git diff --stat origin/main...HEAD -- evals/replay_bench` is empty.
4. The closure fact: Dispatch 2's closure test passes in step 1, so `calibrate.py` stays out of every frozen field (row 6).
5. Worker independence, which CI does not exercise because its tests run with workers 1. These commands run no model and cost nothing:
   - Run `scripts/venv-run.sh python3 evals/run_review_bench.py calibrate --metric recall --k 10 --fixtures 20 --fixtures 30 --replicates 200 --workers 1 --out evals/review_bench/.local/calibration/w1.json`.
   - Run the same with `--workers 4 --out evals/review_bench/.local/calibration/w4.json`.
   - `cmp evals/review_bench/.local/calibration/w1.json evals/review_bench/.local/calibration/w4.json` exits 0.
   - Record both runs' wall-clock times in the PR body, replacing row 20's estimates.
6. Parity with the drafts, which CI cannot exercise: run `scripts/venv-run.sh python3 evals/run_review_bench.py calibrate --metric recall --k 10 --fixtures 20 --replicates 4000 --workers 4`. Its t and sign-flip adopt rates stay within 0.01 and 0.03 of `gh1114-sim3.py`'s results at 20 fixtures, normal harm, share 1.0: t 0.0248 and sign-flip 0.0222 at a true difference of −0.05, and 0.197 and 0.1895 at 0.
7. `scripts/venv-run.sh python3 evals/run_review_bench.py calibrate --metric precision --k 10 --harm concentrated --over-cap-share 0.5 --fixtures 20 --replicates 100` exits 0 and prints two rows.

## Out of scope

- **Wiring the new statistics into `analyze`.** That covers its report, the verdicts, certification, the ledger, error-budget slots, floors, and constants such as the 10-point precision delta. These belong to PR 2 (Context's Scope; the decision record). Until then the new functions have no caller outside `calibrate.py` and the tests.
- **Any edit to `.claude/plans/measure-review-quality.md`** (Context's Scope). The decision record notes the engineer's earlier ruling against editing that stale plan.
- **Running the calibration sweeps PR 2 needs, or committing their output.** Operator output stays under the gitignored `.local/`.
- **A bootstrap column in calibrate.** The agreed design retires the bootstrap as the decision statistic, and the drafts already measured it.
- **Several defects per fixture in the generator.** It needs a within-fixture correlation that has no basis yet. Dispatch 1's tests cover the multi-defect code path.
- **Changing the frozen-conditions design** (what `freeze` and `analyze` hash, and the smoke-hash precondition). This PR works within it and records its effect on the pilot (rows 6 and 7).
- **Changing `bootstrap_interval`'s or `bootstrap_interval_with_drops`'s signature or draws.** `evals/replay_bench/summary.py:180` uses the first (row 9).
- **Raising `SIGN_FLIP_EXACT_MAX_FIXTURES`.** Meet in the middle would make about 30 fixtures cheap, but the agreed design says about 20 (row 2). PR 2 can take it up if wanted.
