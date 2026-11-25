"""Tests for the capture-scope columns of transcript_analysis/pr_cost_export.py's redacted export rows."""
import pytest
from transcript_analysis import pr_cost

from ._pr_cost_helpers import _export_ledger_rows, _sample_pr_cost_row


class TestPrCostExportCaptureScopeColumns:
    @pytest.mark.parametrize("cell,expected_export", [
        pytest.param("2026-03-04T05:06:07Z", "2026-03-04", id="writer-form-truncated-to-its-date"),
        pytest.param("", "", id="empty-stays-empty"),
    ])
    def test_earliest_surviving_activity_at_exports_as_its_date(
        self, tmp_path, fake_projects, monkeypatch, cell, expected_export,
    ):
        row, _provenance, _text = _export_ledger_rows(
            tmp_path, monkeypatch, [_sample_pr_cost_row(earliest_surviving_activity_at=cell)],
        )

        assert row["earliest_surviving_activity_at"] == expected_export

    @pytest.mark.parametrize("capture_scope", ["repo", "glob", ""])
    def test_capture_scope_exports_unchanged(self, tmp_path, fake_projects, monkeypatch, capture_scope):
        row, _provenance, _text = _export_ledger_rows(
            tmp_path, monkeypatch, [_sample_pr_cost_row(capture_scope=capture_scope)],
        )

        assert row["capture_scope"] == capture_scope

    @pytest.mark.parametrize("absence", ["", *sorted(pr_cost._ROUNDS_ABSENCES)])
    def test_a_known_review_rounds_absence_exports_unchanged(self, tmp_path, fake_projects, monkeypatch, absence):
        row, _provenance, _text = _export_ledger_rows(
            tmp_path, monkeypatch, [_sample_pr_cost_row(review_rounds_absence=absence)],
        )

        assert row["review_rounds_absence"] == absence

    def test_an_unknown_shape_valid_review_rounds_absence_exports_as_unrecognized_without_its_raw_text(
        self, tmp_path, fake_projects, monkeypatch,
    ):
        unknown_absence = "zzfuturereasonzz"
        row, _provenance, text = _export_ledger_rows(
            tmp_path, monkeypatch, [_sample_pr_cost_row(review_rounds_absence=unknown_absence)],
        )

        assert row["review_rounds_absence"] == "unrecognized"
        assert unknown_absence not in text
