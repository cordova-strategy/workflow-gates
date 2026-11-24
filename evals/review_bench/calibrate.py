"""Calibration of the review bench's sign-flip test and fixture t-interval on
synthetic data. No model runs and nothing is spent: each replicate draws
per-defect counts for two arms, feeds them through `analysis`'s production
fixture terms, t-interval and sign-flip test, and records whether each
statistic adopts arm X. A cell's adopt rates are its false-adopt rate (true
difference of -delta) or its power (true difference of 0).

Only `run_review_bench.py`'s `calibrate` handler imports this module, so it
stays outside the harness closure that `freeze` and `analyze` hash. The
statistics are called as `analysis.<name>` so a test can spy on one.
"""
from __future__ import annotations

import concurrent.futures
import contextlib
import json
import math
import os
import platform
import random
import signal
import sys
import time
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import NamedTuple

from review_bench import analysis, defects
from review_bench.arms import ARM_CURRENT_RULE, ARM_FUNCTION_CONTEXT

METRIC_RECALL = "recall"
METRIC_PRECISION = "precision"
METRICS = (METRIC_RECALL, METRIC_PRECISION)
HARM_NORMAL = "normal"
HARM_CONCENTRATED = "concentrated"
HARMS = (HARM_NORMAL, HARM_CONCENTRATED)

SIGN_FLIP_PATH_EXACT = "exact"
SIGN_FLIP_PATH_MONTE_CARLO = "monte-carlo"
SIGN_FLIP_PATH_MIXED = "mixed"

# student_t_upper_quantile's docstring states its accuracy only for upper_tail >= 1e-6.
MIN_ALPHA = 1e-6

# Scenario parameters: synthetic design choices, not measurements of any real campaign.
RECALL_BASELINE_BETA = 0.8  # baseline recall rate ~ Beta(0.8, 0.8): U-shaped, mean 0.5
RECALL_NOISE_SD = 0.1  # per-fixture SD of arm X's rate around baseline + shift
PRECISION_BASELINE_MEAN = 0.6  # mean of the baseline precision rate
PRECISION_BASELINE_CONCENTRATION = 6.0  # Beta(mean * c, (1 - mean) * c) baseline precision rate
PRECISION_NOISE_SD = 0.05  # per-fixture SD of arm X's rate around baseline + shift
FINDING_RATE_SHAPE = 2.0  # lambda ~ Gamma(2, 2), mean 4: a fixture's findings per unit of k
FINDING_RATE_SCALE = 2.0
VOLUME_FACTOR_RANGE = (0.8, 1.2)  # arm X's expected finding volume as a multiple of the baseline's, uniform
CONCENTRATED_HARM_PROBABILITY = 0.10  # chance an acted fixture takes the large drop instead of a small shift
CONCENTRATED_HARM_DROP = 0.5  # the large drop, in absolute rate

# Latent draws per shift solve. A draw's difference lies in [-1, 1], so its variance is at most 1.
# Precision's weights 1 + k * lambda are independent of that difference and E[w^2] / E[w]^2 = 1 + 8k^2 / (1 + 4k)^2 < 1.5
# for lambda ~ Gamma(2, 2), so to first order the expected difference's SE is under sqrt(1.5 / SOLVER_DRAWS), about 0.004.
SOLVER_DRAWS = 100_000
SOLVER_SEED = "calibrate-shift-solver"
SHIFT_BOUND = 1.0  # the bisection brackets the shift in [-SHIFT_BOUND, SHIFT_BOUND]
SOLVER_TOLERANCE = 1e-6  # well below the draw count's own Monte Carlo error
SOLVER_MAX_BISECTIONS = 60  # a ceiling: width 2 reaches SOLVER_TOLERANCE in about 21 halvings

_ALPHA_UPPER_BOUND = 0.5  # student_t_upper_quantile's domain is 0 < upper_tail < 0.5


class CalibrationConfigError(ValueError):
    """A calibration setting is outside its valid range, or a cell cannot be reached."""


def _require(condition: bool, field: str, requirement: str, value: object) -> None:
    if not condition:
        raise CalibrationConfigError(f"{field}: {requirement}, got {value!r}")


def _require_positive_int(field: str, value: object) -> None:
    _require(isinstance(value, int) and not isinstance(value, bool) and value >= 1, field, "must be an int >= 1", value)


def sign_flip_path(value_count: int) -> str:
    """Which sign-flip test `analysis.sign_flip_p_value` runs on this many `null_centered` values."""
    return SIGN_FLIP_PATH_EXACT if value_count <= analysis.SIGN_FLIP_EXACT_MAX_FIXTURES else SIGN_FLIP_PATH_MONTE_CARLO


def smallest_sign_flip_p_value(value_count: int, flips: int) -> float:
    """The smallest p-value `analysis.sign_flip_p_value` can return on this many `null_centered` values."""
    if sign_flip_path(value_count) == SIGN_FLIP_PATH_EXACT:
        return 2.0**-value_count
    return 1 / (flips + 1)


@dataclass(frozen=True)
class CalibrationConfig:
    """One sweep's settings, validated on construction. `delta`, `alphas` and
    `flips` default to the production constants from `analysis`."""

    metric: str
    fixture_counts: Sequence[int]
    k: int
    replicates: int
    delta: float = analysis.DELTA
    alphas: Sequence[float] = (analysis.ALPHA_ONE_SIDED,)
    harm: str = HARM_NORMAL
    over_cap_share: float = 1.0
    seed: int = 0
    workers: int = 1
    flips: int = analysis.SIGN_FLIP_RESAMPLES
    finding_floor: int = 1
    finding_volume_scale: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "fixture_counts", tuple(self.fixture_counts))
        object.__setattr__(self, "alphas", tuple(self.alphas))
        _require(self.metric in METRICS, "metric", f"must be one of {METRICS}", self.metric)
        _require(self.harm in HARMS, "harm", f"must be one of {HARMS}", self.harm)
        _require(bool(self.fixture_counts), "fixture_counts", "must not be empty", self.fixture_counts)
        for fixtures in self.fixture_counts:
            _require(isinstance(fixtures, int) and fixtures >= 2, "fixture_counts", "each must be an int >= 2", fixtures)
        _require(bool(self.alphas), "alphas", "must not be empty", self.alphas)
        for alpha in self.alphas:
            _require(
                MIN_ALPHA <= alpha < _ALPHA_UPPER_BOUND, "alphas", f"each must be in [{MIN_ALPHA}, {_ALPHA_UPPER_BOUND})", alpha,
            )
        _require(0 < self.delta < 1, "delta", "must be in (0, 1)", self.delta)
        _require(0 < self.over_cap_share <= 1, "over_cap_share", "must be in (0, 1]", self.over_cap_share)
        for field in ("k", "replicates", "workers", "flips"):
            _require_positive_int(field, getattr(self, field))
        _require(
            isinstance(self.finding_floor, int) and not isinstance(self.finding_floor, bool) and self.finding_floor in (0, 1),
            "finding_floor", "must be an int that is 0 or 1", self.finding_floor,
        )
        _require(
            0 < self.finding_volume_scale <= 1, "finding_volume_scale", "must be in (0, 1]", self.finding_volume_scale,
        )
        if self.metric == METRIC_RECALL:
            _require(
                self.finding_floor == 1, "finding_floor", "must be 1 under recall, which draws no findings", self.finding_floor,
            )
            _require(
                self.finding_volume_scale == 1.0, "finding_volume_scale",
                "must be 1.0 under recall, which draws no findings", self.finding_volume_scale,
            )
        worker_cap = os.process_cpu_count() or 1
        _require(self.workers <= worker_cap, "workers", f"must be at most the usable CPU count {worker_cap}", self.workers)
        # Above the exact cap no alpha below the smallest attainable p-value can adopt, so a sweep would report a structural zero.
        # A replicate's kept fixtures never exceed its fixture count, so the largest fixture count bounds every replicate's path.
        largest_fixture_count = max(self.fixture_counts)
        smallest_p_value = smallest_sign_flip_p_value(largest_fixture_count, self.flips)
        _require(
            largest_fixture_count <= analysis.SIGN_FLIP_EXACT_MAX_FIXTURES
            or all(alpha >= smallest_p_value for alpha in self.alphas),
            "alphas and flips",
            f"with a fixture count above {analysis.SIGN_FLIP_EXACT_MAX_FIXTURES}, each alpha must be at least "
            f"1 / (flips + 1) = {smallest_p_value!r} (flips={self.flips})",
            self.alphas,
        )


def acted_fixture_count(fixtures: int, over_cap_share: float) -> int:
    """How many of a replicate's fixtures the rule acts on, a half rounding up
    and at least one."""
    # The shortest round-trip decimal keeps a product like 0.29 * 50 exactly 14.5 instead of 14.499999999999998.
    exact_acted = Fraction(repr(over_cap_share)) * fixtures
    return max(1, math.floor(exact_acted + Fraction(1, 2)))


@dataclass(frozen=True, slots=True)
class FixtureLatents:
    """The random draws behind one fixture, before any shift or harm applies.
    `noise` is standard normal and `harm_uniform` is U(0, 1). `finding_rate` and
    `volume_factor` matter to precision only."""

    baseline_rate: float
    noise: float
    harm_uniform: float
    finding_rate: float = 0.0
    volume_factor: float = 1.0


def draw_latents(rng: random.Random, metric: str) -> FixtureLatents:
    if metric == METRIC_RECALL:
        return FixtureLatents(
            baseline_rate=rng.betavariate(RECALL_BASELINE_BETA, RECALL_BASELINE_BETA),
            noise=rng.gauss(0, 1),
            harm_uniform=rng.random(),
        )
    return FixtureLatents(
        finding_rate=rng.gammavariate(FINDING_RATE_SHAPE, FINDING_RATE_SCALE),
        baseline_rate=rng.betavariate(
            PRECISION_BASELINE_MEAN * PRECISION_BASELINE_CONCENTRATION,
            (1 - PRECISION_BASELINE_MEAN) * PRECISION_BASELINE_CONCENTRATION,
        ),
        noise=rng.gauss(0, 1),
        harm_uniform=rng.random(),
        volume_factor=rng.uniform(*VOLUME_FACTOR_RANGE),
    )


def arm_x_rate(latents: FixtureLatents, shift: float, *, metric: str, harm: str) -> float:
    """Arm X's rate on a fixture the rule acts on. Both the generators and the
    shift solver call this, so a solved shift describes the generated data."""
    if harm == HARM_CONCENTRATED and latents.harm_uniform < CONCENTRATED_HARM_PROBABILITY:
        return max(0.0, latents.baseline_rate - CONCENTRATED_HARM_DROP)
    noise_sd = RECALL_NOISE_SD if metric == METRIC_RECALL else PRECISION_NOISE_SD
    return min(1.0, max(0.0, latents.baseline_rate + shift + noise_sd * latents.noise))


def solve_shift(
    metric: str, harm: str, *, k: int, acted_target: float, solver_draws: int | None = None,
) -> float | None:
    """The shift at which the acted fixtures' expected difference (arm X's rate
    minus the baseline rate) equals `acted_target`, or None when the target lies
    outside the differences the bracket's two ends reach. Precision weights each
    draw by 1 + k * lambda, its expected finding count at the default finding floor
    and volume scale, as pooled precision does. `finding_rate` is drawn independently
    of the rates, so any weight on it alone gives the same shift up to draw noise,
    and the floor and scale stay out."""
    draw_count = SOLVER_DRAWS if solver_draws is None else solver_draws
    rng = random.Random(SOLVER_SEED)
    draws = [draw_latents(rng, metric) for _ in range(draw_count)]
    weights = [1 + k * draw.finding_rate for draw in draws] if metric == METRIC_PRECISION else [1.0] * draw_count
    total_weight = sum(weights)

    def expected_difference(shift: float) -> float:
        return sum(
            weight * (arm_x_rate(draw, shift, metric=metric, harm=harm) - draw.baseline_rate)
            for weight, draw in zip(weights, draws, strict=True)
        ) / total_weight

    low, high = -SHIFT_BOUND, SHIFT_BOUND
    if not expected_difference(low) <= acted_target <= expected_difference(high):
        return None
    for _ in range(SOLVER_MAX_BISECTIONS):
        if high - low <= SOLVER_TOLERANCE:
            break
        midpoint = (low + high) / 2
        if expected_difference(midpoint) < acted_target:
            low = midpoint
        else:
            high = midpoint
    return (low + high) / 2


@dataclass(frozen=True)
class Cell:
    """One fixture count at one true gate-level difference, with its solved shift."""

    fixtures: int
    acted_fixtures: int
    true_difference: float
    shift: float


def _describe_cell(fixtures: int, true_difference: float) -> str:
    return f"fixtures={fixtures} true_difference={true_difference!r}"


def plan_cells(config: CalibrationConfig, *, solver_draws: int | None = None) -> list[Cell]:
    """Every cell, in order: for each fixture count the false-adopt cell (true
    difference -delta) and then the power cell (0). Solves and checks every shift
    before any replicate runs, writing one stderr line per cell."""
    cells = []
    for fixtures in config.fixture_counts:
        acted = acted_fixture_count(fixtures, config.over_cap_share)
        smallest_p_value = smallest_sign_flip_p_value(fixtures, config.flips)
        unattainable_alphas = [alpha for alpha in config.alphas if alpha < smallest_p_value]
        unattainable_note = (
            f" sign_flip_smallest_p={smallest_p_value!r} exceeds alpha {unattainable_alphas}, "
            "so the sign-flip adopt rate there is 0.0 by construction"
            if unattainable_alphas else ""
        )
        alphas_token = ",".join(repr(alpha) for alpha in config.alphas)
        for true_difference in (-config.delta, 0.0):
            acted_target = true_difference * fixtures / acted
            started = time.monotonic()
            shift = solve_shift(
                config.metric, config.harm, k=config.k, acted_target=acted_target, solver_draws=solver_draws,
            )
            if shift is None:
                raise CalibrationConfigError(
                    f"delta and over_cap_share: cell {_describe_cell(fixtures, true_difference)} needs the {acted} acted "
                    f"fixture(s) to differ by {acted_target!r}, which no shift in [-{SHIFT_BOUND}, {SHIFT_BOUND}] reaches"
                )
            cells.append(Cell(fixtures, acted, true_difference, shift))
            print(
                f"calibrate: cell {_describe_cell(fixtures, true_difference)} metric={config.metric} k={config.k} "
                f"harm={config.harm} over_cap_share={config.over_cap_share!r} acted={acted} "
                f"finding_floor={config.finding_floor} finding_volume_scale={config.finding_volume_scale!r} "
                f"replicates={config.replicates} alphas={alphas_token} sign_flip_path={sign_flip_path(fixtures)} "
                f"flips={config.flips} seed={config.seed} workers={config.workers} shift={shift:.6f} "
                f"solved in {time.monotonic() - started:.1f}s{unattainable_note}",
                file=sys.stderr,
            )
    return cells


@dataclass(frozen=True)
class FixturePlan:
    """One fixture's arm rates and expected finding volumes, before any count is drawn."""

    baseline_rate: float
    arm_x_rate: float
    baseline_volume: float
    arm_x_volume: float


def plan_fixtures(
    rng: random.Random, *, metric: str, harm: str, k: int, fixtures: int, acted_fixtures: int, shift: float,
    finding_volume_scale: float = 1.0,
) -> list[FixturePlan]:
    """Draws every fixture's latents and derives its rates and volumes. Past
    `acted_fixtures` the rule does not act, so arm X behaves as the current rule there."""
    plans = []
    for index in range(fixtures):
        latents = draw_latents(rng, metric)
        acted = index < acted_fixtures
        baseline_volume = k * latents.finding_rate * finding_volume_scale
        plans.append(
            FixturePlan(
                baseline_rate=latents.baseline_rate,
                arm_x_rate=arm_x_rate(latents, shift, metric=metric, harm=harm) if acted else latents.baseline_rate,
                baseline_volume=baseline_volume,
                arm_x_volume=baseline_volume * (latents.volume_factor if acted else 1.0),
            )
        )
    return plans


def draw_poisson(rng: random.Random, mean: float) -> int:
    """A Poisson count: the unit-rate exponential arrivals before `mean`. The
    standard library has no Poisson sampler, and the product-of-uniforms form
    stops tracking the mean once exp(-mean) underflows."""
    count = 0
    elapsed = rng.expovariate(1.0)
    while elapsed < mean:
        count += 1
        elapsed += rng.expovariate(1.0)
    return count


def defect_id_for_fixture(index: int) -> str:
    return f"fixture-{index}"


def draw_recall_counts(
    rng: random.Random, plans: Sequence[FixturePlan], *, k: int,
) -> dict[str, analysis.DefectRecallCounts]:
    """One defect per fixture, k completed runs per arm, drawn independently per arm."""
    counts = {}
    for index, plan in enumerate(plans):
        defect_id = defect_id_for_fixture(index)
        counts[defect_id] = analysis.DefectRecallCounts(
            defect_id=defect_id,
            found_by_arm={
                ARM_CURRENT_RULE: rng.binomialvariate(k, plan.baseline_rate),
                ARM_FUNCTION_CONTEXT: rng.binomialvariate(k, plan.arm_x_rate),
            },
            completed_by_arm={ARM_CURRENT_RULE: k, ARM_FUNCTION_CONTEXT: k},
        )
    return counts


def draw_precision_counts(
    rng: random.Random, plans: Sequence[FixturePlan], *, finding_floor: int = 1,
) -> dict[str, analysis.DefectPrecisionCounts]:
    """One defect per fixture. Each arm's findings are finding_floor + Poisson(expected volume).
    At a floor of 1 every fixture carries a finding in both arms. At 0 a fixture can carry
    findings in one arm or neither."""
    counts = {}
    for index, plan in enumerate(plans):
        defect_id = defect_id_for_fixture(index)
        total_baseline = finding_floor + draw_poisson(rng, plan.baseline_volume)
        total_arm_x = finding_floor + draw_poisson(rng, plan.arm_x_volume)
        counts[defect_id] = analysis.DefectPrecisionCounts(
            defect_id=defect_id,
            valid_by_arm={
                ARM_CURRENT_RULE: rng.binomialvariate(total_baseline, plan.baseline_rate),
                ARM_FUNCTION_CONTEXT: rng.binomialvariate(total_arm_x, plan.arm_x_rate),
            },
            total_by_arm={ARM_CURRENT_RULE: total_baseline, ARM_FUNCTION_CONTEXT: total_arm_x},
        )
    return counts


@dataclass(frozen=True)
class ReplicateResult:
    """One replicate's statistics and decisions, one entry per alpha in config order.
    An undefined replicate (no terms) has None statistics and adopts nothing.
    `kept_fixtures` counts the fixtures the terms cover, which can fall below the
    cell's fixture count when the finding floor is 0."""

    estimate: float | None
    lower_limits: tuple[float | None, ...]
    p_value: float | None
    t_interval_adopts: tuple[bool, ...]
    sign_flip_adopts: tuple[bool, ...]
    kept_fixtures: int | None

    @property
    def undefined(self) -> bool:
        return self.estimate is None


def decide_replicate(
    terms: analysis.FixtureTerms | None, *, alphas: Sequence[float], delta: float, flips: int,
) -> ReplicateResult:
    """A zero-width interval or a constant `null_centered` gets no special case,
    so this decides as the production statistics do."""
    if terms is None:
        return ReplicateResult(None, (None,) * len(alphas), None, (False,) * len(alphas), (False,) * len(alphas), None)
    p_value = analysis.sign_flip_p_value(terms.null_centered, resamples=flips)
    lower_limits = tuple(analysis.fixture_t_interval(terms, alpha_one_sided=alpha)[0] for alpha in alphas)
    return ReplicateResult(
        estimate=terms.estimate,
        lower_limits=lower_limits,
        p_value=p_value,
        t_interval_adopts=tuple(lower_limit > -delta for lower_limit in lower_limits),
        sign_flip_adopts=tuple(p_value <= alpha for alpha in alphas),
        kept_fixtures=len(terms.residuals),
    )


def replicates_sign_flip_path(results: Sequence[ReplicateResult]) -> str | None:
    """The defined replicates' common sign-flip path, `SIGN_FLIP_PATH_MIXED` when their
    kept counts straddle the exact cap, or None when no replicate is defined."""
    paths = {sign_flip_path(result.kept_fixtures) for result in results if not result.undefined}
    if not paths:
        return None
    return paths.pop() if len(paths) == 1 else SIGN_FLIP_PATH_MIXED


class ReplicateJob(NamedTuple):
    """A replicate's inputs as a plain tuple, so it pickles to a pool worker."""

    metric: str
    k: int
    harm: str
    over_cap_share: float
    fixtures: int
    acted_fixtures: int
    true_difference: float
    shift: float
    replicate_index: int
    run_seed: int
    delta: float
    alphas: tuple[float, ...]
    flips: int
    finding_floor: int
    finding_volume_scale: float


def replicate_seed(
    *, run_seed: int, metric: str, k: int, harm: str, over_cap_share: float, fixtures: int, true_difference: float,
    replicate_index: int,
) -> str:
    """The string a replicate seeds `random.Random` with. `random` hashes a str
    seed with SHA-512, so the draws are the same in every process. Alphas, flips
    and workers stay out, so rerunning with others draws the same data.
    `finding_floor` and `finding_volume_scale` stay out too, so runs that differ
    only in them draw the same fixture latents."""
    return (
        f"calibrate|{run_seed}|{metric}|{k}|{harm}|{over_cap_share!r}|{fixtures}|{true_difference!r}|{replicate_index}"
    )


def _one_fixture_per_defect(defect_ids: Sequence[str]) -> dict[str, tuple[str, str]]:
    return {defect_id: ("calibrate", defect_id) for defect_id in defect_ids}


def run_replicate(job: ReplicateJob) -> ReplicateResult:
    rng = random.Random(
        replicate_seed(
            run_seed=job.run_seed, metric=job.metric, k=job.k, harm=job.harm, over_cap_share=job.over_cap_share,
            fixtures=job.fixtures, true_difference=job.true_difference, replicate_index=job.replicate_index,
        )
    )
    plans = plan_fixtures(
        rng, metric=job.metric, harm=job.harm, k=job.k, fixtures=job.fixtures, acted_fixtures=job.acted_fixtures,
        shift=job.shift, finding_volume_scale=job.finding_volume_scale,
    )
    if job.metric == METRIC_RECALL:
        recall_counts = draw_recall_counts(rng, plans, k=job.k)
        defect_ids = list(recall_counts)
        terms = analysis.recall_fixture_terms(
            recall_counts, defect_ids, ARM_CURRENT_RULE, ARM_FUNCTION_CONTEXT,
            cluster_by_defect=_one_fixture_per_defect(defect_ids), delta=job.delta,
        )
    else:
        precision_counts = draw_precision_counts(rng, plans, finding_floor=job.finding_floor)
        defect_ids = list(precision_counts)
        terms = analysis.precision_fixture_terms(
            precision_counts, defect_ids, ARM_CURRENT_RULE, ARM_FUNCTION_CONTEXT,
            cluster_by_defect=_one_fixture_per_defect(defect_ids), delta=job.delta,
        )
    return decide_replicate(terms, alphas=job.alphas, delta=job.delta, flips=job.flips)


def cell_jobs(config: CalibrationConfig, cell: Cell) -> list[ReplicateJob]:
    return [
        ReplicateJob(
            metric=config.metric, k=config.k, harm=config.harm, over_cap_share=config.over_cap_share,
            fixtures=cell.fixtures, acted_fixtures=cell.acted_fixtures, true_difference=cell.true_difference,
            shift=cell.shift, replicate_index=index, run_seed=config.seed, delta=config.delta,
            alphas=tuple(config.alphas), flips=config.flips, finding_floor=config.finding_floor,
            finding_volume_scale=config.finding_volume_scale,
        )
        for index in range(config.replicates)
    ]


def _ignore_sigint_in_worker() -> None:
    """A terminal Ctrl-C reaches every process in the foreground group. Workers
    ignore it so the parent alone handles the interrupt and tears the pool down."""
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def make_pool(workers: int) -> concurrent.futures.ProcessPoolExecutor:
    return concurrent.futures.ProcessPoolExecutor(max_workers=workers, initializer=_ignore_sigint_in_worker)


def run_jobs(
    jobs: Sequence[ReplicateJob], *, pool: concurrent.futures.ProcessPoolExecutor | None, workers: int,
) -> list[ReplicateResult]:
    """Results in job order, in process when `pool` is None. The chunk size is
    `multiprocessing.Pool.map`'s default, since `ProcessPoolExecutor.map` defaults
    to chunks of one job."""
    if pool is None:
        return [run_replicate(job) for job in jobs]
    chunk_size = math.ceil(len(jobs) / (4 * workers))
    return list(pool.map(run_replicate, jobs, chunksize=chunk_size))


def summarize_cell(
    config: CalibrationConfig, cell: Cell, results: Sequence[ReplicateResult], *, cells_planned: int,
) -> dict:
    """One output row. A rate's denominator includes undefined replicates. The row
    carries no worker count and no timing, so output is byte-identical across worker counts.
    `sign_flip_path` is the defined replicates' path: `exact`, `monte-carlo`, `mixed` when their
    kept counts straddle the exact cap, or None when no replicate is defined.
    Only a floor-0 row carries `replicates_by_kept_fixtures`, because at floor 1 every
    replicate keeps every fixture.
    A row omits `finding_floor` and `finding_volume_scale` at their defaults, so an absent
    one means its default."""
    replicate_count = len(results)
    row = {
        "metric": config.metric,
        "k": config.k,
        "harm": config.harm,
        "over_cap_share": config.over_cap_share,
        "acted_fixtures": cell.acted_fixtures,
        "fixtures": cell.fixtures,
        "true_difference": cell.true_difference,
        "delta": config.delta,
        "replicates": config.replicates,
        "undefined_replicates": sum(result.undefined for result in results),
        "flips": config.flips,
        "seed": config.seed,
        "sign_flip_path": replicates_sign_flip_path(results),
        "python_version": platform.python_version(),
        "cells_planned": cells_planned,
        "alphas": [
            {
                "alpha": alpha,
                "t_interval_adopt_rate": sum(result.t_interval_adopts[index] for result in results) / replicate_count,
                "sign_flip_adopt_rate": sum(result.sign_flip_adopts[index] for result in results) / replicate_count,
            }
            for index, alpha in enumerate(config.alphas)
        ],
    }
    if config.finding_floor == 0:
        row["finding_floor"] = 0
        kept_counts = Counter(result.kept_fixtures for result in results if not result.undefined)
        row["replicates_by_kept_fixtures"] = {str(count): kept_counts[count] for count in sorted(kept_counts)}
    if config.finding_volume_scale != 1.0:
        row["finding_volume_scale"] = config.finding_volume_scale
    return row


def run_sweep(
    config: CalibrationConfig, *, cells: Sequence[Cell] | None = None, out_path: Path | None = None,
    solver_draws: int | None = None,
) -> list[dict]:
    """Runs every cell, planning them first when `cells` is omitted. With `out_path`,
    an empty array is written before the first replicate, so an unwritable path fails
    before any replicate runs. The array is rewritten after each cell, so an
    interrupted sweep keeps its finished cells. A row prints only once it is in the
    file. Any exception leaving the sweep, a KeyboardInterrupt included, terminates
    the pool's workers first. Leaving the pool's `with` would otherwise wait for
    running chunks."""
    if cells is None:
        cells = plan_cells(config, solver_draws=solver_draws)
    if out_path is not None:
        defects.atomic_write_text(out_path, "[]\n")
    rows: list[dict] = []
    pool_scope = make_pool(config.workers) if config.workers > 1 else contextlib.nullcontext()
    with pool_scope as pool:
        try:
            for cell in cells:
                started = time.monotonic()
                results = run_jobs(cell_jobs(config, cell), pool=pool, workers=config.workers)
                rows.append(summarize_cell(config, cell, results, cells_planned=len(cells)))
                if out_path is not None:
                    defects.atomic_write_text(out_path, json.dumps(rows, indent=2) + "\n")
                print(json.dumps(rows[-1]), flush=True)
                print(
                    f"calibrate: cell {_describe_cell(cell.fixtures, cell.true_difference)} finished in "
                    f"{time.monotonic() - started:.1f}s",
                    file=sys.stderr,
                )
        except BaseException:
            if pool is not None:
                pool.terminate_workers()
            raise
    return rows
