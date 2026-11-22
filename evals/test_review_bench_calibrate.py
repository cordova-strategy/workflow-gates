"""Tests for evals/review_bench/calibrate.py and `run_review_bench.py calibrate`:
the scenario generators, the shift solver, the per-replicate decision, the sweep,
worker and seed independence, and the CLI handler. Offline throughout: every
case draws synthetic counts and runs no model. Every sweep is tiny, and runs
with one worker unless a case says otherwise.
"""
from __future__ import annotations

import dataclasses
import json
import math
import os
import pickle
import random
import signal
import statistics

import pytest
import run_review_bench
from review_bench import analysis, calibrate, defects
from review_bench.arms import ARM_CURRENT_RULE, ARM_FUNCTION_CONTEXT

SMALL_SOLVER_DRAWS = 2000
DELTA = 0.05
SIGMA_BOUND = 4  # each statistical bound is about four standard errors
EXACT_CAP = analysis.SIGN_FLIP_EXACT_MAX_FIXTURES
MATERIAL_DIFFERENCE = 1e-3  # far above float rounding, far below the smallest draw-driven difference (about 0.017)


def _config(**overrides) -> calibrate.CalibrationConfig:
    settings = {"metric": "recall", "fixture_counts": (6,), "k": 10, "replicates": 3}
    settings.update(overrides)
    return calibrate.CalibrationConfig(**settings)


def _plan(metric: str, rng: random.Random, *, fixtures: int, acted: int, shift: float = 0.0, k: int = 10, harm="normal"):
    return calibrate.plan_fixtures(
        rng, metric=metric, harm=harm, k=k, fixtures=fixtures, acted_fixtures=acted, shift=shift,
    )


def _terms(estimate: float, residuals: list[float], delta: float) -> analysis.FixtureTerms:
    """Terms built as `analysis`'s builders build them: null_centered is residual + estimate + delta."""
    return analysis.FixtureTerms(
        estimate=estimate, residuals=tuple(residuals),
        null_centered=tuple(residual + estimate + delta for residual in residuals),
    )


def _key_value_tokens(line: str) -> dict[str, str]:
    return dict(token.split("=", 1) for token in line.split() if "=" in token)


def _patch_cpu_count(monkeypatch: pytest.MonkeyPatch, count: int | None) -> None:
    monkeypatch.setattr(os, "process_cpu_count", lambda: count)


class TestScenarioDraws:
    DRAWS = 20_000

    @pytest.mark.parametrize(
        ("metric", "mean", "standard_deviation"), [("recall", 0.5, 0.310), ("precision", 0.6, 0.185)],
    )
    def test_baseline_rate_matches_its_beta_mean_and_spread(self, metric, mean, standard_deviation) -> None:
        rng = random.Random(1)
        rates = [calibrate.draw_latents(rng, metric).baseline_rate for _ in range(self.DRAWS)]

        assert statistics.fmean(rates) == pytest.approx(mean, abs=SIGMA_BOUND * standard_deviation / math.sqrt(self.DRAWS))
        assert statistics.pstdev(rates) == pytest.approx(standard_deviation, abs=0.005)

    @pytest.mark.parametrize(("metric", "noise_sd"), [("recall", 0.1), ("precision", 0.05)])
    def test_arm_x_noise_has_the_metrics_standard_deviation(self, metric, noise_sd) -> None:
        rng = random.Random(2)
        centered = [
            dataclasses.replace(calibrate.draw_latents(rng, metric), baseline_rate=0.5) for _ in range(self.DRAWS)
        ]

        rates = [calibrate.arm_x_rate(latents, 0.0, metric=metric, harm="normal") for latents in centered]

        assert statistics.pstdev(rates) == pytest.approx(noise_sd, abs=SIGMA_BOUND * noise_sd / math.sqrt(2 * self.DRAWS))

    def test_precision_finding_rate_and_volume_factor_have_their_means_and_spreads(self) -> None:
        rng = random.Random(3)
        draws = [calibrate.draw_latents(rng, "precision") for _ in range(self.DRAWS)]

        rates = [latents.finding_rate for latents in draws]
        factors = [latents.volume_factor for latents in draws]

        assert statistics.fmean(rates) == pytest.approx(4.0, abs=SIGMA_BOUND * 2.83 / math.sqrt(self.DRAWS))
        assert statistics.fmean(factors) == pytest.approx(1.0, abs=SIGMA_BOUND * 0.115 / math.sqrt(self.DRAWS))
        # A sample SD's standard error is sd * sqrt((kurtosis - 1) / (4 * n)): Gamma(2, 2) has kurtosis 6, U(0.8, 1.2) 1.8.
        assert statistics.stdev(rates) == pytest.approx(2.83, abs=SIGMA_BOUND * 2.83 * math.sqrt(5 / (4 * self.DRAWS)))
        assert statistics.stdev(factors) == pytest.approx(0.1155, abs=SIGMA_BOUND * 0.1155 * math.sqrt(0.8 / (4 * self.DRAWS)))

    @pytest.mark.parametrize("k", [10, 20])
    def test_precision_mean_total_per_arm_is_one_plus_four_k_and_never_below_one(self, k) -> None:
        rng = random.Random(4)
        fixtures = 2000
        plans = _plan("precision", rng, fixtures=fixtures, acted=fixtures, k=k)

        counts = calibrate.draw_precision_counts(rng, plans)

        for arm in (ARM_CURRENT_RULE, ARM_FUNCTION_CONTEXT):
            totals = [fixture.total_by_arm[arm] for fixture in counts.values()]
            assert min(totals) >= 1
            assert statistics.fmean(totals) == pytest.approx(
                1 + 4 * k, abs=SIGMA_BOUND * statistics.stdev(totals) / math.sqrt(fixtures),
            )

    def test_each_arms_total_follows_its_own_volume(self) -> None:
        fixtures = 300
        plans = [
            calibrate.FixturePlan(baseline_rate=0.5, arm_x_rate=0.5, baseline_volume=1.0, arm_x_volume=40.0)
        ] * fixtures

        counts = calibrate.draw_precision_counts(random.Random(10), plans)

        for arm, expected_total in ((ARM_CURRENT_RULE, 2.0), (ARM_FUNCTION_CONTEXT, 41.0)):
            totals = [fixture.total_by_arm[arm] for fixture in counts.values()]
            assert statistics.fmean(totals) == pytest.approx(
                expected_total, abs=SIGMA_BOUND * statistics.stdev(totals) / math.sqrt(fixtures),
            )

    def test_precision_total_is_exactly_one_for_a_fixture_with_no_extra_finding(self) -> None:
        rng = random.Random(9)
        # At k of 1 about one fixture in nine draws a zero Poisson count: E[exp(-lambda)] is (1 + 2) ** -2 for Gamma(2, 2).
        plans = _plan("precision", rng, fixtures=2000, acted=2000, k=1)

        counts = calibrate.draw_precision_counts(rng, plans)

        for arm in (ARM_CURRENT_RULE, ARM_FUNCTION_CONTEXT):
            assert min(fixture.total_by_arm[arm] for fixture in counts.values()) == 1

    @pytest.mark.parametrize(
        ("mean", "draws"),
        [
            (0.5, 20_000),
            (10, 20_000),
            (800, 5000),  # above the mean (about 745) where exp(-mean) underflows to 0 in double precision
        ],
    )
    def test_poisson_sample_mean_and_variance_match_the_mean(self, mean, draws) -> None:
        rng = random.Random(5)

        samples = [calibrate.draw_poisson(rng, mean) for _ in range(draws)]

        assert statistics.fmean(samples) == pytest.approx(mean, abs=SIGMA_BOUND * math.sqrt(mean / draws))
        # A Poisson's fourth central moment is mean + 3 * mean^2, so the variance's standard error is below.
        assert statistics.variance(samples) == pytest.approx(mean, abs=SIGMA_BOUND * math.sqrt((mean + 2 * mean**2) / draws))

    @pytest.mark.parametrize(
        ("metric", "harm", "latents", "shift", "expected"),
        [
            ("recall", "normal", calibrate.FixtureLatents(0.95, 1.0, 0.7), 0.2, 1.0),
            ("recall", "normal", calibrate.FixtureLatents(0.05, -1.0, 0.7), -0.2, 0.0),
            ("recall", "normal", calibrate.FixtureLatents(0.5, 1.0, 0.7), 0.1, 0.7),
            ("precision", "normal", calibrate.FixtureLatents(0.5, 2.0, 0.7), 0.0, 0.6),
            ("recall", "concentrated", calibrate.FixtureLatents(0.8, 1.0, 0.05), 0.2, 0.3),
            ("recall", "concentrated", calibrate.FixtureLatents(0.3, 1.0, 0.05), 0.2, 0.0),
            ("precision", "concentrated", calibrate.FixtureLatents(0.8, 1.0, 0.05), 0.2, 0.3),
            ("recall", "concentrated", calibrate.FixtureLatents(0.3, 0.0, 0.5), -0.05, 0.25),
        ],
        ids=[
            "clips-at-1", "clips-at-0", "unclipped-shift-plus-noise", "precision-noise-sd",
            "concentrated-drop-for-small-harm-uniform", "concentrated-drop-floors-at-0",
            "concentrated-drop-for-precision", "concentrated-falls-back-to-normal-for-large-harm-uniform",
        ],
    )
    def test_arm_x_rate_for_hand_picked_latents(self, metric, harm, latents, shift, expected) -> None:
        assert calibrate.arm_x_rate(latents, shift, metric=metric, harm=harm) == pytest.approx(expected)

    @pytest.mark.parametrize("metric", ["recall", "precision"])
    def test_every_acted_fixture_takes_arm_xs_rate_and_the_others_keep_the_baseline_rate_and_volume(self, metric) -> None:
        fixtures, acted, shift = 8, 3, -0.3
        plans = _plan(metric, random.Random(6), fixtures=fixtures, acted=acted, shift=shift)
        latents_rng = random.Random(6)
        latents = [calibrate.draw_latents(latents_rng, metric) for _ in range(fixtures)]

        for plan, fixture_latents in zip(plans[:acted], latents[:acted], strict=True):
            expected_rate = calibrate.arm_x_rate(fixture_latents, shift, metric=metric, harm="normal")
            assert plan.arm_x_rate == expected_rate
            assert plan.arm_x_rate != plan.baseline_rate
        for plan in plans[acted:]:
            assert plan.arm_x_rate == plan.baseline_rate
            assert plan.arm_x_volume == plan.baseline_volume

    @pytest.mark.parametrize("metric", ["recall", "precision"])
    def test_concentrated_harm_drops_about_a_tenth_of_the_acted_fixtures_and_leaves_the_rest_unaffected(self, metric) -> None:
        fixtures, acted = 60_000, 50_000  # four standard errors of the dropped share come to about 0.005
        # A shift of 5 clips every undropped rate to exactly 1.0, and a dropped rate is always below 0.5.
        plans = _plan(metric, random.Random(7), fixtures=fixtures, acted=acted, shift=5.0, harm="concentrated")

        dropped_share = sum(plan.arm_x_rate < 1.0 for plan in plans[:acted]) / acted
        standard_error = math.sqrt(0.10 * 0.90 / acted)
        assert dropped_share == pytest.approx(0.10, abs=SIGMA_BOUND * standard_error)
        for plan in plans[acted:]:
            assert plan.arm_x_rate == plan.baseline_rate

    def test_precision_arm_x_volume_is_the_baseline_volume_times_a_factor_inside_the_range_for_acted_fixtures(self) -> None:
        plans = _plan("precision", random.Random(8), fixtures=50, acted=30, shift=0.0)

        factors = [plan.arm_x_volume / plan.baseline_volume for plan in plans[:30]]
        assert all(0.8 < factor < 1.2 for factor in factors)
        assert any(factor != 1.0 for factor in factors)


class TestSolver:
    @pytest.mark.parametrize("metric", ["recall", "precision"])
    @pytest.mark.parametrize("harm", ["normal", "concentrated"])
    @pytest.mark.parametrize("share", [1.0, 0.5])
    def test_solved_shift_gives_the_acted_fixtures_the_target_scaled_by_fixtures_over_acted(
        self, metric, harm, share,
    ) -> None:
        fixtures, k = 20, 10
        acted = calibrate.acted_fixture_count(fixtures, share)
        acted_target = -DELTA * fixtures / acted

        shift = calibrate.solve_shift(metric, harm, k=k, acted_target=acted_target, solver_draws=20_000)

        rng = random.Random(2024)
        fresh = [calibrate.draw_latents(rng, metric) for _ in range(4000)]
        weights = [1 + k * latents.finding_rate if metric == "precision" else 1.0 for latents in fresh]
        differences = [
            calibrate.arm_x_rate(latents, shift, metric=metric, harm=harm) - latents.baseline_rate for latents in fresh
        ]
        mean_weight = statistics.fmean(weights)
        estimand = sum(w * d for w, d in zip(weights, differences, strict=True)) / sum(weights)
        standard_error = statistics.stdev(
            w * (d - estimand) / mean_weight for w, d in zip(weights, differences, strict=True)
        ) / math.sqrt(len(fresh))
        assert estimand == pytest.approx(acted_target, abs=SIGMA_BOUND * standard_error)

    def test_a_fifth_of_twenty_fixtures_acts_on_four_with_an_acted_target_of_minus_a_quarter(self) -> None:
        config = _config(fixture_counts=(20,), over_cap_share=0.2, delta=DELTA)

        cells = calibrate.plan_cells(config, solver_draws=SMALL_SOLVER_DRAWS)

        assert cells[0].acted_fixtures == 4
        expected_shift = calibrate.solve_shift("recall", "normal", k=10, acted_target=-0.25, solver_draws=SMALL_SOLVER_DRAWS)
        assert cells[0].shift == pytest.approx(expected_shift, abs=1e-9)

    def test_one_acted_fixture_out_of_twenty_needs_an_unreachable_target_and_names_the_cell(self) -> None:
        assert calibrate.solve_shift("recall", "normal", k=10, acted_target=-1.0, solver_draws=SMALL_SOLVER_DRAWS) is None
        config = _config(fixture_counts=(20,), over_cap_share=0.05, delta=DELTA)

        with pytest.raises(
            calibrate.CalibrationConfigError, match=r"delta and over_cap_share: cell fixtures=20 true_difference=-0\.05",
        ):
            calibrate.plan_cells(config, solver_draws=SMALL_SOLVER_DRAWS)

    def test_a_delta_larger_than_any_shift_can_produce_names_delta_and_the_cell(self) -> None:
        config = _config(fixture_counts=(6,), delta=0.55)

        with pytest.raises(
            calibrate.CalibrationConfigError, match=r"delta and over_cap_share: cell fixtures=6 true_difference=-0\.55",
        ):
            calibrate.plan_cells(config, solver_draws=SMALL_SOLVER_DRAWS)

    def test_a_cell_whose_smallest_sign_flip_p_value_exceeds_an_alpha_says_so_on_its_plan_line(self, capsys) -> None:
        config = _config(fixture_counts=(4, 8), alphas=(0.025,))

        calibrate.plan_cells(config, solver_draws=SMALL_SOLVER_DRAWS)

        plan_lines = capsys.readouterr().err.splitlines()
        four_fixture_lines, eight_fixture_lines = (
            [line for line in plan_lines if f"fixtures={fixtures} " in line] for fixtures in (4, 8)
        )
        assert len(four_fixture_lines) == len(eight_fixture_lines) == 2
        assert all("sign_flip_smallest_p=0.0625 exceeds alpha [0.025]" in line for line in four_fixture_lines)
        assert not any("sign_flip_smallest_p" in line for line in eight_fixture_lines)

    def test_the_plan_line_renders_each_field_as_one_token_with_the_cells_sign_flip_path(self, capsys) -> None:
        config = _config(fixture_counts=(6, EXACT_CAP + 1), alphas=(0.025, 0.0125), flips=200)

        calibrate.plan_cells(config, solver_draws=SMALL_SOLVER_DRAWS)

        plan_lines = [line for line in capsys.readouterr().err.splitlines() if "solved in" in line]
        assert len(plan_lines) == 4
        settings_by_fixtures = {}
        for line in plan_lines:
            settings = _key_value_tokens(line)
            settings_by_fixtures[settings["fixtures"]] = settings
            assert settings["alphas"] == "0.025,0.0125"
        assert settings_by_fixtures["6"]["sign_flip_path"] == calibrate.SIGN_FLIP_PATH_EXACT
        assert settings_by_fixtures[str(EXACT_CAP + 1)]["sign_flip_path"] == calibrate.SIGN_FLIP_PATH_MONTE_CARLO

    @pytest.mark.parametrize(
        ("fixtures", "share", "expected"),
        [
            (20, 1.0, 20), (20, 0.5, 10), (5, 0.5, 3), (20, 0.05, 1), (6, 0.01, 1),
            (50, 0.29, 15), (50, 0.57, 29), (25, 0.58, 15), (45, 0.7, 32),
        ],
        ids=[
            "all", "half", "half-rounds-up", "one-fixture", "minimum-of-one",
            "float-product-just-below-a-half-0.29x50", "float-product-just-below-a-half-0.57x50",
            "float-product-just-below-a-half-0.58x25", "float-product-just-below-a-half-0.7x45",
        ],
    )
    def test_acted_fixture_count(self, fixtures, share, expected) -> None:
        assert calibrate.acted_fixture_count(fixtures, share) == expected


class TestDecideReplicate:
    ALPHAS = (0.025, 0.0125)

    def _decide(self, terms, *, delta=DELTA, flips=100) -> calibrate.ReplicateResult:
        return calibrate.decide_replicate(terms, alphas=self.ALPHAS, delta=delta, flips=flips)

    def test_fixtures_far_above_minus_delta_adopt_under_both_statistics(self) -> None:
        result = self._decide(_terms(0.2, [0.01, -0.01] * 4, DELTA))

        assert result.t_interval_adopts == (True, True)
        assert result.sign_flip_adopts == (True, True)

    def test_fixtures_far_below_minus_delta_adopt_under_neither(self) -> None:
        result = self._decide(_terms(-0.3, [0.01, -0.01] * 4, DELTA))

        assert result.t_interval_adopts == (False, False)
        assert result.sign_flip_adopts == (False, False)

    def test_missing_terms_are_undefined_and_not_adopted(self) -> None:
        result = self._decide(None)

        assert result.undefined
        assert (result.estimate, result.p_value) == (None, None)
        assert result.lower_limits == (None, None)
        assert result.t_interval_adopts == result.sign_flip_adopts == (False, False)

    @pytest.mark.parametrize(("delta", "adopts"), [(0.10, True), (0.05, False)])
    def test_an_estimate_of_minus_seven_points_adopts_only_inside_the_margin(self, delta, adopts) -> None:
        result = self._decide(_terms(-0.07, [0.005, -0.005] * 4, delta), delta=delta)

        assert result.t_interval_adopts == (adopts, adopts)
        assert result.sign_flip_adopts == (adopts, adopts)

    def test_a_lower_limit_exactly_at_minus_delta_does_not_adopt(self) -> None:
        """Pins the strict `>`: six fixtures, estimate -delta and every residual 0."""
        terms = analysis.FixtureTerms(estimate=-DELTA, residuals=(0.0,) * 6, null_centered=(0.0,) * 6)

        result = self._decide(terms)

        assert result.lower_limits == (-DELTA, -DELTA)
        assert result.p_value == 1.0
        assert result.t_interval_adopts == result.sign_flip_adopts == (False, False)

    def test_each_alphas_lower_limit_is_the_t_intervals_and_only_that_limit_decides(self) -> None:
        """The estimate 0 sits above -delta, the 0.025 lower limit stays above it and the 0.0125 one falls below."""
        terms = _terms(0.0, [0.05, -0.05] * 4, DELTA)

        result = self._decide(terms)

        expected_lower_limits = tuple(
            analysis.fixture_t_interval(terms, alpha_one_sided=alpha)[0] for alpha in self.ALPHAS
        )
        assert expected_lower_limits[0] > -DELTA > expected_lower_limits[1]
        assert result.lower_limits == expected_lower_limits
        assert result.t_interval_adopts == (True, False)


class TestDegenerateTermsFromPrecisionCounts:
    """When one fixture carries every finding, the interval has zero width, so the t-interval compares the estimate
    with -delta. `null_centered` is constant up to float rounding, so the sign-flip p-value is set by the sign of
    the estimate plus delta and by the fixture count. A change to how `precision_fixture_terms` treats fixtures
    with no finding is expected to change these results."""

    ALPHAS = (0.025, 1 / 64, 0.0125)

    def _decide(self, *, fixtures, valid_x, total_x, valid_baseline, total_baseline) -> calibrate.ReplicateResult:
        """Every finding sits in the first fixture. The others carry present defects and no findings."""
        def carried(index: int, value: int) -> int:
            return value if index == 0 else 0

        counts = {
            f"d{index}": analysis.DefectPrecisionCounts(
                defect_id=f"d{index}",
                valid_by_arm={
                    ARM_CURRENT_RULE: carried(index, valid_baseline), ARM_FUNCTION_CONTEXT: carried(index, valid_x),
                },
                total_by_arm={
                    ARM_CURRENT_RULE: carried(index, total_baseline), ARM_FUNCTION_CONTEXT: carried(index, total_x),
                },
            )
            for index in range(fixtures)
        }
        defect_ids = list(counts)
        terms = analysis.precision_fixture_terms(
            counts, defect_ids, ARM_CURRENT_RULE, ARM_FUNCTION_CONTEXT,
            cluster_by_defect={defect_id: (defect_id, defect_id) for defect_id in defect_ids}, delta=DELTA,
        )
        return calibrate.decide_replicate(terms, alphas=self.ALPHAS, delta=DELTA, flips=100)

    def test_a_clear_loss_gives_a_zero_width_interval_and_p_of_one_so_nothing_adopts(self) -> None:
        result = self._decide(fixtures=6, valid_x=6, total_x=10, valid_baseline=8, total_baseline=10)

        assert result.estimate == pytest.approx(-0.20)
        assert result.lower_limits == pytest.approx((result.estimate,) * 3, abs=1e-12)
        assert result.p_value == 1.0
        assert result.t_interval_adopts == result.sign_flip_adopts == (False, False, False)

    def test_a_small_loss_adopts_by_the_t_interval_at_every_alpha_and_by_the_sign_flip_at_p_of_one_sixty_fourth(self) -> None:
        result = self._decide(fixtures=6, valid_x=14, total_x=25, valid_baseline=15, total_baseline=25)

        assert result.lower_limits[0] > -DELTA
        assert result.p_value == 1 / 64
        assert result.t_interval_adopts == (True, True, True)
        assert result.sign_flip_adopts == (True, True, False)

    def test_the_same_counts_over_five_fixtures_give_p_of_one_thirty_second_so_only_the_t_interval_adopts(self) -> None:
        result = self._decide(fixtures=5, valid_x=14, total_x=25, valid_baseline=15, total_baseline=25)

        assert result.p_value == 1 / 32
        assert result.t_interval_adopts[0] is True
        assert result.sign_flip_adopts[0] is False


class TestSummarizeCell:
    def test_rates_count_adopting_replicates_over_all_replicates_including_undefined(self) -> None:
        config = _config(alphas=(0.025, 0.0125))
        cell = calibrate.Cell(fixtures=6, acted_fixtures=6, true_difference=-DELTA, shift=0.0)
        undefined = calibrate.decide_replicate(None, alphas=config.alphas, delta=DELTA, flips=100)
        results = [
            undefined,
            calibrate.ReplicateResult(0.0, (0.1, 0.1), 0.01, (True, False), (True, True)),
            calibrate.ReplicateResult(0.0, (0.1, 0.1), 0.02, (True, True), (False, False)),
        ]

        row = calibrate.summarize_cell(config, cell, results, cells_planned=2)

        assert row["undefined_replicates"] == 1
        assert row["alphas"] == [
            {"alpha": 0.025, "t_interval_adopt_rate": 2 / 3, "sign_flip_adopt_rate": 1 / 3},
            {"alpha": 0.0125, "t_interval_adopt_rate": 1 / 3, "sign_flip_adopt_rate": 1 / 3},
        ]


class TestSweep:
    ROW_KEYS = {
        "metric", "k", "harm", "over_cap_share", "acted_fixtures", "fixtures", "true_difference", "delta", "replicates",
        "undefined_replicates", "flips", "seed", "sign_flip_path", "python_version", "cells_planned", "alphas",
    }

    @pytest.mark.parametrize("metric", ["recall", "precision"])
    def test_a_separated_scenario_rarely_falsely_adopts_and_always_adopts_a_true_tie(self, metric) -> None:
        config = _config(metric=metric, fixture_counts=(12,), k=50, delta=0.4, replicates=20)

        false_adopt_row, power_row = calibrate.run_sweep(config, solver_draws=SMALL_SOLVER_DRAWS)

        assert false_adopt_row["true_difference"] == -0.4
        for rates in false_adopt_row["alphas"]:
            assert rates["t_interval_adopt_rate"] <= 0.25
            assert rates["sign_flip_adopt_rate"] <= 0.25
        for rates in power_row["alphas"]:
            assert rates["t_interval_adopt_rate"] == 1.0
            assert rates["sign_flip_adopt_rate"] == 1.0

    def test_a_recall_sweep_gives_the_false_adopt_row_then_the_power_row(self) -> None:
        rows = calibrate.run_sweep(_config(delta=DELTA), solver_draws=SMALL_SOLVER_DRAWS)

        assert [row["true_difference"] for row in rows] == [-DELTA, 0.0]
        assert [row["acted_fixtures"] for row in rows] == [6, 6]
        assert [row["cells_planned"] for row in rows] == [2, 2]

    def test_a_concentrated_precision_sweep_at_half_share_has_exactly_the_planned_fields(self) -> None:
        config = _config(metric="precision", harm="concentrated", over_cap_share=0.5)

        rows = calibrate.run_sweep(config, solver_draws=SMALL_SOLVER_DRAWS)

        assert [row["acted_fixtures"] for row in rows] == [3, 3]
        for row in rows:
            assert set(row) == self.ROW_KEYS
            (rates,) = row["alphas"]
            assert set(rates) == {"alpha", "t_interval_adopt_rate", "sign_flip_adopt_rate"}
            for rate in (rates["t_interval_adopt_rate"], rates["sign_flip_adopt_rate"]):
                assert rate * config.replicates == pytest.approx(round(rate * config.replicates))

    def test_twenty_one_fixtures_take_the_monte_carlo_path_and_twenty_the_exact_one(self, monkeypatch) -> None:
        resamples_seen = []
        real_p_value = analysis.sign_flip_p_value
        monkeypatch.setattr(
            analysis, "sign_flip_p_value",
            lambda values, **kwargs: resamples_seen.append(kwargs["resamples"]) or real_p_value(values, **kwargs),
        )

        monte_carlo_rows = calibrate.run_sweep(
            _config(fixture_counts=(EXACT_CAP + 1,), replicates=2, flips=200), solver_draws=SMALL_SOLVER_DRAWS,
        )
        exact_rows = calibrate.run_sweep(
            _config(fixture_counts=(EXACT_CAP,), replicates=2, flips=200), solver_draws=SMALL_SOLVER_DRAWS,
        )

        assert {row["sign_flip_path"] for row in monte_carlo_rows} == {"monte-carlo"}
        assert {row["sign_flip_path"] for row in exact_rows} == {"exact"}
        assert set(resamples_seen) == {200}

    @pytest.mark.parametrize(
        ("workers", "failure"),
        [(1, KeyboardInterrupt()), (2, KeyboardInterrupt()), (2, ValueError("aggregation failed"))],
        ids=["serial-interrupt", "pool-interrupt", "pool-value-error"],
    )
    def test_an_exception_in_parent_aggregation_keeps_the_finished_cell_and_terminates_the_pool(
        self, workers, failure, tmp_path, monkeypatch, capsys,
    ) -> None:
        _patch_cpu_count(monkeypatch, 2)
        real_summarize = calibrate.summarize_cell
        summarize_calls = []

        def summarize_then_fail(*args, **kwargs):
            summarize_calls.append(args)
            if len(summarize_calls) == 2:
                raise failure
            return real_summarize(*args, **kwargs)

        monkeypatch.setattr(calibrate, "summarize_cell", summarize_then_fail)
        terminate_calls = []
        real_make_pool = calibrate.make_pool

        def make_pool_spying_on_termination(worker_count):
            pool = real_make_pool(worker_count)
            real_terminate = pool.terminate_workers
            pool.terminate_workers = lambda: terminate_calls.append(1) or real_terminate()
            return pool

        monkeypatch.setattr(calibrate, "make_pool", make_pool_spying_on_termination)
        out_path = tmp_path / "rows.json"

        with pytest.raises(type(failure)) as raised:
            calibrate.run_sweep(_config(workers=workers), out_path=out_path, solver_draws=SMALL_SOLVER_DRAWS)

        assert raised.value is failure
        printed_rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
        assert len(printed_rows) == 1
        assert json.loads(out_path.read_text()) == printed_rows
        assert len(terminate_calls) == (1 if workers == 2 else 0)

    @pytest.mark.parametrize("failing_write", [2, 3])
    def test_every_printed_row_is_already_in_the_file_when_a_later_write_fails(
        self, failing_write, tmp_path, monkeypatch, capsys,
    ) -> None:
        out_path = tmp_path / "rows.json"
        file_rows_at_failure = []
        write_calls = []
        real_write = defects.atomic_write_text

        def write_failing_on_the_chosen_call(path, text):
            write_calls.append(1)
            if len(write_calls) == failing_write:
                file_rows_at_failure.extend(json.loads(path.read_text()))
                raise OSError("disk full")
            real_write(path, text)

        monkeypatch.setattr(defects, "atomic_write_text", write_failing_on_the_chosen_call)

        with pytest.raises(OSError, match="disk full"):
            calibrate.run_sweep(_config(), out_path=out_path, solver_draws=SMALL_SOLVER_DRAWS)

        printed_rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
        assert len(printed_rows) == failing_write - 2
        assert printed_rows == file_rows_at_failure

    def test_an_unwritable_out_path_fails_before_any_replicate_runs(self, tmp_path, monkeypatch) -> None:
        blocker = tmp_path / "blocker"
        blocker.write_text("a regular file, not a directory")
        builder_calls = []
        real_builder = analysis.recall_fixture_terms
        monkeypatch.setattr(
            analysis, "recall_fixture_terms",
            lambda *args, **kwargs: builder_calls.append(1) or real_builder(*args, **kwargs),
        )

        with pytest.raises(OSError):
            calibrate.run_sweep(_config(), out_path=blocker / "rows.json", solver_draws=SMALL_SOLVER_DRAWS)

        assert builder_calls == []


class TestWorkersAndSeeds:
    CELL = calibrate.Cell(fixtures=6, acted_fixtures=6, true_difference=-DELTA, shift=-0.05)
    SEED_FIELDS = {
        "run_seed": 1, "metric": "recall", "k": 10, "harm": "normal", "over_cap_share": 1.0, "fixtures": 6,
        "true_difference": -DELTA, "replicate_index": 0,
    }

    def _jobs(self, **overrides) -> list[calibrate.ReplicateJob]:
        return calibrate.cell_jobs(_config(replicates=6, **overrides), self.CELL)

    def test_the_worker_function_and_a_job_survive_a_pickle_round_trip(self) -> None:
        job = self._jobs()[0]

        assert pickle.loads(pickle.dumps(calibrate.run_replicate)) is calibrate.run_replicate
        assert pickle.loads(pickle.dumps(job)) == job

    def test_every_job_carries_the_configs_seed_and_over_cap_share(self) -> None:
        jobs = self._jobs(seed=7, over_cap_share=0.5)

        assert {job.run_seed for job in jobs} == {7}
        assert {job.over_cap_share for job in jobs} == {0.5}

    def test_each_job_gives_the_same_result_in_reversed_order_and_on_a_rerun(self) -> None:
        jobs = self._jobs()

        forward = calibrate.run_jobs(jobs, pool=None, workers=1)
        backward = calibrate.run_jobs(list(reversed(jobs)), pool=None, workers=1)

        assert backward[::-1] == forward
        assert calibrate.run_jobs(self._jobs(), pool=None, workers=1) == forward

    @pytest.mark.parametrize("metric", ["recall", "precision"])
    def test_a_two_worker_pool_gives_the_in_process_results(self, metric, monkeypatch) -> None:
        # Above the exact cap with 200 flips, so workers also run the Monte Carlo sign-flip path.
        monte_carlo_cell = calibrate.Cell(
            fixtures=EXACT_CAP + 1, acted_fixtures=EXACT_CAP + 1, true_difference=-DELTA, shift=-0.05,
        )
        jobs = calibrate.cell_jobs(
            _config(metric=metric, fixture_counts=(EXACT_CAP + 1,), replicates=16, flips=200), monte_carlo_cell,
        )

        in_process = calibrate.run_jobs(jobs, pool=None, workers=1)
        map_kwargs = []
        with calibrate.make_pool(2) as pool:
            real_map = pool.map
            monkeypatch.setattr(pool, "map", lambda *args, **kwargs: map_kwargs.append(kwargs) or real_map(*args, **kwargs))
            pooled = calibrate.run_jobs(jobs, pool=pool, workers=2)

        assert map_kwargs[0]["chunksize"] > 1, "workers must receive multi-job chunks"
        assert pooled == in_process

    def test_a_pool_worker_ignores_sigint(self) -> None:
        with calibrate.make_pool(1) as pool:
            assert pool.submit(signal.getsignal, signal.SIGINT).result() == signal.SIG_IGN

    @pytest.mark.parametrize(
        ("field", "other"),
        [
            ("run_seed", 2), ("metric", "precision"), ("k", 11), ("harm", "concentrated"), ("over_cap_share", 0.5),
            ("fixtures", 7), ("true_difference", 0.0), ("replicate_index", 1),
        ],
    )
    def test_the_replicate_seed_changes_with_each_input(self, field, other) -> None:
        assert calibrate.replicate_seed(**self.SEED_FIELDS) != calibrate.replicate_seed(**{**self.SEED_FIELDS, field: other})

    def test_other_alphas_and_flips_draw_the_same_data(self) -> None:
        narrow = calibrate.run_jobs(self._jobs(alphas=(0.025,), flips=100), pool=None, workers=1)
        wide = calibrate.run_jobs(self._jobs(alphas=(0.025, 0.0125), flips=200), pool=None, workers=1)

        assert [result.estimate for result in narrow] == [result.estimate for result in wide]
        assert [result.lower_limits[0] for result in narrow] == [result.lower_limits[0] for result in wide]

    @pytest.mark.parametrize(
        "changed",
        [{"run_seed": 1}, {"replicate_index": 1}, {"over_cap_share": 0.75}, {"true_difference": 0.0}],
        ids=["run-seed", "replicate-index", "over-cap-share", "true-difference"],
    )
    def test_jobs_differing_only_in_a_seed_field_give_different_estimates_and_lower_limits(self, changed) -> None:
        job = self._jobs()[0]

        original = calibrate.run_replicate(job)
        changed_result = calibrate.run_replicate(job._replace(**changed))

        # A difference within float rounding would also arise from a reordered sum over the same per-fixture terms.
        assert changed_result.estimate != pytest.approx(original.estimate, abs=MATERIAL_DIFFERENCE)
        assert changed_result.lower_limits != pytest.approx(original.lower_limits, abs=MATERIAL_DIFFERENCE)


class TestPlannedCellsReachTheirTrueDifference:
    """The solved shift, the fixture plans, the count draws and the production builder together give the cell's difference."""

    REPLICATES = 400
    FIXTURES = 20
    K = 10
    OVER_CAP_SHARE = 0.25  # five acted fixtures, so one fewer moves the mean by several standard errors
    MARGIN = 0.1  # wide enough for that effect to clear the four-standard-error bound
    TRUE_DIFFERENCES = (-0.1, 0.0)
    SOLVER_DRAWS = 20_000
    JOB_K = 12  # not the 10 a hard-coded default would use

    def _estimate(self, metric: str, rng: random.Random, plans: list[calibrate.FixturePlan]) -> float:
        if metric == "recall":
            counts = calibrate.draw_recall_counts(rng, plans, k=self.K)
            build_terms = analysis.recall_fixture_terms
        else:
            counts = calibrate.draw_precision_counts(rng, plans)
            build_terms = analysis.precision_fixture_terms
        defect_ids = list(counts)
        terms = build_terms(
            counts, defect_ids, ARM_CURRENT_RULE, ARM_FUNCTION_CONTEXT,
            cluster_by_defect={defect_id: ("calibrate", defect_id) for defect_id in defect_ids}, delta=self.MARGIN,
        )
        assert terms is not None
        return terms.estimate

    @pytest.mark.parametrize("metric", ["recall", "precision"])
    @pytest.mark.parametrize("harm", ["normal", "concentrated"])
    def test_the_mean_estimate_equals_the_cells_true_difference(self, metric, harm) -> None:
        config = _config(
            metric=metric, harm=harm, fixture_counts=(self.FIXTURES,), k=self.K, delta=self.MARGIN,
            over_cap_share=self.OVER_CAP_SHARE,
        )

        cells = calibrate.plan_cells(config, solver_draws=self.SOLVER_DRAWS)

        assert [cell.true_difference for cell in cells] == list(self.TRUE_DIFFERENCES)
        for cell, expected_difference in zip(cells, self.TRUE_DIFFERENCES, strict=True):
            estimates = []
            for replicate_index in range(self.REPLICATES):
                rng = random.Random(f"integration|{metric}|{harm}|{expected_difference}|{replicate_index}")
                plans = calibrate.plan_fixtures(
                    rng, metric=metric, harm=harm, k=self.K, fixtures=cell.fixtures,
                    acted_fixtures=cell.acted_fixtures, shift=cell.shift,
                )
                estimates.append(self._estimate(metric, rng, plans))
            standard_error = statistics.stdev(estimates) / math.sqrt(self.REPLICATES)
            assert statistics.fmean(estimates) == pytest.approx(expected_difference, abs=SIGMA_BOUND * standard_error)

    @pytest.mark.parametrize("metric", ["recall", "precision"])
    def test_the_jobs_a_cell_plans_give_a_mean_estimate_equal_to_its_true_difference(self, metric, monkeypatch) -> None:
        # The sign-flip test is not under test here, so a stub keeps each replicate cheap.
        monkeypatch.setattr(analysis, "sign_flip_p_value", lambda values, **kwargs: 1.0)
        config = _config(
            metric=metric, harm="concentrated", fixture_counts=(self.FIXTURES,), k=self.JOB_K, delta=self.MARGIN,
            over_cap_share=self.OVER_CAP_SHARE, replicates=self.REPLICATES,
        )

        cells = calibrate.plan_cells(config, solver_draws=self.SOLVER_DRAWS)

        assert [cell.true_difference for cell in cells] == list(self.TRUE_DIFFERENCES)
        for cell, expected_difference in zip(cells, self.TRUE_DIFFERENCES, strict=True):
            results = calibrate.run_jobs(calibrate.cell_jobs(config, cell), pool=None, workers=1)
            estimates = [result.estimate for result in results]
            standard_error = statistics.stdev(estimates) / math.sqrt(self.REPLICATES)
            assert statistics.fmean(estimates) == pytest.approx(expected_difference, abs=SIGMA_BOUND * standard_error)

    def test_the_recall_jobs_a_cell_plans_draw_counts_out_of_the_configs_k(self) -> None:
        config = _config(fixture_counts=(self.FIXTURES,), k=self.JOB_K, replicates=30)
        cell = calibrate.Cell(self.FIXTURES, self.FIXTURES, true_difference=0.0, shift=0.0)

        results = calibrate.run_jobs(calibrate.cell_jobs(config, cell), pool=None, workers=1)

        for result in results:
            found_difference = result.estimate * self.JOB_K * self.FIXTURES
            assert found_difference == pytest.approx(round(found_difference))

    def test_the_precision_jobs_a_cell_plans_expect_four_findings_per_unit_of_the_configs_k(self, monkeypatch) -> None:
        monkeypatch.setattr(analysis, "sign_flip_p_value", lambda values, **kwargs: 1.0)
        baseline_volumes = []
        real_draw = calibrate.draw_precision_counts
        monkeypatch.setattr(
            calibrate, "draw_precision_counts",
            lambda rng, plans: baseline_volumes.extend(plan.baseline_volume for plan in plans) or real_draw(rng, plans),
        )
        config = _config(metric="precision", fixture_counts=(self.FIXTURES,), k=self.JOB_K, replicates=100)
        cell = calibrate.Cell(self.FIXTURES, self.FIXTURES, true_difference=0.0, shift=0.0)

        calibrate.run_jobs(calibrate.cell_jobs(config, cell), pool=None, workers=1)

        standard_error = statistics.stdev(baseline_volumes) / math.sqrt(len(baseline_volumes))
        assert statistics.fmean(baseline_volumes) == pytest.approx(4 * self.JOB_K, abs=SIGMA_BOUND * standard_error)


class TestCalibrateCommand:
    @pytest.fixture(autouse=True)
    def small_solver(self, monkeypatch) -> None:
        monkeypatch.setattr(calibrate, "SOLVER_DRAWS", SMALL_SOLVER_DRAWS)

    def _run(self, argv: list[str]) -> int:
        return run_review_bench.cmd_calibrate(run_review_bench.build_parser().parse_args(["calibrate", *argv]))

    def test_two_fixture_counts_print_rows_equal_to_the_out_array(self, tmp_path, monkeypatch, capsys) -> None:
        out_path = tmp_path / "missing-directory" / "rows.json"
        sign_flip_kwargs = []
        real_p_value = analysis.sign_flip_p_value
        monkeypatch.setattr(
            analysis, "sign_flip_p_value",
            lambda values, **kwargs: sign_flip_kwargs.append(kwargs) or real_p_value(values, **kwargs),
        )

        exit_code = self._run([
            "--metric", "recall", "--k", "10", "--fixtures", "6", "--fixtures", "8", "--alpha", "0.025",
            "--alpha", "0.0125", "--flips", "200", "--replicates", "3", "--out", str(out_path),
        ])

        assert exit_code == 0
        printed_rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
        assert printed_rows == json.loads(out_path.read_text())
        for row in printed_rows:
            assert [rates["alpha"] for rates in row["alphas"]] == [0.025, 0.0125]
            assert row["cells_planned"] == 4
        assert len(printed_rows) == 4
        assert sign_flip_kwargs
        assert all(kwargs == {"resamples": 200} for kwargs in sign_flip_kwargs)

    def test_every_flag_at_a_non_default_value_reaches_the_rows_and_the_pool(self, tmp_path, monkeypatch, capsys) -> None:
        _patch_cpu_count(monkeypatch, 2)
        out_path = tmp_path / "rows.json"
        out_path.write_text("stale text")
        pool_sizes = []
        real_make_pool = calibrate.make_pool
        monkeypatch.setattr(calibrate, "make_pool", lambda workers: pool_sizes.append(workers) or real_make_pool(workers))

        exit_code = self._run([
            "--metric", "precision", "--k", "7", "--fixtures", "6", "--alpha", "0.05", "--delta", "0.2",
            "--harm", "concentrated", "--over-cap-share", "0.75", "--replicates", "3", "--seed", "11",
            "--workers", "2", "--flips", "200", "--out", str(out_path),
        ])

        assert exit_code == 0
        captured = capsys.readouterr()
        plan_lines = [line for line in captured.err.splitlines() if "fixtures=6 " in line and "solved in" in line]
        assert len(plan_lines) == 2
        for line in plan_lines:
            settings = _key_value_tokens(line)
            assert {key: settings[key] for key in ("over_cap_share", "flips", "seed", "workers")} == {
                "over_cap_share": "0.75", "flips": "200", "seed": "11", "workers": "2",
            }
            assert settings["alphas"] == "0.05"
            assert settings["sign_flip_path"] == calibrate.SIGN_FLIP_PATH_EXACT
        printed_rows = [json.loads(line) for line in captured.out.splitlines()]
        assert json.loads(out_path.read_text()) == printed_rows
        assert pool_sizes == [2]
        assert printed_rows[0]["true_difference"] == -0.2
        for row in printed_rows:
            echoed = {
                "metric": "precision", "k": 7, "harm": "concentrated", "over_cap_share": 0.75, "delta": 0.2,
                "replicates": 3, "seed": 11, "flips": 200, "fixtures": 6,
            }
            assert {key: row[key] for key in echoed} == echoed
            assert [rates["alpha"] for rates in row["alphas"]] == [0.05]

    def test_the_required_flags_alone_run_with_the_analysis_constants(self, capsys) -> None:
        exit_code = self._run(["--metric", "recall", "--k", "10", "--fixtures", "6", "--replicates", "3"])

        assert exit_code == 0
        printed_rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
        assert printed_rows[0]["true_difference"] == -analysis.DELTA
        for row in printed_rows:
            assert (row["harm"], row["over_cap_share"], row["seed"], row["acted_fixtures"]) == ("normal", 1.0, 0, 6)
            assert row["delta"] == analysis.DELTA
            assert row["flips"] == analysis.SIGN_FLIP_RESAMPLES
            assert [rates["alpha"] for rates in row["alphas"]] == [analysis.ALPHA_ONE_SIDED]

    def test_the_replicate_count_defaults_to_4000(self) -> None:
        required_flags = ["calibrate", "--metric", "recall", "--k", "10", "--fixtures", "6"]
        arguments = run_review_bench.build_parser().parse_args(required_flags)

        assert arguments.replicates == 4000

    @pytest.mark.parametrize("out", ["", ".", "/"])
    def test_an_out_path_naming_no_file_returns_2_before_any_cell_is_planned_or_replicate_runs(
        self, out, monkeypatch, capsys,
    ) -> None:
        builder_calls = []
        real_builder = analysis.recall_fixture_terms
        monkeypatch.setattr(
            analysis, "recall_fixture_terms",
            lambda *args, **kwargs: builder_calls.append(1) or real_builder(*args, **kwargs),
        )

        exit_code = self._run(["--metric", "recall", "--k", "10", "--fixtures", "6", "--replicates", "3", "--out", out])

        captured = capsys.readouterr()
        assert exit_code == 2
        assert captured.err == f"calibrate: --out must name a file, got {out!r}\n"
        assert captured.out == ""
        assert builder_calls == []

    def test_a_share_of_zero_returns_2_naming_the_field(self, capsys) -> None:
        exit_code = self._run(["--metric", "recall", "--k", "10", "--fixtures", "6", "--over-cap-share", "0"])

        captured = capsys.readouterr()
        assert exit_code == 2
        assert captured.err.startswith("calibrate:")
        assert "over_cap_share" in captured.err
        assert captured.out == ""

    def test_an_unreachable_second_cell_returns_2_before_any_row_or_out_file(self, tmp_path, capsys) -> None:
        out_path = tmp_path / "rows.json"

        exit_code = self._run([
            "--metric", "recall", "--k", "10", "--fixtures", "2", "--fixtures", "20", "--over-cap-share", "0.05",
            "--replicates", "3", "--out", str(out_path),
        ])

        captured = capsys.readouterr()
        assert exit_code == 2
        assert captured.err.splitlines()[-1].startswith("calibrate: delta and over_cap_share:")
        assert captured.out == ""
        assert not out_path.exists()

    def test_a_value_error_inside_planning_propagates_instead_of_returning_2(self, monkeypatch) -> None:
        def fail(*args, **kwargs):
            raise ValueError("solver bug")

        monkeypatch.setattr(calibrate, "solve_shift", fail)

        with pytest.raises(ValueError, match="solver bug"):
            self._run(["--metric", "recall", "--k", "10", "--fixtures", "6", "--replicates", "3"])

    def test_a_value_error_inside_the_sweep_propagates_instead_of_returning_2(self, monkeypatch) -> None:
        def fail(job):
            raise ValueError("generator bug")

        monkeypatch.setattr(calibrate, "run_replicate", fail)

        with pytest.raises(ValueError, match="generator bug"):
            self._run(["--metric", "recall", "--k", "10", "--fixtures", "6", "--replicates", "3"])


class TestCalibrationConfig:
    @pytest.mark.parametrize(
        ("overrides", "field"),
        [
            ({"metric": "accuracy"}, "metric"),
            ({"harm": "diffuse"}, "harm"),
            ({"fixture_counts": (1,)}, "fixture_counts"),
            ({"fixture_counts": ()}, "fixture_counts"),
            ({"alphas": (0.0,)}, "alphas"),
            ({"alphas": (0.5,)}, "alphas"),
            ({"alphas": (math.nextafter(calibrate.MIN_ALPHA, 0.0),)}, "alphas"),
            ({"alphas": (float("nan"),)}, "alphas"),
            ({"delta": 0.0}, "delta"),
            ({"delta": 1.0}, "delta"),
            ({"delta": float("nan")}, "delta"),
            ({"over_cap_share": 0.0}, "over_cap_share"),
            ({"over_cap_share": 1.5}, "over_cap_share"),
            ({"over_cap_share": float("nan")}, "over_cap_share"),
            ({"k": 0}, "k"),
            ({"replicates": 0}, "replicates"),
            ({"workers": 0}, "workers"),
            ({"flips": 0}, "flips"),
        ],
    )
    def test_rejects_a_setting_outside_its_range_naming_the_field(self, overrides, field) -> None:
        with pytest.raises(calibrate.CalibrationConfigError, match=field):
            _config(**overrides)

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("fixture_counts", (2,)), ("alphas", (calibrate.MIN_ALPHA,)), ("alphas", (0.4999,)), ("delta", 0.5),
            ("over_cap_share", 1.0),
        ],
    )
    def test_accepts_a_setting_at_its_boundary(self, field, value) -> None:
        assert getattr(_config(**{field: value}), field) == value

    def test_calibration_config_error_is_a_value_error(self) -> None:
        assert issubclass(calibrate.CalibrationConfigError, ValueError)

    def test_workers_are_capped_at_the_usable_cpu_count(self, monkeypatch) -> None:
        _patch_cpu_count(monkeypatch, 2)

        assert _config(workers=2).workers == 2
        with pytest.raises(calibrate.CalibrationConfigError, match="workers"):
            _config(workers=3)

    def test_workers_above_one_are_rejected_when_the_cpu_count_is_unknown(self, monkeypatch) -> None:
        _patch_cpu_count(monkeypatch, None)

        with pytest.raises(calibrate.CalibrationConfigError, match="workers"):
            _config(workers=2)

    def test_one_worker_is_accepted_when_the_cpu_count_is_unknown(self, monkeypatch) -> None:
        _patch_cpu_count(monkeypatch, None)

        assert _config(workers=1).workers == 1

    @pytest.mark.parametrize("fixture_counts", [(EXACT_CAP + 1,), (6, EXACT_CAP + 1)])
    def test_rejects_an_alpha_below_the_smallest_monte_carlo_p_value_naming_alphas_and_flips(self, fixture_counts) -> None:
        with pytest.raises(calibrate.CalibrationConfigError, match=r"alphas and flips") as raised:
            _config(fixture_counts=fixture_counts, flips=50, alphas=(0.0125,))

        assert "1 / (flips + 1)" in str(raised.value)

    def test_accepts_that_alpha_when_every_fixture_count_takes_the_exact_path(self) -> None:
        assert _config(fixture_counts=(6, EXACT_CAP), flips=50, alphas=(0.0125,)).alphas == (0.0125,)

    def test_the_smallest_monte_carlo_p_value_is_adoptable_so_an_alpha_equal_to_it_is_accepted(self) -> None:
        smallest_p_value = 1 / 51

        assert _config(fixture_counts=(EXACT_CAP + 1,), flips=50, alphas=(smallest_p_value,)).alphas == (smallest_p_value,)
        with pytest.raises(calibrate.CalibrationConfigError, match=r"alphas and flips"):
            _config(fixture_counts=(EXACT_CAP + 1,), flips=50, alphas=(math.nextafter(smallest_p_value, 0.0),))

    @pytest.mark.parametrize(
        ("fixtures", "flips"), [(5, 50), (EXACT_CAP, 50), (EXACT_CAP + 1, 50)],
        ids=["exact-path", "exact-cap", "monte-carlo-path"],
    )
    def test_the_smallest_sign_flip_p_value_is_what_analysis_returns_for_all_positive_values(self, fixtures, flips) -> None:
        p_value = analysis.sign_flip_p_value([1.0] * fixtures, resamples=flips)

        assert p_value == calibrate.smallest_sign_flip_p_value(fixtures, flips)

    def test_omitted_delta_alphas_and_flips_take_the_analysis_constants(self) -> None:
        config = _config()

        assert config.delta == analysis.DELTA
        assert config.alphas == (analysis.ALPHA_ONE_SIDED,)
        assert config.flips == analysis.SIGN_FLIP_RESAMPLES


def test_calibrate_stays_outside_the_harness_closure_while_a_module_analysis_imports_is_inside() -> None:
    """Repo-relative string keys: a Path-typed probe would pass vacuously."""
    closure = analysis.compute_harness_closure()

    assert "evals/review_bench/arms.py" in closure
    assert "evals/review_bench/calibrate.py" not in closure

