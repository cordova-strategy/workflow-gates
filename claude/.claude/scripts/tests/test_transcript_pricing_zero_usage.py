"""How pricing's requestId-run merge treats an all-zero-usage record."""
from datetime import date

import pytest
from transcript_analysis import cost, pricing

from .conftest import (
    _EXCLUDED_SPEND_MARKER,
    _SYNTHETIC_MODEL,
    _cost_args,
    _extract_grand_total,
    _extract_unpriced_total,
    _priced,
    _tool_result,
    _user_msg,
    _write_jsonl,
)


def _real_usage_record(request_id: str, *, input: int = 1_000_000) -> dict:
    """A record holding a request's real usage, with cache and output counters as a real request carries."""
    return _priced("claude-sonnet-5", input=input, cache_read=30_000, ephemeral_5m=1_000, output=300,
                   request_id=request_id)


def _synthetic_zero_record(request_id: str) -> dict:
    """The shape observed as the trailing record of a refusal-ended request: model `<synthetic>`, every usage counter 0."""
    return _priced(_SYNTHETIC_MODEL, request_id=request_id)


def _synthetic_record_with_usage(request_id: str, usage: dict | None) -> dict:
    rec = _synthetic_zero_record(request_id)
    rec["message"]["usage"] = usage
    return rec


_FLAT_ZERO_USAGE = {
    "input_tokens": 0, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0, "output_tokens": 0,
}


class TestSyntheticZeroUsageRecordInRun:
    def test_trailing_record_leaves_usage_and_model_to_the_earlier_record(self):
        real = _real_usage_record("req-1")
        turns = pricing.dedup_turns_by_request_id([real, _synthetic_zero_record("req-1")])
        assert len(turns) == 1
        assert turns[0]["message"]["usage"] == real["message"]["usage"]
        assert turns[0]["message"]["model"] == "claude-sonnet-5"

    def test_trailing_record_still_prices_the_request_through_cost_report(self, fake_projects, capsys):
        """1,000,000 input tokens at sonnet-5's $2.00/M; a $0 total means the all-zero record's usage was priced."""
        real = _priced("claude-sonnet-5", input=1_000_000, request_id="req-1")
        _write_jsonl(fake_projects / "sess.jsonl", [real, _synthetic_zero_record("req-1")])
        cost._cost_report(_cost_args(), date(2026, 8, 2))
        assert _extract_grand_total(capsys.readouterr().out) == pytest.approx(2.00)

    def test_leading_record_supplies_neither_model_nor_usage(self, fake_projects, capsys):
        real = _priced("claude-sonnet-5", input=1_000_000, request_id="req-1")  # $2.00
        records = [_synthetic_zero_record("req-1"), real]
        _write_jsonl(fake_projects / "sess.jsonl", records)

        turns = pricing.dedup_turns_by_request_id(records)
        cost._cost_report(_cost_args(), date(2026, 8, 2))
        out = capsys.readouterr().out

        assert len(turns) == 1
        assert turns[0]["message"]["model"] == "claude-sonnet-5"
        assert turns[0]["message"]["usage"] == real["message"]["usage"]
        assert _extract_grand_total(out) == pytest.approx(2.00)
        assert _EXCLUDED_SPEND_MARKER not in out

    def test_non_contiguous_leading_record_merges_into_one_priced_turn(self, fake_projects, capsys):
        first_real = _priced("claude-sonnet-5", input=1_000_000, request_id="req-1")  # $2.00
        second_real = _priced("claude-sonnet-5", input=1_000_000, request_id="req-1")
        records = [
            _synthetic_zero_record("req-1"), _user_msg([_tool_result("t1", "one")]),
            first_real, _user_msg([_tool_result("t2", "two")]),
            second_real,
        ]
        _write_jsonl(fake_projects / "sess.jsonl", records)

        turns = pricing.dedup_turns_by_request_id(records)
        cost._cost_report(_cost_args(), date(2026, 8, 2))
        out = capsys.readouterr().out

        assert [turn["type"] for turn in turns] == ["assistant", "user", "user"]
        assert turns[0]["message"]["model"] == "claude-sonnet-5"
        assert turns[0]["message"]["usage"] == second_real["message"]["usage"]
        assert _extract_grand_total(out) == pytest.approx(2.00)
        assert _EXCLUDED_SPEND_MARKER not in out

    def test_skipped_record_still_contributes_its_content_in_record_order(self):
        skipped = _priced(_SYNTHETIC_MODEL, request_id="req-1", content=[{"type": "text", "text": "from-skipped"}])
        real = _priced(
            "claude-sonnet-5", input=100, request_id="req-1", content=[{"type": "text", "text": "from-real"}],
        )

        turns = pricing.dedup_turns_by_request_id([skipped, _user_msg([_tool_result("t1", "one")]), real])

        assert turns[0]["message"]["content"] == [
            {"type": "text", "text": "from-skipped"}, {"type": "text", "text": "from-real"},
        ]

    def test_non_contiguous_trailing_record_merges_and_prices_the_request_once(self, fake_projects, capsys):
        """Without skipping the all-zero record, usage matching fails and the two real
        records would stay separate turns, double-counting the request's input tokens."""
        first_real = _priced("claude-sonnet-5", input=1_000_000, request_id="req-1")  # $2.00
        second_real = _priced("claude-sonnet-5", input=1_000_000, request_id="req-1")
        records = [
            first_real, _user_msg([_tool_result("t1", "one")]),
            second_real, _user_msg([_tool_result("t2", "two")]),
            _synthetic_zero_record("req-1"),
        ]
        _write_jsonl(fake_projects / "sess.jsonl", records)

        turns = pricing.dedup_turns_by_request_id(records)
        cost._cost_report(_cost_args(), date(2026, 8, 2))

        assert [turn["type"] for turn in turns] == ["assistant", "user", "user"]
        assert turns[0]["message"]["usage"] == first_real["message"]["usage"]
        assert _extract_grand_total(capsys.readouterr().out) == pytest.approx(2.00)

    @pytest.mark.parametrize(
        "run_with_a_zero_record",
        [
            pytest.param(
                lambda: [_real_usage_record("req-1"), _synthetic_zero_record("req-1")],
                id="zero-record-trailing",
            ),
            pytest.param(
                lambda: [
                    _synthetic_zero_record("req-1"), _real_usage_record("req-1"), _real_usage_record("req-1"),
                ],
                id="zero-record-leading",
            ),
            pytest.param(
                lambda: [
                    _real_usage_record("req-1"), _synthetic_zero_record("req-1"), _real_usage_record("req-1"),
                ],
                id="zero-record-between-two-agreeing-real-records",
            ),
        ],
    )
    def test_usage_canary_stays_silent_for_a_zero_record(self, run_with_a_zero_record, capsys):
        run = run_with_a_zero_record()

        assert pricing._warn_if_run_usage_drift(run) is False
        assert capsys.readouterr().err == ""

    def test_run_of_only_zero_records_takes_usage_from_the_last_one(self, capsys):
        first_zero = _synthetic_record_with_usage("req-1", {**_FLAT_ZERO_USAGE, "service_tier": "first"})
        last_zero = _synthetic_record_with_usage("req-1", {**_FLAT_ZERO_USAGE, "service_tier": "last"})

        turns = pricing.dedup_turns_by_request_id([first_zero, last_zero])

        assert len(turns) == 1
        assert turns[0]["message"]["usage"]["service_tier"] == "last"
        assert turns[0]["message"]["model"] == _SYNTHETIC_MODEL
        assert capsys.readouterr().err == ""

    def test_run_of_only_zero_records_prices_at_zero_without_excluded_spend(self, fake_projects, capsys):
        _write_jsonl(fake_projects / "sess.jsonl", [_synthetic_zero_record("req-1"), _synthetic_zero_record("req-1")])
        cost._cost_report(_cost_args(), date(2026, 8, 2))
        out = capsys.readouterr().out
        assert _extract_grand_total(out) == 0.0
        assert _EXCLUDED_SPEND_MARKER not in out

    @pytest.mark.parametrize(
        ("branch_filter", "expected_total"),
        [("feature-leading", 2.00), ("feature-real", 0.00)],
        ids=["filter-on-skipped-record-branch", "filter-on-usage-record-branch"],
    )
    def test_skipped_leading_record_still_decides_the_turns_timestamp_and_branch(
        self, branch_filter, expected_total, fake_projects, capsys
    ):
        """The merged turn's timestamp and gitBranch, which --since and --branches read, come from the run's
        first record even when that record supplies no usage."""
        leading = _priced(
            _SYNTHETIC_MODEL, ts="2026-05-19T10:00:00.000Z", branch="feature-leading", request_id="req-1",
        )
        real = _priced(
            "claude-sonnet-5", input=1_000_000, ts="2026-05-20T10:00:00.000Z", branch="feature-real",
            request_id="req-1",
        )
        records = [leading, _user_msg([_tool_result("t1", "one")], branch="feature-leading"), real]
        _write_jsonl(fake_projects / "sess.jsonl", records)

        merged = pricing.dedup_turns_by_request_id(records)[0]
        cost._cost_report(_cost_args(branches=branch_filter), date(2026, 8, 2))

        assert merged["timestamp"] == "2026-05-19T10:00:00.000Z"
        assert merged["gitBranch"] == "feature-leading"
        assert _extract_grand_total(capsys.readouterr().out) == pytest.approx(expected_total)

    def test_merged_model_comes_from_the_record_that_supplies_usage(self):
        first = _priced("claude-sonnet-5", input=100, request_id="req-1")
        last = _priced("claude-sonnet-4-6", input=100, request_id="req-1")
        turns = pricing.dedup_turns_by_request_id([first, last])
        assert turns[0]["message"]["model"] == "claude-sonnet-4-6"

    @pytest.mark.parametrize(
        "cache_creation_fields",
        [
            pytest.param({}, id="nested-block-absent"),
            pytest.param({"cache_creation": None}, id="nested-block-null"),
            pytest.param(
                {"cache_creation": {"ephemeral_1h_input_tokens": 0, "ephemeral_5m_input_tokens": 0}},
                id="nested-keys-zero",
            ),
            pytest.param({"cache_creation": {"ephemeral_5m_input_tokens": 0}}, id="one-nested-key-absent"),
        ],
    )
    def test_zero_record_is_skipped_whatever_zero_form_its_nested_block_takes(self, cache_creation_fields, capsys):
        real = _real_usage_record("req-1")
        zero = _synthetic_record_with_usage("req-1", {**_FLAT_ZERO_USAGE, **cache_creation_fields})

        deduped = pricing._dedup_session([real, zero])

        assert deduped.turns[0]["message"]["usage"] == real["message"]["usage"]
        assert deduped.usage_drift is False
        assert capsys.readouterr().err == ""

    @pytest.mark.parametrize(
        "run_with_genuine_drift",
        [
            pytest.param(
                lambda: [_real_usage_record("req-1"), _real_usage_record("req-1", input=999)],
                id="two-non-zero-records",
            ),
            pytest.param(
                lambda: [
                    _real_usage_record("req-1"), _real_usage_record("req-1", input=999),
                    _synthetic_zero_record("req-1"),
                ],
                id="drift-before-trailing-zero-record",
            ),
            pytest.param(
                lambda: [
                    _real_usage_record("req-1"), _synthetic_zero_record("req-1"),
                    _real_usage_record("req-1", input=999),
                ],
                id="drift-after-zero-record",
            ),
            pytest.param(
                lambda: [
                    _real_usage_record("req-1"),
                    _synthetic_record_with_usage("req-1", {**_FLAT_ZERO_USAGE, "input_tokens": 999}),
                ],
                id="synthetic-record-with-non-zero-usage",
            ),
        ],
    )
    def test_usage_canary_still_fires_for_kept_records_that_disagree(self, run_with_genuine_drift, capsys):
        run = run_with_genuine_drift()

        assert pricing._warn_if_run_usage_drift(run) is True
        assert "WARNING" in capsys.readouterr().err


# Usage shapes on a `<synthetic>` record that are not all-zero.
_KEPT_SYNTHETIC_USAGE = [
    pytest.param(
        {**_FLAT_ZERO_USAGE, "cache_creation": {"ephemeral_5m_input_tokens": 1_000}},
        id="non-zero-nested-cache-write",
    ),
    pytest.param(
        {**_FLAT_ZERO_USAGE, "cache_creation": {"ephemeral_1h_input_tokens": 1_000}},
        id="non-zero-nested-1h-cache-write",
    ),
    pytest.param({**_FLAT_ZERO_USAGE, "cache_read_input_tokens": 5}, id="cache-read-only"),
    pytest.param({**_FLAT_ZERO_USAGE, "cache_creation_input_tokens": 5}, id="flat-cache-write-only"),
    pytest.param({**_FLAT_ZERO_USAGE, "output_tokens": 5}, id="output-only"),
    pytest.param(
        {"input_tokens": 0, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0},
        id="missing-flat-key",
    ),
    pytest.param({}, id="empty-usage"),
    pytest.param(None, id="non-dict-usage"),
]


class TestZeroLookingRecordsTheFilterKeeps:
    """Records that resemble the skipped shape and must still reach the drift canary and the merge gate."""

    def test_real_model_zero_record_after_partial_output_trips_the_canary(self):
        run = [_real_usage_record("req-1"), _priced("claude-sonnet-5", request_id="req-1")]

        assert pricing._warn_if_run_usage_drift(run) is True
        assert pricing._dedup_session(run).usage_drift is True

    def test_non_contiguous_real_model_zero_record_stays_a_separate_turn(self):
        records = [
            _real_usage_record("req-1"), _user_msg([_tool_result("t1", "one")]),
            _priced("claude-sonnet-5", request_id="req-1"),
        ]
        assert pricing.dedup_turns_by_request_id(records) == records

    def test_non_contiguous_disagreeing_real_records_stay_separate_beside_a_skipped_record(self):
        """Skipping the zero record must not stop the merge gate comparing the real records."""
        records = [
            _real_usage_record("req-1"), _user_msg([_tool_result("t1", "one")]),
            _real_usage_record("req-1", input=999), _user_msg([_tool_result("t2", "two")]),
            _synthetic_zero_record("req-1"),
        ]
        assert pricing.dedup_turns_by_request_id(records) == records

    @pytest.mark.parametrize("kept_usage", _KEPT_SYNTHETIC_USAGE)
    def test_synthetic_record_trips_the_canary(self, kept_usage):
        run = [_real_usage_record("req-1"), _synthetic_record_with_usage("req-1", kept_usage)]
        assert pricing._warn_if_run_usage_drift(run) is True

    @pytest.mark.parametrize("kept_usage", _KEPT_SYNTHETIC_USAGE)
    def test_non_contiguous_synthetic_record_stays_a_separate_turn(self, kept_usage):
        records = [
            _real_usage_record("req-1"), _user_msg([_tool_result("t1", "one")]),
            _synthetic_record_with_usage("req-1", kept_usage),
        ]
        assert pricing.dedup_turns_by_request_id(records) == records

    def test_nested_only_cache_write_tokens_reach_pricing_as_unpriced_spend(self, fake_projects, capsys):
        """`<synthetic>` has no rate, so the kept record's tokens surface as excluded spend."""
        nested_only = _synthetic_record_with_usage(
            "req-1", {**_FLAT_ZERO_USAGE, "cache_creation": {"ephemeral_5m_input_tokens": 1_000}},
        )
        _write_jsonl(fake_projects / "sess.jsonl", [
            _real_usage_record("req-1"), _user_msg([_tool_result("t1", "one")]), nested_only,
        ])

        cost._cost_report(_cost_args(), date(2026, 8, 2))
        out = capsys.readouterr().out

        assert _EXCLUDED_SPEND_MARKER in out
        assert _extract_unpriced_total(out) == 1_000

    @pytest.mark.parametrize("cache_creation", ["not-an-object", [], 0])
    def test_non_dict_nested_block_is_not_all_zero_and_does_not_raise(self, cache_creation):
        assert pricing._usage_is_all_zero({**_FLAT_ZERO_USAGE, "cache_creation": cache_creation}) is False
