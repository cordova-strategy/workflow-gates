"""review_ledger's reader and index on a line that makes json.loads raise past a decode error."""
import pytest
from transcript_analysis import review_ledger

from ._ledger_reader_helpers import HOSTILE_LINES, LINES_OVER_DECODER_LIMITS, fake_transcript_path
from .conftest import _ledger_row, _write_branch_ledger_file, _write_ledger_file

pytestmark = pytest.mark.usefixtures("default_int_str_digit_limit")


def _append_line(ledger_path, line):
    with ledger_path.open("a") as ledger_file:
        ledger_file.write(line + "\n")


class TestReaderFlag:
    @pytest.mark.parametrize(("line", "decoder_exception"), LINES_OVER_DECODER_LIMITS)
    def test_the_error_propagates_by_default_so_a_caller_can_count_the_file_unreadable(
        self, tmp_path, line, decoder_exception,
    ):
        ledger_path = _write_ledger_file(tmp_path, "sess-1", [_ledger_row(round=1, disposition="ADDRESS")])
        _append_line(ledger_path, line)

        with pytest.raises(decoder_exception):
            review_ledger._read_ledger_rows_from_file(ledger_path)

    @pytest.mark.parametrize("line", HOSTILE_LINES)
    def test_the_line_is_skipped_and_its_neighbours_are_kept_when_asked(
        self, tmp_path, capfd, caplog, recwarn, line,
    ):
        ledger_path = _write_ledger_file(tmp_path, "sess-1", [_ledger_row(round=1, disposition="ADDRESS")])
        _append_line(ledger_path, line)
        _append_line(ledger_path, '{"round": 2, "disposition": "DEFER"}')

        rows, opened = review_ledger._read_ledger_rows_from_file(ledger_path, skip_lines_over_decoder_limits=True)

        assert opened is True
        assert [row["round"] for row in rows] == [1, 2]
        captured = capfd.readouterr()
        assert captured.out == "" and captured.err == ""
        assert caplog.records == [] and len(recwarn) == 0


@pytest.mark.parametrize("line", HOSTILE_LINES)
class TestSessionLookupOverAFileWithSuchALine:
    def test_the_rows_around_the_line_and_in_the_other_files_are_kept(self, tmp_path, line):
        poisoned_path = _write_ledger_file(tmp_path, "sess-1", [_ledger_row(round=1, disposition="ADDRESS")])
        _append_line(poisoned_path, line)
        _append_line(poisoned_path, '{"round": 2, "disposition": "DEFER"}')
        _write_branch_ledger_file(
            tmp_path, "b" * 64, [_ledger_row(round=3, disposition="DEFER", session_id="sess-1")],
        )

        entries, any_file_found = review_ledger._read_ledger_row_entries_for_session(fake_transcript_path(tmp_path, "sess-1"))

        assert any_file_found is True
        assert sorted(row["round"] for _, row in entries) == [1, 2, 3]

    def test_a_file_holding_only_the_line_is_present_and_empty(self, tmp_path, line):
        ledger_path = _write_ledger_file(tmp_path, "sess-1", [])
        _append_line(ledger_path, line)

        entries, any_file_found = review_ledger._read_ledger_row_entries_for_session(fake_transcript_path(tmp_path, "sess-1"))

        assert entries == []
        assert any_file_found is True

    def test_the_file_is_parsed_once_across_two_lookups_sharing_an_index(self, tmp_path, monkeypatch, line):
        poisoned_path = _write_ledger_file(tmp_path, "sess-1", [_ledger_row(round=1, disposition="ADDRESS")])
        _append_line(poisoned_path, line)
        real_read = review_ledger._read_ledger_rows_from_file
        parsed_paths = []

        def _counting_read(ledger_path, **reader_options):
            parsed_paths.append(ledger_path)
            return real_read(ledger_path, **reader_options)

        monkeypatch.setattr(review_ledger, "_read_ledger_rows_from_file", _counting_read)
        session_jsonl = fake_transcript_path(tmp_path, "sess-1")
        ledger_indexes = {}

        for _ in range(2):
            entries, _ = review_ledger._read_ledger_row_entries_for_session(session_jsonl, ledger_indexes)
            assert [row["round"] for _, row in entries] == [1]

        assert parsed_paths == [poisoned_path]
