# Review-bench decision statistics and calibration tooling

## Context

Goal: give the review benchmark the small-sample decision statistics that the agreed decision rule needs, as tooling only, with no change to any verdict the benchmark can produce today. The statistics shipped in #1565 (`13b23d57`). This PR ships the calibration tool that exercises them: a `calibrate` subcommand that measures their false-adopt and power rates on synthetic scenarios.

Ask: "yes begin" — the engineer's answer to the session's question "shall I begin PR 1?", where PR 1 was the architect's first step: new statistic functions in `evals/review_bench/analysis.py`, a `calibrate` subcommand, tests and a README line, changing no verdict. For the follow-up, "Let's go with your recommendation" — the engineer's answer to the session's recommendation that the `calibrate` plan is the next work.

The review benchmark (`evals/review_bench/`) decides whether a capacity-aware read rule may replace "read every changed file fully" for reviewer agents. Its interval for the recall difference is a percentile cluster bootstrap. Synthetic simulations run in this session, using no model, showed that statistic falsely adopts a rule that is 5 percentage points worse more often than its nominal 2.5%, at 15 to 40 fixtures. A sign-flip test on per-fixture differences and a per-fixture linearized t-interval held nearer the nominal rate, and the same held for pooled precision, a ratio, in those simulations. Those simulations were not designed for the case where most fixtures carry no findings, and the code shows the statistics degenerate there (carry-over below). The decision rule built on them (margins, floors, two error-budget slots, a ledger) lands in a later PR whose constants depend on calibration runs the follow-up calibrate PR makes possible. The decision record is `~/.local/state/gh1114-src/decision-record-2026-11-20.md`, and the simulation drafts `gh1114-sim3.py` and `gh1114-sim4.py` sit in the same directory. The drafts live outside the repo; port them, do not copy.

Scope of this PR: the parameterized `calibrate` subcommand that runs #1565's functions on synthetic scenarios, with its tests and a README usage line (M7 to M9, Dispatch 2, Verification steps 4 to 7). M1 to M6 and Dispatch 1 shipped in #1565 and are context only. Three carry-overs from #1565's review land here:
- A guard test for a zero-width `fixture_t_interval`, and for `sign_flip_p_value` on the same degenerate terms, lands with this first caller that makes an adopt decision.
- Precision's behavior when most fixtures carry zero findings is pinned here by guard tests, not simulated (row 25). A sparse-findings generator and its rate sweep move to PR 2 with the remedy (row 29).
- The false-adopt and power rates were not verified in #1565. This PR's calibrate runs measure them for the every-fixture-carries-findings regime, on synthetic data only, with no model and no spend.

Not in this PR: the ledger, gate logic, constants changes, the case study, the skill, any edit to `.claude/plans/measure-review-quality.md`.

## Approach

This PR adds a `calibrate` subcommand. Its new module, `evals/review_bench/calibrate.py`, feeds synthetic per-defect counts through #1565's production statistics and prints their false-adopt and power rates per fixture count, so PR 2 can set the decision rule's constants from measured rates. Guard tests on hand-built counts pin what the statistics decide where most fixtures carry no finding (row 25). Measuring that regime's rates is PR 2's (rows 26 and 29).

No file in the harness closure changes, so no verdict, `analysis` constant, report field, frozen field or `analyze` path moves (rows 6 and 7). Rows marked **(sizing)** say how this PR moves the pilot's smoke campaign and freeze.

#1565 shipped the statistics (M1 to M6). Recall and pooled precision are each a ratio of per-fixture sums, linearized per fixture. That shape feeds a t-interval with an exact Student t quantile, and a one-sided sign-flip test of H0 "difference = −delta", exact up to 20 fixtures and seeded Monte Carlo above.

Alternatives weighed:
- **Calibrate on raw arrays, as the drafts do.** It would measure a copy of the statistics, not the functions PR 2 gates on.
- **The calibrate CLI test in `evals/test_review_bench_cli.py`.** That file is 7,124 lines and its docstring lists the subcommands it covers. `cmd_calibrate` is a thin adapter over `calibrate.py`, so its test sits with calibrate's own (row 19).
- **A sparse-findings generator and sweep in this PR**, through a `--fixtures-with-findings` parameter. With one fixture carrying findings the code fixes the outcome (row 25), and a sweep over how many fixtures carry findings decides nothing until PR 2 has remedies to compare (row 26). The split moved them to PR 2 (row 29).
- **A calibrate-side guard that counts a zero-width interval or a constant `null_centered` as not adopted.** Calibrate would then measure a rule PR 2 has not adopted, and PR 2's sparse-regime rates would hide the behavior they exist to show. Guard tests pin the production statistics' degenerate behavior instead (Critical files).

### Assumption ledger

**Root:** The bench's only decision statistic, a percentile cluster bootstrap, falsely adopts a rule 5 points worse more often than its nominal 2.5% at 15 to 40 fixtures (Context). #1565 added the agreed replacement statistics. PR 2 cannot set the decision rule's constants until a tool measures their false-adopt and power rates on synthetic data. This PR adds that tool. It may change no verdict the bench produces today.

**Givens:**
- G1. The bench's statistics and their calibration use the standard library only. Reason: a numerical dependency needs the engineer's named-package confirmation under `CLAUDE.md`'s Safety rules, a decision outside this plan, and `analysis.py:1-2` states the constraint (row 4).

Two conditions the plan could change and deliberately does not. One is the frozen-conditions design, under which `freeze` and `analyze` hash `analysis.py` and every first-party module it imports (rows 6 and 7). The other is #1565's statistics themselves, whose sparse-regime decisions this PR pins with guard tests (row 25). Out of scope lists both.

**Mechanisms:**
- **M1 (shipped in #1565).** `SIGN_FLIP_EXACT_MAX_FIXTURES = 20`, `SIGN_FLIP_RESAMPLES = 100_000`, `SIGN_FLIP_SEED = 0` and the tie tolerance (`analysis.py:47-53`). Line numbers in M1 to M6 are this worktree's `analysis.py`.

  anchors: row2, row8
- **M2 (shipped in #1565).** `student_t_upper_quantile(df, upper_tail)` (`:433-467`), from the finite trigonometric series for integer df.

  anchors: row2, row5, row12
- **M3 (shipped in #1565).** `sign_flip_p_value(values, *, resamples, seed)` (`:489-516`): exact by meet in the middle up to 20 values, seeded `getrandbits` flips above, and ValueError on empty or non-finite input.

  anchors: row2, row8, row20
- **M4 (shipped in #1565).** `FixtureTerms`, `recall_fixture_terms` and `precision_fixture_terms` (`:519-626`), each builder returning None below two fixtures. Precision's `null_centered` is the plug-in residual + estimate + delta, and a fixture with present defects but no finding stays in F (row 25).

  anchors: root, row10, row11, row13, row25
- **M5 (shipped in #1565).** `fixture_t_interval(terms, *, alpha_one_sided)` (`:629-638`), the two-sided 1 − 2α interval, so a lower limit above −delta is the one-sided test at α.

  anchors: row2, row10
- **M6 (shipped in #1565).** `analyze`, the verdict functions, `DELTA`, `ALPHA_ONE_SIDED` and every report field stayed as they were. This PR edits no line of `analysis.py`.

  anchors: root, row6, row9
- **M7.** Add `evals/review_bench/calibrate.py`. Only `run_review_bench.py`'s handler imports it, so it stays outside the closure (row 6). It calls the statistics as `analysis.<name>`, so a test can spy on one.
  - `CalibrationConfig` holds the metric (`recall` or `precision`), delta, alphas, fixture counts, k, harm (`normal` or `concentrated`), over-cap share, replicates, seed, workers and flips. It validates on construction and raises `CalibrationConfigError`, a ValueError subclass, naming the field (row 34):
    - metric and harm among their choices;
    - fixture counts >= 2;
    - `MIN_ALPHA <= alpha < 0.5`, where `MIN_ALPHA = 1e-6` is `student_t_upper_quantile`'s documented accuracy floor and its comment cites that docstring (row 33);
    - 0 < delta < 1;
    - 0 < share <= 1;
    - k, replicates, workers and flips positive;
    - workers at most `os.process_cpu_count() or 1`, the pool's own default worker count, called at validation so a test can patch it (row 30).

    Each float check is written as the in-range comparison, so a NaN fails it. Delta, alphas and flips default to `analysis.DELTA`, `(analysis.ALPHA_ONE_SIDED,)` and `analysis.SIGN_FLIP_RESAMPLES`.
  - A cell is one fixture count and one true gate-level difference: −delta for the false-adopt rate, then 0 for power.
    - In each replicate the first `max(1, floor(share · F + 0.5))` fixtures are acted on, where F is the fixture count. On every other fixture arm X's rate is its baseline rate exactly, and precision's volume factor is 1. Both arms' counts there are still drawn independently, as two runs of an unchanged rule would be (row 22).
    - One pure function maps a fixture's latent draws and a shift to arm X's rate. The generators and the shift solver both call it, so a solved shift describes the generated data.
    - The shift is solved per cell by bisection over [−1, 1] on 100,000 seeded latent draws, so that the acted fixtures' expected difference is target · F / acted and the gate-level expectation is the target. For recall that expectation is the mean of arm X's rate minus the baseline rate. For precision each draw is weighted by its expected finding count, 1 + K·λ. The draw-count constant's comment states its Monte Carlo error, and the bisection's iteration cap and tolerance are named constants.
    - Every cell's shift is solved and checked before the first replicate runs. A target outside the differences reached at the bracket's two ends raises `CalibrationConfigError` naming the cell.
  - The generators port `gh1114-sim3.py`'s `recall_replicate` (`:129-141`) and `precision_replicate` (`:191-203`), one defect per fixture.
    - A generator first draws each fixture's latent draws, its two arm rates and, for precision, its two expected finding volumes, and then the counts, so a test can read the first step.
    - Normal harm is clip(p1 + shift + noise). Concentrated harm gives each acted fixture, with probability 0.10, max(0, p1 − 0.5), and normal harm otherwise, for both metrics. The draft modeled it for recall only.
    - A precision fixture draws 1 + Poisson(K·λ) findings for the baseline and 1 + Poisson(K·λ·U(0.8, 1.2)) for arm X, the draft's 10·λ at K = 10. Every fixture therefore carries findings in both arms, the drafts' regime, and a sparse-findings generator is PR 2's (row 29).
    - Binomial counts use `random.binomialvariate`. A Poisson count counts unit-rate `random.expovariate` arrivals up to the mean. The standard library has no Poisson sampler, and the draft's product form stops counting once exp(−mean) underflows (row 27).
    - Each scenario parameter is a named module constant with a one-line comment (row 14).
  - Each replicate builds `DefectRecallCounts` or `DefectPrecisionCounts`, with `arms.ARM_CURRENT_RULE` as baseline and `arms.ARM_FUNCTION_CONTEXT` as arm X, and a cluster map with one fixture key per defect. It then calls M4's builder with the config's delta, M5 once per alpha, and M3 on `null_centered` with `resamples=flips` and the default production seed.
    - The t-interval adopts when its lower limit is above −delta. The sign-flip adopts when p <= alpha.
    - A None from M4 counts as not adopted and as undefined.
    - A zero-width interval or a constant `null_centered` gets no special case, so calibrate decides as the production statistics do, and the degenerate-terms guard tests pin that (row 25).
    - The per-replicate decision, from the terms to the adopt flags per alpha, is its own function, so tests can drive it with hand-built terms.
    - A replicate's result holds the estimate, each alpha's lower limit and the p-value beside the adopt flags, so tests compare floats, not only flags.
  - Each replicate seeds `random.Random` with a string built from the run seed, metric, k, harm, share, fixture count, true difference and replicate index, with floats written by `repr`. Alphas, flips and workers stay out of it, so a rerun with other alphas or flips draws the same data. A string seed is hashed with SHA-512 (row 27), so the draws are the same for any worker count and process within one Python minor version.
    - Workers = 1 runs in process.
    - Workers > 1 uses one `concurrent.futures.ProcessPoolExecutor` for the sweep, built by one module function whose initializer sets SIGINT to ignored in each worker, so the parent alone handles an interrupt (row 31).
    - Each cell maps a top-level worker function over plain-tuple jobs that carry the solved shift, in job order, with a chunk size of ceil(jobs / (4 · workers)), `multiprocessing.Pool`'s default (row 31).
    - When any exception leaves the sweep, a KeyboardInterrupt included, the sweep calls the pool's `terminate_workers()` inside its `with` block. That call cancels queued jobs and terminates running workers, so no running chunk finishes first (row 31).
    - The sweep then re-raises the same exception object with a bare `raise`, so `main()` sees the original exception and a signal's interrupt keeps its number for the exit code (row 18).
  - A row holds metric, k, harm, over_cap_share, acted_fixtures, fixtures, true_difference, delta, replicates, undefined_replicates, flips, seed, the sign-flip path used (exact or Monte Carlo), the Python version and `cells_planned`. It also holds, per alpha, `{alpha, t_interval_adopt_rate, sign_flip_adopt_rate}`. A rate counts adopting replicates over all replicates, undefined ones included.
    - Rows carry no worker count and no timing, so output is byte-identical across worker counts. Before the sweep, stderr gets one line per cell with its parameters, replicate count, solved shift and solve time. Each cell's wall-clock time goes to stderr when it finishes.
    - With an output path, the sweep writes `[]` through `defects.atomic_write_text` after the solve step and before the first replicate, so an unwritable path fails before any replicate runs (row 32).
    - When a cell finishes, the sweep first rewrites the whole `--out` array the same way with the new row, so an interrupted sweep keeps its finished cells. It then prints the row as one JSON line with `flush=True`, so every printed row is already in the file (Verification step 8).
    - A file is complete when its length equals its rows' `cells_planned`. The sweep replaces any earlier file at the path, by design.

  Over-powered check. A process pool is heavier than one loop. Each lighter primitive fails:
  - **A single process:** above 20 fixtures each replicate draws 100,000 sign patterns in pure Python, which a scratch port measured at 0.16 s per replicate at 21 fixtures and 0.40 s at 40 (row 20). One 4,000-replicate cell then takes about 11 to 27 minutes serial, and a sweep of several cells takes hours.
  - **Raising the exact cap to about 30:** it would make those cells cheap, at about 23 ms per exact call at 30 fixtures. The agreed design says about 20 (row 2), so PR 2 decides it.
  - **Several operator-launched processes over slices of the grid:** merging rows and keeping seeds disjoint falls on the operator, and one command no longer reproduces a sweep.
  - **A thread pool, the review_bench precedent** (`runner.py:1795-1799`): the work is CPU-bound, so the GIL serializes it.

  anchors: row2, row3, row6, row14, row15, row18, row20, row22, row25, row27, row29, row30, row31, row32, row33
- **M8.** Changes to `evals/run_review_bench.py`:
  - `cmd_calibrate(args)` imports `review_bench.calibrate` inside the function, as every handler does (row 18).
    - Its `try` wraps only building the config and solving every cell's shift. On `CalibrationConfigError` it prints `calibrate: <message>` to stderr, prints no row, writes no `--out` file and returns 2.
    - The sweep runs outside the `try`, so any other ValueError keeps its traceback and exits 1 through `main()` (row 34). A finished sweep returns 0.
  - `build_parser` registers `calibrate` after `freeze` (`:2248-2266`), with these flags:
    - `--metric`: required, with choices.
    - `--fixtures`: required, repeatable, int.
    - `--k`: required, `_positive_int`, as `analyze` and `freeze` require it (`:2223`, `:2252`).
    - `--alpha`: repeatable.
    - `--delta`.
    - `--harm`: choices, default normal.
    - `--over-cap-share`: default 1.0.
    - `--replicates`: `_positive_int`, default 4000.
    - `--seed`: default 0.
    - `--workers`: `_positive_int`, default 1, with its CPU cap in the config (M7).
    - `--flips`: `_positive_int`.
    - `--out`: default none, handed to the sweep as a `Path`, as `analyze` converts it (`:1912`).

    A flag whose default is an `analysis` constant defaults to None in the parser, so `build_parser` imports nothing, and the config fills it in. The 4000-replicate default gets a one-line comment: it puts the Monte Carlo standard error of a 2.5% rate near 0.0025.
  - The module docstring's subcommand list (`:2-5`) gains `calibrate`.

  anchors: row1, row16, row18, row34
- **M9.** `evals/README.md`'s "Usage" block under "Review bench" gains one comment line and one command after the `analyze` example (`:759-761`). The comment says the command simulates the decision statistics' false-adopt and power rates on synthetic data, with no model and no spend.

  anchors: row16

**Rows:**
1. The Ask. [engineer-verified: "yes begin"] covers #1565. This PR rests on [engineer-verified: "Let's go with your recommendation"], the engineer's answer to the session's recommendation that the `calibrate` plan is the next work. Neither quote covers PR 2's constants, ledger or gate logic. The split that moved the sparse regime to PR 2 rests on row 29.
2. The plan reads the agreed design's "about 20" as at most 20 and keeps the threshold a named constant. [unverified: reading]
   - The agreed recall statistic is a sign-flip test on per-fixture differences with a frozen seed. It enumerates exactly up to about 20 fixtures and otherwise uses at least 100,000 flips. A cluster t-interval is reported beside it. [verified: `~/.local/state/gh1114-src/decision-record-2026-11-20.md` § "The design as agreed", re-read for this PR]
   - The same section's floor line reads "a floor on fixtures where the rule acts (size from a simulation not yet run)", which `--over-cap-share` serves. [verified: read]
   - That file is the session's summary of the approvals it quotes, not the engineer's words in this session.
3. Precision is linearized per fixture, not bootstrapped. It needs its own simulation before freeze. Its 10-point delta is a PR 2 constants change. [verified: decision record § "The design as agreed", re-read for this PR; Context's Scope] Calibrate therefore takes delta as a parameter. It defaults to `DELTA`, which `analysis.py:43` applies to both metrics. [verified: read, for this PR]
4. `analysis.py` is standard library only, and `random.Random(seed)` is its existing seeded-RNG form (`:383`). [verified: `analysis.py:1-2`, `:14-25`, re-read for this PR]
5. CI and the README floor are Python 3.14 (`.github/workflows/tests.yml:115`, `pyproject.toml:3`, `README.md:116`). [verified: during #1565; `tests.yml:115` re-read for this PR]
   - (#1565.) The standard library has no Student t distribution. [verified for Python 3.12: `/usr/lib/python3.12/statistics.py` defines only `StatisticsError` and `NormalDist` as classes; not re-checked for this PR]
   - (#1565.) 3.14's `statistics` still lacks one. [verified: the worktree's `python3` is 3.14.10 and its `statistics` exports `NormalDist` and no t distribution; not re-checked for this PR]
6. **(sizing)** The harness closure is a static import walk from `review_bench.runner`, `.adjudicate` and `.analysis` (`analysis.py:940`, `:989-1011`). It excludes `run_review_bench.py` (`:993-994`). The frozen fields are the closure plus the arm directories, judge agents, `defects.json` and prompt templates (`:1092-1116`). `review_bench/__init__.py` imports nothing. A module none of the three roots imports, such as `calibrate.py`, changes no frozen field, so calibrate edits never move a freeze. [verified: reads and a Grep of `__init__.py`, for this PR]
7. **(sizing)** Run the pilot's smoke campaign and freeze after PR 2 merges, and pay smoke's model cost once.
   - PR 2 edits `analysis.py` again, which moves the closure manifest hash. This PR edits no closure file (row 6), so it leaves that hash where #1565 left it.
   - `freeze` refuses unless that hash equals the last passing smoke campaign's (`analysis.py:1255-1258`), so a smoke campaign run on either side of this PR's merge feeds the same freeze. [verified: read, for this PR]
   - No committed freeze exists. [verified: Glob finds no `evals/review_bench/**/conditions*.json`, re-run for this PR; `run_review_bench.py:47` makes `evals/review_bench/conditions.json` the default path]
   - `.gitignore:48` ignores `evals/review_bench/.local/`, where Verification writes. [verified: read]
   - Whether an uncommitted `conditions.json` sits in another checkout is [unverified].
8. The draft's sign-flip divides by √(Σu²), computed once from the unflipped values (`gh1114-sim3.py:85-96`). That denominator is the same for every sign pattern, so it changes no p-value, and the port uses the plain sum. [verified: read, re-read for this PR] A per-pattern studentized statistic would give the same p-values too, because with Σu² fixed the t statistic increases with the sum. [unverified: the architect's algebra] The draft also draws 5,000 Monte Carlo flips at every fixture count (`:20`, `:90-95`), where production is exact up to 20 fixtures. [verified: read]
9. (#1565.) `evals/replay_bench/summary.py:180` calls `analysis.bootstrap_interval`, and `TestFixtureClusterBootstrap` (`evals/test_review_bench_analysis.py:1197`) pins the draws #1565's extraction kept. [verified: Grep, re-run for this PR] This PR edits neither file.
10. The precision residuals and plug-in centering port `gh1114-sim3.py:204-215`, and the t-interval's √(Σe² / (F (F − 1))) is at `:213`. `precision_fixture_terms` computes the same terms (`analysis.py:607-626`). The residuals sum to zero by construction. [verified: reads, for this PR]
11. The existing recall is the defect-weighted mean of per-defect detection rates (`analysis.py:138-147`, `:658-665`). [verified: read, for this PR] The agreed "per-fixture differences" has two readings when fixtures hold unequal defect counts. The plan reads it as each fixture's linearized contribution to the existing defect-weighted difference. That reading keeps delta's meaning and matches the drafts exactly at one defect per fixture, which is calibrate's only shape. [unverified: reading; the decision record does not say]
12. (#1565.) The architect checked M2's series by hand against the closed-form CDFs for df = 1 to 4.
    - The tests pin df 1 and 2 against closed-form quantiles and df 3 against its closed-form CDF (`evals/test_review_bench_decision_statistics.py:41-75`). [verified: test names read, for this PR]
    - They check df 4 to 40 against numerical integration of the density (`:93-100`) and pin six-place critical values (`:81-91`). [verified: read, for this PR]
    - A reviewer of #1565 verified df 4 and 5 analytically. [verified: during #1565's planning; not re-checked for this PR]
    - The series' source is Abramowitz and Stegun 26.7.3–26.7.4. [unverified: the equation numbers were not re-read]
13. `pooled_precision` skips a defect ID absent from the counts (`analysis.py:199-207`), and `precision_difference` is None when either arm has no finding (`:668-676`). [verified: read, for this PR] Calibrate's counts hold every defect, and every fixture carries at least one finding per arm, so neither fires on generated data.
14. The ported scenario parameters are synthetic design choices, each read at its draft line [verified: read, for this PR]:
    - baseline recall rate Beta(0.8, 0.8) (`gh1114-sim3.py:101`);
    - defect noise SD 0.1 (`:102`);
    - concentrated drops of 0.5 with probability 0.10 (`:135-136`);
    - precision mean 0.6 with concentration 6 (`:155-156`);
    - findings per run Gamma(2, 2) (`:196`);
    - arm X's volume factor U(0.8, 1.2) and the floor of one finding per arm (`:199-200`);
    - precision noise SD 0.05 (`:157`).

    That none was drawn from a private corpus is [unverified]. The reviewer confirms it before the parameters ship in a public file.
15. The pool's worker is a top-level function over plain-tuple jobs, because Python 3.14 defaults to the forkserver start method on Linux, so each job and the function it names must pickle.
    - The repo's precedent for CPU-bound parallelism is `ProcessPoolExecutor` (`run_skill_evals.py:45`, `:1162`, `:1242`). [verified: Grep, re-run for this PR]
    - Its tests check the math apart from the pool (`claude-skills/skills/tests/test_trigger_detector.py:911`). [verified: Grep, re-run for this PR]
    - A scratch run on the worktree's Python 3.14.10 showed forkserver as the default, and a top-level worker over plain-tuple jobs gave pool output equal to serial output. It did not use the real script-plus-package shape. [verified: that scratch run; not re-checked for this PR]
    - Forkserver forwards the parent's `sys.path` and re-imports the script as `__mp_main__`. That is safe because `run_review_bench.py`'s only top-level action is its `__main__` guard (`:2350-2351`). [unverified: a reviewer's reading of source; Verification step 5's `cmp` confirms it]
16. `evals/README.md`'s "Usage" block (`:726-762`) is the only place subcommands are listed with commands. [verified: read, for this PR; the Grep of `docs/`, `README.md` and `evals/*.md` for `snapshot-arms` was not re-run]
    - `evals/README.md:10-37` keeps the harness out of CI because of the cost of `claude -p`, while its `evals/test_*.py` unit tests run in CI. [verified: read, for this PR]
    - `run_review_bench.py:2-5` lists the subcommands. [verified: read, for this PR]
17. `select-tests.py` maps `evals/review_bench/**`, `evals/run_review_bench.py` and `evals/test_review_bench*.py` to every evals test target (`:79-81`, `:709-723`, `:752`), and `evals/README.md` to the skills tests (`:71`, `:973`), so it needs no edit. [verified: reads, for this PR]
18. What `run_review_bench.py` and its CLI tests show, each [verified: Grep and reads, for this PR]:
    - All 35 `from review_bench import` lines sit inside functions, and none is at module level.
    - `cmd_snapshot_arms` (`:1125-1135`) is the smallest handler.
    - CLI tests build the parser and call the handler directly (`evals/test_review_bench_cli.py:219-225`).
    - `main()` turns SIGTERM and SIGHUP into a KeyboardInterrupt (`:2327-2329`).
    - `main()` reports any KeyboardInterrupt with exit 128 plus the signal number (`:2343-2347`).
19. Each `evals/test_review_bench_<area>.py` covers one module or area: adjudicate, analysis, cli, decision_statistics, fixtures, mining, runner. [verified: Glob, for this PR] `calibrate.py` therefore gets its own test file.
20. Runtime: a scratch port of the plan's `getrandbits` Monte Carlo path took 0.16 s at 21 fixtures, 0.31 s at 30 and 0.40 s at 40 per 100,000-flip call. The exact path took 1 ms at 20 fixtures, 4 ms at 26 and 23 ms at 30. [verified: a reviewer's scratch timings on this machine during #1565's planning, not the production code] Not re-checked for this PR. Verification step 5 records the real timings.
21. Python 3.14 is the floor (row 5), so `random.binomialvariate` is available. [verified: CPython 3.14.10's `Lib/random.py:789`, read for this PR]
22. These defaults have no engineer quote behind them [unverified]:
    - #1565, the architect's: the tie tolerance, and the test-file placement.
    - This PR, the architect's: M7's acted-fixture semantics, with independent counts on fixtures the rule does not act on; concentrated harm for precision; the K·λ finding volume; the solver's 1 + K·λ weight; the 4,000-replicate default; decisions on degenerate terms with no special case; and terminating workers on an interrupt rather than letting running jobs finish.
    - This PR, the session's, from plan-review round 2's findings: terminating workers when any other exception leaves the sweep too; and capping `--workers` at the CPU count.
23. The size. The engineer twice chose to proceed unsplit, at about 930 and then about 1,190 lines. Plan-review round 2's fixes move the projection to about 1,270 lines (Critical files), which neither answer covers. Asked again at about 1,270 lines, "This plan projects about 1270 changed lines (an estimate; threshold 400). Split into smaller PRs now, or proceed?", the engineer first answered "Ask the architect" and, after the architect's consult recommended proceeding, answered [engineer-verified: "Proceed anyway"]. The session adds one tripwire of its own, from that consult and not the engineer's: if the implemented diff passes about 1,500 lines, or the test file about 950, split at the worker-pool seam and ask the engineer again. [unverified: the consult's estimates of about 1,070 lines for the pool-free part and about 200 for the pool part, not measured]
    - At about 930 lines plan-review asked "This plan projects about 930 changed lines (an estimate; threshold 400). Split into smaller PRs now, or proceed?", and the engineer answered [engineer-verified: "Proceed anyway"].
    - The row-29 split then cut the projection to about 860 lines. That answer covers the cut, since it only shrank the diff.
    - Plan-review round 1's findings added tests and hardening, which moved the projection to about 1,190 lines. Asked "This plan projects about 1190 changed lines (an estimate; threshold 400). Split into smaller PRs now, or proceed?", the engineer answered [engineer-verified: "Proceed anyway"].
24. (#1565, history.) The engineer twice answered [engineer-verified: "Proceed anyway"] to plan-review's "Split into smaller PRs now, or proceed?", at about 900 and then about 1,100 lines. When the PR then grew to about 1,600 lines and the session asked whether to split at the dispatch boundary, the engineer chose [engineer-verified: "Split now (Recommended)"]. #1565's plan was cut to Dispatch 1, at a `Projected diff:` of about 1,020 lines, and calibrate moved to a follow-up PR, which is this PR.
25. On terms where one fixture carries every finding, both statistics decide from the estimate alone, up to float rounding:
    - The t-interval's half-width is 0 or of float-rounding size, so it adopts when the computed estimate exceeds −delta by more than that.
    - The sign-flip gives p = 1/2^F when every `null_centered` value is positive, and 1.0 when none is. So it adopts when estimate + delta is positive by more than the residuals' rounding size, wherever 1/2^F <= alpha, which is F >= 6 at 0.025 and F >= 7 at 0.0125. It never adopts when estimate + delta is negative.
    - An estimate whose exact value is −delta can compute to either side of −delta, so its outcome follows float rounding, not the counts. 11/20 against 12/20 at F = 6 computes to −0.04999999999999993, with every residual exactly 0 and every `null_centered` value 6.9e-17, so both statistics adopt at 0.025.

    The code behind it [verified: reads, re-read for this PR]:
    - `compute_precision_counts` records a defect whose judged run had no findings (`analysis.py:173-179`), and `precision_fixture_terms` keeps its fixture in F (`:585-586`, `:590-594`).
    - A fixture with no finding in either arm has residual exactly 0 (`:616-622`), so its `null_centered` value is estimate + delta (`:625`).
    - The fixture carrying every finding has residual 0 up to float rounding (`:587-588`), and the interval's half-width scales with the residuals (`:636-638`).
    - `sign_flip_p_value` counts the sign patterns whose sum reaches the observed sum less a 1e-9 relative tie tolerance (`:53`, `:505-508`). With every value positive only the unflipped pattern does, and with every value zero or negative all do.

    Each direction's evidence:
    - Not adopting: [verified: the session's scratch run, six fixtures, estimate −0.20, delta 0.05, gave a zero-width interval at −0.20 and p = 1.0].
    - Adopting: [verified: a plan reviewer's run of `precision_fixture_terms` on 14/25 against 15/25 at F = 6 gave residuals near 4e-16, a lower limit above −delta and p = 1/64].
    - Exactly −delta: [verified: the same reviewer's run on 11/20 against 12/20, and the architect's derivation of the doubles: 0.55 − 0.6 is exact by Sterbenz's lemma, and 0.55·20 and 0.6·20 round to 11 and 12, so every residual is exactly 0].

    Critical files' guard tests drive the first two through `precision_fixture_terms` from hand-built counts, and pin the exact −delta boundary on hand-built terms.
26. Hand-off to PR 2: the sparse regime's rates are expected, not measured, and measuring them is PR 2's (row 29). The drafts never reach this regime, because every fixture's totals carry a floor of one finding per arm (row 14), and this PR's generator keeps that floor (M7).
    - With one fixture carrying findings and a true difference of −delta, both false-adopt rates should sit near the chance that one fixture's estimate lands above its own mean, on the order of one half rather than alpha, and nearly equal to each other. [unverified: inference from row 25]
    - With m such fixtures among F, the t-interval keeps F − 1 degrees of freedom and divides by F (F − 1). Its understatement is bounded: at equal volumes it shrinks the standard error by a factor of about √((m − 1)/m) and uses the df F − 1 quantile where df m − 1 belongs. [unverified: the architect's algebra, not run]
    - The sign-flip's false-adopt rate has no such bound. Each of the F − m empty fixtures takes the plug-in value c = estimate + delta, and the observed sum is F·c, since the residuals sum to zero (row 10). The empty fixtures add only about √(F − m)·|c| to the flipped sums' spread. So as F grows at fixed m the p-value goes to 0 whenever c > 0, and the false-adopt rate approaches P(estimate > −delta). A floor on fixtures that carry findings alone therefore cannot bound it. [unverified: the architect's algebra, not run]
    - Candidate remedies PR 2 would compare:
      - Leading: dropping, inside `precision_fixture_terms`, fixtures with no finding in either arm, since their residual is identically 0 (`analysis.py:616-622`). [verified: read, for this PR] That dropping them restores a near-nominal rate is [unverified].
      - Weighting precision's plug-in by each fixture's finding volume, as recall weights by defect count.
      - A floor on fixtures that carry findings, which alone does not bound the sign-flip's false-adopt rate (above).
    - Recall needs no such change, because its `null_centered` is exact, not a plug-in (`analysis.py:567-570`). [verified: read, for this PR; that recall's rates are therefore unaffected is unverified]
    - A `--fixtures-with-findings` parameter on calibrate's precision generator, whose first m fixtures carry findings and the rest none in either arm, is worth adding only if PR 2 keeps such fixtures in the fixture set. [unverified: the architect's design]
27. A replicate's draws depend on its seed string alone, not on `PYTHONHASHSEED` or the process, because CPython 3.14.10's `Lib/random.py` hashes a str seed with SHA-512 before seeding (`:165-167`). [verified: read, for this PR]
    - `binomialvariate` (`:789`) and `expovariate` (`:605`) exist, and no Poisson sampler is defined. [verified: read and a Grep for `def poisson`, for this PR]
    - The draft's Poisson sampler multiplies uniforms until the product falls below exp(−mean) (`gh1114-sim3.py:160-165`). [verified: read]
    - Past a mean of about 745, exp(−mean) underflows to 0, so the draft's count no longer tracks the mean. [unverified: the architect's reading of double-precision underflow]
28. Parity references, each pair t then sign-flip, at −0.05 then at 0:
    - `sim3-results.json`, recall at K 10 and 20 fixtures over 4,000 replicates. Normal harm gives 0.02475 and 0.02225, then 0.197 and 0.1895, at alpha 0.025, and 0.01175 and 0.0115, then 0.119 and 0.11375, at 0.0125. Concentrated harm gives 0.03275 and 0.031, then 0.17475 and 0.169, at 0.025, and 0.0175 and 0.01725, then 0.1165 and 0.111, at 0.0125.
    - `sim4-precision-5pp-results.json`, precision at delta 0.05 and 20 fixtures over 2,000 replicates: 0.0355 and 0.037, then 0.412 and 0.418, at 0.025, and 0.022 and 0.021, then 0.3155 and 0.3175, at 0.0125.

    `gh1114-sim4.py` is `gh1114-sim3.py` with `PRECISION_DELTA = 0.05` (`:25`). [verified: reads of both result files and both drafts in `~/.local/state/gh1114-src/`, for this PR] The port differs from the drafts in its exact sign-flip at 20 fixtures and its solver weight. That neither moves a rate past Verification step 6's bounds is [unverified].
29. The scope split: the engineer selected [engineer-verified: "Apply the split (Recommended)"]. The label covers only the split. It does not choose PR 2's remedy (row 26).
    - Asked whether to keep the sparse-findings regime in this PR, the engineer answered "Ask the architect".
    - The architect's consult recommended keeping the degenerate-terms guard tests and moving the `--fixtures-with-findings` parameter, its sparse sweep and the sparse-regime Verification run to PR 2. [unverified: the architect's recommendation, the session's content]
    - The session then asked "Apply the architect's split?", saying three things in its own words:
      - this PR keeps the guard tests and drops the parameter and its sweep;
      - the sparse-regime rate run moves to PR 2;
      - the "Measure only" answer would then cover pinned and derived behaviour.
30. Calibrate caps `--workers` at the pool's own default worker count (M7).
    - `ProcessPoolExecutor` defaults to `os.process_cpu_count() or 1` workers (CPython 3.14.10 `concurrent/futures/process.py:759-760`). [verified: read, for this PR]
    - `os.process_cpu_count()` returns the number of CPUs the process may use, or None when that cannot be determined (`os.py:1180-1191`). [verified: read, for this PR]
    - The pool starts its workers at the first cell's `map`, so a mistyped count has started that many interpreters, each importing `review_bench`, before anyone can act on the stderr plan. [unverified: plan-review round 2's backend reviewer, reasoning from `process.py`]
31. Interrupts and the worker pool, in CPython 3.14.10:
    - A forkserver child restores the handlers the forkserver process held before it set SIGINT to ignored (`multiprocessing/forkserver.py:253-260`, `:379-383`). [verified: read, for this PR]
    - Those include Python's default SIGINT handler, so a worker keeps it from its start until the pool's initializer runs. [verified: read, by plan-review round 2's backend reviewer at `forkserver.py:249-258` and `:379-383`]
    - That a terminal Ctrl-C, which reaches the whole foreground process group, then kills a worker with a traceback and breaks the pool is [unverified: a plan reviewer's reasoning from source, not run]. Without the initializer that window would be the worker's whole life. Verification step 8 checks the initializer end to end.
    - `ProcessPoolExecutor.terminate_workers()` (`concurrent/futures/process.py:1027-1036`) calls `shutdown(wait=False, cancel_futures=True)` and then terminates each live worker (`:978-1025`). [verified: read, for this PR]
    - `Executor.__exit__` calls `shutdown(wait=True)` without cancelling (`_base.py:672-673`). [verified: read, for this PR] That an exception leaving the `with` any other way therefore waits for every running chunk is [unverified: plan-review round 2's backend reviewer's reading].
    - `ProcessPoolExecutor.map` takes a chunk size, default 1 (`process.py:920`), and `multiprocessing.Pool.map` defaults it to ceil(jobs / (4 · workers)) (`multiprocessing/pool.py:481`). [verified: read, for this PR] At 20 fixtures a replicate costs about as much as a job's IPC (row 20), so a chunk size of 1 would waste most of `--workers 4`. [unverified: a plan reviewer's estimate]
32. `defects.atomic_write_text` (`defects.py:219-228`) creates the parent directory, writes `<name>.tmp-<pid>` beside the target and replaces the target with it. `analyze` and `freeze` write through it (`run_review_bench.py:1913`, `:2032`). [verified: reads, for this PR] Calibrate reuses it rather than writing a second temp-file replace.
33. `student_t_upper_quantile` states its accuracy for `upper_tail >= 1e-6` only and degrades without raising below it (`analysis.py:438-440`). It raises once 1 − 2·upper_tail rounds to 1.0 (`:445-447`). [verified: read, for this PR] This PR edits no line of `analysis.py` (M6), so calibrate repeats the floor as a named constant that cites the docstring.
34. `main()` catches only `HarnessInvalidatedError`, `InvalidIdentifierError`, `UnsafeFixtureConfigError`, `RunStoreLocked` and `KeyboardInterrupt` (`run_review_bench.py:2337-2347`), so any other exception exits 1 with a traceback. A handler reports its own refusal with its subcommand's prefix and returns 2, as `confirm` does (`:902-904`). `random.binomialvariate` raises ValueError for p outside [0, 1] (CPython 3.14.10 `random.py:819`), so catching every ValueError would report a generator bug as a bad configuration. [verified: reads, for this PR]
35. The separated-scenario sweep test (Critical files) runs at normal harm, delta 0.4, 12 fixtures and k 50, where both statistics' rates sit far from its bounds.
    - At a true difference of −delta the false-adopt rate is about alpha whatever delta is, so a CI test can bound it but not pin it at 0. [unverified: the architect's reasoning]
    - The SDET measured that false-adopt rate at 0.020 to 0.023 for recall and 0.031 to 0.042 for precision. [verified: the SDET's scratch runs this session, its own port of the generator and solver over the worktree's statistics, 1,500 to 3,000 replicates]
    - At 0.042, 6 or more adoptions in 20 replicates, which the 0.25 bound fails, has a chance of about 1.2e-4. [verified: the architect's binomial arithmetic]
    - At a true difference of 0, one fixture's recall difference has an SD of 0.121, and the t-interval's lower limit sits near −0.077. Power was 1.0000 for both statistics and both metrics. [verified: the SDET's scratch runs this session] Every `null_centered` value then sits near +0.4. [unverified: the architect's arithmetic]
    - Each mutation the test exists to catch fails it in those runs. Swapped arms gave a false-adopt rate of 1.0. A gate left at `analysis.DELTA` gave power 0.23 for recall and 0.54 for precision. A builder left at `analysis.DELTA` gave sign-flip power 0.26 and 0.57. [verified: the SDET's scratch runs this session]
    - Concentrated harm gave power 0.9997 for recall and 0.98 for precision. [verified: the SDET's scratch runs this session] At 0.98 a 20-of-20 requirement fails on about a third of seeds (1 − 0.98^20 ≈ 0.33), so the test pins normal harm. [verified: the architect's arithmetic]

## Critical files

This PR is one dispatch, Dispatch 2, because its four files share one design and its tests drive the module and the handler together. Dispatch 1 shipped in #1565. The session runs `/code-review` and commits Dispatch 2. Line numbers are base lines.

**Before Dispatch 2:** commit this plan (plan-it Step 7).

**Dispatch 2: calibrate.** Verify with `scripts/venv-run.sh pytest evals/test_review_bench_calibrate.py` and `scripts/venv-run.sh ruff check evals/review_bench/calibrate.py evals/run_review_bench.py evals/test_review_bench_calibrate.py`.
- New `evals/review_bench/calibrate.py` (M7). Port the drafts' generators and shift solvers; do not copy their script structure.
  - Reuse from `analysis`: `recall_fixture_terms`, `precision_fixture_terms`, `fixture_t_interval`, `sign_flip_p_value`, `FixtureTerms`, `DefectRecallCounts`, `DefectPrecisionCounts`, `DELTA`, `ALPHA_ONE_SIDED`, `SIGN_FLIP_RESAMPLES` and `SIGN_FLIP_EXACT_MAX_FIXTURES`.
  - Reuse `arms.ARM_CURRENT_RULE` and `arms.ARM_FUNCTION_CONTEXT` (`arms.py:15-16`) as the two arm names.
  - Reuse `defects.atomic_write_text` (`defects.py:219-228`) for every `--out` write (row 32).
- `evals/run_review_bench.py` (M8). Reuse `_positive_int` (`:51-55`), and follow `cmd_snapshot_arms`'s shape (`:1125-1135`).
- `evals/README.md` (M9).
- New `evals/test_review_bench_calibrate.py`. Every sweep in it is tiny and runs with workers 1 unless a case says otherwise. Each statistical bound is about four standard errors. A case with workers 2 patches `os.process_cpu_count` to return 2, so no case depends on the runner's CPU count.
  - Scenario and generator:
    - A fixture's latent draws, over 20,000 seeded fixtures, match literal expected values, not the module's constants: the recall baseline's mean 0.5 and SD 0.310, the precision baseline's mean 0.6 and SD 0.185, noise SDs of 0.1 for recall and 0.05 for precision, λ's mean 4 and the volume factor's mean 1.
    - Precision's mean finding total per arm is 1 + 4K at k 10 and 20, and every arm's total is at least 1 in every draw.
    - The Poisson sampler's sample mean and variance match the mean at means 0.5, 10 and 800.
    - Hand-picked latent draws give exact arm X rates: clipping at 0 and at 1 under normal harm, and max(0, p1 − 0.5) under concentrated harm for a harm uniform of 0.05, but normal harm for 0.5.
    - Every fixture the rule does not act on has arm X's rate equal to its baseline rate and a volume factor of 1.
  - Solver:
    - For each metric and harm, at share 1.0 and 0.5, the estimand over 4,000 fresh latent draws, seeded apart from the solver's, equals target · F / acted. For recall the estimand is the mean of arm X's rate minus the baseline rate, and for precision that difference weighted by 1 + K·λ. Four standard errors at these sizes sit well inside the 0.05 gap a missing F / acted factor opens at share 0.5.
    - The solver's draw count is a keyword parameter of the solver and the sweep, defaulting to the module constant, so every sweep in this file uses a small one. The CLI has no flag for it, so the CLI cases patch the module constant, and the solver reads that constant at call time rather than binding it as a default.
    - Share 0.2 at 20 fixtures solves, with 4 acted fixtures and an acted target of −0.25. Share 0.05 leaves one acted fixture and an acted target of −1.0, and raises `CalibrationConfigError` naming the cell before any replicate runs.
    - Acted counts, as a parametrized table of (F, share, acted): (20, 1.0, 20), (20, 0.5, 10), (5, 0.5, 3) where a half rounds up, (20, 0.05, 1), and (6, 0.01, 1) at the minimum.
  - The per-replicate decision function, driven by hand-built terms:
    - All fixtures far above −delta adopt under both statistics, all far below adopt under neither, and None is undefined and not adopted.
    - Terms with estimate −0.07 and small residuals, with `null_centered` built for each delta as M4 builds it, adopt under both statistics at delta 0.10 and under neither at 0.05.
    - The exact −delta boundary: six fixtures with estimate −0.05, the float −delta, and residuals and `null_centered` all 0. The lower limit equals −delta and p is 1.0, so neither adopts, which pins the strict `>`. `precision_fixture_terms` need not produce these terms (row 25).
  - Degenerate terms through `precision_fixture_terms`, the guard deferred from #1565 (DEFER row 7accfcdfc25a; ledger row 25). Hand-built `DefectPrecisionCounts` give six fixtures of one defect each, with every finding in the first, at delta 0.05 and alphas (0.025, 1/64, 0.0125). Each case feeds `precision_fixture_terms`' output into calibrate's per-replicate decision function and asserts that function's floats and adopt flags. The class docstring says in one line that these characterize a known weakness of the statistics on such terms, so a remedy inverts them.
    - 6/10 against 8/10: both interval ends equal the estimate, about −0.20, p is exactly 1.0, and neither statistic adopts at any alpha. This is the session's scratch case.
    - 14/25 against 15/25: the lower limit is above −delta and p is exactly 1/64. The t-interval adopts at every alpha. The sign-flip adopts at 0.025 and at 1/64, which pins `p <= alpha`, and not at 0.0125.
    - The same counts over five fixtures: p is exactly 1/32, so at 0.025 the t-interval adopts and the sign-flip does not.
  - Aggregation: hand-built replicate results, one undefined and two whose flags differ by alpha, give `undefined_replicates` 1 and each alpha's rates over all three replicates.
  - Sweeps:
    - A separated scenario for each metric, at normal harm, delta 0.4, 12 fixtures, k 50 and 20 replicates: the false-adopt cell's rates are at most 0.25 under both statistics, and the power cell's are 1.0 (row 35). Swapped arms, a gate or builder left at `analysis.DELTA`, or an adopt flag that never fires each fail it.
    - A recall sweep at 6 fixtures and 3 replicates gives two rows, true difference −delta then 0, with `acted_fixtures` set.
    - A precision sweep with concentrated harm and share 0.5 at 6 fixtures gives two rows with `acted_fixtures` 3, rates in [0, 1] and exactly the planned key set, so no worker or timing field leaks.
    - 21 fixtures with 200 flips and 2 replicates take the Monte Carlo path.
    - A sweep whose parent-side aggregation raises on its second cell, in three cases: workers 1 with a KeyboardInterrupt, workers 2 with a KeyboardInterrupt, and workers 2 with a ValueError. The same exception object propagates, the `--out` array holds one row equal to the one printed row, and no `.tmp-` file remains. With 2 workers a spy on the pool's `terminate_workers` saw one call.
    - An `--out` path beneath a regular file raises OSError, and a spy on the metric's M4 builder saw no call, so no replicate ran.
  - Workers and seeds. Each comparison covers every replicate's estimate, lower limits and p-value, not only its flags:
    - The worker function and one job survive a `pickle` round trip.
    - Running a cell's jobs in reversed order gives each job the same result, and running the same config twice gives identical results.
    - A cell's results from a 2-worker pool equal its in-process results.
    - A pool from the sweep's own pool constructor reports SIGINT as ignored inside its worker.
    - The replicate seed string changes with the run seed and with each of metric, k, harm, share, fixture count, true difference and replicate index. It does not change with alphas, flips or workers.
    - Two jobs that differ only in the run seed give different estimates and lower limits, and so do two that differ only in replicate index. This comparison leaves the p-value out, since at few fixtures two draws can share one.
  - CLI:
    - `build_parser().parse_args(["calibrate", …])` over two fixture counts, alphas 0.025 and 0.0125, `--flips 200` and an `--out` path under a missing directory, followed by `cmd_calibrate`, returns 0. Its stdout JSON lines equal the `--out` array, the directory exists, and each row carries both alphas and `cells_planned` 4. A spy on `analysis.sign_flip_p_value` saw `resamples=200` and no seed in every call.
    - One case passes a non-default value for every flag: `--metric precision --k 7 --fixtures 6 --alpha 0.05 --delta 0.2 --harm concentrated --over-cap-share 0.75 --replicates 3 --seed 11 --workers 2 --flips 200`, with `--out` naming an existing file of stale text. It returns 0, and every row echoes metric, k, harm, over_cap_share, delta, replicates, seed, flips, fixtures and alpha. The false-adopt row's `true_difference` is −0.2. A spy on the sweep's pool constructor saw 2 workers, and the `--out` file now holds exactly the printed rows. These values keep the acted target at −0.24, well inside the solver's bracket.
    - `--over-cap-share 0` returns 2, with a stderr message that starts `calibrate:` and names the field.
    - A sweep over 2 and 20 fixtures at share 0.05, whose second cell is unreachable, returns 2 with no row printed and no `--out` file written.
    - A ValueError raised inside the sweep propagates out of `cmd_calibrate` instead of returning 2.
  - Config validation, one parametrized case per rule at its boundary, each matching the field name in the message:
    - metric and harm outside their choices fail;
    - fixture count 1 fails and 2 passes;
    - alpha 0, 0.5 and just below `MIN_ALPHA` fail, while `MIN_ALPHA` and 0.4999 pass;
    - delta 0 and 1 fail and 0.5 passes;
    - share 0 and above 1 fail and 1.0 passes;
    - NaN fails for alpha, delta and share;
    - each positive-int field fails at 0;
    - with `os.process_cpu_count` patched to 2, workers 3 fails and 2 passes, and with it patched to None, workers 2 fails.

    Omitted delta, alphas and flips resolve to the `analysis` constants in the row.
  - A positive control in one test shows `"evals/review_bench/arms.py"`, which `analysis` imports, is a key of `analysis.compute_harness_closure()` while `"evals/review_bench/calibrate.py"` is not. The keys are repo-relative strings, so a Path-typed probe would pass vacuously.

This change only reads `evals/review_bench/analysis.py`, `evals/review_bench/arms.py`, `evals/review_bench/defects.py` and `claude/.claude/scripts/select-tests.py` (rows 6, 17, 32).

Projected diff: about 1,270 lines. That is about 415 in `calibrate.py`, 65 in `run_review_bench.py`, 3 in `evals/README.md` and 790 in the new test file (row 23).

## Verification

1. Scoped suite: `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py` passes. It selects every evals test target for this diff, and the skills tests for `evals/README.md` (row 17).
2. Lint: `scripts/venv-run.sh ruff check evals/` is clean.
3. No verdict or frozen-field change: `git diff --name-only origin/main...HEAD` lists only this plan file and the four Critical files. No closure module and nothing under `evals/replay_bench` changes (rows 6 and 7).
4. The closure fact: Dispatch 2's closure test passes in step 1, so `calibrate.py` stays out of every frozen field (row 6).
5. Worker independence, which CI exercises only at 6 fixtures and 2 replicates. These commands, like steps 6 to 8, run no model and cost nothing:
   - Run `scripts/venv-run.sh python3 evals/run_review_bench.py calibrate --metric recall --k 10 --fixtures 20 --fixtures 30 --replicates 200 --workers 1 --out evals/review_bench/.local/calibration/w1.json`.
   - Run the same with `--workers 4 --out evals/review_bench/.local/calibration/w4.json`.
   - `cmp evals/review_bench/.local/calibration/w1.json evals/review_bench/.local/calibration/w4.json` exits 0.
   - Record both runs' wall-clock times and each cell's solve time from stderr in the PR body, replacing row 20's estimates.
6. Parity with the drafts, which CI cannot exercise. These runs measure the false-adopt and power rates #1565 left unverified (Context); record every rate in the PR body. The reference rates are row 28's. Each bound is about three standard errors of the difference between two independent binomial rates, at the draft's rate and both runs' replicate counts. A miss means re-reading the port against the draft before any tolerance changes.
   - `scripts/venv-run.sh python3 evals/run_review_bench.py calibrate --metric recall --k 10 --fixtures 20 --replicates 4000 --alpha 0.025 --alpha 0.0125 --workers 4`: each false-adopt rate stays within 0.0105 of the draft's at 0.025 and 0.0073 at 0.0125, and each power rate within 0.027 and 0.022.
   - The same command with `--harm concentrated`: each false-adopt rate within 0.012 and 0.0088, and each power rate within 0.026 and 0.022.
   - `scripts/venv-run.sh python3 evals/run_review_bench.py calibrate --metric precision --k 10 --fixtures 20 --replicates 4000 --alpha 0.025 --alpha 0.0125 --workers 4`: each false-adopt rate within 0.015 and 0.0121, and each power rate within 0.040 and 0.039.
7. `scripts/venv-run.sh python3 evals/run_review_bench.py calibrate --metric precision --k 10 --harm concentrated --over-cap-share 0.5 --fixtures 20 --replicates 100` exits 0 and prints two rows, each with `acted_fixtures` 10.
8. Interrupt, run by the engineer in a terminal, because it needs a real Ctrl-C to the process group (row 31). Start step 5's `--workers 4` command with `--out evals/review_bench/.local/calibration/interrupt.json`, and press Ctrl-C once the first row prints. The command exits 130, stderr shows `calibrate: interrupted` and no worker traceback, and the `--out` file holds the rows printed before the interrupt.

## Out of scope

- **Changing #1565's statistics in `analysis.py`.** That includes how `precision_fixture_terms` treats a fixture with no finding, through its `null_centered` value and its place in the degrees of freedom, and any floor on fixtures that carry findings. An `analysis.py` edit would also move the closure hash (row 7).
  - The follow-up fix and PR 2 are the same PR: PR 2 measures the sparse regime's rates, picks a remedy from row 26's candidates and edits `precision_fixture_terms` and its tests, beside wiring the statistics into `analyze` (next item). [unverified: the plan's reading of Context's "move to PR 2 with the remedy"; the engineer's "follow up" names no PR]
  - [engineer-verified: "Measure only (Recommended)"] is the engineer's selected label when asked whether this PR should only measure the sparse-findings behaviour or also change `precision_fixture_terms`. After the split it covers pinned and derived behaviour (row 29): this PR pins the sparse regime's decisions with guard tests (row 25). It does not cover measuring the sparse regime's rates, which moved to PR 2.
  - [engineer-verified: "Can you add that fix as a follow up"] covers recording the fix as a follow-up. It does not choose the remedy.
- **Wiring the statistics into `analyze`.** That covers its report, the verdicts, certification, the ledger, error-budget slots, floors, and constants such as the 10-point precision delta. These belong to PR 2 (Context's Scope; the decision record). `calibrate.py` is the statistics' first non-test caller.
- **Any edit to `.claude/plans/measure-review-quality.md`** (Context's Scope). The decision record notes the engineer's earlier ruling against editing that stale plan.
- **A sparse-findings generator, its `--fixtures-with-findings` parameter and a sparse-regime rate run.** They move to PR 2 (row 29), and this PR's body carries row 26 as a note for PR 2.
- **Running the calibration sweeps PR 2 needs, or committing their output.** Verification's runs check the tool and measure parity at one point. Operator output stays under the gitignored `.local/`.
- **A bootstrap column in calibrate.** The agreed design retires the bootstrap as the decision statistic, and the drafts already measured it.
- **Several defects per fixture in the generator.** It needs a within-fixture correlation that has no basis yet. #1565's tests cover the multi-defect code path.
- **Changing the frozen-conditions design** (what `freeze` and `analyze` hash, and the smoke-hash precondition). This PR works within it and records its effect on the pilot (rows 6 and 7).
- **Raising `SIGN_FLIP_EXACT_MAX_FIXTURES`.** Meet in the middle would make about 30 fixtures cheap, but the agreed design says about 20 (row 2). PR 2 can take it up if wanted.
- **Review asks this plan declines**, one reason each:
  - Homing the degenerate-terms pins in `evals/test_review_bench_decision_statistics.py`: that file would join Critical files, which needs the engineer, and the pins run `precision_fixture_terms`' output through calibrate's per-replicate decision function, so they characterize calibrate's adopt decision, which Context places with this first adopting caller.
  - A case for the concentrated branch at a harm uniform of exactly 0.10: a continuous draw lands there with probability zero, so the comparison's strictness changes no rate.
  - A CI test that sends Ctrl-C to a live pool: its outcome depends on signal timing, so CI checks the worker initializer and an exception raised in the parent instead, and Verification step 8 checks the whole path.
  - Reporting a `BrokenProcessPool` after an interrupt as an interrupt: a worker ignores SIGINT only once its initializer runs, so only a Ctrl-C in the startup window after the first cell's `map` spawns the workers, or a group-wide SIGTERM or SIGHUP, can kill a worker first (row 31). That run exits 1 rather than 130, and `--out`, the durable output, still holds `[]` or its finished cells.
  - Upper bounds on `--k`, `--fixtures`, `--replicates` and `--flips`: no source gives a cap value, and the per-cell plan on stderr shows a mistyped size before the sweep starts.
  - A `timeout=` on the CI pool test's wait: a pool start-up fault still fails the job at its 30-minute limit (`.github/workflows/tests.yml:43`), so a bound buys a faster failure, not a caught defect, at the cost of a test-only sweep parameter.
  - A parity run above 20 fixtures: calibrate's code is the same at every fixture count, #1565's tests check the Monte Carlo path against the binomial tail (`evals/test_review_bench_decision_statistics.py:166`), and a 4,000-replicate cell pair at 30 fixtures costs about 10 minutes (row 20).
  - Naming `calibrate.py` beside the closure's exclusion notes (`analysis.py:993-994`, `evals/README.md:1032-1034`): they warn about edits that go undetected after freeze, and an edit to `calibrate.py` changes no verdict.
  - Documenting the owner-only umask and the `.local` check for calibrate: `main()` applies both to every subcommand alike (`run_review_bench.py:2330-2335`).
