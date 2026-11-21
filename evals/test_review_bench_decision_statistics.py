"""Tests for the decision statistics in evals/review_bench/analysis.py: the
Student t quantile, the sign-flip p-value and the fixture-level terms and
interval. Offline throughout: every case works from synthetic counts, never a
real campaign. No test launches `claude`.
"""
from __future__ import annotations

import math
import random
import statistics
import types
from collections.abc import Callable, Hashable
from fractions import Fraction

import pytest
from review_bench import analysis
from test_review_bench_analysis import ARM_BASELINE, ARM_X, _own_fixture_each


def _student_t_central_probability_by_integration(t: float, df: int, *, intervals: int = 2000) -> float:
    """P(|T| < t) from Simpson's rule over the density, built from math.lgamma
    so it shares no code with the series under test."""
    log_normalizer = math.lgamma((df + 1) / 2) - math.lgamma(df / 2) - 0.5 * math.log(df * math.pi)

    def density(x: float) -> float:
        return math.exp(log_normalizer - (df + 1) / 2 * math.log1p(x * x / df))

    step = t / intervals
    simpson_sum = density(0.0) + density(t)
    for index in range(1, intervals):
        simpson_sum += (4 if index % 2 else 2) * density(index * step)
    return 2 * simpson_sum * step / 3


class TestStudentTUpperQuantile:
    ALPHAS = (0.025, 0.0125)
    # Tails whose df 1 and df 2 quantiles are at most 1.0, so the bracketing search needs no doubling.
    LARGE_ALPHAS = (0.25, 0.4, 0.49)

    @pytest.mark.parametrize("alpha", ALPHAS + LARGE_ALPHAS)
    def test_df_1_is_the_cauchy_quantile(self, alpha: float) -> None:
        assert analysis.student_t_upper_quantile(1, alpha) == pytest.approx(math.tan(math.pi * (0.5 - alpha)), abs=1e-9)

    @pytest.mark.parametrize("alpha", ALPHAS + LARGE_ALPHAS)
    def test_df_2_matches_its_closed_form_quantile(self, alpha: float) -> None:
        expected = (1 - 2 * alpha) / math.sqrt(2 * alpha * (1 - alpha))

        assert analysis.student_t_upper_quantile(2, alpha) == pytest.approx(expected, abs=1e-9)

    @pytest.mark.parametrize("alpha", [1e-4, 1e-5, 1e-6])
    @pytest.mark.parametrize("df", [1, 2])
    def test_df_1_and_df_2_stay_relatively_accurate_in_the_far_tail(self, df: int, alpha: float) -> None:
        """The df 1 quantile at tail 1e-6 is about 3.2e5. Bracketing it from 1.0 takes 19 doublings,
        so a cap under 19 fails here. The df 1 reference tan(pi * (0.5 - alpha)) itself
        loses relative precision near its pole, so the tolerance sits well above the accuracy
        student_t_upper_quantile documents."""
        expected_by_df = {
            1: math.tan(math.pi * (0.5 - alpha)),
            2: (1 - 2 * alpha) / math.sqrt(2 * alpha * (1 - alpha)),
        }

        assert analysis.student_t_upper_quantile(df, alpha) == pytest.approx(
            expected_by_df[df], rel=1e-9,
        )

    @pytest.mark.parametrize("alpha", ALPHAS)
    def test_df_3_quantile_lands_on_one_minus_alpha_in_its_closed_form_cdf(self, alpha: float) -> None:
        t = analysis.student_t_upper_quantile(3, alpha)
        scaled = t / math.sqrt(3)

        cdf = 0.5 + (math.atan(scaled) + scaled / (1 + scaled**2)) / math.pi

        assert cdf == pytest.approx(1 - alpha, abs=1e-9)

    @pytest.mark.parametrize("alpha", ALPHAS)
    def test_df_10000_is_within_a_thousandth_of_the_normal_quantile(self, alpha: float) -> None:
        assert analysis.student_t_upper_quantile(10_000, alpha) == pytest.approx(
            statistics.NormalDist().inv_cdf(1 - alpha), abs=1e-3,
        )

    @pytest.mark.parametrize(
        ("df", "alpha", "expected"),
        [
            (4, 0.025, 2.776445), (9, 0.025, 2.262157), (19, 0.025, 2.093024), (29, 0.025, 2.045230),
            (39, 0.025, 2.022691), (4, 0.0125, 3.495406),
        ],
    )
    def test_pinned_critical_values(self, df: int, alpha: float, expected: float) -> None:
        """Standard t tables list these to three places (e.g. 2.776 at df 4, two-sided 95%).
        The six-place pins are confirmed by the integration check below."""
        assert analysis.student_t_upper_quantile(df, alpha) == pytest.approx(expected, abs=5e-7)

    @pytest.mark.parametrize("alpha", ALPHAS)
    @pytest.mark.parametrize("df", range(4, 41))
    def test_central_probability_at_the_quantile_equals_numerical_integration_of_the_density(
        self, df: int, alpha: float,
    ) -> None:
        t = analysis.student_t_upper_quantile(df, alpha)

        assert _student_t_central_probability_by_integration(t, df) == pytest.approx(1 - 2 * alpha, abs=1e-9)

    @pytest.mark.parametrize("alpha", ALPHAS)
    def test_the_quantile_decreases_as_df_rises(self, alpha: float) -> None:
        quantiles = [analysis.student_t_upper_quantile(df, alpha) for df in range(1, 41)]

        assert all(later < earlier for earlier, later in zip(quantiles, quantiles[1:], strict=False))

    @pytest.mark.parametrize(
        ("df", "upper_tail", "message"),
        [
            (0, 0.025, "df must be an integer >= 1"), (-3, 0.025, "df must be an integer >= 1"),
            (2.5, 0.025, "df must be an integer >= 1"), (True, 0.025, "df must be an integer >= 1"),
            (4, 0.0, "upper_tail must be in"), (4, 0.5, "upper_tail must be in"),
            (4, -0.1, "upper_tail must be in"), (4, float("nan"), "upper_tail must be in"),
            (4, 1e-17, "below float resolution"),
        ],
    )
    def test_a_df_or_tail_outside_the_domain_raises_its_own_guards_message(self, df, upper_tail, message) -> None:
        """The last case's 1 - 2 * tail rounds to 1.0, which no finite t reaches."""
        with pytest.raises(ValueError, match=message):
            analysis.student_t_upper_quantile(df, upper_tail)


def _exact_integer_sign_flip_p(lattice_values: list[int], *, strictly_above: bool = False) -> float:
    """The one-sided sign-flip p-value counted in exact integers by a
    subset-sum DP, so a tie between two sign patterns is never a float
    comparison. `strictly_above` drops the patterns that tie the observed sum."""
    observed_sum = sum(lattice_values)
    patterns_by_sum = {0: 1}
    for value in lattice_values:
        next_patterns_by_sum: dict[int, int] = {}
        for partial_sum, pattern_count in patterns_by_sum.items():
            for signed in (partial_sum + value, partial_sum - value):
                next_patterns_by_sum[signed] = next_patterns_by_sum.get(signed, 0) + pattern_count
        patterns_by_sum = next_patterns_by_sum
    counted_patterns = sum(
        count for total, count in patterns_by_sum.items()
        if (total > observed_sum if strictly_above else total >= observed_sum)
    )
    return counted_patterns / 2 ** len(lattice_values)


class TestSignFlipPValue:
    # Just under the lowest tied mass, 0.035, among the vectors of the Monte Carlo tie test.
    MIN_TIED_PATTERN_MASS = 0.03

    def test_all_positive_values_give_one_over_two_to_the_f(self) -> None:
        assert analysis.sign_flip_p_value([1, 2, 3]) == 1 / 8

    def test_a_mixed_sign_vector_counts_every_pattern_at_least_as_large(self) -> None:
        assert analysis.sign_flip_p_value([1, -1, 2]) == 3 / 8

    def test_patterns_tying_the_observed_sum_only_in_exact_arithmetic_count(self) -> None:
        """0.1 + 0.2 - 0.3 is not 0.0 in floats, so a bare >= would miss the two patterns that tie."""
        assert analysis.sign_flip_p_value([0.1, 0.2, -0.3]) == 5 / 8

    @pytest.mark.parametrize("value_count", range(1, 21))
    def test_the_exact_path_equals_an_exact_integer_oracle_at_every_size_up_to_20(self, value_count: int) -> None:
        rng = random.Random(value_count)
        lattice_values = [rng.randint(-6, 9) for _ in range(value_count)]
        lattice_values[-1] = lattice_values[0]
        floats_on_the_lattice = [lattice_value / 10 for lattice_value in lattice_values]

        assert analysis.sign_flip_p_value(floats_on_the_lattice) == _exact_integer_sign_flip_p(lattice_values)

    def test_the_monte_carlo_path_lands_within_four_standard_errors_of_the_binomial_tail(self) -> None:
        """Every flipped term is +/-1 whatever the sign pattern, so the flipped sum is 2b - 24 for
        b positive signs, and the observed sum 4 needs b >= 14."""
        values = [1.0] * 14 + [-1.0] * 10
        resamples = 20_000
        binomial_tail = sum(math.comb(24, positives) for positives in range(14, 25)) / 2**24
        standard_error = math.sqrt(binomial_tail * (1 - binomial_tail) / resamples)

        p_value = analysis.sign_flip_p_value(values, resamples=resamples)

        assert abs(p_value - binomial_tail) < 4 * standard_error

    def test_the_same_seed_repeats_the_monte_carlo_p_value(self) -> None:
        values = [1.0] * 14 + [-1.0] * 10

        assert analysis.sign_flip_p_value(values, resamples=500, seed=3) == analysis.sign_flip_p_value(
            values, resamples=500, seed=3,
        )

    def test_the_exact_path_ignores_the_seed(self) -> None:
        values = [0.3, -0.1, 0.4, 0.15] * 5

        assert analysis.sign_flip_p_value(values, seed=1) == analysis.sign_flip_p_value(values, seed=2)

    def test_all_positive_values_above_the_exact_cap_give_the_smallest_monte_carlo_p_value(self) -> None:
        resamples = 1000

        assert analysis.sign_flip_p_value([1.0] * 24, resamples=resamples) == 1 / (resamples + 1)

    @pytest.mark.parametrize(("value_count", "vector_seed"), [(21, 15), (22, 45), (23, 52), (24, 45)])
    def test_the_monte_carlo_path_counts_float_ties_like_the_exact_integer_oracle(
        self, value_count: int, vector_seed: int,
    ) -> None:
        """Each (value_count, vector_seed) vector is on a 0.1 lattice and was chosen for its tied sign-pattern mass.
        The floor fails the test when a changed random.Random stream yields a vector with less tied mass than
        MIN_TIED_PATTERN_MASS. test_a_drawn_pattern_tying_the_observed_sum_only_in_exact_arithmetic_is_counted pins
        the tie handling deterministically."""
        rng = random.Random(vector_seed)
        lattice_values = [rng.randint(-3, 6) for _ in range(value_count)]
        resamples = 20_000
        exact_p_value = _exact_integer_sign_flip_p(lattice_values)
        tied_mass = exact_p_value - _exact_integer_sign_flip_p(lattice_values, strictly_above=True)
        assert tied_mass >= self.MIN_TIED_PATTERN_MASS
        standard_error = math.sqrt(exact_p_value * (1 - exact_p_value) / resamples)

        p_value = analysis.sign_flip_p_value([lattice_value / 10 for lattice_value in lattice_values], resamples=resamples)

        assert abs(p_value - exact_p_value) < 4 * standard_error

    def test_a_drawn_pattern_tying_the_observed_sum_only_in_exact_arithmetic_is_counted(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The drawn pattern flips -0.3, 0.4 and -0.1, which sum to zero, so it ties the observed sum exactly.
        Its float sum rounds below the float observed sum, so a bare >= would miss it."""
        lattice_values = [6, -3, 3, 4, 6, -3, 0, 4, 4, 1, -1, -3, 5, 4, 2, -2, 0, 2, -3, 3, -1]
        values = [lattice_value / 10 for lattice_value in lattice_values]
        flipped_indexes = {1, 3, 10}
        tied_sign_bits = sum(1 << index for index in range(len(values)) if index not in flipped_indexes)
        tied_float_sum = sum(
            value if (tied_sign_bits >> index) & 1 else -value for index, value in enumerate(values)
        )
        tied_lattice_sum = sum(
            lattice_value if (tied_sign_bits >> index) & 1 else -lattice_value
            for index, lattice_value in enumerate(lattice_values)
        )
        assert tied_lattice_sum == sum(lattice_values)
        assert tied_float_sum < sum(values)

        class FakeRandom:
            def __init__(self, seed: int) -> None:
                pass

            def getrandbits(self, count: int) -> int:
                return tied_sign_bits

        monkeypatch.setattr(analysis, "random", types.SimpleNamespace(Random=FakeRandom))

        resamples = 1

        assert analysis.sign_flip_p_value(values, resamples=resamples) == (1 + 1) / (resamples + 1)

    def test_different_seeds_give_different_monte_carlo_p_values(self) -> None:
        rng = random.Random(45)
        values = [rng.randint(-3, 6) / 10 for _ in range(24)]

        assert analysis.sign_flip_p_value(values, resamples=2000, seed=1) != analysis.sign_flip_p_value(
            values, resamples=2000, seed=2,
        )

    def test_twenty_values_are_exact_and_twenty_one_are_monte_carlo(self) -> None:
        rng = random.Random(7)
        twenty_values = [rng.randint(-3, 6) / 10 for _ in range(20)]
        twenty_one_values = [*twenty_values, 0.4]

        exact_by_seed = {analysis.sign_flip_p_value(twenty_values, resamples=500, seed=seed) for seed in (1, 2, 3)}
        monte_carlo_by_seed = {analysis.sign_flip_p_value(twenty_one_values, resamples=500, seed=seed) for seed in (1, 2, 3)}

        assert len(exact_by_seed) == 1
        assert (exact_by_seed.pop() * 2**20).is_integer()
        assert len(monte_carlo_by_seed) > 1

    def test_all_zero_values_are_never_evidence_against_the_null(self) -> None:
        assert analysis.sign_flip_p_value([0.0, 0.0, 0.0]) == 1.0

    def test_all_zero_values_above_the_exact_cap_are_never_evidence_against_the_null(self) -> None:
        assert analysis.sign_flip_p_value([0.0] * 24, resamples=100) == 1.0

    def test_sign_sums_a_millionth_of_the_magnitude_sum_apart_are_counted_as_distinct(self) -> None:
        """Flipping 1e-6 lowers the sum by 2e-6, about 1e-6 of the 2.000001 magnitude sum, so only the
        observed sign pattern ties it."""
        assert analysis.sign_flip_p_value([1.0, 1.0, 1e-6]) == 1 / 8

    @pytest.mark.parametrize("value_count", [3, 24])
    @pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), float("-inf")])
    def test_a_non_finite_value_raises_on_both_paths(self, value_count: int, bad_value: float) -> None:
        values = [1.0] * (value_count - 1) + [bad_value]

        with pytest.raises(ValueError, match="finite"):
            analysis.sign_flip_p_value(values, resamples=10)

    def test_empty_values_raise(self) -> None:
        with pytest.raises(ValueError, match="no values"):
            analysis.sign_flip_p_value([])

    def test_the_default_resamples_give_one_over_100_001_for_all_positive_values(self) -> None:
        """With 24 positive values only the all-positive flip pattern reaches the observed sum. At the default
        seed no draw is that pattern, which a 2^-24 chance per draw makes likely but not certain, so the
        p-value is 1 / (resamples + 1). The literal pins the default of 100,000 resamples, which the
        SIGN_FLIP_RESAMPLES constant cannot pin against itself."""
        p_value = analysis.sign_flip_p_value([1.0] * 24)

        assert p_value == pytest.approx(1 / 100_001)

    def test_a_single_resample_is_accepted_and_gives_one_half_or_one(self) -> None:
        """One flip counts 0 or 1 as extreme, so (1 + count) / 2 is 1/2 or 1."""
        p_value = analysis.sign_flip_p_value([1.0] * 14 + [-1.0] * 10, resamples=1)

        assert p_value in {1 / 2, 1.0}

    @pytest.mark.parametrize("resamples", [0, -5])
    def test_fewer_than_one_resample_raises(self, resamples: int) -> None:
        with pytest.raises(ValueError, match="resamples"):
            analysis.sign_flip_p_value([1.0, 2.0], resamples=resamples)


def _recall_counts_by_defect(found_x_and_baseline_of_ten: dict[str, tuple[int, int]]) -> dict[str, analysis.DefectRecallCounts]:
    """Each defect completed ten runs in both arms; the pair is (found in arm X, found in the baseline arm)."""
    return {
        defect_id: analysis.DefectRecallCounts(
            defect_id=defect_id, found_by_arm={ARM_X: found_x, ARM_BASELINE: found_baseline},
            completed_by_arm={ARM_X: 10, ARM_BASELINE: 10},
        )
        for defect_id, (found_x, found_baseline) in found_x_and_baseline_of_ten.items()
    }


def _exact_recall_terms(
    counts: dict[str, analysis.DefectRecallCounts], clusters: dict, *, delta: float,
) -> tuple[Fraction, list[Fraction], list[Fraction]]:
    """(estimate, residuals, null_centered) for ARM_X minus ARM_BASELINE recall in exact rationals, with
    fixtures in order of first appearance in `counts`. The residual and null-centered scale is each
    fixture's difference sum against its defect count, over the mean defect count."""
    difference_sum_by_fixture: dict[Hashable, Fraction] = {}
    defect_count_by_fixture: dict[Hashable, int] = {}
    for defect_id, defect_counts in counts.items():
        fixture = clusters[defect_id]
        rate_x = Fraction(defect_counts.found_by_arm[ARM_X], defect_counts.completed_by_arm[ARM_X])
        rate_baseline = Fraction(defect_counts.found_by_arm[ARM_BASELINE], defect_counts.completed_by_arm[ARM_BASELINE])
        difference_sum_by_fixture[fixture] = difference_sum_by_fixture.get(fixture, 0) + rate_x - rate_baseline
        defect_count_by_fixture[fixture] = defect_count_by_fixture.get(fixture, 0) + 1
    estimate = sum(difference_sum_by_fixture.values()) / sum(defect_count_by_fixture.values())
    mean_defect_count = Fraction(sum(defect_count_by_fixture.values()), len(defect_count_by_fixture))
    exact_delta = Fraction(delta)
    residuals = [
        (difference_sum_by_fixture[fixture] - estimate * defect_count_by_fixture[fixture]) / mean_defect_count
        for fixture in difference_sum_by_fixture
    ]
    null_centered = [
        (difference_sum_by_fixture[fixture] + exact_delta * defect_count_by_fixture[fixture]) / mean_defect_count
        for fixture in difference_sum_by_fixture
    ]
    return estimate, residuals, null_centered


class TestRecallFixtureTerms:
    def test_mixed_fixture_sizes_with_a_nonzero_delta_match_hand_computed_terms(self) -> None:
        """Fixtures of 1, 2 and 3 defects with per-defect differences (0.2), (-0.2, 0) and (0.4, -0.2, 0):
        the fixture sums are 1/5, -1/5 and 1/5, the estimate 1/30 and the mean defect count 2."""
        counts = _recall_counts_by_defect(
            {"a1": (6, 4), "b1": (3, 5), "b2": (7, 7), "c1": (9, 5), "c2": (2, 4), "c3": (5, 5)},
        )
        clusters = {"a1": "A", "b1": "B", "b2": "B", "c1": "C", "c2": "C", "c3": "C"}

        terms = analysis.recall_fixture_terms(
            counts, list(counts), ARM_BASELINE, ARM_X, cluster_by_defect=clusters, delta=0.1,
        )

        assert terms is not None
        assert terms.estimate == pytest.approx(1 / 30)
        assert terms.residuals == pytest.approx((1 / 12, -2 / 15, 1 / 20))
        assert terms.null_centered == pytest.approx((3 / 20, 0.0, 1 / 4))
        assert statistics.mean(terms.null_centered) == pytest.approx(terms.estimate + 0.1)

    def test_unequal_completed_counts_and_an_arm_missing_from_completed_by_arm_match_hand_computed_terms(self) -> None:
        """Fixture A holds d1 and d2, fixture B holds d3. Arm X completed 4 runs per defect and the baseline 8,
        except d3, whose baseline is absent from completed_by_arm and so has detection rate 0.0 despite a found
        count of 2. The per-defect differences are d1 1/2 - 1/4 = 1/4, d2 1/4 - 3/4 = -1/2 and d3 3/4 - 0 = 3/4,
        so the fixture sums are -1/4 and 3/4, the estimate (1/2) / 3 = 1/6, and the mean defect count 3/2.
        The residuals are (-1/4 - 2/6) / (3/2) = -7/18 and (3/4 - 1/6) / (3/2) = 7/18. With delta 0.1 the
        null-centered terms are (-1/4 + 2/10) / (3/2) = -1/30 and (3/4 + 1/10) / (3/2) = 17/30."""
        counts = {
            "d1": analysis.DefectRecallCounts(
                defect_id="d1", found_by_arm={ARM_X: 2, ARM_BASELINE: 2}, completed_by_arm={ARM_X: 4, ARM_BASELINE: 8},
            ),
            "d2": analysis.DefectRecallCounts(
                defect_id="d2", found_by_arm={ARM_X: 1, ARM_BASELINE: 6}, completed_by_arm={ARM_X: 4, ARM_BASELINE: 8},
            ),
            "d3": analysis.DefectRecallCounts(
                defect_id="d3", found_by_arm={ARM_X: 3, ARM_BASELINE: 2}, completed_by_arm={ARM_X: 4},
            ),
        }
        clusters = {"d1": "A", "d2": "A", "d3": "B"}

        terms = analysis.recall_fixture_terms(
            counts, list(counts), ARM_BASELINE, ARM_X, cluster_by_defect=clusters, delta=0.1,
        )

        assert terms is not None
        assert terms.estimate == pytest.approx(1 / 6)
        assert terms.estimate == pytest.approx(analysis.recall_difference(counts, list(counts), ARM_X, ARM_BASELINE))
        assert terms.residuals == pytest.approx((-7 / 18, 7 / 18))
        assert terms.null_centered == pytest.approx((-1 / 30, 17 / 30))

    @pytest.mark.parametrize("seed", range(5))
    def test_the_estimate_equals_recall_difference_and_the_terms_match_exact_rationals(self, seed: int) -> None:
        rng = random.Random(seed)
        found_pairs = {}
        clusters = {}
        for fixture_index in range(rng.randint(2, 8)):
            for defect_index in range(rng.randint(1, 3)):
                defect_id = f"f{fixture_index}d{defect_index}"
                found_pairs[defect_id] = (rng.randint(0, 10), rng.randint(0, 10))
                clusters[defect_id] = f"f{fixture_index}"
        counts = _recall_counts_by_defect(found_pairs)

        terms = analysis.recall_fixture_terms(counts, list(counts), ARM_BASELINE, ARM_X, cluster_by_defect=clusters)

        assert terms is not None
        assert terms.estimate == pytest.approx(analysis.recall_difference(counts, list(counts), ARM_X, ARM_BASELINE))
        assert sum(terms.residuals) == pytest.approx(0.0, abs=1e-12)
        exact_estimate, exact_residuals, exact_null_centered = _exact_recall_terms(counts, clusters, delta=analysis.DELTA)
        assert terms.estimate == pytest.approx(float(exact_estimate))
        assert terms.residuals == pytest.approx(tuple(float(residual) for residual in exact_residuals))
        assert terms.null_centered == pytest.approx(tuple(float(term) for term in exact_null_centered))

    def test_fixtures_keyed_by_base_and_head_commit_pairs_match_the_exact_rational_terms(self) -> None:
        """Two fixtures share a base commit and differ in head commit, so the whole pair is the fixture."""
        counts = _recall_counts_by_defect(
            {"a1": (6, 4), "a2": (3, 5), "b1": (7, 7), "b2": (9, 5), "b3": (2, 4), "c1": (5, 1)},
        )
        clusters = {
            "a1": ("base1", "head1"), "a2": ("base1", "head1"), "b1": ("base1", "head2"), "b2": ("base1", "head2"),
            "b3": ("base1", "head2"), "c1": ("base2", "head3"),
        }

        terms = analysis.recall_fixture_terms(
            counts, list(counts), ARM_BASELINE, ARM_X, cluster_by_defect=clusters, delta=0.1,
        )

        exact_estimate, exact_residuals, exact_null_centered = _exact_recall_terms(counts, clusters, delta=0.1)
        assert terms is not None
        assert len(terms.residuals) == 3
        assert terms.estimate == pytest.approx(float(exact_estimate))
        assert terms.residuals == pytest.approx(tuple(float(residual) for residual in exact_residuals))
        assert terms.null_centered == pytest.approx(tuple(float(term) for term in exact_null_centered))

    def test_a_defect_absent_from_the_recall_counts_raises_key_error(self) -> None:
        counts = _recall_counts_by_defect({"d1": (6, 4), "d2": (3, 5)})
        clusters = {"d1": ("a", "a"), "d2": ("b", "b"), "absent": ("c", "c")}

        with pytest.raises(KeyError, match="absent"):
            analysis.recall_fixture_terms(
                counts, [*counts, "absent"], ARM_BASELINE, ARM_X, cluster_by_defect=clusters,
            )

    def test_a_defect_missing_from_cluster_by_defect_raises_key_error(self) -> None:
        counts = _recall_counts_by_defect({"d1": (6, 4), "d2": (3, 5), "d3": (7, 7)})
        clusters = _own_fixture_each(["d1", "d2"])

        with pytest.raises(KeyError, match="d3"):
            analysis.recall_fixture_terms(counts, list(counts), ARM_BASELINE, ARM_X, cluster_by_defect=clusters)

    def test_fixtures_follow_the_order_of_first_appearance_not_sorted_key_order(self) -> None:
        """Fixture "z" appears first with one defect (difference 0.4), then fixture "a" with two
        (-0.2 and 0). The sums are 2/5 and -1/5, the estimate 1/15 and the mean defect count 3/2, so the
        residuals are (2/5 - 1/15) / (3/2) = 2/9 and (-1/5 - 2/15) / (3/2) = -2/9. With delta 0.1 the
        null-centered terms are (2/5 + 1/10) / (3/2) = 1/3 and (-1/5 + 1/5) / (3/2) = 0."""
        counts = _recall_counts_by_defect({"z1": (9, 5), "a1": (3, 5), "a2": (7, 7)})
        clusters = {"z1": ("z", "z"), "a1": ("a", "a"), "a2": ("a", "a")}

        terms = analysis.recall_fixture_terms(
            counts, list(counts), ARM_BASELINE, ARM_X, cluster_by_defect=clusters, delta=0.1,
        )

        assert terms is not None
        assert terms.residuals == pytest.approx((2 / 9, -2 / 9))
        assert terms.null_centered == pytest.approx((1 / 3, 0.0))

    def test_a_fixture_whose_defects_are_not_adjacent_in_defect_ids_is_one_fixture(self) -> None:
        """Production feeds sorted defect IDs, so one fixture's defects routinely sit apart in the list."""
        counts = _recall_counts_by_defect({"a1": (6, 4), "b1": (3, 5), "a2": (7, 7)})
        clusters = {"a1": ("a", "a"), "b1": ("b", "b"), "a2": ("a", "a")}

        interleaved = analysis.recall_fixture_terms(
            counts, ["a1", "b1", "a2"], ARM_BASELINE, ARM_X, cluster_by_defect=clusters,
        )
        grouped = analysis.recall_fixture_terms(
            counts, ["a1", "a2", "b1"], ARM_BASELINE, ARM_X, cluster_by_defect=clusters,
        )

        assert interleaved is not None
        assert len(interleaved.residuals) == 2
        assert interleaved == grouped

    def test_one_defect_per_fixture_gives_each_per_defect_difference_plus_delta(self) -> None:
        counts = _recall_counts_by_defect({"d1": (6, 4), "d2": (3, 5), "d3": (7, 7)})

        terms = analysis.recall_fixture_terms(
            counts, list(counts), ARM_BASELINE, ARM_X, cluster_by_defect=_own_fixture_each(counts), delta=0.05,
        )

        assert terms is not None
        assert terms.null_centered == pytest.approx((0.2 + 0.05, -0.2 + 0.05, 0.0 + 0.05))

    def test_one_fixture_gives_none(self) -> None:
        counts = _recall_counts_by_defect({"d1": (6, 4), "d2": (3, 5)})

        terms = analysis.recall_fixture_terms(
            counts, list(counts), ARM_BASELINE, ARM_X, cluster_by_defect={"d1": "shared", "d2": "shared"},
        )

        assert terms is None


def _precision_counts_by_defect(
    valid_and_total_per_arm: dict[str, tuple[int, int, int, int]],
) -> dict[str, analysis.DefectPrecisionCounts]:
    """The tuple is (arm X valid, arm X total, baseline valid, baseline total)."""
    return {
        defect_id: analysis.DefectPrecisionCounts(
            defect_id=defect_id, valid_by_arm={ARM_X: valid_x, ARM_BASELINE: valid_baseline},
            total_by_arm={ARM_X: total_x, ARM_BASELINE: total_baseline},
        )
        for defect_id, (valid_x, total_x, valid_baseline, total_baseline) in valid_and_total_per_arm.items()
    }


def _exact_precision_terms(
    counts: dict[str, analysis.DefectPrecisionCounts], clusters: dict, *, delta: float,
) -> tuple[Fraction, list[Fraction], list[Fraction]]:
    """(estimate, residuals, null_centered) for pooled ARM_X minus ARM_BASELINE precision in exact
    rationals, with fixtures in order of first appearance in `counts`. An arm with no key for a defect
    counts 0, and each arm's residual is (v - p * t) / mean(t) per fixture."""
    fixture_by_defect = {defect_id: clusters[defect_id] for defect_id in counts}
    fixtures = list(dict.fromkeys(fixture_by_defect.values()))

    def arm_residuals_and_precision(arm: str) -> tuple[list[Fraction], Fraction]:
        valid = {fixture: 0 for fixture in fixtures}
        total = {fixture: 0 for fixture in fixtures}
        for defect_id, defect_counts in counts.items():
            valid[fixture_by_defect[defect_id]] += defect_counts.valid_by_arm.get(arm, 0)
            total[fixture_by_defect[defect_id]] += defect_counts.total_by_arm.get(arm, 0)
        precision = Fraction(sum(valid.values()), sum(total.values()))
        mean_total = Fraction(sum(total.values()), len(fixtures))
        return [(valid[fixture] - precision * total[fixture]) / mean_total for fixture in fixtures], precision

    residuals_x, precision_x = arm_residuals_and_precision(ARM_X)
    residuals_baseline, precision_baseline = arm_residuals_and_precision(ARM_BASELINE)
    estimate = precision_x - precision_baseline
    residuals = [
        residual_x - residual_baseline
        for residual_x, residual_baseline in zip(residuals_x, residuals_baseline, strict=True)
    ]
    return estimate, residuals, [residual + estimate + Fraction(delta) for residual in residuals]


class TestPrecisionFixtureTerms:
    UNEQUAL_FIXTURES = {"d1": (3, 4, 1, 5), "d2": (1, 6, 2, 2), "d3": (4, 4, 2, 3)}

    def test_unequal_precisions_and_totals_match_pinned_fraction_terms(self) -> None:
        """Per-arm pooled precision is 8/14 and 5/10, so the estimate is 1/14. The residuals are pinned
        literals, worked by hand from (v_x - p_x t_x) / mean(t_x) - (v_b - p_b t_b) / mean(t_b)."""
        counts = _precision_counts_by_defect(self.UNEQUAL_FIXTURES)

        terms = analysis.precision_fixture_terms(
            counts, list(counts), ARM_BASELINE, ARM_X, cluster_by_defect=_own_fixture_each(counts), delta=0.1,
        )

        assert terms is not None
        assert terms.estimate == pytest.approx(float(Fraction(1, 14)))
        expected_residuals = (Fraction(591, 980), Fraction(-201, 245), Fraction(213, 980))
        assert terms.residuals == pytest.approx(tuple(float(residual) for residual in expected_residuals))
        assert terms.null_centered == pytest.approx(
            tuple(float(residual + Fraction(1, 14)) + 0.1 for residual in expected_residuals),
        )

    @pytest.mark.parametrize("seed", range(5))
    def test_the_estimate_equals_precision_difference_and_the_terms_match_exact_rationals(self, seed: int) -> None:
        rng = random.Random(seed)
        pairs = {}
        clusters = {}
        for fixture_index in range(rng.randint(2, 8)):
            for defect_index in range(rng.randint(1, 3)):
                defect_id = f"f{fixture_index}d{defect_index}"
                total_x, total_baseline = rng.randint(0, 8), rng.randint(0, 8)
                pairs[defect_id] = (rng.randint(0, total_x), total_x, rng.randint(0, total_baseline), total_baseline)
                clusters[defect_id] = f"f{fixture_index}"
        counts = _precision_counts_by_defect(pairs)

        terms = analysis.precision_fixture_terms(counts, list(counts), ARM_BASELINE, ARM_X, cluster_by_defect=clusters)

        assert terms is not None
        assert terms.estimate == pytest.approx(analysis.precision_difference(counts, list(counts), ARM_X, ARM_BASELINE))
        assert sum(terms.residuals) == pytest.approx(0.0, abs=1e-12)
        exact_estimate, exact_residuals, exact_null_centered = _exact_precision_terms(
            counts, clusters, delta=analysis.DELTA,
        )
        assert terms.estimate == pytest.approx(float(exact_estimate))
        assert terms.residuals == pytest.approx(tuple(float(residual) for residual in exact_residuals))
        assert terms.null_centered == pytest.approx(tuple(float(term) for term in exact_null_centered))

    def test_an_arm_with_no_key_for_a_defect_counts_zero_for_it(self) -> None:
        """compute_precision_counts emits no key for an arm that never had a labeled run on a defect."""
        counts = _precision_counts_by_defect(self.UNEQUAL_FIXTURES)
        counts["d1"] = analysis.DefectPrecisionCounts(
            defect_id="d1", valid_by_arm={ARM_X: 3}, total_by_arm={ARM_X: 4},
        )
        clusters = _own_fixture_each(counts)

        terms = analysis.precision_fixture_terms(counts, list(counts), ARM_BASELINE, ARM_X, cluster_by_defect=clusters)

        exact_estimate, exact_residuals, _ = _exact_precision_terms(counts, clusters, delta=analysis.DELTA)
        assert terms is not None
        assert exact_estimate == Fraction(-8, 35)
        assert terms.estimate == pytest.approx(-8 / 35)
        assert terms.residuals == pytest.approx(tuple(float(residual) for residual in exact_residuals))
        assert terms.residuals[0] == pytest.approx(15 / 98)

    def test_a_fixture_with_no_finding_in_one_arm_beside_a_nonzero_pool_still_counts_as_a_fixture(self) -> None:
        counts = _precision_counts_by_defect({"d1": (3, 4, 0, 0), "d2": (1, 6, 2, 2), "d3": (4, 4, 2, 3)})
        clusters = _own_fixture_each(counts)

        terms = analysis.precision_fixture_terms(counts, list(counts), ARM_BASELINE, ARM_X, cluster_by_defect=clusters)

        exact_estimate, exact_residuals, _ = _exact_precision_terms(counts, clusters, delta=analysis.DELTA)
        assert terms is not None
        assert len(terms.residuals) == 3
        assert terms.estimate == pytest.approx(float(exact_estimate))
        assert terms.residuals == pytest.approx(tuple(float(residual) for residual in exact_residuals))

    def test_a_fixture_with_no_finding_in_either_arm_still_counts_as_a_fixture(self) -> None:
        counts = _precision_counts_by_defect({"d1": (0, 0, 0, 0), "d2": (3, 4, 1, 5), "d3": (4, 4, 2, 3)})
        clusters = _own_fixture_each(counts)

        terms = analysis.precision_fixture_terms(counts, list(counts), ARM_BASELINE, ARM_X, cluster_by_defect=clusters)

        exact_estimate, exact_residuals, _ = _exact_precision_terms(counts, clusters, delta=analysis.DELTA)
        assert terms is not None
        assert len(terms.residuals) == 3
        assert terms.estimate == pytest.approx(float(exact_estimate))
        assert terms.residuals == pytest.approx(tuple(float(residual) for residual in exact_residuals))

    def test_every_finding_in_one_fixture_gives_zero_residuals_and_a_zero_width_interval(self) -> None:
        counts = _precision_counts_by_defect({"d1": (3, 4, 1, 5), "d2": (0, 0, 0, 0), "d3": (0, 0, 0, 0)})
        clusters = {"d1": "A", "d2": "B", "d3": "B"}

        terms = analysis.precision_fixture_terms(counts, list(counts), ARM_BASELINE, ARM_X, cluster_by_defect=clusters)

        assert terms is not None
        assert terms.residuals == pytest.approx((0.0, 0.0))
        assert terms.estimate == pytest.approx(3 / 4 - 1 / 5)
        assert analysis.fixture_t_interval(terms) == pytest.approx((terms.estimate, terms.estimate))

    @pytest.mark.parametrize("silent_arm", [ARM_X, ARM_BASELINE])
    def test_an_arm_with_no_finding_gives_none(self, silent_arm: str) -> None:
        counts = _precision_counts_by_defect(self.UNEQUAL_FIXTURES)
        for defect_counts in counts.values():
            defect_counts.total_by_arm[silent_arm] = 0
            defect_counts.valid_by_arm[silent_arm] = 0

        terms = analysis.precision_fixture_terms(
            counts, list(counts), ARM_BASELINE, ARM_X, cluster_by_defect=_own_fixture_each(counts),
        )

        assert terms is None

    def test_a_fixture_of_only_absent_defects_is_dropped_from_the_fixture_count(self) -> None:
        counts = _precision_counts_by_defect(self.UNEQUAL_FIXTURES)
        defect_ids = [*counts, "absent-1", "absent-2"]
        clusters = {**_own_fixture_each(counts), "absent-1": ("ghost", "ghost"), "absent-2": ("ghost", "ghost")}

        with_ghost_fixture = analysis.precision_fixture_terms(
            counts, defect_ids, ARM_BASELINE, ARM_X, cluster_by_defect=clusters,
        )
        without_it = analysis.precision_fixture_terms(
            counts, list(counts), ARM_BASELINE, ARM_X, cluster_by_defect=clusters,
        )

        assert with_ghost_fixture is not None
        assert len(with_ghost_fixture.residuals) == 3
        assert with_ghost_fixture == without_it

    def test_an_absent_defect_beside_a_present_one_in_the_same_fixture_is_skipped(self) -> None:
        counts = _precision_counts_by_defect(self.UNEQUAL_FIXTURES)
        clusters = _own_fixture_each(counts)
        clusters["absent"] = clusters["d1"]

        with_absent = analysis.precision_fixture_terms(
            counts, [*counts, "absent"], ARM_BASELINE, ARM_X, cluster_by_defect=clusters,
        )
        without_it = analysis.precision_fixture_terms(
            counts, list(counts), ARM_BASELINE, ARM_X, cluster_by_defect=clusters,
        )

        assert with_absent == without_it

    def test_a_fixture_whose_defects_are_not_adjacent_in_defect_ids_is_one_fixture(self) -> None:
        """Production feeds sorted defect IDs, so one fixture's defects routinely sit apart in the list."""
        counts = _precision_counts_by_defect(self.UNEQUAL_FIXTURES)
        clusters = {"d1": ("a", "a"), "d2": ("b", "b"), "d3": ("a", "a")}

        interleaved = analysis.precision_fixture_terms(
            counts, ["d1", "d2", "d3"], ARM_BASELINE, ARM_X, cluster_by_defect=clusters,
        )
        grouped = analysis.precision_fixture_terms(
            counts, ["d1", "d3", "d2"], ARM_BASELINE, ARM_X, cluster_by_defect=clusters,
        )

        assert interleaved is not None
        assert len(interleaved.residuals) == 2
        assert interleaved == grouped

    def test_a_present_defect_missing_from_cluster_by_defect_raises_key_error(self) -> None:
        counts = _precision_counts_by_defect(self.UNEQUAL_FIXTURES)
        clusters = _own_fixture_each(["d1", "d2"])

        with pytest.raises(KeyError, match="d3"):
            analysis.precision_fixture_terms(counts, list(counts), ARM_BASELINE, ARM_X, cluster_by_defect=clusters)

    def test_an_absent_defect_missing_from_cluster_by_defect_raises_key_error(self) -> None:
        """The presence filter runs after the grouping, so a defect absent from the counts still needs its entry."""
        counts = _precision_counts_by_defect(self.UNEQUAL_FIXTURES)
        clusters = _own_fixture_each(counts)

        with pytest.raises(KeyError, match="absent"):
            analysis.precision_fixture_terms(
                counts, [*counts, "absent"], ARM_BASELINE, ARM_X, cluster_by_defect=clusters,
            )

    def test_one_present_fixture_beside_an_absent_one_gives_none(self) -> None:
        counts = _precision_counts_by_defect({"d1": (3, 4, 1, 5)})
        clusters = {"d1": ("a", "a"), "absent": ("b", "b")}

        terms = analysis.precision_fixture_terms(
            counts, ["d1", "absent"], ARM_BASELINE, ARM_X, cluster_by_defect=clusters,
        )

        assert terms is None


class TestFixtureTInterval:
    @pytest.mark.parametrize("alpha", [0.025, 0.0125])
    def test_the_interval_is_the_estimate_plus_or_minus_t_times_the_standard_error(self, alpha: float) -> None:
        """Residuals (1, -1, 2, -2) have a squared sum of 10, so the standard error is sqrt(10 / (4 * 3))."""
        terms = analysis.FixtureTerms(estimate=0.5, residuals=(1.0, -1.0, 2.0, -2.0), null_centered=(0.0,) * 4)
        half_width = analysis.student_t_upper_quantile(3, alpha) * math.sqrt(10 / 12)

        lower, upper = analysis.fixture_t_interval(terms, alpha_one_sided=alpha)

        assert lower == pytest.approx(0.5 - half_width)
        assert upper == pytest.approx(0.5 + half_width)

    @pytest.mark.parametrize("residuals", [(), (0.5,)])
    def test_fewer_than_two_fixtures_raises(self, residuals: tuple[float, ...]) -> None:
        terms = analysis.FixtureTerms(estimate=0.5, residuals=residuals, null_centered=residuals)

        with pytest.raises(ValueError, match=f"fixture_t_interval: needs at least two fixtures, got {len(residuals)}"):
            analysis.fixture_t_interval(terms)

    def test_residuals_and_null_centered_of_different_lengths_raise_on_construction(self) -> None:
        with pytest.raises(ValueError, match="FixtureTerms: residuals and null_centered must have one entry per fixture"):
            analysis.FixtureTerms(estimate=0.5, residuals=(1.0, -1.0, 2.0), null_centered=(0.0, 0.0))

    def test_residuals_shorter_than_null_centered_raise_on_construction(self) -> None:
        with pytest.raises(ValueError, match="FixtureTerms: residuals and null_centered must have one entry per fixture"):
            analysis.FixtureTerms(estimate=0.5, residuals=(1.0, -1.0), null_centered=(0.0, 0.0, 0.0))

    def test_the_default_alpha_is_the_one_sided_design_constant(self) -> None:
        terms = analysis.FixtureTerms(estimate=0.5, residuals=(1.0, -1.0, 2.0, -2.0), null_centered=(0.0,) * 4)

        assert analysis.fixture_t_interval(terms) == analysis.fixture_t_interval(
            terms, alpha_one_sided=analysis.ALPHA_ONE_SIDED,
        )


class TestFixtureTIntervalStandardErrorAgainstJackknife:
    """The linearized standard error of the fixture terms against a delete-one-fixture jackknife of the plain
    estimate, which shares no linearization with production."""

    FIXTURES = 40
    SEED = 7

    def _synthetic_clusters_and_counts(self) -> tuple[
        dict[str, str], dict[str, analysis.DefectRecallCounts], dict[str, analysis.DefectPrecisionCounts],
    ]:
        rng = random.Random(self.SEED)
        cluster_by_defect: dict[str, str] = {}
        recall_counts_by_defect: dict[str, analysis.DefectRecallCounts] = {}
        precision_counts_by_defect: dict[str, analysis.DefectPrecisionCounts] = {}
        for fixture_index in range(self.FIXTURES):
            for defect_index in range(rng.randint(1, 5)):
                defect_id = f"f{fixture_index}d{defect_index}"
                cluster_by_defect[defect_id] = f"fixture{fixture_index}"
                recall_counts_by_defect.update(_recall_counts_by_defect(
                    {defect_id: (rng.randint(0, 10), rng.randint(0, 10))},
                ))
                total_x, total_baseline = rng.randint(1, 8), rng.randint(1, 8)
                precision_counts_by_defect.update(_precision_counts_by_defect(
                    {defect_id: (rng.randint(0, total_x), total_x, rng.randint(0, total_baseline), total_baseline)},
                ))
        return cluster_by_defect, recall_counts_by_defect, precision_counts_by_defect

    @staticmethod
    def _standard_error_of_the_interval(terms: analysis.FixtureTerms) -> float:
        lower, upper = analysis.fixture_t_interval(terms)
        t_quantile = analysis.student_t_upper_quantile(len(terms.residuals) - 1, analysis.ALPHA_ONE_SIDED)
        return (upper - lower) / 2 / t_quantile

    @staticmethod
    def _jackknife_standard_error(
        cluster_by_defect: dict[str, str], estimate_over_defects: Callable[[list[str]], float | None],
    ) -> float:
        defect_ids = list(cluster_by_defect)
        fixtures = list(dict.fromkeys(cluster_by_defect.values()))
        leave_one_out_estimates = [
            estimate_over_defects([
                defect_id for defect_id in defect_ids if cluster_by_defect[defect_id] != left_out_fixture
            ])
            for left_out_fixture in fixtures
        ]
        mean_leave_one_out = statistics.fmean(leave_one_out_estimates)
        squared_deviation_sum = sum((estimate - mean_leave_one_out) ** 2 for estimate in leave_one_out_estimates)
        return math.sqrt((len(fixtures) - 1) / len(fixtures) * squared_deviation_sum)

    def test_the_recall_standard_error_matches_a_delete_one_fixture_jackknife_within_five_percent(self) -> None:
        cluster_by_defect, recall_counts, _ = self._synthetic_clusters_and_counts()
        terms = analysis.recall_fixture_terms(
            recall_counts, list(recall_counts), ARM_BASELINE, ARM_X, cluster_by_defect=cluster_by_defect,
        )
        assert terms is not None

        jackknife_standard_error = self._jackknife_standard_error(
            cluster_by_defect,
            lambda defect_ids: analysis.recall_difference(recall_counts, defect_ids, ARM_X, ARM_BASELINE),
        )

        ratio = self._standard_error_of_the_interval(terms) / jackknife_standard_error
        assert 0.95 <= ratio <= 1.05

    def test_the_precision_standard_error_matches_a_delete_one_fixture_jackknife_within_five_percent(self) -> None:
        cluster_by_defect, _, precision_counts = self._synthetic_clusters_and_counts()
        terms = analysis.precision_fixture_terms(
            precision_counts, list(precision_counts), ARM_BASELINE, ARM_X, cluster_by_defect=cluster_by_defect,
        )
        assert terms is not None

        jackknife_standard_error = self._jackknife_standard_error(
            cluster_by_defect,
            lambda defect_ids: analysis.precision_difference(precision_counts, defect_ids, ARM_X, ARM_BASELINE),
        )

        ratio = self._standard_error_of_the_interval(terms) / jackknife_standard_error
        assert 0.95 <= ratio <= 1.05
