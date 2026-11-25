# Sparse-findings sweep: one-arm-only findings in `calibrate`

## Context

Goal: let `calibrate` simulate the precision statistics' regime that the merged sparse-findings fix keeps and the generator cannot yet produce, which is fixtures with adjudicated findings in only one compared arm, so that a follow-up PR can measure the false-adopt and power rates there.

Ask: "No-floor generator option (Recommended)" and "20 with findings (Recommended)", the labels the engineer selected for PR 3's scope and the precision floor, after asking for an architect consult on scope. Later answers, by selected label: "Add the scale now (Recommended)" to whether PR 3 adds a finding-volume scale option (a second generator option, so `calibrate` can reach regimes sparser than k = 1), and "Accept both (Recommended)" to keeping the `docs/reports/` report with its README row and the `mixed` path plus `replicates_by_kept_fixtures` histogram fields. To the plan-review question whether to split a plan projecting about 420 changed lines, by selected label: "Split now". To whether the report moves to a follow-up PR pinned to this PR's squash-merge commit, by selected label: "Report in follow-up (Recommended)".

Why now: the merged fix (#1594) drops fixtures with no adjudicated finding in either compared arm, so the exact sign-flip's smallest p-value is 1/2^m for m fixtures carrying findings. The precision generator draws `1 + Poisson(volume)` findings per arm (`evals/review_bench/calibrate.py` near lines 345-352), so every simulated fixture carries a finding in both arms and the one-arm-only regime (kept by `evals/review_bench/analysis.py` near lines 580-590) is unmeasured. `calibrate.sign_flip_path`, `smallest_sign_flip_p_value` and `CalibrationConfig`'s alpha guard key on the planned fixture count F (near lines 83-92, 131-141, 247-253).

Once a replicate can hold fixtures without findings, only the row's `sign_flip_path` must describe the kept count m instead (live DEFER `f4833cda5e3a`). The alpha guard and the plan line run before any replicate exists, so they stay on F (row 5).

Intended outcome, this PR delivers:
- a `calibrate` option that removes the `1 +` floor;
- a finding-volume scale option that reaches regimes sparser than k = 1 (row 9 gives why k = 1 is not enough);
- the row's `sign_flip_path` rekeyed on the kept count m, with a kept-count histogram.

The follow-up PR owns the sweeps and the recorded synthetic result, and the rates stay unmeasured until it lands (row 20).

Out of scope for this PR, from the architect consult: the `analyze` wiring (separate PRs afterward), and the `--fixtures-with-findings` first-m generator, which reduces to the existing `--fixtures m` sweep after #1594 and was conditional in `.claude/plans/decision-statistics-calibrate.md` row 26. The architect's 150-250 line size estimate is unverified.

## Approach

`calibrate` gains two precision-only generator options:
- `--finding-floor {0,1}`, default 1, sets the findings every fixture gets in each arm before its Poisson draw.
- `--finding-volume-scale`, a float in (0, 1] with default 1.0, multiplies every fixture's expected finding volume in both arms.

At floor 0, a fixture can carry findings in one compared arm or in neither, so `precision_fixture_terms` can keep fewer fixtures than planned. A scale below 1 makes both cases common, where the floor alone leaves them thin (rows 9 and 24). Each replicate records how many fixtures its terms kept, and the row's `sign_flip_path` comes from those counts. A floor-0 row adds `finding_floor` and a histogram of kept counts, and a row at a scale below 1 adds `finding_volume_scale`. At the defaults, the stdout rows and the `--out` file stay byte-identical (row 6).

This PR stops at the code and its tests. A follow-up PR runs the sweeps and records the rates (rows 10 and 20).

Under recall, which draws no findings, `CalibrationConfig` rejects either option at any value but its default, naming its field. The two options are otherwise independent: a scale below 1 at floor 1 is valid, and every fixture there still carries a finding in both arms. Neither option enters the replicate seed or the shift solver, so runs that differ only in the options share what row 6 lists.

Alternatives set aside:
- **Drop the floor by default.** That would change the default rows that #1583 and #1594 measured, which row 14's byte-identity constraint rules out.
- **A boolean `--no-finding-floor`.** The integer feeds the total (`finding_floor + Poisson`) directly, and a row echoes it as a number. `choices=(0, 1)` bars any other value.
- **Rekey the alpha guard and the plan-line note on m.** Row 5 sets it aside.
- **Per-path counts, or rates split by kept count, in the row.** The histogram is the smallest record from which the path counts, each alpha's structural zeros (row 11) and the share below the verdict floor of 20 all follow. Split rates wait for a consumer (Out of scope).
- **Put either option into the replicate seed.** The seed must not change at the defaults, so an option could enter only conditionally. Leaving both out costs nothing, and it lets the follow-up's sweeps pair their cells at each fixture count they share (row 6).
- **Let precision's `k` take fractional values** instead of adding a scale. `k` is also recall's binomial run count and an int in the seed string (`calibrate.py:424`), so a fraction would change its meaning for both metrics.
- **Scale the Gamma's `FINDING_RATE_SCALE` inside `draw_latents`.** s · Gamma(2, 2) is Gamma(2, 2s), so it reaches the same volumes. But it threads a config value into the latent draws that the solver and both generators share, while `plan_fixtures` derives the volume on one line (row 28).
- **Apply the scale in `draw_precision_counts`, beside the floor.** `FixturePlan`'s volumes would then stop being the expected volumes its docstring names (`calibrate.py:280`).
- **Thread both options into `solve_shift`'s weight**, so the weight tracks the generator's expected finding count. Any weight on the finding latents alone solves the same shift up to draw noise (row 8). Threading would add two parameters, a rewritten `SOLVER_DRAWS` bound and a test, for no change in what a cell targets. It would also give cells that differ only in the options slightly different shifts, so their pairs would share latents but not rates.
- **Allow a scale above 1.** Integer k already reaches denser regimes, and the one-arm-only regime lies only at sparser ones.
- **Add the new tests to `evals/test_review_bench_calibrate.py`.** The file would cross 1,000 lines and need a new table row. That is the size check's third remedy, and its first remedy, a new test file, fits (row 16).
- **Cut the PR anywhere but between the code and the report.** Moving the scale, the `mixed` path or the histogram out would undo the engineer's choices for this PR (rows 26 and 27). Splitting M1 from M2 would put `calibrate.py` and both test files in two PRs. The report needs only fields this PR's rows carry (row 25), and the engineer chose its move (row 10).

### Assumption ledger

**Root:** `calibrate`'s precision generator gives every arm of every fixture at least one finding (`evals/review_bench/calibrate.py:346-352`). So no replicate holds a fixture with findings in only one compared arm or in neither. `precision_fixture_terms` keeps the first kind of fixture and drops the second (row 1). No sweep can therefore measure the false-adopt and power rates in that regime. Removing the floor alone would reach the regime only thinly, because the expected volume scales with k, an int of at least 1 (row 9). The row's `sign_flip_path` is keyed on F, which describes what ran only while every fixture is kept (DEFER `f4833cda5e3a`, row 19).

**Givens:**
- G1. On m values, the exact sign-flip test's smallest p-value is 1/2^m, and the Monte Carlo path's is 1/(resamples + 1) (`evals/review_bench/analysis.py:506-516`). Reason: the methods impose it.
- G2. Test data and the smoke runs' rows are synthetic, with no per-project dimension. Reason: the repository `CLAUDE.md`'s "Redact private-project-identifying content" governs every artifact, and changing that rule is outside this plan.

**Mechanisms:**
- **M1. The kept-fixture count**, in `calibrate.py`. Implement it first, so M4's Kept count case passes before M2 exists. Row path and Rows land with the rest of M4, because they build floor-0 configs.
  - `ReplicateResult` gains a required last field with no default, `kept_fixtures: int | None`. `decide_replicate` sets it to `len(terms.residuals)`, or to None when the terms are None. Add one docstring line: `` `kept_fixtures` counts the fixtures the terms cover, which can fall below the cell's fixture count when the finding floor is 0. ``
  - `sign_flip_path` and `smallest_sign_flip_p_value` rename their `fixtures` parameter to `value_count`. Their docstrings say "on this many `null_centered` values", which is the count `analysis.sign_flip_p_value` branches on (row 3). Every caller passes the argument positionally (row 23).
  - Add `SIGN_FLIP_PATH_MIXED = "mixed"` and `replicates_sign_flip_path(results)`. It reads the kept counts of the results whose `undefined` is false, the one test for a defined replicate that M1 and M2 use. It returns their common path when every count gives the same `sign_flip_path`, `SIGN_FLIP_PATH_MIXED` when the counts straddle the exact cap, and None when no result is defined. `summarize_cell` takes the row's `sign_flip_path` from it.
  - Below the alpha guard's comment (`:131`), add one line: `# A replicate's kept fixtures never exceed its fixture count, so the largest fixture count bounds every replicate's path.`

  anchors: root, row2, row3, row4, row5, row19, row23, row27
- **M2. The finding floor and the finding-volume scale**, in `calibrate.py`. Implement the floor's items before the scale's.
  - `CalibrationConfig` gains two fields, and each failure names its field.
    - `finding_floor: int = 1` must be an int that is not a bool and is 0 or 1.
    - `finding_volume_scale: float = 1.0` must satisfy `0 < finding_volume_scale <= 1`, as `over_cap_share`'s check does (`:126`), which also rejects NaN.
    - Each must hold its default unless `metric` is precision, because recall draws no findings.
  - `plan_fixtures` takes `finding_volume_scale: float = 1.0` and sets `baseline_volume = k * latents.finding_rate * finding_volume_scale`. Arm X's volume at `:303` inherits the scale unchanged (row 28).
  - `draw_precision_counts(rng, plans, *, finding_floor: int = 1)` draws each total as `finding_floor + draw_poisson(...)`. Its docstring reads: "Each arm's findings are finding_floor + Poisson(expected volume). At a floor of 1 every fixture carries a finding in both arms. At 0 a fixture can carry findings in one arm or neither."
  - `solve_shift` takes neither option, and `plan_cells` passes neither, so a cell's shift is the same at every floor and scale (row 8). Its docstring's last sentence becomes two: "Precision weights each draw by 1 + k * lambda, its expected finding count at the default finding floor and volume scale, as pooled precision does. `finding_rate` is drawn independently of the rates, so any weight on it alone gives the same shift up to draw noise, and the floor and scale stay out." The `SOLVER_DRAWS` comment (`:58-60`) stays as it is.
  - `plan_cells` adds `finding_floor=<n>` and `finding_volume_scale=<repr>` to every plan line.
  - `ReplicateJob` gains `finding_floor` and `finding_volume_scale` as its last fields, with no defaults, so a `ReplicateJob` built without them raises `TypeError`. `cell_jobs`, its only constructor, fills them from the config. `run_replicate` passes the scale to `plan_fixtures` and the floor to `draw_precision_counts`.
  - `replicate_seed` leaves both out. Add one docstring line: `` `finding_floor` and `finding_volume_scale` stay out too, so runs that differ only in them draw the same fixture latents. ``
  - `summarize_cell` adds fields only away from the defaults, after every existing key.
    - When `config.finding_floor == 0`, it adds `"finding_floor": 0` and `"replicates_by_kept_fixtures"`. The histogram counts the defined replicates by kept count, using M1's `undefined` test. It sorts by the integer count and then keys each entry by the count's string, so "9" precedes "10". String keys keep `run_sweep`'s returned rows equal to the rows read back from `--out`.
    - When `config.finding_volume_scale != 1.0`, it adds `"finding_volume_scale"` with the config's value.
    - Its docstring gains three lines:
      - "`sign_flip_path` is the defined replicates' path: `exact`, `monte-carlo`, `mixed` when their kept counts straddle the exact cap, or None when no replicate is defined."
      - "Only a floor-0 row carries `replicates_by_kept_fixtures`, because at floor 1 every replicate keeps every fixture."
      - "A row omits `finding_floor` and `finding_volume_scale` at their defaults, so an absent one means its default."

  anchors: root, row6, row7, row8, row12, row24, row26, row27, row28
- **M3. The CLI**, in `evals/run_review_bench.py`. Add two arguments after `--over-cap-share` (`:2316-2320`).
  - `--finding-floor` with `type=int`, `choices=(0, 1)` and `default=1`. Its help reads: "Precision only: the findings every fixture gets in each arm before its Poisson draw. At 0 a fixture can carry findings in one arm or neither."
  - `--finding-volume-scale` with `type=float` and `default=1.0`. Its help reads: "Precision only: a multiplier in (0, 1] on every fixture's expected finding volume in both arms. With --finding-floor 0, a smaller scale leaves more fixtures with findings in one arm or neither."
  - `cmd_calibrate` passes `finding_floor=args.finding_floor` and `finding_volume_scale=args.finding_volume_scale` beside `harm`.
  - argparse rejects a value its `type` or `choices` refuses, and `CalibrationConfig` rejects every other bad value (row 18).

  anchors: row12, row15, row18, row26
- **M4. Tests.**
  - In `evals/test_review_bench_calibrate.py`, three edits:
    - `TestSummarizeCell` (`:389-390`) passes `6` as each `ReplicateResult`'s last argument (row 22).
    - The `draw_precision_counts` spy (`:713-716`) takes and forwards `**kwargs` (row 21).
    - `test_every_flag_at_a_non_default_value_reaches_the_rows_and_the_pool` (`:758`) adds `--finding-floor 0` and `--finding-volume-scale 0.5` to its argv, `"finding_floor": 0` and `"finding_volume_scale": 0.5` to `echoed`, and both options to the plan-line tokens it checks.
  - The tests that pin the defaults stay unchanged: the floor-1 totals (`:96`, `:124`), the default row's exact key set (`:429`), the path at 20 and 21 fixtures (`:442`), and the four findings per unit of k (`:709`).
  - A new `evals/test_review_bench_calibrate_sparse_findings.py` imports only module-level helpers from `test_review_bench_calibrate`: `_config`, `_terms`, `SIGMA_BOUND` and `EXACT_CAP`. It imports no `Test*` class, because pytest would collect an imported test class a second time. It defines two module helpers: one builds a `ReplicateResult` from a kept count, undefined for None, and one computes the Draws case's population values. Its cases:
    - **Config**, as two parametrized tables over `_config` overrides:
      - Rejected, each raising `CalibrationConfigError` that names its field: under precision, a floor of 2, -1, `True` or `0.0` and a scale of 0.0, -0.25, 1.5 or NaN; under recall, a floor of 0 and a scale of 0.25.
      - Accepted, under precision: a floor of 0, a scale of 0.25 at floor 1, and both together.
      - `_config()` gives floor 1 and scale 1.0.
    - **Draws**, at scales 1.0 and 0.25. Setup: `plan_fixtures` at k = 1 and that scale over 20,000 acted fixtures, then `draw_precision_counts` at floor 0. Checks:
      - Given the plans: the shares of fixtures with findings in one arm only and in neither each lie within `SIGMA_BOUND` binomial standard errors of the plans' mean of `e^-b (1 - e^-x) + e^-x (1 - e^-b)` and of `e^-(b + x)`, where b and x are a plan's two volumes.
      - Population: the same two shares each lie within `SIGMA_BOUND` binomial standard errors of their population value at that scale. The helper evaluates row 9's formulas with the Gamma's shape and scale read from `calibrate.FINDING_RATE_SHAPE` and `FINDING_RATE_SCALE`, averaged over 1,000 midpoints of `VOLUME_FACTOR_RANGE`. Its values are rows 9 and 24's.
      - Three direct checks:
        - both shares are above 0;
        - the mean total per arm is 4k times the scale;
        - the smallest total is 0.
    - **Shared latents.** `run_replicate` runs a default precision job at k = 1 and 6 fixtures, then the same job with `finding_floor=0` and `finding_volume_scale=0.25` through `_replace`. A `draw_precision_counts` spy records each run's plans. Each fixture's two rates are equal across the runs, and its two volumes in the second run are 0.25 times the first run's, by `pytest.approx`.
    - **Kept count.** `decide_replicate` on eight-residual terms records 8, and on None records None.
    - **Jobs reach the replicates**, with `Cell(8, 8, true_difference=0.0, shift=0.0)` and a floor-0, scale-0.25 precision config at k = 1, 8 fixtures and 30 replicates:
      - every job `cell_jobs` returns carries floor 0 and scale 0.25;
      - after `run_jobs`, at least one defined replicate's `kept_fixtures` is below 8;
      - the `summarize_cell` row's `replicates_by_kept_fixtures` values sum to `replicates - undefined_replicates`, and every key is at most 8;
      - the same cell under floor 1 at scale 0.25 gives `kept_fixtures` 8 for every replicate, so real draws at a scale below 1 check row 4's floor-1 claim. The tests that pin the defaults and Verification step 3's `cmp` cover the default configuration.
    - **Row path**, asserted on `summarize_cell`'s `row["sign_flip_path"]` under a floor-0 precision config and `Cell(fixtures=30)`:
      - kept counts (20, 20) and (19, 20) give exact, (21, 21) and (21, 22) give monte-carlo, (undefined, 20, 21) give mixed, and two undefined give None;
      - a row keyed on the cell's fixture count reads monte-carlo at 30, so the exact, mixed and None cases each fail it;
      - a helper that returns mixed whenever the kept counts differ, rather than whenever their paths differ, fails the (19, 20) and (21, 22) cases;
      - no fixture count at or below the cap can hold 21 kept fixtures (row 2), so the monte-carlo cases share the cell's side of the cap and, with the exact cases, pin the threshold.
    - **Rows**, under a floor-0 precision config and `Cell(fixtures=12)`, with results kept 10, undefined, kept 9 and kept 10, in that order:
      - `list(row["replicates_by_kept_fixtures"].items())` equals `[("9", 1), ("10", 2)]`, where an insertion-ordered or string-sorted histogram would put "10" first;
      - `row["sign_flip_path"]` is exact, because kept counts 9 and 10 differ but both take the exact path;
      - the row carries `finding_floor` 0 and no `finding_volume_scale`;
      - the same results under a floor-1 config at scale 0.25 give `finding_volume_scale` 0.25 and neither floor-0 field. A comment marks these results as hand-built, since floor 1 keeps every fixture, so this check covers only the config's gating;
      - the default row's exact key set (`:429`) already pins that the defaults add none of the three fields.
    - **Planned cells**, at scales 1.0 and 0.25: a floor-0 precision cell at k = 1, 20 fixtures, an over-cap share of 0.25, delta 0.1, 400 replicates and 20,000 solver draws, with the sign-flip stubbed as at `:684`, has every replicate defined. Its mean estimate lies within `SIGMA_BOUND` standard errors of each cell's true difference (row 29).
  - The new file holds no sweep-level or CLI-level case for the options, because existing tests and the cases above already carry those assertions (row 18).

  anchors: row2, row3, row4, row6, row9, row10, row16, row18, row21, row22, row24, row28, row29
- **M5. The size table.** After Verification step 1's fetch and any merge, act on every line `test_code_file_sizes` prints for a file this branch changed. The expected line is `evals/run_review_bench.py`'s. Write its printed ceiling into the row at `code-file-size-exceptions.toml:506-507` (row 15). `calibrate.py` and both test files stay under 1,000 lines, so none of them gets a row.

  anchors: row15, row16

**Rows:**
1. `precision_fixture_terms` keeps a fixture with a finding in one compared arm only, and drops a fixture with no finding in either. It returns None when fewer than two fixtures are kept, or when either arm has no finding at all. `len(residuals)` is the kept count. [verified: read of `analysis.py:584-593`, `:603-626`]
2. The kept count never exceeds F, because the drop only removes fixture groups (`analysis.py:603-608`). `calibrate` gives each fixture one defect (`calibrate.py:428-429`). [verified: read]
3. `sign_flip_p_value` chooses its path by the number of values it receives: exact at or below `SIGN_FLIP_EXACT_MAX_FIXTURES`, which is 20 (`analysis.py:47`), and Monte Carlo above it (`analysis.py:506-508`). So a replicate's path is a function of its kept count. [verified: read]
4. At floor 1, every replicate keeps all F fixtures in both metrics, so the row's path is `sign_flip_path(F)`, as it is today. [verified: read]
   - Precision totals are at least 1 in each arm, whatever the volume scale (`calibrate.py:351-352`).
   - `recall_fixture_terms` drops no fixture, and it returns None only below two fixtures (`analysis.py:547-549`).
   - Every fixture count is at least 2 (`calibrate.py:118-119`).
5. The plan-time sites stay true keyed on F, because F bounds every m from above (row 2). Each runs before any replicate draws its m, and F is the only count it has. [verified: read of `calibrate.py:131-141`, `:247-253`; the implications are arithmetic]
   - When the largest F is at most the cap, every replicate takes the exact path, which is all the alpha guard needs.
   - When 2^-F exceeds an alpha, 2^-m exceeds it for every replicate, so the plan-line note stays true. The note states only that F-level bound. At floor 0 a cell can hold replicates whose m cannot adopt at an alpha F can (row 11), and only the row's histogram shows them.
   - The plan line's `sign_flip_path=` token states F's path, and the row's `sign_flip_path` states the replicates' path, so the two can differ at floor 0. For example, F = 21 with every defined replicate at m ≤ 20 prints `monte-carlo` on the plan line and `exact` in the row.
6. At the default floor and scale, the stdout rows and the `--out` file stay byte-identical. [unverified until Verification step 3's `cmp`, a one-time check for this PR]
   - `finding_floor + draw_poisson(...)` with the int 1 makes the same RNG calls and gives the same ints as `1 + draw_poisson(...)`.
   - `k * latents.finding_rate * finding_volume_scale` evaluates as `(k * latents.finding_rate) * 1.0`, and IEEE 754 multiplication by 1.0 returns its operand exactly. So every volume is the same float, and `draw_poisson` makes the same RNG calls.
   - `solve_shift` and every input it reads are unchanged (row 8).
   - The seed string is unchanged.
   - The row's path is unchanged, by row 4.
   - No field is added.
   - Stdout prints each row dict with `json.dumps`, and the `--out` file holds the same dicts (`calibrate.py:549-552`). So byte-identical `--out` files imply byte-identical stdout rows.
   - Stderr is outside the claim, because it already carries timings (`calibrate.py:271-272`).
   - `run_replicate` draws every fixture's latents before any count (`calibrate.py:293-305`, `:439-451`), and neither option reaches the seed or the solver. So runs differing only in the floor or the scale share every fixture's latents, each cell's shift and so every fixture's two rates, while their counts differ. [verified: read]
7. A zero total is safe. `draw_poisson` returns 0 when the first arrival passes the mean (`calibrate.py:313-318`). `random.binomialvariate(0, p)` returns 0 for every p (CPython 3.14.10 `Lib/random.py:812-845`). [verified: read]
8. The shift solver needs neither option. `finding_rate` and `volume_factor` are drawn independently of the rate latents (`calibrate.py:172-181`), so E[w·d]/E[w] = E[d] for any weight that depends on those two alone. Every floor's and scale's expected finding count is such a weight. [verified: read; the consequence is algebra]
   - So `solve_shift` keeps `1 + k * lambda`, and the `SOLVER_DRAWS` comment's bound (`calibrate.py:58-60`) stays exact.
   - `plan_cells` passes neither option, so a cell's shift is the same float at every floor and scale.
   - Only the docstring's "its expected finding count" needs narrowing, to the default floor and scale (M2).
9. At k = 1 with the floor at 0 and the default scale, about 14% of acted fixtures carry findings in only one arm and about 4% in neither. That puts about 15% of kept fixtures at one-arm-only. [verified: the closed form below, worked in this plan; M4's Draws case checks the generator against the same population values]
   - Gamma(2, 2)'s Laplace transform, (1 + 2t)^-2, gives P(an arm's total is 0) = (1 + 2av)^-2, with a = s · k at scale s and v that arm's volume factor (1 for the baseline). Both totals are 0 with probability (1 + 2a(1 + v))^-2.
   - Averaging (1 + 2au)^-2 over u uniform on [lo, hi] gives (1/(1 + 2a·lo) − 1/(1 + 2a·hi)) / (2a(hi − lo)). Arm X's u is v on [0.8, 1.2], and both arms' u is 1 + v on [1.8, 2.2].
   - At a = 1, P(baseline 0) = 1/9 ≈ 0.111, P(arm X 0) ≈ 0.113 and P(both 0) ≈ 0.040. So one-arm-only is 0.111 + 0.113 − 2 · 0.040 ≈ 0.144, which is 0.144 / 0.960 ≈ 0.150 of kept fixtures.
   - At k = 2, the two shares fall to about 6% and 1%.
   - The volume enters only as the product a = s · k, and k is an int of at least 1 (`calibrate.py:127-128`). So without a scale below 1, k = 1 is the sparsest regime the generator reaches.
10. This plan is cut to a `Projected diff:` below 400 changed lines. [engineer-verified: "Split now"]
    - The cut falls between the code and the report: the report moves to a follow-up PR pinned to this PR's squash-merge commit. [engineer-verified: "Report in follow-up (Recommended)"]
    - The report's `docs/reports/README.md` row and the sweeps move with it, because the row indexes the report and the sweeps exist only to produce its figures. [unverified: the plan's reading]
    - The projection is about 360 changed lines (Critical files), near the low end of the 350 to 430 that the architect's second consult, on splitting, gave the code and tests alone. [unverified: an estimate drafted from each edit against the current files] It reflects three trims:
      - The new file drops two cases whose assertions other tests carry (row 18).
      - It folds the floor and scale config cases into one table of rejected settings and one of accepted ones.
      - `solve_shift` takes neither option (row 8).
    - Those trims pay for M4's Jobs case and the Draws case's population check, and nothing moves to the follow-up.
11. On the exact path, the smallest kept count that can adopt is 6 at alpha 0.025 and 7 at 0.0125, because 1/32 > 0.025 ≥ 1/64 and 1/64 > 0.0125 ≥ 1/128. Smaller kept counts are structural zeros. [verified: arithmetic on G1]
12. Scope: [engineer-verified: "No-floor generator option (Recommended)"]. The option's description is the session's own: an option removing the `1 +` floor at low volume, the helper rekey, then the sweep and its record. [unverified: the session's proposal] The option removes the floor at every volume, and low k is where that bites (row 9). The sweep and its record land in the follow-up PR (row 10).
13. The verdict floor: [engineer-verified: "20 with findings (Recommended)"]. The quote covers the floor's value only. The constant lands with the `analyze` wiring (Out of scope). No code in this PR reads it, and the histogram lets the follow-up's report read each cell's share below it by row 25's denominator rule. The session's own description said sub-20 rates never reach a verdict, so the sparse sweep informs only the failure-mode picture. [unverified: the session's proposal]
14. Byte-identity at the default floor and scale is the dispatching session's constraint, not the engineer's words. [unverified: session constraint] This plan keeps it, because it keeps #1583's and #1594's default rows reproducible and lets step 3's `cmp` prove the default path untouched.
15. `evals/run_review_bench.py` is 2,421 lines against a ceiling of 2,421 (`code-file-size-exceptions.toml:506-507`), so M3 moves its row. [verified: Read of `:2420-2421` and of the table]
    - The check's first remedy, moving the new code into a new module (`claude/.claude/tests/code_file_size.py:415-418`), does not fit. The code is one argument on an existing subparser and one keyword in its handler.
    - Its second remedy, a subcommand split, is the row's backlog (Out of scope).
16. `evals/test_review_bench_calibrate.py` has 973 lines and no row, and M4's new cases, about 205 to 270 lines, would cross 1,000. M4's three edits there add only a few net lines. [verified: Read and table Grep]
    - The check's first remedy is a new test file (`code_file_size.py:416`).
    - Evals test modules already import helpers from sibling test modules, for example `evals/test_review_bench_decision_statistics.py:17`.
    - `select-tests.py` selects every `evals/test_review_bench*.py` (`claude/.claude/scripts/select-tests.py:93`, `:751`).
17. The repository allows only squash merges, which record a PR as one new commit on `main`. So no commit on this branch is an ancestor of `main` afterward, and a report pinned to a branch commit would cite a commit `main` does not hold. [verified: gh repo view, this session] `gh repo view --json squashMergeAllowed,mergeCommitAllowed,rebaseMergeAllowed` printed `{"mergeCommitAllowed":false,"rebaseMergeAllowed":false,"squashMergeAllowed":true}`.
18. The new file needs no sweep-level or CLI-level case, because other tests carry those assertions. [verified: read of `evals/test_review_bench_calibrate.py`, `evals/run_review_bench.py:1150-1158` and CPython 3.14.10 `Lib/argparse.py:2774-2785`]
    - Rows carrying both fields through the CLI: the every-flag test (`:758`), with M4's edit, echoes `finding_floor` and `finding_volume_scale` from its rows.
    - The key set a floor-0 or scale-0.25 sweep adds: M4's Rows case pins what `summarize_cell` adds, and `:429` pins the default row's keys. `run_sweep` builds every row through `summarize_cell`.
    - A histogram of real draws summing to the defined replicates: M4's Jobs case.
    - Each rejection has one owning layer:
      - argparse rejects a `--finding-floor` outside `choices=(0, 1)` or not an int, and a `--finding-volume-scale` that is not a float. `ArgumentParser.error` exits with status 2 (`argparse.py:2785`) inside `parse_args`, before `cmd_calibrate` runs, so a test sees `SystemExit(2)` and no return value. That is the library's own handling, so no case tests it.
      - `CalibrationConfig` rejects every value that parses but breaks its rule: either option off its default under recall, and a scale outside (0, 1], NaN included. `cmd_calibrate` returns 2 for every `CalibrationConfigError` (`run_review_bench.py:1156-1158`), and `:832` tests that path. M4's Config tables check that each message names its field.
    - The parsed defaults: `:795` runs recall with the required flags alone and asserts exit 0, which a CLI default other than 1 or 1.0 would fail under M2's recall check.
19. DEFER `f4833cda5e3a` reads "calibrate F-keyed helpers assume terms cover all planned fixtures; only the generator guarantees it", with its remediation deferred to the sparse generator PR. M1 closes it. [verified: read of the ledger row]
20. The floor-0 false-adopt and power rates, at both scales, stay unmeasured in this PR, and nothing in it states them. The follow-up PR's sweeps measure them, and its report is where they land (row 10). [unverified]
21. The `draw_precision_counts` spy at `evals/test_review_bench_calibrate.py:713-716` takes `(rng, plans)` only, so it fails on M2's keyword unless it forwards `**kwargs`. [verified: read]
22. `TestSummarizeCell` builds `ReplicateResult` positionally (`:389-390`), so a required last field needs both lines. [verified: read]
23. Every caller of `sign_flip_path` and `smallest_sign_flip_p_value` passes the count positionally (`calibrate.py:90`, `:133`, `:247`, `:270`, `:513`, and `evals/test_review_bench_calibrate.py:957`). [verified: Grep of `evals/`]
24. At k = 1 with the floor at 0 and the scale at 0.25, about 39% of acted fixtures carry findings in only one arm and about 25% in neither. So about 75% are kept, and about 52% of the kept ones are one-arm-only. [verified: row 9's closed form at a = 0.25, worked in this plan; M4's Draws case checks the generator against the same population values]
    - P(baseline total 0) = (1 + 0.5)^-2 = 4/9 ≈ 0.444, P(arm X total 0) ≈ 0.446 and P(both 0) ≈ 0.251. So one-arm-only is about 0.390, which is 0.390 / 0.749 ≈ 0.520 of kept fixtures.
25. Every figure the follow-up's report needs, as Out of scope's first bullet and row 13 list them, is a field of this PR's rows or arithmetic on those fields and on rows 9, 11 and 24. [verified: those lists against `summarize_cell`'s fields at `calibrate.py:500-524` and M2's additions]
    - The rates sit in `alphas`, and `fixtures`, `true_difference`, `finding_floor` and `finding_volume_scale` name each cell.
    - The share below the smallest adoptable kept count (row 11) and the share below the verdict floor (row 13) come from `replicates_by_kept_fixtures` and `undefined_replicates`, by one denominator rule:
      - A share that explains a rate has numerator `undefined_replicates` plus the histogram's counts below the threshold, and denominator `replicates`, which is the rates' own (`calibrate.py:497`, `:519-520`).
      - A share among defined replicates divides the histogram's counts below the threshold by `replicates` minus `undefined_replicates`, and the report labels it as such.
    - That the follow-up changes no code, and any item its own plan adds, is the plan's expectation. [unverified]
26. Adding the scale in this PR: [engineer-verified: "Add the scale now (Recommended)"]. The quote answers whether PR 3 adds a finding-volume scale option. Its name, range, default, placement and absence from the seed are this plan's design. [unverified: the plan's design choices] A sweep at a scale of 0.25 is the follow-up PR's (Out of scope).
27. The `mixed` path and the `replicates_by_kept_fixtures` histogram stay in this PR: [engineer-verified: "Accept both (Recommended)"]. The report's place comes from the later answer instead: the `docs/reports/` report moves to the follow-up PR, [engineer-verified: "Report in follow-up (Recommended)"]. Row 10 covers its README row.
28. The scale has one entry point in the generator. [verified: read of `calibrate.py:165-181`, `:288-318`, `:432-442`, and Grep of `evals/` for `plan_fixtures`]
    - `plan_fixtures` derives the baseline volume at `:297`, and arm X's volume is that volume times the volume factor at `:303`, so one multiplication scales both arms.
    - `draw_latents` (`:295`) never reads a volume, so the scale leaves every latent draw untouched. Only the count draws after it change, because `draw_poisson` makes one `expovariate` call per arrival plus one (`:313-318`).
    - Every `plan_fixtures` caller passes keywords: `run_replicate` (`:439-442`), the `_plan` helper (`evals/test_review_bench_calibrate.py:36-39`) and the planned-cells test (`:673-676`). No test patches `plan_fixtures`, so a keyword with a default keeps every caller working.
29. At any floor and scale, the pooled estimate's expectation is the cell's true difference, up to a second-order effect of the volume factor when only some fixtures are acted. Each arm's totals depend only on `finding_rate` and `volume_factor`, which are drawn independently of the rate latents (`calibrate.py:172-181`). Given the totals, each valid count is binomial on its fixture's rate (`:356-357`). [unverified: algebra; M4's planned-cells case measures it at both scales]

## Critical files

- `evals/review_bench/calibrate.py`: M1 and M2. Reuse `sign_flip_path` inside `replicates_sign_flip_path`, `_require` for both options' validation with `over_cap_share`'s range check (`:126`) as the scale's pattern, and `collections.Counter` for the histogram.
- `evals/run_review_bench.py`: M3. Reuse the `choices` pattern of `--harm` (`:2311-2315`), the float pattern of `--over-cap-share` (`:2316-2320`) and the explicit keywords at `:1150-1153`.
- `evals/test_review_bench_calibrate.py`: M4's three edits.
- `evals/test_review_bench_calibrate_sparse_findings.py`, new: M4's cases. Reuse the imported helpers and the spy shape at `evals/test_review_bench_calibrate.py:713-716`.
- `code-file-size-exceptions.toml` at the repository root: M5, the `evals/run_review_bench.py` row only.
- This plan file.

Dispatch split: one `code-writer` dispatch covers the first five files, in the order M1, M2's floor, then M2's scale. Its verification is Verification steps 2-5. It is not split further, because M1 and M2 both edit `calibrate.py` and both test files.

Overrun fallback: when Verification step 5's count reaches 400, the `code-writer` applies these trims in order and stops once the count falls below 400. Each keeps every named risk covered.
1. Drop the Config case's `_config()` default check. The exact key set at `evals/test_review_bench_calibrate.py:429` already fails a config whose floor or scale defaults off 1 or 1.0, because its row then carries an extra field.
2. Fold Kept count into the Rows case. Rows builds its four results with `decide_replicate`, from `_terms` of 10 residuals, None, `_terms` of 9 and `_terms` of 10 in that order, and asserts each result's `kept_fixtures`.
3. Drop the Draws case's given-the-plans check. Its population check runs the same `plan_fixtures` and `draw_precision_counts` path against rows 9 and 24's values.

If the count still reaches 400 after all three, the `code-writer` stops and reports it, cutting no further case.

Projected diff: about 360 changed lines, counting a modified line as one deletion and one addition, within a range of about 320 to 410. That is about 90 in `calibrate.py` (80 to 105), 14 in `run_review_bench.py`, 2 in the table, 18 in the existing test file and 235 in the new test file (205 to 270). Row 10 records how the cut reached it.

## Verification

1. Before the `code-writer` dispatch, on the unedited tree:
   - Run `git fetch origin main`. If `origin/main` has moved past the branch's base, merge it first.
   - Run `scripts/venv-run.sh pytest claude/.claude/tests/test_code_file_size.py::test_code_file_sizes` and keep every line it prints. This run is the merge-base reproduction that the global `CLAUDE.md`'s "Prove your change caused a failing check" bullet asks for.
   - Capture the default output: `scripts/venv-run.sh python3 evals/run_review_bench.py calibrate --metric precision --k 1 --fixtures 6 --fixtures 21 --replicates 200 --flips 2000 --out evals/review_bench/.local/finding-floor/precision-before.json`.
   - Capture it again with `--metric recall --k 10` and `recall-before.json`.
   - The 21-fixture cells run the Monte Carlo path through M1's path helper. If a capture is missed, run it from a merge-base worktree made by that same bullet's recipe, with `--out` naming this worktree's path. Output stays under the gitignored `evals/review_bench/.local/` (`.gitignore:48`).
2. After the dispatch, run two commands:
   - `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py` passes. The only allowed failures are `test_code_file_sizes` lines that step 1 also printed for files this branch did not change.
   - `scripts/venv-run.sh ruff check evals/` is clean.
3. Rerun step 1's two commands with `-after.json` names. Run the precision command once more with `--finding-floor 1 --finding-volume-scale 1.0` added and `precision-explicit.json`. `cmp` of each of the three files against the `-before.json` file of its metric prints nothing and exits 0. That proves row 6 for the `--out` files, and row 6 derives stdout from them. The check runs once, for this PR (Out of scope).
4. Run two smoke commands:
   - `scripts/venv-run.sh python3 evals/run_review_bench.py calibrate --metric precision --k 1 --finding-floor 0 --fixtures 21 --replicates 200 --flips 2000 --out evals/review_bench/.local/finding-floor/floor0-smoke.json`
   - The same command with `--finding-volume-scale 0.25` added, `--fixtures 30` in place of `--fixtures 21`, and `floor0-scale-smoke.json`.

   Check each file's rows:
   - Each row carries `"finding_floor": 0`, and only the second file's rows carry `"finding_volume_scale": 0.25`.
   - Its `replicates_by_kept_fixtures` values sum to `replicates` minus `undefined_replicates`, and at least one key is below `fixtures`.
   - Its `sign_flip_path` is `exact` only when every histogram key is at most 20, `monte-carlo` only when every key is above 20, and `mixed` otherwise.
5. Run `git add --intent-to-add evals/test_review_bench_calibrate_sparse_findings.py`, so that `git diff` counts the untracked new file. Then check `git diff --stat --merge-base origin/main`:
   - it lists only Critical files' paths, and the table diff changes only the `evals/run_review_bench.py` row;
   - its insertions plus deletions, less this plan file's, stay below 400, or Critical files' overrun fallback applies.

## Out of scope

- **The sweeps and their report**, owned by a follow-up PR planned to change no code (row 25). It runs at this PR's squash-merge commit on `main`, not at a commit on this branch, which a squash merge leaves off `main` (row 17). It owns:
  - three precision sweeps at k = 1 and alphas 0.025 and 0.0125, one at floor 0, one at floor 1 as a control, and one at floor 0 and a scale of 0.25. A starting point for their fixture counts is 6, 12, 20, 24 and 30 for the first two and 6, 12, 20, 30 and 40 for the third;
  - the dated report under `docs/reports/` that records the false-adopt and power rates, pinned to that commit, and its `docs/reports/README.md` row (row 10);
  - in that report, per alpha, each floor-0 cell's share of replicates whose kept count lies below the smallest that can adopt (row 11), counted by row 25's denominator rule, because neither the plan line nor the row's `sign_flip_path` shows it (row 5);
  - the checks that the report's figures equal its `--out` files and that it carries no timing or machine detail.
- **Wiring the terms into `analyze`**, including the verdict floor of 20 kept fixtures (row 13). Separate PRs follow (Context).
- **The `--fixtures-with-findings` first-m generator** (Context).
- **Rates split by kept count in the row.** The histogram lets the follow-up's report bound a cell's rate under the verdict floor, and no consumer needs more yet.
- **A per-row count of one-arm-only fixtures.** M4's Draws case checks the generator against rows 9 and 24's population shares, and the follow-up's report can cite them.
- **A test pinning the default rows' bytes.** Verification step 3 checks byte-identity once, which is all row 14's constraint asks of this PR.
- **Changing `precision_fixture_terms`' membership rule or `SIGN_FLIP_EXACT_MAX_FIXTURES`** (`analysis.py:47`). The generator exercises the rule as merged.
- **Splitting `evals/run_review_bench.py`** along its row's seam (`code-file-size-exceptions.toml:509`).
- **Main's failing size-check lines** for files this branch does not change. The check's did-not-change procedure owns them (`claude/.claude/tests/code_file_size.py:67-92`).
- **Committing any run's JSON rows.** Verification's captures and smoke runs stay under the gitignored `evals/review_bench/.local/`.
- **Documenting `--finding-floor` and `--finding-volume-scale` in `evals/README.md`** beyond their `--help` text.
- **Editing `.claude/plans/decision-statistics-calibrate.md` or `.claude/plans/sparse-findings-calibration.md`.**
