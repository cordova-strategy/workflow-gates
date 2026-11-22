"""Tests for reviewer-reads accumulation: outcome classes, size buckets, the headline population, follow-up and coverage,
the Read share, per-type rows, main-thread round Reads, window edges, comparability and diagnostics."""
from collections import Counter

import pytest
from transcript_analysis import pricing, read_cost, reviewer_reads

from ._read_cost_helpers import _HUNDRED_TOKEN_TEXT, _TRACKED_AGENT_TYPE
from ._reviewer_reads_helpers import (
    _BEFORE_WINDOW,
    _IN_WINDOW,
    _SINCE_TS,
    _UNTIL_EPOCH,
    _WITHHELD,
    _access_recording_read_facts,
    _failed_read_exchange,
    _next_prompt,
    _reviewer_turn,
    _round_records,
    _structured_read_exchange,
)
from .conftest import (
    _WINDOW_EDGE_TIMESTAMPS,
    _read_result,
    _read_truncation_notice,
    _read_use,
    _user_msg,
)

_CODE_PATH = "/repo/src/module.py"
_PROSE_PATH = "/repo/docs/guide.md"
_DIFF_PATH = "/home/user/.claude/code-review-diff-markers/review.diff"
_REFUSAL = "File content (51.2KB) exceeds maximum allowed size (50KB)"
_PAGED_REFUSAL = "File content (30000 tokens) exceeds maximum allowed tokens (25000)"


def _text_of_tokens(tokens: int) -> str:
    return "x" * (tokens * 4)


def _with_tool_use_result(tool_use_result) -> list[dict]:
    """A Read of the code path whose result record carries the given `toolUseResult`."""
    return [_reviewer_turn("m1", [_read_use("r1", _CODE_PATH)]), _read_result("r1", "x", tool_use_result=tool_use_result)]


def _one_call(path: str, num_lines: int, total_lines: int, **options) -> list[dict]:
    return _structured_read_exchange("m1", "r1", path, num_lines=num_lines, total_lines=total_lines, **options)


def _flat(*exchanges: list[dict]) -> list[dict]:
    return [record for exchange in exchanges for record in exchange]


def _accumulate(*windows: list[dict], main_records: list[dict] | None = None, agent_type: str = _TRACKED_AGENT_TYPE):
    """Accumulates one session whose subagent windows are `windows`, each typed `agent_type`."""
    totals = reviewer_reads._Totals()
    reviewer_reads._accumulate_session(
        totals, read_cost._SeenIds(), main_records or [], [(agent_type, list(window)) for window in windows],
        pricing._cache_read_equivalent_weights(), _SINCE_TS, _UNTIL_EPOCH, frozenset({_TRACKED_AGENT_TYPE}),
    )
    return totals


def _nonzero(counter: Counter) -> dict:
    return {key: count for key, count in counter.items() if count}


def _only_call(totals: reviewer_reads._Totals) -> tuple:
    """The (role, outcome, bucket) of the one whole-file call a test accumulated."""
    assert sum(totals.outcome_calls.values()) == 1
    return next(key for key, count in totals.outcome_calls.items() if count)


_ASSISTANT_WITH_INVALID_USAGE = {"type": "assistant", "message": {"usage": {"output_tokens": -1}}}


def _assistant(**changes) -> dict:
    return {"type": "assistant", "timestamp": _IN_WINDOW, "message": {"id": "m1", "content": []}, **changes}


class TestOutcomeClasses:
    @pytest.mark.parametrize(
        ("start_line", "num_lines", "total_lines", "truncated", "allow_large", "expected_outcome", "expected_reason"),
        [
            pytest.param(1, 10, 10, False, False, "complete", None, id="complete"),
            pytest.param(1, 10, 10, False, True, "complete_allow_large", None, id="complete_allow_large"),
            pytest.param(1, 5, 10, False, False, "partial_unflagged", None, id="partial_unflagged"),
            pytest.param(1, 5, 10, False, True, "partial_unflagged", None, id="allow_large_below_total_is_partial"),
            pytest.param(1, 5, 10, True, False, "partial_token_cap", None, id="cap_flag_alone"),
            pytest.param(1, 10, 10, True, False, "partial_token_cap", None, id="cap_flag_beats_equal_counts"),
            pytest.param(1, 10, 10, True, True, "partial_token_cap", None, id="cap_flag_beats_allow_large"),
            pytest.param(3, 5, 10, True, False, "partial_token_cap", None, id="cap_flag_beats_start_after_first_line"),
            pytest.param(1, 11, 10, True, False, "partial_token_cap", None, id="cap_flag_beats_lines_exceed_total"),
            pytest.param(3, 5, 10, False, False, "size_unknown", "start_after_first_line", id="start_after_first_line"),
            pytest.param(2, 5, 10, False, False, "size_unknown", "start_after_first_line", id="start_at_line_two"),
            pytest.param(3, 11, 10, False, False, "size_unknown", "start_after_first_line", id="start_beats_lines_exceed_total"),
            pytest.param(3, 10, 10, False, True, "size_unknown", "start_after_first_line", id="start_beats_allow_large"),
            pytest.param(1, 11, 10, False, False, "size_unknown", "lines_exceed_total", id="lines_exceed_total"),
            pytest.param(1, 11, 10, False, True, "size_unknown", "lines_exceed_total", id="lines_exceed_beats_allow_large"),
            pytest.param(0, 0, 0, False, False, "complete", None, id="empty_file_at_start_line_zero"),
            pytest.param(1, 0, 0, False, False, "complete", None, id="empty_file_at_start_line_one"),
        ],
    )
    def test_whole_file_success_takes_the_first_class_that_fits(
        self, start_line, num_lines, total_lines, truncated, allow_large, expected_outcome, expected_reason,
    ):
        window = _structured_read_exchange(
            "m1", "r1", _CODE_PATH, num_lines=num_lines, total_lines=total_lines, start_line=start_line,
            truncated=truncated or None, allow_large=allow_large or None,
        )

        totals = _accumulate(window)

        assert _only_call(totals)[1] == expected_outcome
        assert _nonzero(totals.size_unknown_reasons) == ({expected_reason: 1} if expected_reason else {})

    def test_cap_flag_on_a_record_failing_a_check_is_size_unknown_under_that_check(self):
        window = _flat(_structured_read_exchange("m1", "r1", _CODE_PATH, num_lines=-1, total_lines=10, truncated=True))

        totals = _accumulate(window)

        assert _only_call(totals)[1] == "size_unknown"
        assert _nonzero(totals.size_unknown_reasons) == {"line_field_invalid": 1}

    @pytest.mark.parametrize(
        ("error_text", "expected_outcome", "expected_unrecognised"),
        [
            pytest.param(_REFUSAL, "refused_over_limit", 0, id="byte_size_refusal"),
            pytest.param(_PAGED_REFUSAL, "refused_over_limit", 0, id="token_refusal"),
            pytest.param(
                "File content (1 tokens) exceeds maximum allowed size, and is too large",
                "refused_over_limit", 0, id="recognised_text_holding_the_unrecognised_triggers",
            ),
            pytest.param("File content (1 tokens) is over a limit", "other_error", 1, id="unrecognised_file_content_text"),
            pytest.param("EXCEEDS MAXIMUM ALLOWED", "other_error", 1, id="recased_refusal_is_unrecognised"),
            pytest.param("File does not exist.", "other_error", 0, id="missing_file_error"),
        ],
    )
    def test_failed_whole_file_call_is_refused_or_another_error(self, error_text, expected_outcome, expected_unrecognised):
        totals = _accumulate(_failed_read_exchange("m1", "r1", _CODE_PATH, error_text))

        assert _only_call(totals) == ("code/other", expected_outcome, "unknown")
        assert totals.unrecognised_limit_errors == expected_unrecognised

    @pytest.mark.parametrize(
        ("total_lines", "expected_bucket"),
        [
            (0, "up_to_1000"), (1, "up_to_1000"), (1000, "up_to_1000"), (1001, "1001_to_2000"),
            (2000, "1001_to_2000"), (2001, "over_2000"),
        ],
    )
    def test_complete_call_is_bucketed_by_its_total_lines(self, total_lines, expected_bucket):
        window = _structured_read_exchange("m1", "r1", _CODE_PATH, num_lines=total_lines, total_lines=total_lines)

        assert _only_call(_accumulate(window)) == ("code/other", "complete", expected_bucket)

    def test_a_refused_call_with_no_sized_read_of_its_path_is_bucketed_unknown(self):
        assert _only_call(_accumulate(_failed_read_exchange("m1", "r1", _CODE_PATH, _REFUSAL)))[2] == "unknown"

    def test_the_size_unknown_reasons_are_exactly_the_eight_a_run_can_report(self):
        # Literal, not read from the module: an after-run compares these names.
        assert set(reviewer_reads._SIZE_UNKNOWN_REASONS) == {
            "multi_result_record", "tool_use_result_not_a_dict", "file_not_a_dict", "file_path_mismatch",
            "line_field_invalid", "truncation_flag_invalid", "start_after_first_line", "lines_exceed_total",
        }


class TestSizeUnknownReasons:
    @pytest.mark.parametrize(
        ("window", "expected_reason"),
        [
            pytest.param(_with_tool_use_result(None), "tool_use_result_not_a_dict", id="no_structured_result"),
            pytest.param(_with_tool_use_result({"file": "nope"}), "file_not_a_dict", id="file_not_a_dict"),
            pytest.param(
                _with_tool_use_result({"file": {"filePath": "/other.py", "startLine": 1, "numLines": 1, "totalLines": 1}}),
                "file_path_mismatch", id="file_path_mismatch",
            ),
            pytest.param(
                _with_tool_use_result({"file": {"filePath": _CODE_PATH, "startLine": "1", "numLines": 1, "totalLines": 1}}),
                "line_field_invalid", id="line_field_invalid",
            ),
            pytest.param(
                _with_tool_use_result({"file": {
                    "filePath": _CODE_PATH, "startLine": 1, "numLines": 1, "totalLines": 1, "truncatedByTokenCap": "yes",
                }}),
                "truncation_flag_invalid", id="truncation_flag_invalid",
            ),
        ],
    )
    def test_a_success_whose_structured_fields_fail_a_check_is_size_unknown_under_that_check(self, window, expected_reason):
        totals = _accumulate(window)

        assert _only_call(totals) == ("code/other", "size_unknown", "unknown")
        assert _nonzero(totals.size_unknown_reasons) == {expected_reason: 1}

    def test_a_record_batching_two_results_is_size_unknown_for_both_calls(self):
        batched_result = _user_msg([
            {"type": "tool_result", "tool_use_id": "r1", "content": "x"},
            {"type": "tool_result", "tool_use_id": "r2", "content": "x"},
        ])
        window = [_reviewer_turn("m1", [_read_use("r1", _CODE_PATH), _read_use("r2", _PROSE_PATH)]), batched_result]

        totals = _accumulate(window)

        assert _nonzero(totals.size_unknown_reasons) == {"multi_result_record": 2}


class TestFileRoles:
    @pytest.mark.parametrize(
        ("path", "expected_role"),
        [
            pytest.param("/home/user/.claude/code-review-diff-markers/review.diff", "diff_handoff", id="code_review_diff"),
            pytest.param("/c/cumulative-review-diff-markers/review.diff", "diff_handoff", id="cumulative_review_diff"),
            pytest.param("/c/code-review-diff-markers/CLAUDE.md", "diff_handoff", id="diff_handoff_wins_over_prose"),
            pytest.param("/c/code-review-diff-markers/sub/review.py", "code/other", id="nested_below_the_directory"),
            pytest.param("/c/my-code-review-diff-markers/review.py", "code/other", id="prefixed_lookalike_directory"),
            pytest.param("/c/code-review-diff-markers-old/review.py", "code/other", id="suffixed_lookalike_directory"),
            pytest.param("/c/code-review-diff-markers.py", "code/other", id="lookalike_file_name"),
            pytest.param("/repo/docs/guide.md", "prose", id="markdown_is_prose"),
            pytest.param("/repo/notes.txt", "prose", id="text_is_prose"),
            pytest.param("/repo/claude-skills/skills/x/helper.py", "prose", id="instruction_is_decided_by_path"),
            pytest.param("/repo/src/module.py", "code/other", id="code"),
        ],
    )
    def test_role_follows_the_exact_parent_directory_then_the_prose_split(self, path, expected_role):
        window = _structured_read_exchange("m1", "r1", path, num_lines=3, total_lines=3)

        assert _only_call(_accumulate(window))[0] == expected_role


class TestLargestTotalFallback:
    def test_a_refused_call_takes_the_largest_total_a_later_paged_read_of_its_path_saw(self):
        window = _flat(
            _failed_read_exchange("m1", "r1", _CODE_PATH, _REFUSAL),
            _structured_read_exchange("m2", "r2", _CODE_PATH, num_lines=10, total_lines=1500, offset=0, limit=10),
            _structured_read_exchange("m3", "r3", _CODE_PATH, num_lines=10, total_lines=3000, offset=0, limit=10),
            _structured_read_exchange("m4", "r4", _PROSE_PATH, num_lines=10, total_lines=10, offset=0, limit=10),
        )

        assert _nonzero(_accumulate(window).outcome_calls) == {("code/other", "refused_over_limit", "over_2000"): 1}

    def test_a_size_unknown_success_takes_the_largest_total_of_its_path_too(self):
        window = _flat(
            _with_tool_use_result(None),
            _structured_read_exchange("m2", "r2", _CODE_PATH, num_lines=10, total_lines=1200, offset=0, limit=10),
        )

        assert _nonzero(_accumulate(window).outcome_calls) == {("code/other", "size_unknown", "1001_to_2000"): 1}

    def test_another_windows_total_is_not_used(self):
        first_window = _failed_read_exchange("m1", "r1", _CODE_PATH, _REFUSAL)
        second_window = _structured_read_exchange("m2", "r2", _CODE_PATH, num_lines=10, total_lines=3000, offset=0, limit=10)

        assert _nonzero(_accumulate(first_window, second_window).outcome_calls) == {
            ("code/other", "refused_over_limit", "unknown"): 1,
        }


class TestHeadlinePopulation:
    @pytest.mark.parametrize(
        ("window", "role", "expected_headline"),
        [
            pytest.param(
                _one_call(_CODE_PATH, 5, 9000, truncated=True), "code/other",
                {("code/other", "denominator"): 1, ("code/other", "partial"): 1}, id="token_cap_partial",
            ),
            pytest.param(
                _one_call(_CODE_PATH, 5, 9), "code/other",
                {("code/other", "denominator"): 1, ("code/other", "partial"): 1}, id="unflagged_partial",
            ),
            pytest.param(
                _failed_read_exchange("m1", "r1", _CODE_PATH, _REFUSAL), "code/other",
                {("code/other", "denominator"): 1, ("code/other", "refused"): 1}, id="refused",
            ),
            pytest.param(
                _one_call(_PROSE_PATH, 5, 9), "prose", {("prose", "denominator"): 1, ("prose", "partial"): 1},
                id="prose_partial",
            ),
            pytest.param(
                _one_call(_CODE_PATH, 2001, 2001), "code/other", {("code/other", "denominator"): 1},
                id="complete_over_the_default_limit",
            ),
            pytest.param(_one_call(_CODE_PATH, 2000, 2000), "code/other", {}, id="complete_at_the_default_limit_stays_out"),
            pytest.param(
                _one_call(_CODE_PATH, 50, 50, text=_text_of_tokens(25_000)), "code/other", {},
                id="plain_complete_at_25000_estimated_tokens_stays_out",
            ),
            pytest.param(
                _one_call(_CODE_PATH, 50, 50, allow_large=True, text=_text_of_tokens(24_999)), "code/other",
                {("band",): 1}, id="allow_large_at_24999_tokens_stays_out_but_is_in_the_band",
            ),
            pytest.param(
                _one_call(_CODE_PATH, 50, 50, allow_large=True, text=_text_of_tokens(25_000)), "code/other",
                {("code/other", "denominator"): 1, ("band",): 1}, id="allow_large_at_25000_tokens_enters",
            ),
            pytest.param(
                _one_call(_CODE_PATH, 2001, 2001, allow_large=True), "code/other", {("code/other", "denominator"): 1},
                id="allow_large_over_the_default_limit_enters",
            ),
            pytest.param(
                _failed_read_exchange("m1", "r1", _CODE_PATH, "File does not exist."), "code/other", {},
                id="other_error_stays_out",
            ),
            pytest.param(_with_tool_use_result(None), "code/other", {}, id="size_unknown_stays_out"),
            pytest.param(
                _one_call(_DIFF_PATH, 5, 9000, truncated=True), "diff_handoff", {}, id="diff_handoff_is_not_a_reviewed_file",
            ),
        ],
    )
    def test_which_whole_file_calls_enter_the_headline(self, window, role, expected_headline):
        totals = _accumulate(window)

        assert _only_call(totals)[0] == role
        assert _nonzero(totals.headline) == expected_headline

    @pytest.mark.parametrize("path", [_CODE_PATH, _PROSE_PATH])
    @pytest.mark.parametrize(
        ("tokens", "total_lines", "expected_band_count"),
        [
            (19_999, 1000, 0), (20_000, 1000, 1), (29_999, 1000, 1), (30_000, 1000, 0),
            (25_000, 2000, 1), (25_000, 2001, 0),
        ],
    )
    def test_allow_large_calls_whose_estimate_alone_decides_the_denominator_are_counted(
        self, path, tokens, total_lines, expected_band_count,
    ):
        window = _structured_read_exchange(
            "m1", "r1", path, num_lines=total_lines, total_lines=total_lines, allow_large=True,
            text=_text_of_tokens(tokens),
        )

        assert _accumulate(window).headline[("band",)] == expected_band_count

    @pytest.mark.parametrize("allow_large", [None, True])
    def test_band_counts_allow_large_calls_only_and_reviewed_files_only(self, allow_large):
        reviewed_plain = _structured_read_exchange(
            "m1", "r1", _CODE_PATH, num_lines=10, total_lines=10, text=_text_of_tokens(25_000),
            allow_large=allow_large,
        )
        diff_handoff = _structured_read_exchange(
            "m2", "r2", _DIFF_PATH, num_lines=10, total_lines=10, text=_text_of_tokens(25_000), allow_large=True,
        )

        assert _accumulate(_flat(reviewed_plain, diff_handoff)).headline[("band",)] == int(allow_large is True)

    @pytest.mark.parametrize(
        ("refusal_text", "paging", "expected_follow_up"),
        [
            pytest.param(_PAGED_REFUSAL, {"offset": 10, "limit": 50}, "later_offset_read", id="paged_is_a_later_read"),
            pytest.param(_REFUSAL, {"limit": 50}, "neither", id="limit_only_refusal_leaves_no_trace"),
        ],
    )
    def test_a_refused_targeted_call_takes_no_class_and_leaves_the_headline_alone(self, refusal_text, paging, expected_follow_up):
        partial_call = _structured_read_exchange("m1", "r1", _CODE_PATH, num_lines=5, total_lines=9)
        refusal = _failed_read_exchange("m2", "r2", _CODE_PATH, refusal_text, **paging)

        totals = _accumulate(_flat(partial_call, refusal))

        assert _nonzero(totals.outcome_calls) == {("code/other", "partial_unflagged", "up_to_1000"): 1}
        assert _nonzero(totals.headline) == {("code/other", "denominator"): 1, ("code/other", "partial"): 1}
        assert _nonzero(totals.follow_up) == {("code/other", "calls"): 1, ("code/other", expected_follow_up): 1}


_BIG_PATH = "/repo/src/big.py"


def _partial_call() -> list[dict]:
    """The call every follow-up scenario starts from: lines 1 to 40 of a 100-line file."""
    return _structured_read_exchange("m1", "r1", _BIG_PATH, num_lines=40, total_lines=100)


def _paged(message_id: str, tool_id: str, start_line: int, num_lines: int, *, path: str = _BIG_PATH, total: int = 100):
    return _structured_read_exchange(
        message_id, tool_id, path, num_lines=num_lines, total_lines=total, start_line=start_line,
        offset=start_line - 1, limit=num_lines,
    )


def _unstructured_paged_read() -> list[dict]:
    """A paged read of the big file whose result record carries no structured fields."""
    return [
        _reviewer_turn("m2", [_read_use("r2", _BIG_PATH, offset=40, limit=60)]), _read_result("r2", "x", tool_use_result=None),
    ]


class TestFollowUpAndCoverage:
    @pytest.mark.parametrize(
        ("before", "after", "other_window", "expected"),
        [
            pytest.param([], _paged("m2", "r2", 1, 10), [], (1, 0, 0), id="later_read_with_offset_zero_counts"),
            pytest.param(_paged("m0", "r0", 5, 5), [], [], (0, 0, 1), id="offset_read_before_the_call_does_not_count"),
            pytest.param([], _paged("m2", "r2", 5, 5, path=_PROSE_PATH), [], (0, 0, 1), id="offset_read_of_another_path"),
            pytest.param([], [], _paged("m9", "r9", 41, 60), (0, 0, 1), id="offset_read_in_another_window"),
            pytest.param(
                [], _failed_read_exchange("m2", "r2", _BIG_PATH, "boom", offset=50, limit=10), [], (1, 0, 0),
                id="later_failed_offset_read_counts",
            ),
            pytest.param(
                [], _failed_read_exchange("m2", "r2", _BIG_PATH, "boom", offset=0, limit=10), [], (1, 0, 0),
                id="later_failed_read_with_offset_zero_counts",
            ),
            pytest.param(
                [], _flat(_paged("m2", "r2", 30, 41), _paged("m3", "r3", 60, 41)), [], (1, 1, 0),
                id="overlapping_ranges_cover_the_file",
            ),
            pytest.param(
                [], _flat(_paged("m2", "r2", 30, 16), _paged("m3", "r3", 60, 41)), [], (1, 0, 0),
                id="gapped_ranges_do_not_cover_the_file",
            ),
            pytest.param(
                [], _flat(_paged("m2", "r2", 30, 71), _paged("m3", "r3", 35, 11)), [], (1, 1, 0),
                id="a_range_inside_a_larger_one_does_not_shrink_the_coverage",
            ),
            pytest.param([], _paged("m2", "r2", 41, 59), [], (1, 0, 0), id="ranges_one_line_short_of_the_end"),
            pytest.param([], _paged("m2", "r2", 41, 60), [], (1, 1, 0), id="adjacent_ranges_cover_the_file"),
            pytest.param(
                [], _structured_read_exchange("m2", "r2", _BIG_PATH, num_lines=100, total_lines=100), [], (0, 1, 0),
                id="whole_file_reread_covers_without_an_offset_read",
            ),
            pytest.param(_paged("m0", "r0", 41, 60), [], [], (0, 0, 1), id="covering_read_before_the_call_does_not_count"),
            pytest.param([], _paged("m2", "r2", 41, 60, path=_PROSE_PATH), [], (0, 0, 1), id="coverage_of_another_path"),
            pytest.param([], _unstructured_paged_read(), [], (1, 0, 0), id="later_read_without_structured_fields"),
        ],
    )
    def test_follow_up_of_a_partial_whole_file_call(self, before, after, other_window, expected):
        windows = [_flat(before, _partial_call(), after)] + ([other_window] if other_window else [])

        totals = _accumulate(*windows)

        later_offset_read, covered_after, neither = expected
        assert _nonzero(totals.follow_up) == {
            key: count for key, count in {
                ("code/other", "calls"): 1, ("code/other", "later_offset_read"): later_offset_read,
                ("code/other", "covered_after"): covered_after, ("code/other", "neither"): neither,
            }.items() if count
        }

    def test_a_refused_call_is_covered_by_later_reads_that_reveal_its_size(self):
        window = _flat(_failed_read_exchange("m1", "r1", _BIG_PATH, _REFUSAL), _paged("m2", "r2", 1, 100))

        assert _accumulate(window).follow_up[("code/other", "covered_after")] == 1

    def test_a_call_of_unknown_size_is_never_covered(self):
        window = _flat(_failed_read_exchange("m1", "r1", _BIG_PATH, _REFUSAL), _unstructured_paged_read())

        totals = _accumulate(window)

        assert _nonzero(totals.follow_up) == {("code/other", "calls"): 1, ("code/other", "later_offset_read"): 1}

    @pytest.mark.parametrize(("later_start", "expected_covered"), [(41, 1), (42, 0)])
    def test_a_trillion_line_file_is_decided_by_interval_without_enumerating_lines(self, later_start, expected_covered):
        huge = 10**12
        call = _structured_read_exchange("m1", "r1", _BIG_PATH, num_lines=40, total_lines=huge)
        later = _paged("m2", "r2", later_start, huge - later_start + 1, total=huge)

        assert _accumulate(_flat(call, later)).follow_up[("code/other", "covered_after")] == expected_covered

    def test_follow_up_work_grows_with_the_reads_of_a_path_and_not_with_their_square(self, monkeypatch):
        fact_accesses = []
        monkeypatch.setattr(
            reviewer_reads, "_ReadFacts", _access_recording_read_facts(reviewer_reads._ReadFacts, fact_accesses),
        )
        window = [
            record for n in range(2000)
            for record in (*_failed_read_exchange(f"m{n}", f"r{n}", _BIG_PATH, _REFUSAL), *_paged(f"p{n}", f"q{n}", n + 1, 1))
        ]

        totals = _accumulate(window)

        # Every refused call has a later offset read, and only the first has later reads reaching back to line 1.
        counts = [totals.follow_up[("code/other", name)] for name in ("calls", "later_offset_read", "covered_after")]
        assert counts == [2000, 2000, 1]
        inspected = [name for name in fact_accesses if name in ("has_offset", "interval")]
        assert len(inspected) <= 2 * 4000
        # The facts are read at least once per read, so the bound is not met by reading none. A read costs at most
        # call_order twice, has_offset once and interval twice, and a rescan per read by any route exceeds that.
        assert 4000 <= len(fact_accesses) <= 5 * 4000
    def test_follow_up_counts_per_role(self):
        window = _flat(
            _structured_read_exchange("m1", "r1", _DIFF_PATH, num_lines=5, total_lines=9),
            _structured_read_exchange("m2", "r2", _PROSE_PATH, num_lines=5, total_lines=9),
        )

        assert _nonzero(_accumulate(window).follow_up) == {
            ("diff_handoff", "calls"): 1, ("diff_handoff", "neither"): 1,
            ("prose", "calls"): 1, ("prose", "neither"): 1,
        }


class TestReadShare:
    def test_read_weight_parts_reconcile_and_other_windows_are_outside_both_sides(self):
        window = [
            *_structured_read_exchange("m1", "r1", _CODE_PATH, num_lines=1500, total_lines=1500),
            *_structured_read_exchange("m2", "r2", _DIFF_PATH, num_lines=1200, total_lines=1200),
            _reviewer_turn("m3", [_read_use("r3", _CODE_PATH + "x")]),
            _read_result("r3", _HUNDRED_TOKEN_TEXT, tool_use_result=None),
            *_structured_read_exchange("m4", "r4", _CODE_PATH, num_lines=500, total_lines=500),
            _reviewer_turn("m5", []),
        ]
        outside = _structured_read_exchange("o1", "ro1", _CODE_PATH, num_lines=1500, total_lines=1500)
        totals = reviewer_reads._Totals()

        reviewer_reads._accumulate_session(
            totals, read_cost._SeenIds(), [], [
                (_TRACKED_AGENT_TYPE, window), ("skill-fidelity-reviewer", outside), ("general-purpose", outside),
                (_TRACKED_AGENT_TYPE, [_reviewer_turn("m1")]),
            ],
            pricing._cache_read_equivalent_weights(), _SINCE_TS, _UNTIL_EPOCH, frozenset({_TRACKED_AGENT_TYPE}),
        )

        # Five turns of 10 output tokens at weight 50 each; the second window repeats m1 and bills nothing new.
        assert totals.billed_weight == 2500.0
        # 100 estimated tokens at a 12.5 cache write plus one cache read per later turn: 4, 3, 2 and 1 later turns.
        assert totals.read_weight == 100 * (16.5 + 15.5 + 14.5 + 13.5)
        assert totals.read_weight_over_page == 100 * (16.5 + 15.5)
        assert totals.read_weight_over_page_code_or_other == 100 * 16.5
        assert totals.read_weight_over_page_diff_handoff == 100 * 15.5
        assert totals.read_weight_unknown_size == 100 * 14.5
        assert totals.reviewer_windows == 2
        assert totals.skill_fidelity_windows_left_out == 1

    @pytest.mark.parametrize("total_lines", [1001, 2001])
    @pytest.mark.parametrize("targeted", [False, True])
    def test_a_prose_read_over_1000_lines_adds_to_the_over_page_weight_and_to_neither_role_part(self, total_lines, targeted):
        paging = {"offset": 0, "limit": 10} if targeted else {}
        exchange = _structured_read_exchange(
            "m1", "r1", _PROSE_PATH, num_lines=10 if targeted else total_lines, total_lines=total_lines, **paging,
        )

        totals = _accumulate([*exchange, _reviewer_turn("m2", [])])

        assert totals.read_weight_over_page == 100 * 13.5
        assert (totals.read_weight_over_page_code_or_other, totals.read_weight_over_page_diff_handoff) == (0.0, 0.0)

    def test_a_targeted_read_adds_to_the_read_weight(self):
        window = [
            *_structured_read_exchange("m1", "r1", _CODE_PATH, num_lines=10, total_lines=1500, offset=0, limit=10),
            _reviewer_turn("m2", []),
        ]

        # 100 estimated tokens at a 12.5 cache write plus one cache read for the one later turn.
        assert _accumulate(window).read_weight == 100 * 13.5


class TestPerType:
    def test_untracked_names_fold_into_one_withheld_row_and_tracked_names_keep_their_own(self):
        totals = reviewer_reads._Totals()
        partial = _structured_read_exchange("m1", "r1", _CODE_PATH, num_lines=5, total_lines=9)
        refused = _failed_read_exchange("m2", "r2", _CODE_PATH, _REFUSAL)

        reviewer_reads._accumulate_session(
            totals, read_cost._SeenIds(), [], [
                (_TRACKED_AGENT_TYPE, partial), ("staff-untracked-a", refused), ("staff-untracked-b", [_reviewer_turn("m3")]),
            ],
            pricing._cache_read_equivalent_weights(), _SINCE_TS, _UNTIL_EPOCH, frozenset({_TRACKED_AGENT_TYPE}),
        )

        assert totals.type_rows == {
            _TRACKED_AGENT_TYPE: Counter(windows=1, larger_than_one_call=1, partial=1),
            _WITHHELD: Counter(windows=2, larger_than_one_call=1, refused=1),
        }
        assert "staff-untracked-a" not in {*totals.type_rows}


def _block_turn(*blocks) -> dict:
    return _assistant(message={"content": list(blocks)})


def _tool_use(tool_input, *, name: str = "Read", tool_id: object = "r1") -> dict:
    return {"type": "tool_use", "id": tool_id, "name": name, "input": tool_input}


class TestReadCallBlocks:
    @pytest.mark.parametrize(
        ("turn", "expected"),
        [
            pytest.param(_block_turn(_tool_use({"file_path": "/a.py"})), [("r1", "/a.py", True)], id="whole_file"),
            pytest.param(
                _block_turn(_tool_use({"file_path": "/a.py", "offset": 0})), [("r1", "/a.py", False)],
                id="offset_only_is_targeted",
            ),
            pytest.param(
                _block_turn(_tool_use({"file_path": "/a.py", "limit": 5})), [("r1", "/a.py", False)], id="limit_only_is_targeted",
            ),
            pytest.param(
                _block_turn(_tool_use({"file_path": "/a.py", "allow_large": True})), [("r1", "/a.py", True)],
                id="allow_large_stays_whole_file",
            ),
            pytest.param(_block_turn(_tool_use({"notebook_path": "/n.ipynb"})), [("r1", "/n.ipynb", True)], id="notebook_path"),
            pytest.param(_block_turn(_tool_use({"file_path": "/a"}, name="Grep")), [], id="another_tool"),
            pytest.param(_block_turn(_tool_use("x")), [], id="non_object_input"),
            pytest.param(_block_turn(_tool_use({"file_path": 5})), [], id="non_string_path"),
            pytest.param(_block_turn(_tool_use({"file_path": ""})), [], id="empty_path"),
            pytest.param(_block_turn(_tool_use({"file_path": "/a"}, tool_id=7)), [], id="non_string_id"),
            pytest.param(_block_turn(_tool_use({"file_path": "/a"}, tool_id="")), [], id="empty_id"),
            pytest.param(_block_turn("text", None, 5), [], id="non_object_blocks"),
            pytest.param(_assistant(message="text"), [], id="non_object_message"),
            pytest.param(_assistant(message={"content": "text"}), [], id="non_list_content"),
        ],
    )
    def test_each_read_block_yields_its_id_path_and_whole_file_flag_and_malformed_ones_yield_nothing(self, turn, expected):
        read_calls = reviewer_reads._read_call_blocks(turn)
        assert [(call.tool_use_id, call.path, call.whole_file) for call in read_calls] == expected


class TestSharedScanState:
    def test_a_main_threads_invalid_usage_turn_is_counted(self):
        main = [_assistant(message={"id": "m1", "usage": {"output_tokens": -1}, "content": []})]

        assert _accumulate(main_records=main).invalid_usage_turns == 1

    def test_a_failed_call_replayed_in_a_second_window_counts_once(self):
        replay = _failed_read_exchange("m1", "r1", _CODE_PATH, _REFUSAL)
        second_window = _failed_read_exchange("m2", "r1", _CODE_PATH, _REFUSAL)

        assert _nonzero(_accumulate(replay, second_window).outcome_calls) == {("code/other", "refused_over_limit", "unknown"): 1}

    def test_a_successful_call_replayed_in_a_second_window_counts_once(self):
        first = _structured_read_exchange("m1", "r1", _CODE_PATH, num_lines=5, total_lines=9)
        replay = _structured_read_exchange("m2", "r1", _CODE_PATH, num_lines=5, total_lines=9)

        assert _nonzero(_accumulate(first, replay).outcome_calls) == {("code/other", "partial_unflagged", "up_to_1000"): 1}

    def test_a_turn_the_main_thread_billed_is_not_billed_again_in_a_reviewer_window(self):
        turn = _reviewer_turn("m1")

        totals = _accumulate([turn], main_records=[turn])

        assert totals.billed_weight == 0.0

    def test_a_sidechain_record_in_the_main_file_is_not_a_main_thread_round_read(self):
        sidechain_read = {**_reviewer_turn("c", [_read_use("r1", _CODE_PATH)]), "isSidechain": True}
        main = [*_round_records("code-review", "a"), sidechain_read, _next_prompt()]

        assert _accumulate(main_records=main).rounds["code-review"].whole_file_calls == 0


class TestMainThreadRoundReads:
    @staticmethod
    def _round_reads(skill: str, tag: str, *exchanges, ts: str = _IN_WINDOW) -> list[dict]:
        """A window: its opening record, a turn with every exchange's Read block, and the exchanges' results."""
        uses = [block for exchange in exchanges for record in exchange if record["type"] == "assistant"
                for block in record["message"]["content"]]
        results = [record for exchange in exchanges for record in exchange if record["type"] == "user"]
        return [*_round_records(skill, tag, ts=ts, reads=tuple(uses)), *results]

    def test_reads_in_a_window_count_whole_file_and_targeted_and_split_by_outcome_and_size(self):
        whole = _structured_read_exchange("w1", "rw", _CODE_PATH, num_lines=5, total_lines=2500)
        targeted = _structured_read_exchange("w2", "rt", _CODE_PATH, num_lines=5, total_lines=2500, offset=0, limit=5)
        diff = _structured_read_exchange("w3", "rd", _DIFF_PATH, num_lines=5, total_lines=5)
        main = [*self._round_reads("code-review", "a", whole, targeted, diff), _next_prompt()]

        totals = _accumulate(main_records=main)

        round_totals = totals.rounds["code-review"]
        assert (round_totals.windows, round_totals.whole_file_calls, round_totals.targeted_calls) == (1, 2, 1)
        assert round_totals.diff_handoff_whole_file_calls == 1
        assert _nonzero(round_totals.outcomes) == {"partial_unflagged": 1}
        assert _nonzero(round_totals.buckets) == {"over_2000": 1}
        assert totals.rounds["plan-review"].windows == 0

    def test_a_read_split_into_a_duplicate_record_at_the_window_start_and_at_its_end_is_inside_it(self):
        start_read = _read_use("r-start", _CODE_PATH)
        end_read = _read_use("r-end", _CODE_PATH)
        opening = _reviewer_turn("o", [], request_id="req-open")
        opening["message"]["content"] = [{"type": "tool_use", "id": "s", "name": "Skill", "input": {"skill": "code-review"}}]
        start_duplicate = _reviewer_turn("o", [start_read], request_id="req-open")
        last = _reviewer_turn("l", [], request_id="req-last")
        end_duplicate = _reviewer_turn("l", [end_read], request_id="req-last")
        after_window = _reviewer_turn("x", [_read_use("r-after", _CODE_PATH)])
        main = [opening, start_duplicate, last, end_duplicate, _next_prompt(), after_window]

        totals = _accumulate(main_records=main)

        round_totals = totals.rounds["code-review"]
        assert (round_totals.windows, round_totals.whole_file_calls) == (1, 2)

    def test_reads_at_the_first_and_last_record_of_a_window_count_and_the_next_record_does_not(self):
        opening = _reviewer_turn("o", [
            {"type": "tool_use", "id": "s", "name": "Skill", "input": {"skill": "code-review"}},
            _read_use("r-first", _CODE_PATH),
        ])
        last_inside = _reviewer_turn("l", [_read_use("r-last", _CODE_PATH)])
        next_round = _reviewer_turn("p", [
            {"type": "tool_use", "id": "s2", "name": "Skill", "input": {"skill": "plan-review"}},
            _read_use("r-next", _CODE_PATH),
        ])

        totals = _accumulate(main_records=[opening, last_inside, next_round])

        assert (totals.rounds["code-review"].windows, totals.rounds["code-review"].whole_file_calls) == (1, 2)
        assert (totals.rounds["plan-review"].windows, totals.rounds["plan-review"].whole_file_calls) == (1, 1)

    def test_a_read_outside_every_window_counts_nowhere(self):
        before_any_round = _reviewer_turn("b", [_read_use("r-before", _CODE_PATH)])
        main = [before_any_round, _next_prompt()]

        totals = _accumulate(main_records=main)

        assert [(r.windows, r.whole_file_calls, r.targeted_calls) for r in totals.rounds.values()] == [(0, 0, 0)] * 3

    def test_a_replayed_tool_use_block_counts_once(self):
        read = _read_use("r1", _CODE_PATH)
        main = [*_round_records("code-review", "a", reads=(read, read)), _next_prompt()]

        assert _accumulate(main_records=main).rounds["code-review"].whole_file_calls == 1

    def test_a_window_opening_before_since_is_not_counted_whatever_it_holds(self):
        main = [*_round_records("code-review", "a", ts=_BEFORE_WINDOW, reads=(_read_use("r1", _CODE_PATH),)), _next_prompt()]

        assert _accumulate(main_records=main).rounds["code-review"].windows == 0

    @pytest.mark.parametrize(
        ("timestamp", "_ledger_expectation", "expected"), [*_WINDOW_EDGE_TIMESTAMPS, (None, "event_time", "out")],
    )
    def test_round_windows_are_selected_by_their_opening_records_timestamp_and_unparsable_ones_are_counted(
        self, timestamp, _ledger_expectation, expected,
    ):
        main = [*_round_records("code-review", "a", ts=timestamp), _next_prompt()]

        totals = _accumulate(main_records=main)

        assert totals.rounds["code-review"].windows == int(expected == "in")
        assert totals.round_windows_without_timestamp == int(timestamp in (None, "not-a-timestamp"))


class TestReviewerWindowEdges:
    @pytest.mark.parametrize(("timestamp", "_ledger_expectation", "expected"), _WINDOW_EDGE_TIMESTAMPS)
    def test_a_reviewer_window_is_selected_by_its_first_timestamped_record(self, timestamp, _ledger_expectation, expected):
        totals = _accumulate([_reviewer_turn("m1", ts=timestamp)])

        assert totals.reviewer_windows == int(expected == "in")
        assert totals.windows_without_timestamp == int(timestamp == "not-a-timestamp")

    @pytest.mark.parametrize(
        ("first_timestamp", "expected_windows"),
        [pytest.param(None, 1, id="untimestamped_records_are_skipped"), pytest.param(_BEFORE_WINDOW, 0, id="no_rescue")],
    )
    def test_a_window_is_selected_by_its_first_timestamped_record_whatever_a_later_one_holds(
        self, first_timestamp, expected_windows,
    ):
        window = [_reviewer_turn("m0", ts=first_timestamp), _reviewer_turn("m1", ts=_IN_WINDOW)]

        assert _accumulate(window).reviewer_windows == expected_windows

    def test_a_non_string_timestamp_is_no_timestamp(self):
        totals = _accumulate([{**_reviewer_turn("m1"), "timestamp": 12345}])

        assert (totals.reviewer_windows, totals.windows_without_timestamp) == (0, 1)


class TestComparability:
    @pytest.mark.parametrize(
        ("version", "expected_label"),
        [
            pytest.param("2.1.0", "2.1.0", id="valid"),
            pytest.param("1.2", "1.2", id="two_parts"),
            pytest.param("1234.1234.1234.1234", "1234.1234.1234.1234", id="four_parts_of_four_digits"),
            pytest.param("1", "other", id="one_part"),
            pytest.param("1.2.3.4.5", "other", id="five_parts"),
            pytest.param("12345.1", "other", id="five_digit_part"),
            pytest.param("1.12345", "other", id="five_digit_second_part"),
            pytest.param("1" * 33 + ".1", "other", id="thirty_three_digits_and_a_dot"),
            pytest.param(5, "other", id="int"),
            pytest.param(["2.1.0"], "other", id="list"),
            pytest.param({"v": "2.1.0"}, "other", id="dict"),
            pytest.param(None, "other", id="null"),
            pytest.param("1.2.3\n", "other", id="trailing_newline"),
            pytest.param("１.２.３", "other", id="non_ascii_digits"),
            pytest.param("/home/user/HOSTILE", "other", id="path"),
            pytest.param("a" * 32, "other", id="thirty_two_hex_digits"),
            pytest.param("9" * 100_000 + ".1", "other", id="overlong"),
        ],
    )
    def test_a_version_prints_only_in_the_bounded_ascii_form(self, version, expected_label):
        totals = _accumulate([_reviewer_turn("m1", version=version)])

        assert dict(totals.version_counts) == {expected_label: 1}

    def test_the_first_record_carrying_a_version_decides_and_none_at_all_is_unknown(self):
        carrying = _accumulate(
            [_reviewer_turn("m1"), _reviewer_turn("m2", version="2.1.0"), _reviewer_turn("m3", version="9.9.9")],
        )
        carrying_none = _accumulate([_reviewer_turn("m1"), _reviewer_turn("m2")])

        assert dict(carrying.version_counts) == {"2.1.0": 1}
        assert dict(carrying_none.version_counts) == {"unknown": 1}

    @pytest.mark.parametrize(
        ("model", "expected_label"),
        [
            pytest.param("claude-unpriced-model", "other", id="unpriced"),
            pytest.param("<synthetic>", "other", id="synthetic"),
            pytest.param(5, "other", id="int"),
            pytest.param(["claude-sonnet-5"], "other", id="unhashable_list"),
            pytest.param({"m": "claude-sonnet-5"}, "other", id="unhashable_dict"),
            pytest.param(None, "other", id="null"),
            pytest.param("/home/user/HOSTILE", "other", id="path"),
        ],
    )
    @pytest.mark.parametrize("leading", [[], [_user_msg("dispatch prompt", ts=_IN_WINDOW)]], ids=["alone", "after_a_user_record"])
    def test_a_model_pricing_does_not_name_prints_as_other(self, leading, model, expected_label):
        totals = _accumulate([*leading, _reviewer_turn("m1", model=model)])

        assert dict(totals.model_counts) == {expected_label: 1}

    @pytest.mark.parametrize("model", sorted(pricing._MODEL_BASE_INPUT_RATES))
    def test_every_model_pricing_names_prints_by_name_whether_or_not_it_has_one_rate_set(self, model):
        assert dict(_accumulate([_reviewer_turn("m1", model=model)]).model_counts) == {model: 1}

    def test_a_window_with_no_assistant_record_or_no_model_key_has_an_unknown_model(self):
        no_model_key = _reviewer_turn("m1")
        del no_model_key["message"]["model"]

        totals = _accumulate([_user_msg("hello", ts=_IN_WINDOW)], [no_model_key])

        assert dict(totals.model_counts) == {"unknown": 2}

    def test_the_first_assistant_record_alone_decides_the_model(self):
        window = [_reviewer_turn("m1", model="claude-unpriced-model"), _reviewer_turn("m2")]

        assert dict(_accumulate(window).model_counts) == {"other": 1}


class TestDiagnostics:
    def test_an_unexplained_partial_counts_only_on_files_of_up_to_the_default_limit(self):
        window = _flat(
            _structured_read_exchange("m1", "r1", _CODE_PATH, num_lines=5, total_lines=2000),
            _structured_read_exchange("m2", "r2", _CODE_PATH + "2", num_lines=2000, total_lines=2500),
            _structured_read_exchange("m3", "r3", _CODE_PATH + "3", num_lines=5, total_lines=2001),
            _structured_read_exchange("m4", "r4", _CODE_PATH + "4", num_lines=5, total_lines=50, truncated=True),
        )

        assert _accumulate(window).unexplained_partials == 1

    def test_a_partial_token_cap_call_without_a_notice_is_counted(self):
        window = _structured_read_exchange("m1", "r1", _CODE_PATH, num_lines=5, total_lines=9000, truncated=True)

        assert _accumulate(window).notices_missing_for_partial_token_cap == 1

    def test_an_unrecognised_limit_error_and_its_other_error_are_counted_together(self):
        totals = _accumulate(_failed_read_exchange("m1", "r1", _CODE_PATH, "File content (9) too large"))

        assert (totals.unrecognised_limit_errors, _only_call(totals)[1]) == (1, "other_error")

    def test_a_skill_fidelity_reviewer_window_is_left_out_and_counted(self):
        totals = _accumulate([_reviewer_turn("m1")], agent_type="skill-fidelity-reviewer")

        assert (totals.reviewer_windows, totals.skill_fidelity_windows_left_out) == (0, 1)

    @pytest.mark.parametrize(
        ("timestamp", "expected_without_timestamp"), [(_BEFORE_WINDOW, 0), ("2026-08-13T00:00:00.000Z", 0), (None, 1)],
    )
    def test_a_skill_fidelity_window_outside_the_window_or_without_a_timestamp_is_not_left_out(
        self, timestamp, expected_without_timestamp,
    ):
        totals = _accumulate([_reviewer_turn("m1", ts=timestamp)], agent_type="skill-fidelity-reviewer")

        assert (totals.skill_fidelity_windows_left_out, totals.windows_without_timestamp) == (0, expected_without_timestamp)

    def test_a_window_of_a_non_reviewer_type_is_not_counted_anywhere(self):
        totals = _accumulate([_reviewer_turn("m1")], agent_type="general-purpose")

        assert (totals.reviewer_windows, totals.skill_fidelity_windows_left_out, totals.windows_without_timestamp) == (0, 0, 0)

    @pytest.mark.parametrize(
        ("exchange", "notice_for", "expected_counts"),
        [
            pytest.param(
                _structured_read_exchange("m1", "r1", _CODE_PATH, num_lines=5, total_lines=9000, truncated=True), "r1",
                (0, 0, 0), id="partial_token_cap_call_agrees",
            ),
            pytest.param(
                _structured_read_exchange("m1", "r1", _CODE_PATH, num_lines=5, total_lines=9000, truncated=True), None,
                (1, 0, 0), id="partial_token_cap_call_with_no_notice",
            ),
            pytest.param(_with_tool_use_result(None), "r1", (0, 0, 1), id="size_unknown_call"),
            pytest.param(
                _structured_read_exchange("m1", "r1", _CODE_PATH, num_lines=5, total_lines=9), "r1", (0, 1, 0),
                id="partial_unflagged_call",
            ),
            pytest.param(
                _structured_read_exchange("m1", "r1", _CODE_PATH, num_lines=9, total_lines=9), "r1", (0, 1, 0),
                id="complete_call",
            ),
            pytest.param(
                _structured_read_exchange("m1", "r1", _CODE_PATH, num_lines=9, total_lines=9), "r-unknown", (0, 1, 0),
                id="no_call_at_all",
            ),
        ],
    )
    def test_notice_agreement_counts_by_the_call_a_notice_names(self, exchange, notice_for, expected_counts):
        window = [*exchange, *([_read_truncation_notice(notice_for)] if notice_for else [])]

        totals = _accumulate(window)

        assert (
            totals.notices_missing_for_partial_token_cap, totals.notices_naming_other_calls,
            totals.notices_naming_size_unknown_calls,
        ) == expected_counts


class TestUsableRecords:
    @pytest.mark.parametrize(
        ("record", "expected"),
        [
            pytest.param("text", None, id="string_record"),
            pytest.param(["list"], None, id="list_record"),
            pytest.param(5, None, id="int_record"),
            pytest.param(None, None, id="null_record"),
            pytest.param({"type": ["assistant"]}, None, id="list_type"),
            pytest.param({"type": 5}, None, id="int_type"),
            pytest.param({"type": "assistant", "message": "text"}, {"type": "assistant", "message": {}}, id="string_message"),
            pytest.param({"type": "assistant", "message": ["x"]}, {"type": "assistant", "message": {}}, id="list_message"),
            pytest.param(
                {"type": "assistant", "message": {"id": ["m"]}}, {"type": "assistant", "message": {"id": None}},
                id="list_message_id",
            ),
            pytest.param(
                {"type": "assistant", "requestId": {"a": 1}}, {"type": "assistant", "requestId": None},
                id="dict_request_id",
            ),
            pytest.param(
                {"type": "assistant", "message": {"usage": {"output_tokens": 10**400}}}, _ASSISTANT_WITH_INVALID_USAGE,
                id="overflowing_usage_count",
            ),
            pytest.param(
                {"type": "assistant", "message": {"usage": {"cache_creation": {"ephemeral_5m_input_tokens": 10**400}}}},
                _ASSISTANT_WITH_INVALID_USAGE, id="overflowing_nested_usage_count",
            ),
            pytest.param(
                {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": ["Read"]}, "text"]}},
                {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": None}, "text"]}},
                id="list_block_name",
            ),
            pytest.param({"type": "assistant", "message": {"usage": "x"}}, _ASSISTANT_WITH_INVALID_USAGE, id="string_usage"),
            pytest.param({"type": "assistant", "message": {"usage": 7}}, _ASSISTANT_WITH_INVALID_USAGE, id="int_usage"),
            pytest.param(
                {"type": "assistant", "message": {"content": 5}}, {"type": "assistant", "message": {"content": []}},
                id="int_content",
            ),
            pytest.param(
                {"type": "assistant", "message": {"content": {"a": 1}}}, {"type": "assistant", "message": {"content": []}},
                id="object_content",
            ),
            pytest.param(
                {"type": "user", "message": {"content": [{"type": "text", "text": 5}, {"type": "text", "text": "ok"}]}},
                {"type": "user", "message": {"content": [{"type": "text", "text": ""}, {"type": "text", "text": "ok"}]}},
                id="int_text_block_text",
            ),
        ],
    )
    def test_a_shape_a_shared_scanner_would_choke_on_is_reduced_or_dropped(self, record, expected):
        assert reviewer_reads._usable_record(record) == expected

    @pytest.mark.parametrize(
        "record",
        [
            {"type": "assistant", "message": {"id": "m", "usage": {"output_tokens": 10**15}, "content": []}},
            {"type": "user", "requestId": "req-1", "message": {"content": [{"type": "tool_use", "name": "Read"}]}},
            {"type": "system", "subtype": "compact_boundary"},
            {"message": {"id": "m"}},
            {"type": "user", "message": {"usage": 0, "content": [{"type": "tool_use", "text": 5}]}},
        ],
    )
    def test_a_well_formed_record_is_returned_unchanged_and_uncopied(self, record):
        assert reviewer_reads._usable_record(record) is record

    @pytest.mark.parametrize(
        "hostile",
        [
            pytest.param("not a record", id="string"),
            pytest.param(["list"], id="list"),
            pytest.param({"type": ["assistant"], "timestamp": _IN_WINDOW}, id="list_type"),
            pytest.param(_assistant(message="text"), id="string_message"),
            pytest.param(_assistant(message={"id": ["x"], "content": []}), id="list_message_id"),
            pytest.param(_assistant(requestId=["req"]), id="list_request_id"),
            pytest.param(_assistant(message={"id": "m1", "usage": {"output_tokens": 10**400}, "content": []}), id="usage"),
            pytest.param(
                _assistant(message={"id": "m1", "content": [{"type": "tool_use", "name": ["Read"], "id": "r"}]}),
                id="list_tool_name",
            ),
        ],
    )
    def test_a_hostile_record_in_the_main_thread_or_a_reviewer_window_raises_nothing(self, hostile):
        read = [_reviewer_turn("m2", [_read_use("r1", _CODE_PATH)]), _read_result("r1", ["not text"], tool_use_result="x")]
        window = [hostile, *read]

        totals = _accumulate(window, main_records=window)

        assert (totals.sessions, totals.reviewer_windows) == (1, 1)

    def test_an_overflowing_usage_is_counted_as_an_invalid_usage_turn_and_bills_nothing(self):
        window = [_assistant(message={"id": "m1", "usage": {"output_tokens": 10**400}, "content": []})]

        totals = _accumulate(window)

        assert (totals.invalid_usage_turns, totals.billed_weight) == (1, 0.0)
