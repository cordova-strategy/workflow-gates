"""Tests for the capture-scope columns of transcript_analysis/pr_cost_ledger.py: review_rounds_absence,
earliest_surviving_activity_at and capture_scope, which the parser checks per cell, and the short-row hint
that follows the file header's missing columns. The rest of the ledger's format lives in
test_transcript_pr_cost_ledger.py."""
import pytest
from transcript_analysis import pr_cost, pr_cost_ledger

from ._pr_cost_helpers import (
    _APPEND_TAB_HINT,
    _EMPTY_SCOPE_RESCOPE_HINT,
    _GLOB_RESCOPE_HINT,
    _PRE_INVALID_USAGE_HEADER_LINE,
    _PRE_REVIEW_ROUNDS_HEADER_LINE,
    _current_line_with_cell,
    _pre_invalid_usage_row_line,
    _pre_review_rounds_row_line,
    _sample_pr_cost_row,
)

_CELL_TEXT_MARKER = "zzcellmarkerzz"  # passes the absence key shape; must never reach a refusal message


def _current_ledger_text_with_cell(column: str, cell: str) -> str:
    return pr_cost_ledger._PR_COST_LEDGER_HEADER_LINE + "\n" + _current_line_with_cell(column, cell) + "\n"


def _parse_one_row_with_cell(column: str, cell: str) -> dict:
    return pr_cost_ledger._parse_pr_cost_ledger_file_text(_current_ledger_text_with_cell(column, cell))[0]


class TestCaptureScopeColumn:
    @pytest.mark.parametrize("capture_scope", [*pr_cost_ledger._PR_COST_CAPTURE_SCOPE_VALUES, ""])
    def test_a_known_value_and_the_empty_legacy_value_round_trip(self, capture_scope):
        row = _sample_pr_cost_row(capture_scope=capture_scope)
        line = pr_cost_ledger._format_pr_cost_ledger_row(row)

        assert pr_cost_ledger._parse_pr_cost_ledger_row_cells(line.split("\t"), 2) == row

    def test_the_closed_set_is_repo_and_glob(self):
        assert pr_cost_ledger._PR_COST_CAPTURE_SCOPE_VALUES == ("repo", "glob")

    @pytest.mark.parametrize("unknown_value", ["Repo", "repos", "unknown", _CELL_TEXT_MARKER])
    def test_an_unknown_value_is_refused_without_echoing_the_cell(self, unknown_value):
        with pytest.raises(pr_cost_ledger._PrCostLedgerParseError) as exc_info:
            _parse_one_row_with_cell("capture_scope", unknown_value)

        assert str(exc_info.value) == "line 2: unknown capture_scope"


class TestReviewRoundsAbsenceColumn:
    @pytest.mark.parametrize(
        "absence",
        ["", *sorted(pr_cost._ROUNDS_ABSENCES), "zz-a-future-writers-code"],
        ids=lambda absence: absence or "empty",
    )
    def test_empty_every_writer_code_and_an_unknown_shape_valid_word_parse(self, absence):
        row = _parse_one_row_with_cell("review_rounds_absence", absence)

        assert row["review_rounds_absence"] == absence

    @pytest.mark.parametrize("malformed_cell", [
        pytest.param(f"Upper {_CELL_TEXT_MARKER}", id="uppercase-and-space"),
        pytest.param(f"-{_CELL_TEXT_MARKER}", id="leading-hyphen"),
        pytest.param(f"{_CELL_TEXT_MARKER}!", id="punctuation"),
        pytest.param("a" * 65, id="over-64-characters"),
    ])
    def test_a_shape_invalid_value_is_refused_without_echoing_the_cell(self, malformed_cell):
        with pytest.raises(pr_cost_ledger._PrCostLedgerParseError) as exc_info:
            _parse_one_row_with_cell("review_rounds_absence", malformed_cell)

        assert str(exc_info.value) == "line 2: malformed review_rounds_absence"


class TestEarliestSurvivingActivityAtColumn:
    @pytest.mark.parametrize("cell", ["", "2026-03-04T05:06:07Z"], ids=["empty", "writer-form"])
    def test_empty_and_the_writers_form_parse(self, cell):
        row = _parse_one_row_with_cell("earliest_surviving_activity_at", cell)

        assert row["earliest_surviving_activity_at"] == cell

    @pytest.mark.parametrize("malformed_cell", [
        pytest.param("2026-03-04 05:06:07Z", id="space-separator"),
        pytest.param("2026-03-04T05:06:07", id="missing-z"),
        pytest.param("2026-03-04T05:06:07.123Z", id="fractional-second"),
        pytest.param("2026-03-04T05:06:07+00:00", id="utc-offset"),
        pytest.param("2026-13-04T05:06:07Z", id="writer-shape-with-an-impossible-month"),
        pytest.param("2026-03-04T05:06:07Z" + _CELL_TEXT_MARKER, id="trailing-text"),
    ])
    def test_any_other_form_is_refused_without_echoing_the_cell(self, malformed_cell):
        with pytest.raises(pr_cost_ledger._PrCostLedgerParseError) as exc_info:
            _parse_one_row_with_cell("earliest_surviving_activity_at", malformed_cell)

        assert str(exc_info.value) == "line 2: malformed earliest_surviving_activity_at"


class TestShortRowHintFollowsTheMissingColumns:
    @staticmethod
    def _shortfall_message(header_line: str, row_line: str, shortfall: int) -> str:
        cells = row_line.split("\t")
        text = header_line + "\n" + "\t".join(cells[:-shortfall]) + "\n"
        with pytest.raises(pr_cost_ledger._PrCostLedgerParseError) as exc_info:
            pr_cost_ledger._parse_pr_cost_ledger_file_text(text)
        return str(exc_info.value)

    def test_a_pre_invalid_usage_row_two_cells_short_gets_no_hint(self):
        message = self._shortfall_message(_PRE_INVALID_USAGE_HEADER_LINE, _pre_invalid_usage_row_line(), 2)

        assert message.endswith("got " + str(len(_PRE_INVALID_USAGE_HEADER_LINE.split("\t")) - 2))

    def test_a_pre_review_rounds_row_two_cells_short_gets_no_hint(self):
        message = self._shortfall_message(_PRE_REVIEW_ROUNDS_HEADER_LINE, _pre_review_rounds_row_line(), 2)

        assert message.endswith("got " + str(len(_PRE_REVIEW_ROUNDS_HEADER_LINE.split("\t")) - 2))

    def test_a_current_row_one_cell_short_gets_the_append_a_tab_hint(self):
        line = pr_cost_ledger._format_pr_cost_ledger_row(_sample_pr_cost_row())

        message = self._shortfall_message(pr_cost_ledger._PR_COST_LEDGER_HEADER_LINE, line, 1)

        assert message.endswith(_APPEND_TAB_HINT)

    @pytest.mark.parametrize("shortfall", [2, 3, 4])
    def test_a_current_row_short_by_trailing_empty_columns_gets_the_append_n_tabs_hint(self, shortfall):
        line = pr_cost_ledger._format_pr_cost_ledger_row(_sample_pr_cost_row())

        message = self._shortfall_message(pr_cost_ledger._PR_COST_LEDGER_HEADER_LINE, line, shortfall)

        assert message.endswith(f" (if an editor trimmed trailing whitespace, append {shortfall} tabs to this line)")

    def test_a_current_row_short_past_the_empty_defaults_gets_no_hint(self):
        line = pr_cost_ledger._format_pr_cost_ledger_row(_sample_pr_cost_row())

        message = self._shortfall_message(pr_cost_ledger._PR_COST_LEDGER_HEADER_LINE, line, 5)

        assert "(" not in message


class TestAppendRefusalNamesTheRowsScope:
    _REFUSAL_STEM = (
        "a row for pr_number=1 machine=c0ffee01 already exists -- pass --force with --pr to append a correcting row"
    )

    @pytest.mark.parametrize(("capture_scope", "expected_hint"), [
        pytest.param(pr_cost_ledger._PR_COST_CAPTURE_SCOPE_GLOB, _GLOB_RESCOPE_HINT, id="glob-row-names-the-re-scope"),
        pytest.param(pr_cost_ledger._PR_COST_CAPTURE_SCOPE_REPO, "", id="repo-row-keeps-the-plain-text"),
        pytest.param("", _EMPTY_SCOPE_RESCOPE_HINT, id="legacy-empty-scope-row-names-the-re-scope"),
    ])
    def test_a_duplicate_key_without_force_adds_the_re_scope_hint_for_a_glob_or_legacy_row_and_none_for_a_repo_row(
        self, capture_scope, expected_hint,
    ):
        existing_row = _sample_pr_cost_row(pr_number=1, machine="c0ffee01", capture_scope=capture_scope)

        with pytest.raises(ValueError) as exc_info:
            pr_cost_ledger._append_pr_cost_ledger_row(
                [existing_row], _sample_pr_cost_row(pr_number=1, machine="c0ffee01"), already=existing_row, force=False,
            )

        assert str(exc_info.value) == self._REFUSAL_STEM + expected_hint
