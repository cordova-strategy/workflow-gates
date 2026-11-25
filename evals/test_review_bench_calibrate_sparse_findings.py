"""Tests for `calibrate`'s finding floor and finding-volume scale: the config
checks, the one-arm-only and no-finding draws, the kept-fixture count and the row
fields built from it. Offline throughout: every case draws synthetic counts and
runs no model.
"""
from __future__ import annotations

import math
import random
import statistics

import pytest
from review_bench import analysis, calibrate
from review_bench.arms import ARM_CURRENT_RULE, ARM_FUNCTION_CONTEXT
from test_review_bench_calibrate import EXACT_CAP, SIGMA_BOUND, _config, _terms

DELTA = 0.05
SCALES = (1.0, 0.25)
ARMS = (ARM_CURRENT_RULE, ARM_FUNCTION_CONTEXT)


def _result(kept_fixtures: int | None) -> calibrate.ReplicateResult:
    if kept_fixtures is None:
        return calibrate.decide_replicate(None, alphas=(0.025,), delta=DELTA, flips=100)
    return calibrate.ReplicateResult(0.0, (0.1,), 0.5, (True,), (False,), kept_fixtures)


def _population_shares(finding_volume_scale: float) -> tuple[float, float]:
    """The shares of acted fixtures at k = 1 with a finding in one arm only and in neither.
    A total of 0 has probability E[exp(-m * lambda)] = (1 + m * FINDING_RATE_SCALE) ** -FINDING_RATE_SHAPE for
    lambda ~ Gamma(FINDING_RATE_SHAPE, FINDING_RATE_SCALE), where m is the arm's volume per unit of lambda.
    Averaging over the volume factor's midpoints gives the arm X and both-arm probabilities."""
    low, high = calibrate.VOLUME_FACTOR_RANGE
    midpoints = 1000
    factors = [low + (high - low) * (index + 0.5) / midpoints for index in range(midpoints)]

    def zero_probability(volume_per_lambda: float) -> float:
        return (1 + volume_per_lambda * calibrate.FINDING_RATE_SCALE) ** -calibrate.FINDING_RATE_SHAPE

    baseline_zero = zero_probability(finding_volume_scale)
    arm_x_zero = statistics.fmean(zero_probability(finding_volume_scale * factor) for factor in factors)
    both_zero = statistics.fmean(zero_probability(finding_volume_scale * (1 + factor)) for factor in factors)
    return baseline_zero + arm_x_zero - 2 * both_zero, both_zero


class TestFindingOptionConfig:
    @pytest.mark.parametrize(
        ("overrides", "field"),
        [
            ({"finding_floor": 2}, "finding_floor"),
            ({"finding_floor": -1}, "finding_floor"),
            ({"finding_floor": True}, "finding_floor"),
            ({"finding_floor": 0.0}, "finding_floor"),
            ({"finding_volume_scale": 0.0}, "finding_volume_scale"),
            ({"finding_volume_scale": -0.25}, "finding_volume_scale"),
            ({"finding_volume_scale": 1.5}, "finding_volume_scale"),
            ({"finding_volume_scale": math.nan}, "finding_volume_scale"),
            ({"metric": "recall", "finding_floor": 0}, "finding_floor"),
            ({"metric": "recall", "finding_volume_scale": 0.25}, "finding_volume_scale"),
        ],
        ids=[
            "floor-2", "floor-negative", "floor-bool", "floor-float", "scale-zero", "scale-negative", "scale-above-1",
            "scale-nan", "recall-floor-0", "recall-scale-0.25",
        ],
    )
    def test_a_rejected_setting_names_its_field(self, overrides, field) -> None:
        settings = {"metric": "precision", **overrides}

        with pytest.raises(calibrate.CalibrationConfigError, match=field):
            _config(**settings)

    @pytest.mark.parametrize(
        "overrides",
        [{"finding_floor": 0}, {"finding_volume_scale": 0.25}, {"finding_floor": 0, "finding_volume_scale": 0.25}],
        ids=["floor-0", "scale-0.25-at-floor-1", "both"],
    )
    def test_precision_accepts_the_options(self, overrides) -> None:
        config = _config(metric="precision", **overrides)

        assert (config.finding_floor, config.finding_volume_scale) == (
            overrides.get("finding_floor", 1), overrides.get("finding_volume_scale", 1.0),
        )


class TestFloorZeroDraws:
    FIXTURES = 20_000

    @pytest.mark.parametrize("finding_volume_scale", SCALES)
    def test_one_arm_only_and_empty_fixtures_follow_the_population(self, finding_volume_scale) -> None:
        rng = random.Random(21)
        plans = calibrate.plan_fixtures(
            rng, metric="precision", harm="normal", k=1, fixtures=self.FIXTURES, acted_fixtures=self.FIXTURES,
            shift=0.0, finding_volume_scale=finding_volume_scale,
        )

        counts = calibrate.draw_precision_counts(rng, plans, finding_floor=0)

        totals = {arm: [fixture.total_by_arm[arm] for fixture in counts.values()] for arm in ARMS}
        one_arm_only = sum((baseline > 0) != (arm_x > 0) for baseline, arm_x in zip(*totals.values(), strict=True))
        neither = sum(baseline == 0 and arm_x == 0 for baseline, arm_x in zip(*totals.values(), strict=True))
        shares = (one_arm_only / self.FIXTURES, neither / self.FIXTURES)
        for share, expected in zip(shares, _population_shares(finding_volume_scale), strict=True):
            assert share == pytest.approx(expected, abs=SIGMA_BOUND * math.sqrt(expected * (1 - expected) / self.FIXTURES))
        assert min(shares) > 0
        for arm in ARMS:
            assert min(totals[arm]) == 0
            assert statistics.fmean(totals[arm]) == pytest.approx(
                4 * finding_volume_scale, abs=SIGMA_BOUND * statistics.stdev(totals[arm]) / math.sqrt(self.FIXTURES),
            )


class TestSharedLatents:
    @pytest.mark.parametrize("k", (1, 3), ids=("k-1", "k-3"))
    def test_a_floor_0_scaled_job_draws_the_default_jobs_rates_at_a_scaled_volume(self, monkeypatch, k) -> None:
        plans_by_run = []
        real_draw = calibrate.draw_precision_counts
        monkeypatch.setattr(
            calibrate, "draw_precision_counts",
            lambda rng, plans, **kwargs: plans_by_run.append(plans) or real_draw(rng, plans, **kwargs),
        )
        config = _config(metric="precision", fixture_counts=(6,), k=k, replicates=1, flips=100)
        cell = calibrate.Cell(6, 6, true_difference=0.0, shift=0.0)
        (default_job,) = calibrate.cell_jobs(config, cell)

        calibrate.run_replicate(default_job)
        calibrate.run_replicate(default_job._replace(finding_floor=0, finding_volume_scale=0.25))

        default_plans, scaled_plans = plans_by_run
        assert len(default_plans) == len(scaled_plans) == 6
        for default_plan, scaled_plan in zip(default_plans, scaled_plans, strict=True):
            assert scaled_plan.baseline_rate == default_plan.baseline_rate
            assert scaled_plan.arm_x_rate == default_plan.arm_x_rate
            assert scaled_plan.baseline_volume == pytest.approx(0.25 * default_plan.baseline_volume)
            assert scaled_plan.arm_x_volume == pytest.approx(0.25 * default_plan.arm_x_volume)

    def test_the_scale_applies_once_to_acted_and_non_acted_fixtures_alike(self) -> None:
        fixtures, acted_fixtures, k, finding_volume_scale = 8, 5, 3, 0.25

        def plan(scale: float) -> list[calibrate.FixturePlan]:
            return calibrate.plan_fixtures(
                random.Random(7), metric="precision", harm="normal", k=k, fixtures=fixtures,
                acted_fixtures=acted_fixtures, shift=0.0, finding_volume_scale=scale,
            )

        default_plans, scaled_plans = plan(1.0), plan(finding_volume_scale)

        for index, (default_plan, scaled_plan) in enumerate(zip(default_plans, scaled_plans, strict=True)):
            assert scaled_plan.baseline_volume == pytest.approx(finding_volume_scale * default_plan.baseline_volume)
            assert scaled_plan.arm_x_volume == pytest.approx(finding_volume_scale * default_plan.arm_x_volume)
            if index >= acted_fixtures:
                assert scaled_plan.arm_x_volume == pytest.approx(scaled_plan.baseline_volume)


class TestKeptFixtures:
    def test_jobs_carry_the_floor_and_scale_into_the_replicates(self, monkeypatch) -> None:
        drawn_counts_by_replicate = []
        real_draw = calibrate.draw_precision_counts
        # Replicates run in order in this process, so captures align with results by index.
        monkeypatch.setattr(
            calibrate, "draw_precision_counts",
            lambda rng, plans, **kwargs: drawn_counts_by_replicate.append(real_draw(rng, plans, **kwargs))
            or drawn_counts_by_replicate[-1],
        )
        cell = calibrate.Cell(8, 8, true_difference=0.0, shift=0.0)
        # A scale this small leaves some replicates with fewer than two finding-carrying fixtures.
        config = _config(
            metric="precision", fixture_counts=(8,), k=1, replicates=30, flips=100, finding_floor=0,
            finding_volume_scale=0.1,
        )

        jobs = calibrate.cell_jobs(config, cell)
        results = calibrate.run_jobs(jobs, pool=None, workers=1)
        row = calibrate.summarize_cell(config, cell, results, cells_planned=1)

        assert {(job.finding_floor, job.finding_volume_scale) for job in jobs} == {(0, 0.1)}
        assert len(drawn_counts_by_replicate) == len(results) == 30
        expected_undefined = 0
        for drawn_counts, result in zip(drawn_counts_by_replicate, results, strict=True):
            kept_counts = [
                fixture for fixture in drawn_counts.values() if any(fixture.total_by_arm[arm] for arm in ARMS)
            ]
            arm_has_no_findings = any(sum(fixture.total_by_arm[arm] for fixture in kept_counts) == 0 for arm in ARMS)
            replicate_is_undefined = len(kept_counts) < 2 or arm_has_no_findings
            expected_undefined += replicate_is_undefined
            assert result.undefined == replicate_is_undefined
            if not replicate_is_undefined:
                assert result.kept_fixtures == len(kept_counts)
        assert expected_undefined > 0
        assert row["undefined_replicates"] == expected_undefined
        assert any(result.kept_fixtures < 8 for result in results if not result.undefined)
        assert sum(row["replicates_by_kept_fixtures"].values()) == row["replicates"] - row["undefined_replicates"]

    def test_a_floor_0_row_straddling_the_exact_cap_reads_mixed_and_matches_the_lengths_the_test_received(
        self, monkeypatch,
    ) -> None:
        lengths_received = []
        real_p_value = analysis.sign_flip_p_value
        monkeypatch.setattr(
            analysis, "sign_flip_p_value",
            lambda values, **kwargs: lengths_received.append(len(values)) or real_p_value(values, **kwargs),
        )
        fixtures = EXACT_CAP + 2
        cell = calibrate.Cell(fixtures, fixtures, true_difference=0.0, shift=0.0)
        config = _config(
            metric="precision", fixture_counts=(fixtures,), k=1, replicates=60, flips=200, finding_floor=0,
        )

        results = calibrate.run_jobs(calibrate.cell_jobs(config, cell), pool=None, workers=1)
        row = calibrate.summarize_cell(config, cell, results, cells_planned=1)

        kept_counts = {int(count) for count in row["replicates_by_kept_fixtures"]}
        assert min(kept_counts) <= EXACT_CAP < max(kept_counts)
        assert row["sign_flip_path"] == "mixed"
        assert set(lengths_received) == kept_counts

    def test_a_smaller_volume_scale_keeps_fewer_fixtures_at_floor_0(self) -> None:
        cell = calibrate.Cell(8, 8, true_difference=0.0, shift=0.0)

        def mean_kept_fixtures(finding_volume_scale: float) -> float:
            config = _config(
                metric="precision", fixture_counts=(8,), k=1, replicates=30, flips=100, finding_floor=0,
                finding_volume_scale=finding_volume_scale,
            )
            results = calibrate.run_jobs(calibrate.cell_jobs(config, cell), pool=None, workers=1)
            return statistics.fmean(result.kept_fixtures for result in results if not result.undefined)

        # Seeds exclude the scale, so both runs draw the same latents and differ only in volume.
        assert mean_kept_fixtures(0.25) < mean_kept_fixtures(1.0)

    def test_a_scaled_replicate_at_floor_1_keeps_every_fixture(self) -> None:
        cell = calibrate.Cell(8, 8, true_difference=0.0, shift=0.0)
        config = _config(
            metric="precision", fixture_counts=(8,), k=1, replicates=30, flips=100, finding_volume_scale=0.25,
        )

        results = calibrate.run_jobs(calibrate.cell_jobs(config, cell), pool=None, workers=1)

        assert {result.kept_fixtures for result in results} == {8}


class TestRowFields:
    CELL = calibrate.Cell(fixtures=30, acted_fixtures=30, true_difference=0.0, shift=0.0)

    @pytest.mark.parametrize(
        ("kept_counts", "expected_path"),
        [
            ((EXACT_CAP, EXACT_CAP), calibrate.SIGN_FLIP_PATH_EXACT),
            ((EXACT_CAP - 1, EXACT_CAP), calibrate.SIGN_FLIP_PATH_EXACT),
            ((EXACT_CAP + 1, EXACT_CAP + 1), calibrate.SIGN_FLIP_PATH_MONTE_CARLO),
            ((EXACT_CAP + 1, EXACT_CAP + 2), calibrate.SIGN_FLIP_PATH_MONTE_CARLO),
            ((None, EXACT_CAP, EXACT_CAP + 1), "mixed"),
            ((None, EXACT_CAP + 1, EXACT_CAP + 1), calibrate.SIGN_FLIP_PATH_MONTE_CARLO),
            ((None, None), None),
        ],
        ids=[
            "both-at-cap",
            "below-and-at-cap",
            "both-above-cap",
            "two-above-cap",
            "straddling-cap",
            "undefined-and-above-cap",
            "none-defined",
        ],
    )
    def test_the_rows_sign_flip_path_is_the_defined_replicates_path(self, kept_counts, expected_path) -> None:
        config = _config(metric="precision", fixture_counts=(30,), finding_floor=0)

        row = calibrate.summarize_cell(config, self.CELL, [_result(kept) for kept in kept_counts], cells_planned=1)

        assert row["sign_flip_path"] == expected_path

    def test_a_floor_0_row_counts_replicates_by_kept_fixtures_in_numeric_order(self) -> None:
        cell = calibrate.Cell(fixtures=12, acted_fixtures=12, true_difference=0.0, shift=0.0)
        config = _config(metric="precision", fixture_counts=(12,), finding_floor=0)
        results = [
            calibrate.decide_replicate(
                None if kept is None else _terms(0.0, [0.0] * kept, DELTA), alphas=(0.025,), delta=DELTA, flips=100,
            )
            for kept in (10, None, 9, 10)
        ]

        row = calibrate.summarize_cell(config, cell, results, cells_planned=1)

        assert [result.kept_fixtures for result in results] == [10, None, 9, 10]
        # A string-sorted or insertion-ordered histogram would list "10" first.
        assert list(row["replicates_by_kept_fixtures"].items()) == [("9", 1), ("10", 2)]
        assert row["sign_flip_path"] == calibrate.SIGN_FLIP_PATH_EXACT
        assert row["finding_floor"] == 0
        assert "finding_volume_scale" not in row

    def test_a_scaled_floor_1_row_carries_only_the_scale(self) -> None:
        cell = calibrate.Cell(fixtures=12, acted_fixtures=12, true_difference=0.0, shift=0.0)
        config = _config(metric="precision", fixture_counts=(12,), finding_volume_scale=0.25)
        # Hand-built: floor 1 keeps every fixture, so this covers only the config's gating of the row fields.
        results = [_result(10), _result(None), _result(9), _result(10)]

        row = calibrate.summarize_cell(config, cell, results, cells_planned=1)

        assert row["finding_volume_scale"] == 0.25
        assert "finding_floor" not in row
        assert "replicates_by_kept_fixtures" not in row


class TestFloorZeroPlannedCells:
    """The solved shift, the scaled plans, the floor-0 draws and the production builder together give the cell's difference."""

    # Many replicates keep the SIGMA_BOUND tolerance small.
    REPLICATES = 1600
    TRUE_DIFFERENCES = (-0.1, 0.0)

    @pytest.mark.parametrize("finding_volume_scale", SCALES)
    def test_the_mean_estimate_equals_the_cells_true_difference(self, finding_volume_scale, monkeypatch) -> None:
        # The sign-flip test is not under test here, so a stub keeps each replicate cheap.
        monkeypatch.setattr(analysis, "sign_flip_p_value", lambda values, **kwargs: 1.0)
        config = _config(
            metric="precision", fixture_counts=(20,), k=1, delta=0.1, over_cap_share=0.25, replicates=self.REPLICATES,
            finding_floor=0, finding_volume_scale=finding_volume_scale,
        )

        cells = calibrate.plan_cells(config, solver_draws=20_000)

        assert [cell.true_difference for cell in cells] == list(self.TRUE_DIFFERENCES)
        for cell, expected_difference in zip(cells, self.TRUE_DIFFERENCES, strict=True):
            results = calibrate.run_jobs(calibrate.cell_jobs(config, cell), pool=None, workers=1)
            assert not any(result.undefined for result in results)
            estimates = [result.estimate for result in results]
            standard_error = statistics.stdev(estimates) / math.sqrt(self.REPLICATES)
            assert statistics.fmean(estimates) == pytest.approx(expected_difference, abs=SIGMA_BOUND * standard_error)
