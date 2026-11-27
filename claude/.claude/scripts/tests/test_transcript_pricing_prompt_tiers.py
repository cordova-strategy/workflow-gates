"""Tests for transcript_analysis/pricing.py's prompt-length tiers: _LONG_PROMPT_TIERS, the long-prompt
pricing-variant labels, and the rate and pricing functions that read them."""
import itertools
from datetime import date

import pytest
from transcript_analysis import cost, pricing

from .conftest import _EXCLUDED_SPEND_MARKER, _cost_args, _extract_grand_total, _priced, _write_jsonl

_HAIKU_5_5 = "claude-haiku-5-5"
_THRESHOLD = 100_000

# Haiku 5.5's five rates per MTok, from the vendor pricing page's two prompt-length rows.
_LOWER_TIER_RATES = {"input": 0.10, "cache_write_5m": 0.125, "cache_write_1h": 0.20, "cache_read": 0.01, "output": 0.50}
_HIGHER_TIER_RATES = {"input": 0.50, "cache_write_5m": 0.625, "cache_write_1h": 1.00, "cache_read": 0.05, "output": 2.50}

# The usage speed and inference_geo fields each lower-tier and long-prompt label implies.
_LOWER_TIER_LABEL_FIELDS = [
    ("standard", {}),
    ("fast", {"speed": "fast"}),
    ("us_geo", {"inference_geo": "us"}),
    ("fast_us_geo", {"speed": "fast", "inference_geo": "us"}),
]
_LONG_PROMPT_LABEL_FIELDS = [
    ("long_prompt", {}),
    ("fast_long_prompt", {"speed": "fast"}),
    ("us_geo_long_prompt", {"inference_geo": "us"}),
    ("fast_us_geo_long_prompt", {"speed": "fast", "inference_geo": "us"}),
]
_DOLLARS_FOR_ONE_MILLION_INPUT_TOKENS = {
    "standard": 0.10, "fast": 0.20, "us_geo": 0.11, "fast_us_geo": 0.22,
    "long_prompt": 0.50, "fast_long_prompt": 1.00, "us_geo_long_prompt": 0.55, "fast_us_geo_long_prompt": 1.10,
}
# Input dollars for a usage selecting each label: 100,000 tokens at a lower-tier label, 1,000,000 at a long-prompt one.
_DOLLARS_FOR_A_USAGE_SELECTING_THE_LABEL = {
    "standard": 0.01, "fast": 0.02, "us_geo": 0.011, "fast_us_geo": 0.022,
    "long_prompt": 0.50, "fast_long_prompt": 1.00, "us_geo_long_prompt": 0.55, "fast_us_geo_long_prompt": 1.10,
}


def _haiku_usage(**priced_fields) -> dict:
    return _priced(_HAIKU_5_5, **priced_fields)["message"]["usage"]


class TestLongPromptTierRates:
    def test_each_tier_matches_the_vendor_rows(self):
        assert pricing._rates_for_variant(_HAIKU_5_5, "standard") == pytest.approx(_LOWER_TIER_RATES)
        assert pricing._rates_for_variant(_HAIKU_5_5, "long_prompt") == pytest.approx(_HIGHER_TIER_RATES)

    def test_us_geo_applies_to_the_higher_tier(self):
        long_prompt_rates = pricing._rates_for_variant(_HAIKU_5_5, "long_prompt")
        us_geo_rates = pricing._rates_for_variant(_HAIKU_5_5, "us_geo_long_prompt")
        assert us_geo_rates == pytest.approx({cls: rate * 1.1 for cls, rate in long_prompt_rates.items()})

    @pytest.mark.parametrize(
        "label,rate_multiplier",
        [("fast_long_prompt", 2), ("fast_us_geo_long_prompt", 2 * 1.1)],
    )
    def test_fast_applies_to_all_five_token_classes_of_the_higher_tier(self, label, rate_multiplier):
        long_prompt_rates = pricing._rates_for_variant(_HAIKU_5_5, "long_prompt")
        label_rates = pricing._rates_for_variant(_HAIKU_5_5, label)
        assert set(label_rates) == set(pricing._TOKEN_CLASSES)
        assert label_rates == pytest.approx({cls: rate * rate_multiplier for cls, rate in long_prompt_rates.items()})

    @pytest.mark.parametrize("label", pricing._PRICING_VARIANTS)
    def test_every_label_prices_a_fixed_input_at_its_literal_dollars(self, label):
        dollars = pricing._price_token_counts(_HAIKU_5_5, label, {"input": 1_000_000})
        assert dollars["input"] == pytest.approx(_DOLLARS_FOR_ONE_MILLION_INPUT_TOKENS[label])

    @pytest.mark.parametrize("label,speed_and_geo_fields", _LOWER_TIER_LABEL_FIELDS + _LONG_PROMPT_LABEL_FIELDS)
    def test_price_turn_on_a_usage_selecting_each_label_matches_its_literal_dollars(
        self, label, speed_and_geo_fields,
    ):
        input_tokens = _THRESHOLD + 900_000 if label.endswith("long_prompt") else _THRESHOLD
        usage = {**_haiku_usage(input=input_tokens), **speed_and_geo_fields}
        assert pricing._pricing_variant(_HAIKU_5_5, usage) == label
        dollars, _context, _unpriced = pricing._price_turn(_HAIKU_5_5, usage)
        assert dollars["input"] == pytest.approx(_DOLLARS_FOR_A_USAGE_SELECTING_THE_LABEL[label])

    def test_model_rates_has_no_single_rate_for_a_tiered_model(self):
        assert _HAIKU_5_5 in pricing._MODEL_BASE_INPUT_RATES
        assert pricing._model_rates(_HAIKU_5_5) is None

    @pytest.mark.parametrize(
        "model,variant",
        [
            pytest.param("claude-sonnet-5", "long_prompt", id="long-prompt-label-on-a-model-without-a-tier"),
            pytest.param("claude-unpriced-model-sentinel", "standard", id="unpriced-model"),
            pytest.param(_HAIKU_5_5, "unknown-label", id="unknown-label"),
        ],
    )
    def test_rates_for_variant_returns_none_off_the_table(self, model, variant):
        assert pricing._rates_for_variant(model, variant) is None

    def test_every_tiered_model_is_in_the_rate_table(self):
        assert set(pricing._LONG_PROMPT_TIERS) <= set(pricing._MODEL_BASE_INPUT_RATES)


class TestLongPromptTierSelection:
    @pytest.mark.parametrize(
        "build_usage",
        [
            pytest.param(lambda extra: _haiku_usage(input=_THRESHOLD + extra), id="input-only"),
            pytest.param(
                lambda extra: _haiku_usage(
                    input=25_000 + extra, cache_read=25_000, ephemeral_1h=25_000, ephemeral_5m=25_000,
                ),
                id="spread-across-input-cache-read-and-both-nested-writes",
            ),
            pytest.param(
                lambda extra: _haiku_usage(input=50_000 + extra, flat_cache_creation=50_000),
                id="write-through-flat-cache-creation",
            ),
        ],
    )
    def test_threshold_is_strictly_greater_than_100k(self, build_usage):
        at_threshold, over_threshold = build_usage(0), build_usage(1)
        assert pricing._context_at_turn(at_threshold) == _THRESHOLD
        assert pricing._context_at_turn(over_threshold) == _THRESHOLD + 1
        assert pricing._pricing_variant(_HAIKU_5_5, at_threshold) == "standard"
        assert pricing._pricing_variant(_HAIKU_5_5, over_threshold) == "long_prompt"

    def test_output_tokens_do_not_count_toward_the_threshold(self):
        usage = _haiku_usage(input=_THRESHOLD, output=500_000)
        assert pricing._pricing_variant(_HAIKU_5_5, usage) == "standard"

    def test_a_model_without_a_tier_keeps_its_label_over_the_threshold(self):
        usage = _priced("claude-sonnet-5", input=500_000)["message"]["usage"]
        assert pricing._pricing_variant("claude-sonnet-5", usage) == "standard"

    @pytest.mark.parametrize("label,speed_and_geo_fields", _LONG_PROMPT_LABEL_FIELDS)
    def test_each_fast_and_geo_combination_on_a_long_prompt_gets_its_own_label(self, label, speed_and_geo_fields):
        usage = {**_haiku_usage(input=_THRESHOLD + 1), **speed_and_geo_fields}
        assert pricing._pricing_variant(_HAIKU_5_5, usage) == label

    def test_a_synthetic_tier_selects_and_prices_by_its_own_threshold_and_rates(self, monkeypatch):
        """The mechanism reads the tier row, not Haiku's constants: threshold 50,000, base $1.00, long $4.00 per MTok."""
        synthetic_model = "claude-synthetic-tiered-sentinel"
        monkeypatch.setitem(pricing._MODEL_BASE_INPUT_RATES, synthetic_model, 1.00)
        monkeypatch.setitem(pricing._LONG_PROMPT_TIERS, synthetic_model, pricing._LongPromptTier(50_000, 4.00))
        at_threshold = _priced(synthetic_model, input=50_000)["message"]["usage"]
        over_threshold = _priced(synthetic_model, input=50_001)["message"]["usage"]

        assert pricing._pricing_variant(synthetic_model, at_threshold) == "standard"
        assert pricing._pricing_variant(synthetic_model, over_threshold) == "long_prompt"
        assert pricing._rates_for_variant(synthetic_model, "standard") == pytest.approx(
            {"input": 1.00, "cache_write_5m": 1.25, "cache_write_1h": 2.00, "cache_read": 0.10, "output": 5.00}
        )
        assert pricing._rates_for_variant(synthetic_model, "long_prompt") == pytest.approx(
            {"input": 4.00, "cache_write_5m": 5.00, "cache_write_1h": 8.00, "cache_read": 0.40, "output": 20.00}
        )
        at_threshold_dollars, _context, _unpriced = pricing._price_turn(synthetic_model, at_threshold)
        over_threshold_dollars, _context, _unpriced = pricing._price_turn(synthetic_model, over_threshold)
        # 50,000 tokens at $1.00/MTok = $0.05; 50,001 tokens at $4.00/MTok = $0.200004.
        assert at_threshold_dollars["input"] == pytest.approx(0.05)
        assert over_threshold_dollars["input"] == pytest.approx(0.200004)

    def test_variant_terms_hold_each_condition_combination_once(self):
        condition_count = len(pricing._VariantTerms._fields)
        every_combination = {
            pricing._VariantTerms(*flags) for flags in itertools.product([False, True], repeat=condition_count)
        }
        terms_by_label = list(pricing._PRICING_VARIANT_TERMS.values())
        assert len(terms_by_label) == len(every_combination)
        assert set(terms_by_label) == every_combination

    def test_a_multi_iteration_usage_selects_its_tier_from_the_top_level_fields(self):
        """The tier follows the top-level `input_tokens`, not any single iteration's tokens."""
        usage = {
            "input_tokens": 120_000,
            "output_tokens": 20,
            "iterations": [
                {"type": "message", "input_tokens": 60_000, "output_tokens": 10},
                {"type": "message", "input_tokens": 60_000, "output_tokens": 10},
            ],
        }
        assert pricing._pricing_variant(_HAIKU_5_5, usage) == "long_prompt"

    def test_a_compaction_iteration_the_top_level_excludes_does_not_count_toward_the_tier(self):
        """Summing every iteration would give 140,000 tokens and `long_prompt`; top-level `input_tokens` excludes compaction."""
        usage = {
            "input_tokens": 90_000,
            "output_tokens": 20,
            "iterations": [
                {"type": "message", "input_tokens": 45_000, "output_tokens": 10},
                {"type": "message", "input_tokens": 45_000, "output_tokens": 10},
                {"type": "compaction", "input_tokens": 50_000, "output_tokens": 5},
            ],
        }
        assert pricing._pricing_variant(_HAIKU_5_5, usage) == "standard"


class TestTurnRates:
    @pytest.mark.parametrize("label,speed_and_geo_fields", _LOWER_TIER_LABEL_FIELDS + _LONG_PROMPT_LABEL_FIELDS)
    def test_a_usage_selecting_each_label_gets_that_labels_rates(self, label, speed_and_geo_fields):
        input_tokens = _THRESHOLD + 1 if label.endswith("long_prompt") else _THRESHOLD
        usage = {**_haiku_usage(input=input_tokens), **speed_and_geo_fields}
        assert pricing._pricing_variant(_HAIKU_5_5, usage) == label
        assert pricing._turn_rates(_HAIKU_5_5, usage) == pricing._rates_for_variant(_HAIKU_5_5, label)

    def test_a_us_geo_turn_on_a_model_without_a_tier_gets_its_standard_rates_times_the_geo_multiplier(self):
        usage = {**_priced("claude-sonnet-5", input=1_000)["message"]["usage"], "inference_geo": "us"}
        standard_sonnet_rates = pricing._model_rates("claude-sonnet-5")
        assert standard_sonnet_rates is not None
        assert pricing._turn_rates("claude-sonnet-5", usage) == pytest.approx(
            {
                token_class: rate * pricing._INFERENCE_GEO_US_RATE_MULTIPLIER
                for token_class, rate in standard_sonnet_rates.items()
            }
        )


class TestHaiku55PricedTurns:
    def test_turn_at_100k_prompt_tokens_prices_whole_at_the_lower_tier(self):
        dollars, _context, unpriced_tokens = pricing._price_turn(_HAIKU_5_5, _haiku_usage(input=_THRESHOLD))
        assert dollars is not None
        assert unpriced_tokens == 0
        assert dollars["input"] == pytest.approx(0.01)

    def test_turn_at_100001_prompt_tokens_prices_whole_at_the_higher_tier(self):
        """Every token takes the higher rate, not only the tokens past the threshold."""
        dollars, _context, unpriced_tokens = pricing._price_turn(_HAIKU_5_5, _haiku_usage(input=_THRESHOLD + 1))
        assert dollars is not None
        assert unpriced_tokens == 0
        assert dollars["input"] == pytest.approx(0.0500005)

    def test_cost_report_prices_both_tiers_and_excludes_nothing(self, fake_projects, capsys):
        _write_jsonl(fake_projects / "sess.jsonl", [
            _priced(_HAIKU_5_5, input=_THRESHOLD, ts="2026-05-19T10:00:00.000Z"),
            _priced(_HAIKU_5_5, input=1_000_000, ts="2026-05-19T10:01:00.000Z"),
        ])
        cost._cost_report(_cost_args(), date(2026, 8, 2))
        out = capsys.readouterr().out
        assert _EXCLUDED_SPEND_MARKER not in out
        # $0.10/MTok on 100,000 tokens = $0.01; $0.50/MTok on 1,000,000 tokens = $0.50.
        assert _extract_grand_total(out) == pytest.approx(0.51)
