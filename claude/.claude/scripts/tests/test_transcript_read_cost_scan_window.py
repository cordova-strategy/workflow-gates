"""Tests for read_cost._scan_window: one window's reads, turns and billing."""
import pytest
from transcript_analysis import pricing, read_cost

from ._read_cost_helpers import (
    _HUNDRED_TOKEN_TEXT,
    _file_record,
    _read_exchange,
    _scan,
    _turn,
    _weights,
)
from .conftest import (
    _NON_CONVERSATION_CONTENT_RECORD_TYPES,
    _api_request_blob_rec,
    _asst,
    _compact_boundary_rec,
    _edit_use,
    _non_boundary_system_rec,
    _read_result,
    _read_truncation_notice,
    _read_use,
    _user_msg,
)


def _event_for(scan: read_cost._WindowScan, path: str) -> read_cost._ReadEvent:
    return next(event for event in scan.events if event.path == path)


class TestScanWindow:
    def test_turns_count_distinct_message_ids_not_records(self):
        scan = _scan([
            _turn("m1", [_read_use("r1", file_path="/a.py")]),
            _turn("m1"),
            _read_result("r1", _HUNDRED_TOKEN_TEXT),
            _turn("m2"),
            _turn("m2"),
            _turn("m3"),
        ])
        assert len(scan.turn_message_ids) == 3
        assert _event_for(scan, "/a.py").remaining_turns == 2

    def test_compaction_boundary_ends_the_window_a_read_is_resent_in(self):
        scan = _scan([
            _turn("m1", [_read_use("r1", file_path="/a.py")]),
            _read_result("r1", _HUNDRED_TOKEN_TEXT),
            _non_boundary_system_rec(),
            _turn("m2", [_read_use("r2", file_path="/b.py")]),
            _read_result("r2", _HUNDRED_TOKEN_TEXT),
            _compact_boundary_rec(),
            _turn("m3", [_read_use("r3", file_path="/c.py")]),
            _read_result("r3", _HUNDRED_TOKEN_TEXT),
            _turn("m4"),
        ])
        assert len(scan.turn_message_ids) == 4
        # r1 is resent once (turn 2) before the boundary, r2 in the last turn before it is never resent, and r3
        # is resent in the one turn after it. The non-boundary system record changes none of these values and
        # exists so a guard keyed on type == "system" alone fails the /a.py assertion.
        assert _event_for(scan, "/a.py").remaining_turns == 1
        assert _event_for(scan, "/b.py").remaining_turns == 0
        assert _event_for(scan, "/c.py").remaining_turns == 1

    def test_token_estimate_counts_characters_not_bytes_of_a_multibyte_result(self):
        multibyte_text = "é" * 400
        assert len(multibyte_text.encode("utf-8")) == 2 * len(multibyte_text)
        scan = _scan(_read_exchange("m1", "r1", "/a.py", text=multibyte_text))
        assert _event_for(scan, "/a.py").tokens == 400 // read_cost._READ_COST_CHARS_PER_TOKEN

    def test_read_with_no_boundary_after_it_runs_to_the_end_of_the_window(self):
        scan = _scan([
            _turn("m1", [_read_use("r1", file_path="/a.py")]),
            _read_result("r1", _HUNDRED_TOKEN_TEXT),
            _turn("m2"),
            _turn("m3"),
        ])
        assert _event_for(scan, "/a.py").remaining_turns == 2

    @pytest.mark.parametrize("record_type", _NON_CONVERSATION_CONTENT_RECORD_TYPES)
    def test_api_request_blob_adds_no_event_and_is_not_a_repeated_read(self, record_type):
        scan = _scan([
            _turn("m1", [_read_use("r1", file_path="/a.py")]),
            _read_result("r1", _HUNDRED_TOKEN_TEXT),
            _api_request_blob_rec([_read_use("r1", file_path="/a.py")], agent_id="agent-a", record_type=record_type),
            _api_request_blob_rec([_read_use("r2", file_path="/b.py")], agent_id="agent-a", record_type=record_type),
            _api_request_blob_rec(
                [{"type": "tool_result", "tool_use_id": "r2", "content": _HUNDRED_TOKEN_TEXT}], record_type=record_type,
            ),
        ])
        assert [event.path for event in scan.events] == ["/a.py"]
        assert scan.repeated_reads == 0

    def test_assistant_record_without_message_id_is_not_a_turn_billed_or_invalid(self):
        id_less_turn = _asst("claude-sonnet-5")
        id_less_turn["message"]["usage"] = {"output_tokens": 1}
        invalid_id_less_turn = _asst("claude-sonnet-5")
        invalid_id_less_turn["message"]["usage"] = {"output_tokens": -1}
        scan = _scan([id_less_turn, invalid_id_less_turn])
        assert len(scan.turn_message_ids) == 0
        assert scan.usage_by_message == {}
        assert scan.invalid_usage_message_ids == frozenset()

    def test_read_without_a_file_path_produces_no_event_and_leaves_its_id_unseen(self):
        seen: set[str] = set()
        pathless_read = {"type": "tool_use", "id": "r1", "name": "Read", "input": {}}
        scan = _scan([_turn("m1", [pathless_read]), _read_result("r1", _HUNDRED_TOKEN_TEXT)], seen)
        assert scan.events == []
        assert scan.repeated_reads == 0
        assert seen == set()

    def test_id_less_read_and_id_less_result_do_not_pair_with_each_other(self):
        seen: set[str] = set()
        id_less_read = {"type": "tool_use", "name": "Read", "input": {"file_path": "/a.py"}}
        id_less_result = _user_msg([{"type": "tool_result", "content": _HUNDRED_TOKEN_TEXT}])
        scan = _scan([_turn("m1", [id_less_read]), id_less_result], seen)
        assert scan.events == []
        assert seen == set()

    @pytest.mark.parametrize("unusable_tool_id", ["", 7, ["r1"], {"id": "r1"}])
    def test_read_with_an_empty_or_non_string_id_produces_no_event_and_leaves_no_id_seen(self, unusable_tool_id):
        seen: set[str] = set()
        scan = _scan([
            _turn("m1", [_read_use(unusable_tool_id, file_path="/a.py")]),
            _read_result(unusable_tool_id, _HUNDRED_TOKEN_TEXT),
        ], seen)
        assert scan.events == []
        assert scan.repeated_reads == 0
        assert seen == set()

    @pytest.mark.parametrize("unusable_result_id", ["", 7, ["r1"], {"id": "r1"}])
    def test_result_with_an_empty_or_non_string_tool_use_id_leaves_a_pending_read_to_its_own_result(
        self, unusable_result_id,
    ):
        seen: set[str] = set()
        stray_result = _user_msg([
            {"type": "tool_result", "tool_use_id": unusable_result_id, "content": _HUNDRED_TOKEN_TEXT},
        ])
        scan = _scan([
            _turn("m1", [_read_use("r1", file_path="/a.py")]),
            stray_result,
            _read_result("r1", "x" * 800),
        ], seen)
        assert [(event.path, event.tokens) for event in scan.events] == [("/a.py", 200)]
        assert seen == {"r1"}

    @pytest.mark.parametrize("unusable_content", [None, "a plain-text user prompt"])
    def test_record_whose_message_content_is_not_a_block_list_is_skipped_without_error(self, unusable_content):
        scan = _scan([
            _user_msg(unusable_content),
            _turn("m1", unusable_content),
            *_read_exchange("m2", "r1", "/a.py"),
        ])
        assert [event.path for event in scan.events] == ["/a.py"]

    def test_id_less_assistant_record_is_no_turn_and_its_read_sits_at_the_previous_turns_index(self):
        id_less_turn = _asst("claude-sonnet-5", content=[_read_use("r1", file_path="/a.py")])
        id_less_turn_after_the_read = _asst("claude-sonnet-5", content=[])
        scan = _scan([
            _turn("m1"), id_less_turn, _read_result("r1", _HUNDRED_TOKEN_TEXT), id_less_turn_after_the_read,
            _turn("m2"),
        ])
        assert scan.turn_message_ids == {"m1", "m2"}
        assert _event_for(scan, "/a.py").remaining_turns == 1

    def test_read_result_without_an_is_error_key_is_counted(self):
        successful_result = _user_msg([{"type": "tool_result", "tool_use_id": "r1", "content": _HUNDRED_TOKEN_TEXT}])
        scan = _scan([_turn("m1", [_read_use("r1", file_path="/a.py")]), successful_result])
        assert _event_for(scan, "/a.py").tokens == 100

    def test_non_dict_content_block_is_skipped_beside_a_valid_read(self):
        scan = _scan([
            _turn("m1", ["stray text", None, _read_use("r1", file_path="/a.py")]),
            _read_result("r1", _HUNDRED_TOKEN_TEXT),
        ])
        assert [event.path for event in scan.events] == ["/a.py"]

    def test_edit_after_the_read_marks_the_read_edited_later(self):
        scan = _scan([
            _turn("m1", [_read_use("r1", file_path="/a.py")]),
            _read_result("r1", _HUNDRED_TOKEN_TEXT),
            _turn("m2", [_edit_use("e1", path="/a.py")]),
        ])
        assert _event_for(scan, "/a.py").edited_later is True

    def test_edit_in_the_same_turn_as_the_read_marks_the_read_edited_later(self):
        scan = _scan([
            _turn("m1", [_read_use("r1", file_path="/a.py"), _edit_use("e1", path="/a.py")]),
            _read_result("r1", _HUNDRED_TOKEN_TEXT),
        ])
        assert _event_for(scan, "/a.py").edited_later is True

    def test_edit_only_before_the_read_or_of_another_path_leaves_the_read_unedited(self):
        scan = _scan([
            _turn("m1", [_edit_use("e1", path="/a.py")]),
            _turn("m2", [_read_use("r1", file_path="/a.py"), _edit_use("e2", path="/other.py")]),
            _read_result("r1", _HUNDRED_TOKEN_TEXT),
        ])
        assert _event_for(scan, "/a.py").edited_later is False

    def test_non_dict_tool_input_is_skipped_without_error(self):
        malformed = {"type": "tool_use", "id": "r1", "name": "Read", "input": ["/a.py"]}
        assert _scan([_turn("m1", [malformed]), _read_result("r1", _HUNDRED_TOKEN_TEXT)]).events == []

    def test_read_with_offset_or_limit_is_not_whole_file(self):
        scan = _scan([
            _turn("m1", [
                _read_use("r1", file_path="/a.py", limit=10),
                _read_use("r2", file_path="/b.py", offset=0),
                _read_use("r3", file_path="/c.py"),
            ]),
            _read_result("r1", _HUNDRED_TOKEN_TEXT),
            _read_result("r2", _HUNDRED_TOKEN_TEXT),
            _read_result("r3", _HUNDRED_TOKEN_TEXT),
        ])
        assert {event.path: event.whole_file for event in scan.events} == {
            "/a.py": False, "/b.py": False, "/c.py": True,
        }

    def test_read_with_only_pages_set_is_whole_file(self):
        pages_only_read = _read_use("r1", file_path="/a.pdf")
        pages_only_read["input"]["pages"] = "1-5"
        scan = _scan([_turn("m1", [pages_only_read]), _read_result("r1", _HUNDRED_TOKEN_TEXT)])
        assert _event_for(scan, "/a.pdf").whole_file is True

    def test_error_and_non_text_results_produce_no_event(self):
        scan = _scan([
            _turn("m1", [
                _read_use("r1", file_path="/a.py"),
                _read_use("r2", file_path="/b.py"),
            ]),
            _read_result("r1", "boom", is_error=True),
            _read_result("r2", [{"type": "image"}]),
        ])
        assert scan.events == []

    def test_text_block_list_result_is_dropped_like_any_non_string_result(self):
        # docs/transcript-analysis.md's read-cost Known limits: a result that is not plain text is left out.
        scan = _scan([
            _turn("m1", [_read_use("r1", file_path="/a.py")]),
            _read_result("r1", [{"type": "text", "text": _HUNDRED_TOKEN_TEXT}]),
        ])
        assert scan.events == []

    def test_tool_use_id_already_seen_in_another_window_is_not_counted_again(self):
        seen: set[str] = set()
        records = [
            _turn("m1", [_read_use("r1", file_path="/a.py")]),
            _read_result("r1", _HUNDRED_TOKEN_TEXT),
        ]
        assert len(_scan(records, seen).events) == 1
        assert _scan(records, seen).events == []

    def test_event_tokens_and_lines_come_from_the_result_text(self):
        scan = _scan([
            _turn("m1", [_read_use("r1", file_path="/a.py")]),
            _read_result("r1", "ab\n" * 7 + "abc"),
        ])
        event = _event_for(scan, "/a.py")
        assert (event.tokens, event.lines) == (6, 8)

    @pytest.mark.parametrize(("result_text", "expected_lines"), [
        ("", 0),
        ("ab", 1),
        ("ab\n", 1),
        ("ab\nab", 2),
        ("ab\nab\n", 2),
    ])
    def test_event_lines_count_the_numbered_lines_whether_or_not_the_result_ends_in_a_newline(
        self, result_text, expected_lines,
    ):
        scan = _scan([
            _turn("m1", [_read_use("r1", file_path="/a.py")]),
            _read_result("r1", result_text),
        ])
        assert _event_for(scan, "/a.py").lines == expected_lines

    @pytest.mark.parametrize(("line_threshold", "row_count", "in_cohort"), [
        (350, 351, True),
        (350, 350, False),
        (800, 801, True),
        (800, 800, False),
    ])
    def test_unterminated_numbered_read_result_lands_in_the_cohort_only_above_the_threshold(
        self, line_threshold, row_count, in_cohort,
    ):
        # The real Read tool prefixes each row with a line number and a tab, and ends the last row without a newline.
        real_shape_result = "\n".join(f"{row_number:6d}\t line {row_number}" for row_number in range(1, row_count + 1))
        scan = _scan([
            _turn("m1", [_read_use("r1", file_path="/a.py")]),
            _read_result("r1", real_shape_result),
        ])

        cohort = read_cost._cohort_figures(scan.events, line_threshold, _weights(), 0.0, 0.0)

        assert cohort.reads == (1 if in_cohort else 0)

    def test_tool_result_of_a_legacy_human_record_is_kept(self):
        human_result = _read_result("r1", _HUNDRED_TOKEN_TEXT)
        human_result["type"] = "human"
        scan = _scan([_turn("m1", [_read_use("r1", file_path="/a.py")]), human_result])
        assert [event.path for event in scan.events] == ["/a.py"]

    @pytest.mark.parametrize(("tool_name", "path_key"), [
        ("Edit", "file_path"),
        ("Write", "file_path"),
        ("MultiEdit", "file_path"),
        ("NotebookEdit", "notebook_path"),
    ])
    def test_each_edit_tool_marks_the_read_edited_later(self, tool_name, path_key):
        edit = {"type": "tool_use", "id": "e1", "name": tool_name, "input": {path_key: "/a.py"}}
        scan = _scan([*_read_exchange("m1", "r1", "/a.py"), _turn("m2", [edit])])
        assert _event_for(scan, "/a.py").edited_later is True

    def test_non_edit_tool_naming_the_path_leaves_the_read_unedited(self):
        grep = {"type": "tool_use", "id": "g1", "name": "Grep", "input": {"file_path": "/a.py"}}
        scan = _scan([*_read_exchange("m1", "r1", "/a.py"), _turn("m2", [grep])])
        assert _event_for(scan, "/a.py").edited_later is False

    def test_failed_edit_still_marks_the_read_edited_later(self):
        scan = _scan([
            *_read_exchange("m1", "r1", "/a.py"),
            _turn("m2", [_edit_use("e1", path="/a.py")]),
            _read_result("e1", "old_string not found", is_error=True),
        ])
        assert _event_for(scan, "/a.py").edited_later is True

    def test_second_boundary_does_not_extend_the_window_of_a_read_before_the_first(self):
        scan = _scan([
            *_read_exchange("m1", "r1", "/a.py"),
            _turn("m2"),
            _compact_boundary_rec(),
            *_read_exchange("m3", "r3", "/b.py"),
            _turn("m4"),
            _compact_boundary_rec(),
            *_read_exchange("m5", "r5", "/c.py"),
            _turn("m6"),
        ])
        assert [_event_for(scan, path).remaining_turns for path in ("/a.py", "/b.py", "/c.py")] == [1, 1, 1]

    def test_edit_after_a_compaction_marks_a_read_before_it_edited_later(self):
        scan = _scan([
            *_read_exchange("m1", "r1", "/a.py"),
            _compact_boundary_rec(),
            _turn("m2", [_edit_use("e1", path="/a.py")]),
        ])
        event = _event_for(scan, "/a.py")
        assert (event.edited_later, event.remaining_turns) == (True, 0)

    def test_synthetic_turn_is_neither_a_turn_nor_usage(self):
        synthetic = _turn("m-synthetic", usage={"output_tokens": 5})
        synthetic["message"]["model"] = pricing._SYNTHETIC_MODEL_ID
        scan = _scan([synthetic, _turn("m1", usage={"output_tokens": 7})])
        assert len(scan.turn_message_ids) == 1
        assert list(scan.usage_by_message) == ["m1"]

    @pytest.mark.parametrize("invalid_usage", [
        {"output_tokens": None},
        {"output_tokens": "5"},
        {"output_tokens": -1},
        {"cache_creation": {"ephemeral_5m_input_tokens": -1}},
        "not-an-object",
    ])
    def test_turn_with_invalid_usage_is_excluded_and_reported(self, invalid_usage):
        scan = _scan([_turn("m1", usage=invalid_usage)])
        assert scan.usage_by_message == {}
        assert scan.invalid_usage_message_ids == {"m1"}
        assert len(scan.turn_message_ids) == 1

    def test_invalid_usage_in_a_later_record_does_not_replace_valid_usage(self):
        good_usage = {"output_tokens": 5}
        scan = _scan([_turn("m1", usage=good_usage), _turn("m1", usage={"output_tokens": -1})])
        assert scan.usage_by_message == {"m1": good_usage}
        assert scan.invalid_usage_message_ids == frozenset()

    def test_valid_usage_in_a_later_record_replaces_invalid_usage(self):
        good_usage = {"output_tokens": 5}
        scan = _scan([_turn("m1", usage={"output_tokens": -1}), _turn("m1", usage=good_usage)])
        assert scan.usage_by_message == {"m1": good_usage}
        assert scan.invalid_usage_message_ids == frozenset()

    def test_record_with_no_usage_after_a_populated_one_keeps_the_populated_usage(self):
        usage = {"output_tokens": 5}
        scan = _scan([_turn("m1", usage=usage), _turn("m1")])
        assert scan.usage_by_message == {"m1": usage}

    def test_last_usage_for_a_repeated_message_id_wins(self):
        scan = _scan([_turn("m1", usage={"output_tokens": 1}), _turn("m1", usage={"output_tokens": 9})])
        assert scan.usage_by_message == {"m1": {"output_tokens": 9}}

    def test_read_already_seen_in_another_window_is_counted_as_a_repeated_read(self):
        seen: set[str] = set()
        records = _read_exchange("m1", "r1", "/a.py")
        assert _scan(records, seen).repeated_reads == 0
        assert _scan(records, seen).repeated_reads == 1

    def test_copy_cut_off_before_the_result_does_not_hide_the_read_in_a_later_copy(self):
        seen: set[str] = set()
        cut_off = [_turn("m1", [_read_use("r1", file_path="/a.py")])]
        assert _scan(cut_off, seen).events == []
        assert seen == set()
        full_copy = _scan([*cut_off, _read_result("r1", _HUNDRED_TOKEN_TEXT)], seen)
        assert [event.path for event in full_copy.events] == ["/a.py"]
        assert seen == {"r1"}

    def test_read_with_an_error_result_leaves_its_id_unseen(self):
        seen: set[str] = set()
        _scan([_turn("m1", [_read_use("r1", file_path="/a.py")]), _read_result("r1", "boom", is_error=True)], seen)
        assert seen == set()


_NULL_TRUNCATION_FLAG_RECORD = {"type": "text", "file": {**_file_record("/a.py")["file"], "truncatedByTokenCap": None}}
_RECORD_WITHOUT_NUM_LINES = {
    "type": "text", "file": {key: value for key, value in _file_record("/a.py")["file"].items() if key != "numLines"},
}


def _read_with_result(tool_use_result, *, path: str = "/a.py", **read_use_kwargs) -> list[dict]:
    return [
        _turn("m1", [_read_use("r1", file_path=path, **read_use_kwargs)]),
        _read_result("r1", _HUNDRED_TOKEN_TEXT, tool_use_result=tool_use_result),
    ]


def _the_six_original_fields(event: read_cost._ReadEvent) -> tuple:
    return event[:6]


_NO_STRUCTURED_FIELDS = {
    "start_line": None, "num_lines": None, "total_lines": None, "truncated_by_token_cap": None,
}


class TestStructuredResultFields:
    def test_whole_file_record_supplies_every_new_field(self):
        records = _read_with_result(
            _file_record("/a.py", num_lines=100, total_lines=100, truncated_by_token_cap=True), allow_large=True,
        )

        event = _event_for(_scan(records), "/a.py")

        assert (event.tool_use_id, event.offset, event.allow_large, event.call_order) == ("r1", None, True, 0)
        assert (event.start_line, event.num_lines, event.total_lines, event.truncated_by_token_cap) == (1, 100, 100, True)
        assert event.structured_status == read_cost._STRUCTURED_OK

    def test_paged_record_supplies_its_offset_and_window(self):
        records = _read_with_result(_file_record("/a.py", start_line=11, num_lines=20, total_lines=500), offset=11, limit=20)

        event = _event_for(_scan(records), "/a.py")

        assert (event.whole_file, event.offset, event.allow_large) == (False, 11, False)
        assert (event.start_line, event.num_lines, event.total_lines) == (11, 20, 500)
        assert event.structured_status == read_cost._STRUCTURED_OK

    def test_absent_truncation_flag_reads_as_false(self):
        event = _event_for(_scan(_read_with_result(_file_record("/a.py"))), "/a.py")

        assert event.truncated_by_token_cap is False

    def test_empty_file_with_zero_counts_is_a_valid_record(self):
        event = _event_for(
            _scan(_read_with_result(_file_record("/a.py", start_line=0, num_lines=0, total_lines=0))), "/a.py",
        )

        assert (event.start_line, event.num_lines, event.total_lines) == (0, 0, 0)

    @pytest.mark.parametrize(("tool_use_result", "expected_status"), [
        ("Error: not a dict", read_cost._STRUCTURED_TOOL_USE_RESULT_NOT_A_DICT),
        (["not", "a", "dict"], read_cost._STRUCTURED_TOOL_USE_RESULT_NOT_A_DICT),
        (None, read_cost._STRUCTURED_TOOL_USE_RESULT_NOT_A_DICT),
        ({"type": "text", "file": "not a dict"}, read_cost._STRUCTURED_FILE_NOT_A_DICT),
        ({"type": "text"}, read_cost._STRUCTURED_FILE_NOT_A_DICT),
        (_file_record(7), read_cost._STRUCTURED_FILE_PATH_MISMATCH),
        (_file_record("/other.py"), read_cost._STRUCTURED_FILE_PATH_MISMATCH),
        (_file_record("/a.py", num_lines=True), read_cost._STRUCTURED_LINE_FIELD_INVALID),
        (_file_record("/a.py", num_lines=-1), read_cost._STRUCTURED_LINE_FIELD_INVALID),
        (_file_record("/a.py", total_lines=100.0), read_cost._STRUCTURED_LINE_FIELD_INVALID),
        (_file_record("/a.py", start_line="1"), read_cost._STRUCTURED_LINE_FIELD_INVALID),
        (_file_record("/a.py", truncated_by_token_cap="true"), read_cost._STRUCTURED_TRUNCATION_FLAG_INVALID),
        (_file_record("/a.py", truncated_by_token_cap=1), read_cost._STRUCTURED_TRUNCATION_FLAG_INVALID),
        (_NULL_TRUNCATION_FLAG_RECORD, read_cost._STRUCTURED_TRUNCATION_FLAG_INVALID),
        (_RECORD_WITHOUT_NUM_LINES, read_cost._STRUCTURED_LINE_FIELD_INVALID),
    ])
    def test_malformed_shape_leaves_every_structured_field_none_and_counting_unchanged(
        self, tool_use_result, expected_status,
    ):
        seen: set[str] = set()
        scan = _scan(_read_with_result(tool_use_result), seen)
        baseline_seen: set[str] = set()
        baseline = _scan(_read_exchange("m1", "r1", "/a.py"), baseline_seen)

        event = _event_for(scan, "/a.py")

        assert event.structured_status == expected_status
        assert {key: getattr(event, key) for key in _NO_STRUCTURED_FIELDS} == _NO_STRUCTURED_FIELDS
        assert [_the_six_original_fields(e) for e in scan.events] == [_the_six_original_fields(e) for e in baseline.events]
        assert (scan.repeated_reads, seen) == (baseline.repeated_reads, baseline_seen)

    def test_file_path_that_differs_from_the_calls_path_is_a_mismatch(self):
        event = _event_for(_scan(_read_with_result(_file_record("/other.py"))), "/a.py")

        assert event.structured_status == read_cost._STRUCTURED_FILE_PATH_MISMATCH
        assert event.tokens == 100

    def test_record_holding_two_results_names_multi_result_record_even_with_a_valid_tool_use_result(self):
        batched_results = _user_msg([
            {"type": "tool_result", "tool_use_id": "r1", "content": _HUNDRED_TOKEN_TEXT},
            {"type": "tool_result", "tool_use_id": "r2", "content": _HUNDRED_TOKEN_TEXT},
        ])
        batched_results["toolUseResult"] = _file_record("/a.py")

        scan = _scan([
            _turn("m1", [_read_use("r1", file_path="/a.py"), _read_use("r2", file_path="/b.py")]), batched_results,
        ])

        assert {event.path: event.structured_status for event in scan.events} == {
            "/a.py": read_cost._STRUCTURED_MULTI_RESULT_RECORD, "/b.py": read_cost._STRUCTURED_MULTI_RESULT_RECORD,
        }
        assert all(event.start_line is None for event in scan.events)

    def test_record_holding_many_results_is_classified_without_recounting_its_blocks_for_each_result(self):
        result_count = 200
        type_lookups = 0

        class CountingBlock(dict):
            def get(self, key, default=None):
                nonlocal type_lookups
                if key == "type":
                    type_lookups += 1
                return super().get(key, default)

        batched_results = _user_msg([
            CountingBlock(type="tool_result", tool_use_id=f"r{index}", content=_HUNDRED_TOKEN_TEXT)
            for index in range(result_count)
        ])
        batched_results["toolUseResult"] = _file_record("/0.py")

        scan = _scan([
            _turn("m1", [_read_use(f"r{index}", file_path=f"/{index}.py") for index in range(result_count)]),
            batched_results,
        ])

        assert {event.structured_status for event in scan.events} == {read_cost._STRUCTURED_MULTI_RESULT_RECORD}
        assert len(scan.events) == result_count
        # Each block is read a fixed number of times, so a count that grows with results x blocks fails the upper
        # bound. The lower bound fails a counter the scan no longer reaches.
        assert result_count <= type_lookups <= 4 * result_count

    def test_result_record_without_a_tool_use_result_key_reads_as_not_a_dict(self):
        event = _event_for(_scan(_read_exchange("m1", "r1", "/a.py")), "/a.py")

        assert event.structured_status == read_cost._STRUCTURED_TOOL_USE_RESULT_NOT_A_DICT

    @pytest.mark.parametrize("raw_offset", ["5", 5.0, True, -1])
    def test_offset_that_is_not_a_non_negative_integer_is_stored_as_none_on_a_paged_read(self, raw_offset):
        event = _event_for(_scan(_read_with_result(_file_record("/a.py"), offset=raw_offset)), "/a.py")

        assert (event.offset, event.whole_file) == (None, False)

    @pytest.mark.parametrize("raw_offset", ["5", 5.0, True, -1])
    def test_offset_that_is_not_a_non_negative_integer_is_stored_as_none_on_a_failed_read(self, raw_offset):
        scan = _scan([
            _turn("m1", [_read_use("r1", file_path="/a.py", offset=raw_offset)]),
            _read_result("r1", "boom", is_error=True),
        ])

        (failed,) = scan.failed_reads

        assert (failed.offset, failed.whole_file) == (None, False)

    @pytest.mark.parametrize("file_fields", [
        {},
        {"startLine": 1, "numLines": 100, "totalLines": 100},
    ])
    def test_file_record_without_a_file_path_is_a_mismatch_and_raises_nothing(self, file_fields):
        event = _event_for(_scan(_read_with_result({"type": "text", "file": file_fields})), "/a.py")

        assert event.structured_status == read_cost._STRUCTURED_FILE_PATH_MISMATCH
        assert {key: getattr(event, key) for key in _NO_STRUCTURED_FIELDS} == _NO_STRUCTURED_FIELDS

    def test_zero_offset_is_stored_as_given(self):
        event = _event_for(_scan(_read_with_result(_file_record("/a.py", start_line=0), offset=0)), "/a.py")

        assert (event.offset, event.whole_file) == (0, False)

    @pytest.mark.parametrize("non_string_path", [["/a.py"], 7, {"path": "/a.py"}])
    def test_read_or_edit_with_a_non_string_path_is_skipped_without_error(self, non_string_path):
        seen: set[str] = set()
        scan = _scan([
            _turn("m1", [
                _read_use("r1", file_path=non_string_path),
                _edit_use("e1", path=non_string_path),
            ]),
            _read_result("r1", _HUNDRED_TOKEN_TEXT),
        ], seen)

        assert scan.events == []
        assert seen == set()

    @pytest.mark.parametrize("raw_allow_large", ["true", 1])
    def test_allow_large_that_is_not_the_boolean_true_reads_as_false(self, raw_allow_large):
        event = _event_for(_scan(_read_with_result(_file_record("/a.py"), allow_large=raw_allow_large)), "/a.py")

        assert event.allow_large is False


_RECOGNISED_WORDINGS = (
    "File content (51.2KB) exceeds maximum allowed size (50KB)",
    "File content (30000 tokens) exceeds maximum allowed tokens (25000)",
)
_WHOLE_FILE_CALL: dict = {}
_PAGED_CALL = {"offset": 1, "limit": 10}
_LIMIT_ONLY_CALL = {"limit": 10}
_TEXT_BLOCK = {"type": "text", "text": _RECOGNISED_WORDINGS[0]}
_IMAGE_SOURCE_SENTINEL = "image-bytes-sentinel"
_IMAGE_BLOCK = {"type": "image", "source": _IMAGE_SOURCE_SENTINEL}
_SPLIT_PHRASE_BLOCKS = [
    {"type": "text", "text": "File content (9KB) exceeds"},
    {"type": "text", "text": "maximum allowed size"},
]


def _error_text(error_content) -> str:
    if isinstance(error_content, list):
        return " ".join(block["text"] for block in error_content if block["type"] == "text")
    return error_content


def _failed_scan(call: dict, error_content, tool_use_result="Error: stand-in") -> read_cost._WindowScan:
    return _scan([
        _turn("m1", [_read_use("r1", file_path="/a.py", **call)]),
        _read_result("r1", error_content, is_error=True, tool_use_result=tool_use_result),
    ])


class TestFailedReads:
    @pytest.mark.parametrize(("call", "error_content", "expected_class"), [
        (_WHOLE_FILE_CALL, _RECOGNISED_WORDINGS[0], read_cost._LIMIT_REFUSAL_RECOGNISED),
        (_PAGED_CALL, _RECOGNISED_WORDINGS[0], read_cost._LIMIT_REFUSAL_RECOGNISED),
        (_WHOLE_FILE_CALL, _RECOGNISED_WORDINGS[1], read_cost._LIMIT_REFUSAL_RECOGNISED),
        (_PAGED_CALL, _RECOGNISED_WORDINGS[1], read_cost._LIMIT_REFUSAL_RECOGNISED),
        (_WHOLE_FILE_CALL, "File content (9KB) is bigger than allowed", read_cost._LIMIT_REFUSAL_UNRECOGNISED),
        (_WHOLE_FILE_CALL, "this would exceed the cap", read_cost._LIMIT_REFUSAL_UNRECOGNISED),
        (_WHOLE_FILE_CALL, "THIS WOULD EXCEED THE CAP", read_cost._LIMIT_REFUSAL_UNRECOGNISED),
        (_WHOLE_FILE_CALL, "over the maximum", read_cost._LIMIT_REFUSAL_UNRECOGNISED),
        (_WHOLE_FILE_CALL, "OVER THE MAXIMUM", read_cost._LIMIT_REFUSAL_UNRECOGNISED),
        (_WHOLE_FILE_CALL, "the file is too large", read_cost._LIMIT_REFUSAL_UNRECOGNISED),
        (_WHOLE_FILE_CALL, "THE FILE IS TOO LARGE", read_cost._LIMIT_REFUSAL_UNRECOGNISED),
        (_WHOLE_FILE_CALL, _RECOGNISED_WORDINGS[0].upper(), read_cost._LIMIT_REFUSAL_UNRECOGNISED),
        (_WHOLE_FILE_CALL, [_TEXT_BLOCK], read_cost._LIMIT_REFUSAL_RECOGNISED),
        (_WHOLE_FILE_CALL, [_TEXT_BLOCK, _IMAGE_BLOCK], read_cost._LIMIT_REFUSAL_RECOGNISED),
        (_WHOLE_FILE_CALL, _SPLIT_PHRASE_BLOCKS, read_cost._LIMIT_REFUSAL_UNRECOGNISED),
        (_WHOLE_FILE_CALL, [_IMAGE_BLOCK], read_cost._LIMIT_REFUSAL_NONE),
        (_WHOLE_FILE_CALL, "File does not exist.", read_cost._LIMIT_REFUSAL_NONE),
        (_LIMIT_ONLY_CALL, _RECOGNISED_WORDINGS[1], read_cost._LIMIT_REFUSAL_RECOGNISED),
    ])
    def test_error_text_is_classified_and_never_kept(self, call, error_content, expected_class):
        scan = _failed_scan(call, error_content)

        assert scan.events == []
        (failed,) = scan.failed_reads
        assert failed.limit_refusal == expected_class
        assert (failed.path, failed.tool_use_id, failed.call_order) == ("/a.py", "r1", 0)
        assert failed.whole_file is (not call)
        assert failed.offset == call.get("offset")
        kept_words = {word.lower() for value in failed for word in str(value).split()}
        error_words = {word.lower() for word in _error_text(error_content).split()}
        # An image-only error has no words, so this check passes vacuously for it. The image case below covers it.
        assert not kept_words & error_words

    def test_image_only_error_has_no_text_words_and_keeps_nothing_of_the_image(self):
        error_content = [_IMAGE_BLOCK]
        assert _error_text(error_content).split() == []

        (failed,) = _failed_scan(_WHOLE_FILE_CALL, error_content).failed_reads

        assert failed.limit_refusal == read_cost._LIMIT_REFUSAL_NONE
        assert not any(_IMAGE_SOURCE_SENTINEL in repr(value) for value in failed)

    @pytest.mark.parametrize(("error_content", "expected_class"), [
        (None, read_cost._LIMIT_REFUSAL_NONE),
        (7, read_cost._LIMIT_REFUSAL_NONE),
        ({"type": "text", "text": _RECOGNISED_WORDINGS[0]}, read_cost._LIMIT_REFUSAL_NONE),
        (["bare string", 7, None], read_cost._LIMIT_REFUSAL_NONE),
        ([_RECOGNISED_WORDINGS[0], None, _TEXT_BLOCK], read_cost._LIMIT_REFUSAL_RECOGNISED),
        ([{"type": "text", "text": 7}, {"type": "text"}], read_cost._LIMIT_REFUSAL_NONE),
        ([{"type": "text", "text": 7}, _TEXT_BLOCK], read_cost._LIMIT_REFUSAL_RECOGNISED),
    ])
    def test_error_content_of_an_unexpected_shape_is_classified_without_raising(self, error_content, expected_class):
        assert read_cost._limit_refusal(error_content) == expected_class
        (failed,) = _failed_scan(_WHOLE_FILE_CALL, error_content).failed_reads
        assert failed.limit_refusal == expected_class

    def test_scan_with_no_failed_call_has_an_empty_tuple_of_failed_reads(self):
        assert _scan(_read_exchange("m1", "r1", "/a.py")).failed_reads == ()

    def test_failed_call_replayed_inside_one_window_is_kept_once(self):
        scan = _scan([
            _turn("m1", [_read_use("r1", file_path="/a.py")]),
            _read_result("r1", "boom", is_error=True),
            _turn("m2", [_read_use("r1", file_path="/a.py")]),
            _read_result("r1", "boom", is_error=True),
        ])

        assert len(scan.failed_reads) == 1
        assert scan.repeated_reads == 0

    def test_failed_call_replayed_in_a_later_window_sharing_the_seen_set_is_kept_once(self):
        seen_failed: set[str] = set()
        records = [_turn("m1", [_read_use("r1", file_path="/a.py")]), _read_result("r1", "boom", is_error=True)]

        first = read_cost._scan_window(records, set(), seen_failed)
        second = read_cost._scan_window(records, set(), seen_failed)

        assert (len(first.failed_reads), len(second.failed_reads)) == (1, 0)
        assert (first.repeated_reads, second.repeated_reads) == (0, 0)
        assert seen_failed == {"r1"}


class TestCallOrder:
    def test_same_path_read_between_a_calls_two_blocks_orders_after_the_call(self):
        scan = _scan([
            _turn("m1", [_read_use("r1", file_path="/a.py")]),
            _turn("m2", [_read_use("r2", file_path="/a.py")]),
            _read_result("r2", _HUNDRED_TOKEN_TEXT),
            _turn("m3", [_read_use("r1", file_path="/a.py")]),
            _read_result("r1", _HUNDRED_TOKEN_TEXT),
        ])

        assert {event.tool_use_id: event.call_order for event in scan.events} == {"r1": 0, "r2": 1}

    def test_each_call_takes_the_next_number_in_record_order(self):
        scan = _scan([
            _turn("m1", [_read_use("r1", file_path="/a.py"), _read_use("r2", file_path="/b.py")]),
            _read_result("r2", _HUNDRED_TOKEN_TEXT),
            _read_result("r1", _HUNDRED_TOKEN_TEXT),
        ])

        assert {event.tool_use_id: event.call_order for event in scan.events} == {"r1": 0, "r2": 1}

    @pytest.mark.parametrize(("failed_first", "expected_order"), [
        (True, {"r-failed": 0, "r-ok": 1}),
        (False, {"r-ok": 0, "r-failed": 1}),
    ])
    def test_failed_and_successful_reads_share_one_numbering(self, failed_first, expected_order):
        failed_call = [
            _turn("m-failed", [_read_use("r-failed", file_path="/a.py")]),
            _read_result("r-failed", "boom", is_error=True),
            _turn("m-failed-replay", [_read_use("r-failed", file_path="/a.py")]),
        ]
        successful_call = [
            _turn("m-ok", [_read_use("r-ok", file_path="/b.py")]),
            _read_result("r-ok", _HUNDRED_TOKEN_TEXT),
        ]

        scan = _scan([*failed_call, *successful_call] if failed_first else [*successful_call, *failed_call])

        (failed,) = scan.failed_reads
        (kept,) = scan.events
        assert {failed.tool_use_id: failed.call_order, kept.tool_use_id: kept.call_order} == expected_order


def _notice_with_attachment_tool_use_id(tool_use_id) -> dict:
    notice = _read_truncation_notice("placeholder")
    notice["attachment"]["toolUseID"] = tool_use_id
    return notice


class TestTruncationNoticeIds:
    def test_notice_ahead_of_every_conversation_record_is_collected(self):
        scan = _scan([_read_truncation_notice("r-early"), *_read_exchange("m1", "r1", "/a.py")])

        assert scan.truncation_notice_tool_use_ids == {"r-early"}

    def test_only_a_read_truncation_notice_with_a_string_id_is_collected(self):
        other_attachment = {
            "type": "attachment", "attachment": {"type": "hook_success", "toolUseID": "r-other"},
        }
        idless_notice = {"type": "attachment", "attachment": {"type": "read_truncation_notice"}}
        non_string_id_notice = _notice_with_attachment_tool_use_id(7)
        non_attachment = {**_read_truncation_notice("r-wrong-type"), "type": "user"}

        scan = _scan([
            other_attachment, idless_notice, non_string_id_notice, non_attachment,
            _read_truncation_notice("r1"),
        ])

        assert scan.truncation_notice_tool_use_ids == {"r1"}

    def test_attachment_whose_type_is_not_a_read_truncation_notice_is_not_collected(self):
        other_attachment = {
            **_read_truncation_notice("r1"),
            "attachment": {"type": "hook_success", "toolUseID": "r1"},
        }

        assert _scan([other_attachment]).truncation_notice_tool_use_ids == frozenset()

    @pytest.mark.parametrize("tool_use_id", [7, None, ["r1"], ""])
    def test_notice_with_a_non_string_or_empty_tool_use_id_is_not_collected(self, tool_use_id):
        notice = _notice_with_attachment_tool_use_id(tool_use_id)

        assert _scan([notice]).truncation_notice_tool_use_ids == frozenset()

    def test_notice_whose_id_sits_only_on_the_record_top_level_is_not_collected(self):
        # The harness writes the id inside the attachment object; a top-level id is not the notice shape.
        top_level_only_notice = {
            "type": "attachment", "toolUseID": "r1", "attachment": {"type": "read_truncation_notice"},
        }

        assert _scan([top_level_only_notice]).truncation_notice_tool_use_ids == frozenset()

    def test_notice_id_is_taken_from_inside_the_attachment_not_the_record_top_level(self):
        notice = {**_read_truncation_notice("r-inside"), "toolUseID": "r-top-level"}

        assert _scan([notice]).truncation_notice_tool_use_ids == {"r-inside"}

    @pytest.mark.parametrize("non_dict_attachment", ["read_truncation_notice", ["read_truncation_notice"], None])
    def test_notice_whose_attachment_is_not_a_dict_is_not_collected_and_raises_nothing(self, non_dict_attachment):
        notice = {**_read_truncation_notice("r1"), "attachment": non_dict_attachment}

        assert _scan([notice]).truncation_notice_tool_use_ids == frozenset()

    @pytest.mark.parametrize("attachment_record", [
        {"type": "attachment", "toolUseID": "r1"},
        {"type": "attachment"},
    ])
    def test_attachment_record_without_an_attachment_key_is_not_collected_and_raises_nothing(self, attachment_record):
        assert _scan([attachment_record]).truncation_notice_tool_use_ids == frozenset()

    def test_scan_without_a_notice_has_an_empty_set(self):
        assert _scan(_read_exchange("m1", "r1", "/a.py")).truncation_notice_tool_use_ids == frozenset()
