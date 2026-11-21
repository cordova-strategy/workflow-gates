"""Tests for the reviewer-reads report: printed figures over a hand-computed fixture, the rate markers, and the
reviewer-yield section's wiring."""
import os
from collections import Counter

import pytest
from transcript_analysis import corpus, ledger_dispositions, pricing, read_cost, reviewer_reads, reviewer_yield

from ._reviewer_reads_helpers import (
    _BEFORE_WINDOW,
    _TRACKED_REVIEWER,
    _failed_read_exchange,
    _printed_line,
    _read_exchange,
    _report_text,
    _reviewer_reads_args,
    _reviewer_window,
    _turn,
)
from .conftest import _agent_use, _read_result, _read_truncation_notice, _read_use, _write_jsonl

_SINCE_TS = corpus._parse_ts("2026-08-10T00:00:00Z")
_UNTIL_EPOCH = corpus._parse_ts("2026-08-13T00:00:00Z")
_WITHHELD = "(withheld — untracked agent type)"
_DIFF_HANDOFF_DIR = "/home/user/.claude/code-review-diff-markers"
_BUCKETS = ("up_to_1000", "1001_to_2000", "over_2000", "unknown")


def _fixture_totals() -> reviewer_reads._Totals:
    """12 reviewer windows with every figure chosen by hand, so each printed figure has its own expected value."""
    totals = reviewer_reads._Totals(
        sessions=3, reviewer_windows=12, skill_fidelity_windows_left_out=1, windows_without_timestamp=2,
        invalid_usage_turns=4, billed_weight=20000.0, read_weight=4000.0, read_weight_over_page=1000.0,
        read_weight_over_page_code_or_other=600.0, read_weight_over_page_diff_handoff=240.0,
        read_weight_unknown_size=500.0, unrecognised_limit_errors=1, unexplained_partials=2,
        notices_missing_for_partial_token_cap=1, notices_naming_other_calls=0, notices_naming_size_unknown_calls=5,
    )
    totals.outcome_calls.update({
        ("code/other", "refused_over_limit", "unknown"): 3, ("code/other", "other_error", "unknown"): 2,
        ("code/other", "size_unknown", "unknown"): 1, ("code/other", "partial_token_cap", "over_2000"): 4,
        ("code/other", "partial_token_cap", "1001_to_2000"): 1, ("code/other", "complete_allow_large", "up_to_1000"): 1,
        ("code/other", "complete_allow_large", "over_2000"): 2, ("code/other", "complete", "up_to_1000"): 20,
        ("code/other", "complete", "over_2000"): 1, ("code/other", "partial_unflagged", "up_to_1000"): 2,
        ("code/other", "partial_unflagged", "1001_to_2000"): 1, ("prose", "refused_over_limit", "unknown"): 1,
        ("prose", "other_error", "unknown"): 1, ("prose", "partial_unflagged", "up_to_1000"): 2,
        ("prose", "complete", "up_to_1000"): 5, ("diff_handoff", "partial_token_cap", "over_2000"): 1,
        ("diff_handoff", "complete", "up_to_1000"): 2, ("diff_handoff", "other_error", "unknown"): 4,
    })
    totals.headline.update({
        ("code/other", "denominator"): 14, ("code/other", "partial"): 8, ("code/other", "refused"): 3,
        ("prose", "denominator"): 3, ("prose", "partial"): 2, ("prose", "refused"): 1, ("band",): 7,
    })
    totals.follow_up.update({
        ("code/other", "calls"): 12, ("code/other", "later_offset_read"): 6, ("code/other", "covered_after"): 3,
        ("code/other", "neither"): 4, ("prose", "calls"): 5, ("prose", "later_offset_read"): 2,
        ("prose", "covered_after"): 1, ("prose", "neither"): 2,
    })
    totals.size_unknown_reasons.update({"multi_result_record": 5, "line_field_invalid": 1})
    totals.type_rows.update({
        _TRACKED_REVIEWER: Counter(windows=7, partial=6, refused=3, larger_than_one_call=12),
        "ciso-reviewer": Counter(windows=3, partial=3, larger_than_one_call=3),
        _WITHHELD: Counter(windows=2, partial=1, refused=1, larger_than_one_call=2),
    })
    totals.version_counts.update({"2.1.0": 8, "2.0.9": 3, "other": 1})
    totals.model_counts.update({"claude-sonnet-5": 9, "claude-opus-5": 2, "other": 1})
    code_review = totals.rounds["code-review"]
    code_review.windows, code_review.whole_file_calls, code_review.targeted_calls = 3, 5, 2
    code_review.diff_handoff_whole_file_calls = 1
    code_review.outcomes.update({"partial_unflagged": 1, "complete": 2})
    code_review.buckets.update({"up_to_1000": 2, "over_2000": 1})
    plan_review = totals.rounds["plan-review"]
    plan_review.windows, plan_review.whole_file_calls = 1, 1
    plan_review.outcomes.update({"size_unknown": 1})
    plan_review.buckets.update({"unknown": 1})
    return totals


def _fixture_yield_pass() -> reviewer_reads._YieldPass:
    return reviewer_reads._YieldPass(
        rows={
            _TRACKED_REVIEWER: Counter({
                "dispatches": 11, "findings_found": 6, "zero_finding": 4, "unclassified": 1, "total_findings": 15,
                ("findings-found", "cited"): 8, ("findings-found", "active"): 12, ("findings-found", "edited"): 3,
                ("zero-finding", "cited"): 3, ("zero-finding", "active"): 4, ("zero-finding", "edited"): 1,
            }),
            "ciso-reviewer": Counter({"dispatches": 2, "zero_finding": 2}),
            _WITHHELD: Counter({"dispatches": 1, "unclassified": 1}),
        },
        skipped_input_total=2, meta_read_errors=1, transcript_read_errors=0,
    )


def _fixture_ledger_counts() -> ledger_dispositions.LedgerDispositionCounts:
    return ledger_dispositions.LedgerDispositionCounts(
        directory_state="present", files_read=4, unreadable_files=1,
        terminal_by_disposition={"ADDRESS": 30, "DEFER": 12, "SETTLED": 8}, id_less_disposition_rows=2,
        unknown_disposition_rows=1,
        left_out_by_field={
            "disposition": 0, "id": 1, "ref": 0, "decided_by": 0, "event_time": 3, "session_id": 0,
        },
        sessions_with_disposition_row=6, sessions_covered_by_scan=5,
    )


def _print_report(totals, yield_pass, ledger_counts, capsys) -> list[str]:
    reviewer_reads._print_report(
        totals, pricing._cache_read_equivalent_weights(), _SINCE_TS, _UNTIL_EPOCH, yield_pass, ledger_counts,
    )
    lines = capsys.readouterr().out.splitlines()
    return lines[lines.index(next(line for line in lines if line.startswith("Class weights:"))) + 1:]


class TestPrintedFigures:
    def test_every_figure_over_the_hand_computed_fixture(self, capsys):
        report = _print_report(_fixture_totals(), _fixture_yield_pass(), _fixture_ledger_counts(), capsys)

        assert report == [
            "",
            "window: 2026-08-10 to 2026-08-12 (UTC, both days included)",
            "sessions=3 reviewer_windows=12"
            " (sessions and the skipped input line's scan gaps count every retained in-scope transcript, whatever the window;"
            " its invalid_usage_turns counts every main-thread turn and only the reviewer windows in the window)",
            "skipped input: unreadable_roots=0 unreadable_project_dirs=0 unreadable_main_files=0"
            " unreadable_subagent_dirs=0 unreadable_subagent_files=0 unreadable_subagent_meta=0 invalid_usage_turns=4",
            "",
            "## Whole-file reads of reviewed files larger than one Read call",
            "partial is partial_token_cap or partial_unflagged and refused is refused_over_limit. A refused read is never"
            " counted as partial. The denominator is calls that were partial or refused, complete on a file over 2,000"
            " lines, or allow_large at an estimated 25,000 tokens or more (4 chars/token).",
            "code/other: partial 57.1% (8/14); refused 21.4% (3/14); partial or refused 78.6% (11/14)",
            "prose (instruction and other_prose; instruction is matched by path, whatever the extension):"
            " partial insufficient (2/3); refused insufficient (1/3); partial or refused insufficient (3/3)",
            "pooled: partial 58.8% (10/17); refused 23.5% (4/17); partial or refused 82.4% (14/17)",
            "complete_allow_large calls on files of up to 2,000 lines with an estimate from 20,000 to 29,999 tokens,"
            " where the estimate alone decides the denominator: 7",
            "outside the denominator, reviewed files only: other_error=3 size_unknown=1",
            "",
            "## Whole-file calls in reviewer windows, by outcome and file size (lines)",
            "code/other:",
            "  refused_over_limit: total=3 up_to_1000=0 1001_to_2000=0 over_2000=0 unknown=3",
            "  other_error: total=2 up_to_1000=0 1001_to_2000=0 over_2000=0 unknown=2",
            "  size_unknown: total=1 up_to_1000=0 1001_to_2000=0 over_2000=0 unknown=1",
            "  partial_token_cap: total=5 up_to_1000=0 1001_to_2000=1 over_2000=4 unknown=0",
            "  complete_allow_large: total=3 up_to_1000=1 1001_to_2000=0 over_2000=2 unknown=0",
            "  complete: total=21 up_to_1000=20 1001_to_2000=0 over_2000=1 unknown=0",
            "  partial_unflagged: total=3 up_to_1000=2 1001_to_2000=1 over_2000=0 unknown=0",
            "prose (instruction and other_prose; instruction is matched by path, whatever the extension):",
            "  refused_over_limit: total=1 up_to_1000=0 1001_to_2000=0 over_2000=0 unknown=1",
            "  other_error: total=1 up_to_1000=0 1001_to_2000=0 over_2000=0 unknown=1",
            "  size_unknown: total=0 up_to_1000=0 1001_to_2000=0 over_2000=0 unknown=0",
            "  partial_token_cap: total=0 up_to_1000=0 1001_to_2000=0 over_2000=0 unknown=0",
            "  complete_allow_large: total=0 up_to_1000=0 1001_to_2000=0 over_2000=0 unknown=0",
            "  complete: total=5 up_to_1000=5 1001_to_2000=0 over_2000=0 unknown=0",
            "  partial_unflagged: total=2 up_to_1000=2 1001_to_2000=0 over_2000=0 unknown=0",
            "diff handoff (the review diff, not a reviewed file):",
            "  refused_over_limit: total=0 up_to_1000=0 1001_to_2000=0 over_2000=0 unknown=0",
            "  other_error: total=4 up_to_1000=0 1001_to_2000=0 over_2000=0 unknown=4",
            "  size_unknown: total=0 up_to_1000=0 1001_to_2000=0 over_2000=0 unknown=0",
            "  partial_token_cap: total=1 up_to_1000=0 1001_to_2000=0 over_2000=1 unknown=0",
            "  complete_allow_large: total=0 up_to_1000=0 1001_to_2000=0 over_2000=0 unknown=0",
            "  complete: total=2 up_to_1000=2 1001_to_2000=0 over_2000=0 unknown=0",
            "  partial_unflagged: total=0 up_to_1000=0 1001_to_2000=0 over_2000=0 unknown=0",
            "",
            "## After a partial or refused whole-file call, in the same reviewer window",
            "The command sees Read calls only, so the neither figure is an upper bound on calls after which the reviewer"
            " made no further attempt to read on: a Grep, Bash or diff read that recovered the content is not seen.",
            "code/other: calls=12 later_offset_read 50.0% (6/12); covered_after 25.0% (3/12);"
            " neither (no later offset Read, and not covered by later Reads) 33.3% (4/12)",
            "prose (instruction and other_prose; instruction is matched by path, whatever the extension): calls=5"
            " later_offset_read insufficient (2/5); covered_after insufficient (1/5);"
            " neither (no later offset Read, and not covered by later Reads) insufficient (2/5)",
            "diff handoff (the review diff, not a reviewed file): calls=0 later_offset_read no data (0/0);"
            " covered_after no data (0/0); neither (no later offset Read, and not covered by later Reads) no data (0/0)",
            "",
            "## Read share of reviewer spend, a share of modeled billed weight and not of tokens (12 reviewer windows)",
            "Read weight over billed weight: 20.0% (4,000.0/20,000.0)",
            "  of Read weight, files over 1,000 lines: 25.0% (1,000.0/4,000.0)",
            "  of Read weight, code/other reviewed files over 1,000 lines: 15.0% (600.0/4,000.0)",
            "  of Read weight, diff handoffs over 1,000 lines: 6.0% (240.0/4,000.0)",
            "  of Read weight, files of unknown size: 12.5% (500.0/4,000.0)",
            "sums: billed_weight=20,000.0 read_weight=4,000.0",
            "",
            "## By reviewer type, counts only (windows counts every reviewer window and the other counts cover reviewed"
            " files, not diff handoffs; agent types this repo does not track are folded into one withheld row)",
            "TOTAL: windows=12 partial=10 refused=4 larger_than_one_call=17",
            "ciso-reviewer: windows=3 partial=3 refused=0 larger_than_one_call=3",
            "staff-backend-engineer: windows=7 partial=6 refused=3 larger_than_one_call=12",
            f"{_WITHHELD}: windows=2 partial=1 refused=1 larger_than_one_call=2",
            "",
            "## Main-thread Reads inside review-round windows, counts only",
            "code-review: round_windows=3 read_calls=7 whole_file=5 targeted=2",
            "  reviewed-file whole-file calls by outcome: refused_over_limit=0 other_error=0 size_unknown=0"
            " partial_token_cap=0 complete_allow_large=0 complete=2 partial_unflagged=1",
            "  reviewed-file whole-file calls by file size: up_to_1000=2 1001_to_2000=0 over_2000=1 unknown=0",
            "  diff-handoff whole-file calls: 1",
            "plan-review: round_windows=1 read_calls=1 whole_file=1 targeted=0",
            "  reviewed-file whole-file calls by outcome: refused_over_limit=0 other_error=0 size_unknown=1"
            " partial_token_cap=0 complete_allow_large=0 complete=0 partial_unflagged=0",
            "  reviewed-file whole-file calls by file size: up_to_1000=0 1001_to_2000=0 over_2000=0 unknown=1",
            "  diff-handoff whole-file calls: 0",
            "ready-for-review: round_windows=0 read_calls=0 whole_file=0 targeted=0",
            "  reviewed-file whole-file calls by outcome: refused_over_limit=0 other_error=0 size_unknown=0"
            " partial_token_cap=0 complete_allow_large=0 complete=0 partial_unflagged=0",
            "  reviewed-file whole-file calls by file size: up_to_1000=0 1001_to_2000=0 over_2000=0 unknown=0",
            "  diff-handoff whole-file calls: 0",
            "",
            "## Reviewer-yield: main-thread reviewer dispatches in the window"
            " (agent types this repo does not track are folded into one withheld row)",
            "(--until 2026-08-12 does not bound the cited, active and edited counts:"
            " their tool-result and edit indexes are bounded by --since alone.)",
            "reviewer-yield pass: skipped_input_total=2 meta_read_errors=1 reviewer_transcript_read_errors=0",
            "TOTAL: dispatches=14 findings_found=6 zero_finding=6 unclassified=2 findings=15",
            "  findings-found: cited=8 active=12 edited=3 edited_rate 25.0% (3/12)",
            "  zero-finding: cited=3 active=4 edited=1 edited_rate insufficient (1/4)",
            "ciso-reviewer: dispatches=2 findings_found=0 zero_finding=2 unclassified=0 findings=0",
            "  zero-finding: cited=0 active=0 edited=0 edited_rate no data (0/0)",
            "staff-backend-engineer: dispatches=11 findings_found=6 zero_finding=4 unclassified=1 findings=15",
            "  findings-found: cited=8 active=12 edited=3 edited_rate 25.0% (3/12)",
            "  zero-finding: cited=3 active=4 edited=1 edited_rate insufficient (1/4)",
            f"{_WITHHELD}: dispatches=1 findings_found=0 zero_finding=0 unclassified=1 findings=0",
            "",
            "## Review-ledger terminal disposition rows in the window"
            " (disposition rows, not distinct findings: a finding re-raised without --ref counts again)",
            "terminal rows: ADDRESS=30 DEFER=12 SETTLED=8 total=50",
            "ADDRESS share of terminal rows: 60.0% (30/50)",
            "DEFER share of terminal rows: 24.0% (12/50)",
            "sessions with a disposition row=6 covered by the transcript scan=5",
            "ledger files: directory=present read=4 unreadable=1",
            "ledger rows set aside, in the window: id_less_disposition_rows=2 unknown_disposition_rows=1",
            "ledger rows left out of every file read, whatever the row's date or disposition: left_out_disposition=0"
            " left_out_id=1 left_out_ref=0 left_out_decided_by=0 left_out_event_time=3 left_out_session_id=0",
            "",
            "## Comparability: reviewer windows by harness version and by model",
            "harness version: 2.0.9=3 2.1.0=8 other=1",
            "model: claude-opus-5=2 claude-sonnet-5=9 other=1",
            "",
            "## Diagnostics (calls are counted over every role, diff handoffs included)",
            "unexplained partials (partial_unflagged on files of up to 2,000 lines): 2",
            "notice agreement: partial_token_cap calls with no read_truncation_notice=1;"
            " notices naming neither a partial_token_cap nor a size_unknown call=0;"
            " notices naming a size_unknown call=5",
            "size_unknown by reason: multi_result_record=5 tool_use_result_not_a_dict=0 file_not_a_dict=0"
            " file_path_mismatch=0 line_field_invalid=1 truncation_flag_invalid=0 start_after_first_line=0"
            " lines_exceed_total=0",
            "all roles: other_error=7 unrecognised_limit_error=1",
            "skill-fidelity-reviewer windows left out, in the window: 1",
            "reviewer windows with no timestamped record, whatever the window: 2",
        ]


_BELOW_FLOOR = 9
_AT_FLOOR = 10


def _accumulated_report(sessions: list[tuple[list[dict], list[list[dict]]]], capsys) -> str:
    """The report over `sessions`, each a main-thread record list and its reviewer windows, with empty yield and ledger."""
    totals = reviewer_reads._Totals()
    seen = read_cost._SeenIds()
    for main_records, windows in sessions:
        reviewer_reads._accumulate_session(
            totals, seen, main_records, [(_TRACKED_REVIEWER, window) for window in windows],
            pricing._cache_read_equivalent_weights(), _SINCE_TS, _UNTIL_EPOCH, frozenset({_TRACKED_REVIEWER}),
        )
    empty_ledger = ledger_dispositions.LedgerDispositionCounts(
        directory_state="absent", files_read=0, unreadable_files=0,
        terminal_by_disposition={"ADDRESS": 0, "DEFER": 0, "SETTLED": 0}, id_less_disposition_rows=0,
        unknown_disposition_rows=0, left_out_by_field=dict.fromkeys(
            ("disposition", "id", "ref", "decided_by", "event_time", "session_id"), 0,
        ),
        sessions_with_disposition_row=0, sessions_covered_by_scan=0,
    )
    empty_yield = reviewer_reads._YieldPass(rows={}, skipped_input_total=0, meta_read_errors=0, transcript_read_errors=0)
    return "\n".join(_print_report(totals, empty_yield, empty_ledger, capsys))


class TestPrintedPopulations:
    """Each printed figure covers the population its heading names, so a diff handoff moves only the all-roles figures."""

    @staticmethod
    def _diff_handoff_only_window() -> list[dict]:
        def diff_path(name: str) -> str:
            return f"{_DIFF_HANDOFF_DIR}/{name}.diff"

        size_unknown_call = [
            _turn("m3", [_read_use("r3", diff_path("size-unknown"))]),
            _read_result("r3", "x", tool_use_result=None),
        ]
        return [
            *_read_exchange("m1", "r1", diff_path("partial-unflagged"), num_lines=5, total_lines=9),
            *_read_exchange("m2", "r2", diff_path("partial-token-cap"), num_lines=5, total_lines=9000, truncated=True),
            *size_unknown_call,
            _read_truncation_notice("r3"),
            *_failed_read_exchange("m4", "r4", diff_path("unrecognised"), "The file is too large to read"),
            *_failed_read_exchange(
                "m5", "r5", diff_path("refused"), "File content (51.2KB) exceeds maximum allowed size (50KB)",
            ),
            *_read_exchange("m6", "r6", diff_path("complete"), num_lines=9, total_lines=9),
            _read_truncation_notice("r6"),
        ]

    def test_diff_handoff_calls_move_the_all_roles_diagnostics_and_leave_the_reviewed_file_figures_at_zero(self, capsys):
        report = _accumulated_report([([], [self._diff_handoff_only_window()])], capsys)

        assert "unexplained partials (partial_unflagged on files of up to 2,000 lines): 1" in report
        assert _printed_line(report, "notice agreement:") == (
            "notice agreement: partial_token_cap calls with no read_truncation_notice=1;"
            " notices naming neither a partial_token_cap nor a size_unknown call=1;"
            " notices naming a size_unknown call=1"
        )
        assert " tool_use_result_not_a_dict=1 " in _printed_line(report, "size_unknown by reason:")
        assert _printed_line(report, "all roles:") == "all roles: other_error=1 unrecognised_limit_error=1"
        assert _printed_line(report, "pooled:") == (
            "pooled: partial no data (0/0); refused no data (0/0); partial or refused no data (0/0)"
        )
        assert _printed_line(report, "outside the denominator,") == (
            "outside the denominator, reviewed files only: other_error=0 size_unknown=0"
        )
        assert _printed_line(report, "TOTAL: windows=") == "TOTAL: windows=1 partial=0 refused=0 larger_than_one_call=0"
        assert _printed_line(report, f"{_TRACKED_REVIEWER}: windows=") == (
            f"{_TRACKED_REVIEWER}: windows=1 partial=0 refused=0 larger_than_one_call=0"
        )

    def test_sessions_count_every_scoped_transcript_whatever_the_window_of_its_records(self, capsys):
        before_window = [_turn("m0", ts=_BEFORE_WINDOW)]
        out_of_window_reviewer = [_turn("a0", ts=_BEFORE_WINDOW)]
        in_window_reviewer = [_turn("a1")]

        report = _accumulated_report(
            [(before_window, []), (before_window, [in_window_reviewer, out_of_window_reviewer]), ([], [])], capsys,
        )

        assert _printed_line(report, "sessions=").startswith("sessions=3 reviewer_windows=1 ")

    def test_a_transcript_dated_before_the_window_still_counts_as_a_session_in_the_command_report(
        self, fake_projects, stub_repo_tracked_agent_types, monkeypatch, capsys,
    ):
        stub_repo_tracked_agent_types(_TRACKED_REVIEWER)
        args, _calls = _reviewer_reads_args(monkeypatch)
        for session in ("session-main", "session-other"):
            _write_jsonl(fake_projects / f"{session}.jsonl", [_turn(f"m-{session}", ts=_BEFORE_WINDOW)])
        _reviewer_window(fake_projects, "agent-in-window", [_turn("a1")])

        report = _report_text(args, fake_projects, capsys)

        assert _printed_line(report, "sessions=").startswith("sessions=2 reviewer_windows=1 ")


class TestRateMarkers:
    @pytest.mark.parametrize(
        ("numerator", "denominator", "expected"),
        [
            (0, 0, "no data (0/0)"), (2, _BELOW_FLOOR, "insufficient (2/9)"), (0, _BELOW_FLOOR, "insufficient (0/9)"),
            (3, _AT_FLOOR, "30.0% (3/10)"), (0, _AT_FLOOR, "0.0% (0/10)"), (1_234, 2_000, "61.7% (1,234/2,000)"),
        ],
    )
    def test_a_count_rate_prints_no_data_insufficient_or_a_percentage_with_its_counts(
        self, numerator, denominator, expected,
    ):
        assert reviewer_reads._rate(numerator, denominator) == expected

    @pytest.mark.parametrize(
        ("part", "whole", "windows", "expected"),
        [
            (0.0, 0.0, 0, "no data (0/0)"), (0.0, 0.0, 50, "no data (0/0)"),
            (100.0, 400.0, _BELOW_FLOOR, "insufficient (100.0/400.0)"),
            (100.0, 400.0, 0, "insufficient (100.0/400.0)"), (100.0, 400.0, _AT_FLOOR, "25.0% (100.0/400.0)"),
        ],
    )
    def test_a_weight_share_takes_the_floor_on_its_reviewer_windows(self, part, whole, windows, expected):
        assert reviewer_reads._weight_share(part, whole, windows) == expected

    def test_the_insufficient_label_is_reviewer_yields(self):
        assert reviewer_yield._REVIEWER_YIELD_INSUFFICIENT == "insufficient"
        assert reviewer_reads._rate(1, 2).startswith("insufficient (")

    @pytest.mark.parametrize(
        ("count", "expected_pooled"),
        [
            (0, "pooled: partial no data (0/0); refused no data (0/0); partial or refused no data (0/0)"),
            (_BELOW_FLOOR, "pooled: partial insufficient (9/9); refused insufficient (0/9);"
                           " partial or refused insufficient (9/9)"),
            (_AT_FLOOR, "pooled: partial 100.0% (10/10); refused 0.0% (0/10); partial or refused 100.0% (10/10)"),
        ],
    )
    def test_the_headline_rates_at_zero_below_the_floor_and_at_it(self, count, expected_pooled, capsys):
        totals = reviewer_reads._Totals()
        totals.headline.update({("code/other", "denominator"): count, ("code/other", "partial"): count})

        reviewer_reads._print_headline(totals)

        assert _printed_line(capsys.readouterr().out, "pooled:") == expected_pooled

    @pytest.mark.parametrize(
        ("count", "expected_prefix"),
        [
            (0, "code/other: calls=0 later_offset_read no data (0/0);"),
            (_BELOW_FLOOR, "code/other: calls=9 later_offset_read insufficient (9/9);"),
            (_AT_FLOOR, "code/other: calls=10 later_offset_read 100.0% (10/10);"),
        ],
    )
    def test_the_follow_up_rates_at_zero_below_the_floor_and_at_it(self, count, expected_prefix, capsys):
        totals = reviewer_reads._Totals()
        totals.follow_up.update({("code/other", "calls"): count, ("code/other", "later_offset_read"): count})

        reviewer_reads._print_follow_up(totals)

        assert _printed_line(capsys.readouterr().out, "code/other:").startswith(expected_prefix)

    @pytest.mark.parametrize(
        ("windows", "expected"),
        [
            (0, "Read weight over billed weight: insufficient (50.0/100.0)"),
            (_BELOW_FLOOR, "Read weight over billed weight: insufficient (50.0/100.0)"),
            (_AT_FLOOR, "Read weight over billed weight: 50.0% (50.0/100.0)"),
        ],
    )
    def test_the_read_share_takes_the_floor_on_reviewer_windows(self, windows, expected, capsys):
        totals = reviewer_reads._Totals(reviewer_windows=windows, billed_weight=100.0, read_weight=50.0)

        reviewer_reads._print_read_share(totals)

        assert _printed_line(capsys.readouterr().out, "Read weight over billed weight:") == expected

    def test_the_read_share_with_no_billed_weight_prints_no_data(self, capsys):
        reviewer_reads._print_read_share(reviewer_reads._Totals(reviewer_windows=_AT_FLOOR))

        assert _printed_line(capsys.readouterr().out, "Read weight over billed weight:") == (
            "Read weight over billed weight: no data (0/0)"
        )

    @pytest.mark.parametrize(
        ("total", "expected_address_line"),
        [
            (0, "ADDRESS share of terminal rows: no data (0/0)"),
            (_BELOW_FLOOR, "ADDRESS share of terminal rows: insufficient (9/9)"),
            (_AT_FLOOR, "ADDRESS share of terminal rows: 100.0% (10/10)"),
        ],
    )
    def test_the_ledger_shares_at_zero_below_the_floor_and_at_it(self, total, expected_address_line, capsys):
        counts = ledger_dispositions.LedgerDispositionCounts(
            directory_state="present", files_read=1, unreadable_files=0,
            terminal_by_disposition={"ADDRESS": total, "DEFER": 0, "SETTLED": 0}, id_less_disposition_rows=0,
            unknown_disposition_rows=0, left_out_by_field=dict.fromkeys(
                ("disposition", "id", "ref", "decided_by", "event_time", "session_id"), 0,
            ),
            sessions_with_disposition_row=0, sessions_covered_by_scan=0,
        )

        reviewer_reads._print_ledger(counts)

        assert _printed_line(capsys.readouterr().out, "ADDRESS share") == expected_address_line

    @pytest.mark.parametrize(
        ("active", "expected_rate"),
        [(0, "no data (0/0)"), (_BELOW_FLOOR, "insufficient (1/9)"), (_AT_FLOOR, "10.0% (1/10)")],
    )
    def test_the_yield_edited_rate_at_zero_below_the_floor_and_at_it(self, active, expected_rate, capsys):
        yield_pass = reviewer_reads._YieldPass(
            rows={_TRACKED_REVIEWER: Counter({
                "dispatches": 1, "findings_found": 1, ("findings-found", "active"): active,
                ("findings-found", "edited"): min(active, 1),
            })},
            skipped_input_total=0, meta_read_errors=0, transcript_read_errors=0,
        )

        reviewer_reads._print_yield(yield_pass, _UNTIL_EPOCH)

        lines = [line for line in capsys.readouterr().out.splitlines() if line.startswith("  findings-found:")]
        assert lines[0].endswith(f"edited_rate {expected_rate}")

    @pytest.mark.parametrize(
        ("findings", "expected_figure"),
        [
            pytest.param(1_000_000, "findings=1,000,000", id="at_the_ceiling"),
            pytest.param(1_000_001, "findings=over 1,000,000", id="past_the_ceiling"),
            pytest.param(10**5000, "findings=over 1,000,000", id="past_the_interpreters_digit_limit"),
        ],
    )
    def test_a_findings_count_prints_in_a_closed_width(self, findings, expected_figure, capsys):
        counts = Counter(dispatches=1, findings_found=1, total_findings=findings)
        yield_pass = reviewer_reads._YieldPass(
            rows={_TRACKED_REVIEWER: counts}, skipped_input_total=0, meta_read_errors=0, transcript_read_errors=0,
        )

        reviewer_reads._print_yield(yield_pass, _UNTIL_EPOCH)

        printed = capsys.readouterr().out
        assert expected_figure in _printed_line(printed, "TOTAL: dispatches=")
        assert expected_figure in _printed_line(printed, f"{_TRACKED_REVIEWER}: dispatches=")
        assert len(printed) < 1_000

    def test_an_empty_report_prints_every_rate_as_no_data_and_every_count_as_zero(self, capsys):
        empty_ledger = ledger_dispositions.LedgerDispositionCounts(
            directory_state="absent", files_read=0, unreadable_files=0,
            terminal_by_disposition={"ADDRESS": 0, "DEFER": 0, "SETTLED": 0}, id_less_disposition_rows=0,
            unknown_disposition_rows=0, left_out_by_field=dict.fromkeys(
                ("disposition", "id", "ref", "decided_by", "event_time", "session_id"), 0,
            ),
            sessions_with_disposition_row=0, sessions_covered_by_scan=0,
        )
        yield_pass = reviewer_reads._YieldPass(rows={}, skipped_input_total=0, meta_read_errors=0, transcript_read_errors=0)

        report = "\n".join(_print_report(reviewer_reads._Totals(), yield_pass, empty_ledger, capsys))

        assert "pooled: partial no data (0/0); refused no data (0/0); partial or refused no data (0/0)" in report
        assert "Read weight over billed weight: no data (0/0)" in report
        assert "ADDRESS share of terminal rows: no data (0/0)" in report
        assert "TOTAL: windows=0 partial=0 refused=0 larger_than_one_call=0" in report
        assert "TOTAL: dispatches=0 findings_found=0 zero_finding=0 unclassified=0 findings=0" in report
        assert "ledger files: directory=absent read=0 unreadable=0" in report
        assert "harness version:" in report.splitlines()


class TestReviewerYieldSection:
    def _seed(self, fake_projects):
        _write_jsonl(fake_projects / "session-main.jsonl", [
            _turn("m0", [_agent_use("d1", "staff-LEAKSENTINEL-untracked")]),
        ])

    def test_the_yield_pass_receives_the_window_and_the_next_days_start_and_folds_untracked_names(
        self, fake_projects, stub_repo_tracked_agent_types, monkeypatch, capsys,
    ):
        stub_repo_tracked_agent_types(_TRACKED_REVIEWER)
        args, _calls = _reviewer_reads_args(monkeypatch)
        self._seed(fake_projects)
        received = {}

        def fake_yield_data(session_iter, since_ts=None, until_ts=None):
            received.update(since_ts=since_ts, until_ts=until_ts, sessions=len(list(session_iter)))
            return {
                "agg": {
                    "staff-LEAKSENTINEL-untracked": {
                        "dispatches": 2, "findings_found": 1, "zero_finding": 1, "unclassified": 0, "total_findings": 4,
                    },
                    "staff-LEAKSENTINEL-other": {
                        "dispatches": 1, "findings_found": 0, "zero_finding": 0, "unclassified": 1, "total_findings": 0,
                    },
                },
                "agg2": {("staff-LEAKSENTINEL-untracked", "findings-found"): {"cited": 1, "active": 1, "edited": 1}},
                "meta_read_errors": 0, "transcript_read_errors": 0, "subagent_spawns": 0, "sidechain_turns": 0,
            }

        monkeypatch.setattr(reviewer_yield, "compute_reviewer_yield_data", fake_yield_data)

        report = _report_text(args, fake_projects, capsys)

        assert received == {"since_ts": _SINCE_TS, "until_ts": _UNTIL_EPOCH, "sessions": 1}
        assert f"{_WITHHELD}: dispatches=3 findings_found=1 zero_finding=1 unclassified=1 findings=4" in report
        assert "  findings-found: cited=1 active=1 edited=1 edited_rate insufficient (1/1)" in report
        assert "LEAKSENTINEL" not in report
        assert (
            "(--until 2026-08-12 does not bound the cited, active and edited counts:"
            " their tool-result and edit indexes are bounded by --since alone.)"
        ) in report

    @pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses file permission bits")
    def test_the_yield_passs_gap_counter_prints_on_its_own_line_and_not_in_the_skipped_input_line(
        self, fake_projects, stub_repo_tracked_agent_types, monkeypatch, capsys,
    ):
        stub_repo_tracked_agent_types(_TRACKED_REVIEWER)
        args, _calls = _reviewer_reads_args(monkeypatch)
        fake_projects.chmod(0o000)
        try:
            report = _report_text(args, fake_projects, capsys)
        finally:
            fake_projects.chmod(0o700)

        assert "unreadable_project_dirs=1 " in _printed_line(report, "skipped input:")
        assert _printed_line(report, "reviewer-yield pass:") == (
            "reviewer-yield pass: skipped_input_total=1 meta_read_errors=0 reviewer_transcript_read_errors=0"
        )

    def test_a_dispatch_with_no_meta_sidecar_is_excluded_from_the_yield_section(
        self, fake_projects, stub_repo_tracked_agent_types, monkeypatch, capsys,
    ):
        stub_repo_tracked_agent_types(_TRACKED_REVIEWER)
        args, _calls = _reviewer_reads_args(monkeypatch)
        _write_jsonl(fake_projects / "session-main.jsonl", [_turn("m0", [_agent_use("d1", _TRACKED_REVIEWER)])])

        report = _report_text(args, fake_projects, capsys)

        assert "TOTAL: dispatches=0 findings_found=0 zero_finding=0 unclassified=0 findings=0" in report

    def test_a_yield_pass_that_could_not_complete_prints_one_fixed_notice_and_no_rows(self, capsys):
        yield_pass = reviewer_reads._YieldPass(
            rows={}, skipped_input_total=3, meta_read_errors=0, transcript_read_errors=0, completed=False,
        )

        reviewer_reads._print_yield(yield_pass, _UNTIL_EPOCH)

        assert capsys.readouterr().out.splitlines()[3:] == [
            "reviewer-yield pass: not completed, because the shared reviewer-yield code raised an AttributeError,"
            " TypeError or ValueError, so no yield rows are printed",
        ]

    def test_a_sidecar_the_shared_yield_code_cannot_read_leaves_the_rest_of_the_report_intact(
        self, fake_projects, stub_repo_tracked_agent_types, monkeypatch, capsys,
    ):
        stub_repo_tracked_agent_types(_TRACKED_REVIEWER)
        args, _calls = _reviewer_reads_args(monkeypatch)
        _write_jsonl(fake_projects / "session-main.jsonl", [_turn("m0", [_agent_use("dispatch-agent-a", _TRACKED_REVIEWER)])])
        _reviewer_window(fake_projects, "agent-a", [_turn("a1", [])])
        (fake_projects / "session-main" / "subagents" / "agent-a.meta.json").write_text('["not", "an", "object"]')

        report = _report_text(args, fake_projects, capsys)

        assert "reviewer-yield pass: not completed" in report
        assert "## Diagnostics" in report
