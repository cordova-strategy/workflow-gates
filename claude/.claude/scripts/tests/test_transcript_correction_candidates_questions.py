"""correction_candidates' question seam: free-text answers, question entries, and the question lines built from them."""
import threading

import pytest
from transcript_analysis import correction_candidates

from ._compaction_context_helpers import (
    ABSENT,
    sidechain,
    tool_result_record,
)
from ._correction_candidates_helpers import (
    ask_answer_record,
    ask_record,
    ask_user_question_block,
    assistant_record,
    assistant_text,
    emitted,
    only_line,
    prompt,
    question_spec,
    scan,
    text_block,
    ts,
    with_fields,
)

_PARSE_JOIN_TIMEOUT_SECONDS = 5


# --- answers ------------------------------------------------------------------------------------------------------


class TestAnswerIsFreeText:
    @pytest.mark.parametrize(
        ("answer", "labels", "multi_select", "expected"),
        [
            pytest.param("Yes", ("Yes", "No"), False, False, id="selected-label"),
            pytest.param("Maybe", ("Yes", "No"), False, True, id="single-select-free-text"),
            pytest.param("Yes, No", ("Yes", "No"), True, False, id="multi-select-of-labels"),
            pytest.param("Yes, but later", ("Yes", "Yes, but later"), True, False, id="forced-backtrack"),
            pytest.param("a, b, c", ("a, b", "c"), True, False, id="label-containing-the-separator"),
            pytest.param("Yes, extra", ("Yes", "No"), True, True, id="multi-select-with-extra-text"),
            pytest.param("Yes,No", ("Yes", "No"), True, True, id="separator-without-space"),
            pytest.param("Yes", ("", "Yes"), True, False, id="empty-labels-ignored"),
            pytest.param(None, ("Yes",), False, None, id="null-answer"),
            pytest.param("", ("Yes",), False, None, id="empty-answer"),
            pytest.param("   ", ("Yes",), True, None, id="blank-answer"),
        ],
    )
    def test_flag_for_each_answer_shape(self, answer, labels, multi_select, expected):
        assert correction_candidates._answer_is_free_text(answer, labels, multi_select) is expected

    def test_overlapping_labels_against_a_long_unmatched_answer_finish_instead_of_hanging(self):
        answer = ", ".join(["a"] * 199 + ["zz"])
        outcome: dict[str, object] = {}

        def parse() -> None:
            try:
                outcome["result"] = correction_candidates._answer_is_free_text(answer, ("a", "a, a"), True)
            except Exception as error:  # noqa: BLE001 -- the test records any failure for its assertion
                outcome["error"] = error

        worker = threading.Thread(target=parse, daemon=True)
        worker.start()
        worker.join(_PARSE_JOIN_TIMEOUT_SECONDS)

        assert outcome == {"result": True}, f"the label parse did not return within {_PARSE_JOIN_TIMEOUT_SECONDS} s"


def _answered_line(specs, answers, *, annotations=ABSENT, truncate_chars=2000, **answer_overrides) -> dict:
    records = [
        prompt("go", 1),
        ask_record(specs),
        ask_answer_record(answers=answers, annotations=annotations, timestamp=ts(6), **answer_overrides),
    ]
    return [line for line in emitted(records, truncate_chars=truncate_chars) if line["kind"] == "question"][0]


class TestQuestionEntries:
    def test_answer_longer_than_the_truncation_limit_keeps_the_flag_of_the_untruncated_value(self):
        long_label = "L" * 50

        line = _answered_line([question_spec("Pick?", (long_label, "No"))], {"Pick?": long_label}, truncate_chars=5)

        entry = line["questions"][0]
        assert entry["answer"].startswith("LLLLL… (truncated, 50 chars total)")
        assert entry["answer_is_free_text"] is False

    def test_duplicate_question_text_shares_the_one_answer(self):
        line = _answered_line([question_spec("Same?"), question_spec("Same?", ("Yes", "No"))], {"Same?": "Yes"})

        assert [entry["answer"] for entry in line["questions"]] == ["Yes", "Yes"]

    @pytest.mark.parametrize(
        ("annotations", "expected"),
        [
            pytest.param({"Pick?": {"notes": "because"}}, "because", id="present"),
            pytest.param(ABSENT, None, id="absent-annotations"),
            pytest.param({"Pick?": {}}, None, id="absent-notes"),
            pytest.param({"Pick?": {"notes": 5}}, None, id="non-string-notes"),
            pytest.param({"Pick?": "text"}, None, id="non-dict-annotation"),
            pytest.param("text", None, id="non-dict-annotations"),
        ],
    )
    def test_notes_come_from_the_annotation_of_the_question(self, annotations, expected):
        line = _answered_line([question_spec("Pick?")], {"Pick?": "Yes"}, annotations=annotations)

        assert line["questions"][0]["notes"] == expected

    def test_null_and_blank_answers_have_a_null_flag(self):
        specs = [question_spec("Null?"), question_spec("Blank?"), question_spec("Non-string?")]

        line = _answered_line(specs, {"Blank?": "  ", "Non-string?": 5})

        assert [(entry["answer"], entry["answer_is_free_text"]) for entry in line["questions"]] == [
            (None, None), ("  ", None), (None, None),
        ]

    def test_header_multi_select_and_options_are_read_with_their_types_checked(self):
        spec = {
            "question": "Pick?", "header": 5, "multiSelect": "true",
            "options": [{"label": "Yes", "description": 5}, {"label": 5}, "bare", {"label": "No", "description": "no way"}],
        }

        line = _answered_line([spec], {"Pick?": "Yes"})

        entry = line["questions"][0]
        assert entry["header"] is None
        assert entry["multi_select"] is False
        assert entry["options"] == [{"label": "Yes", "description": None}, {"label": "No", "description": "no way"}]


class TestQuestionRecords:
    @pytest.mark.parametrize(
        "tool_use_result",
        [pytest.param("declined", id="non-dict"), pytest.param({"questions": []}, id="dict-without-answers"),
         pytest.param({"answers": ["x"]}, id="non-dict-answers"), pytest.param(None, id="null")],
    )
    def test_result_without_an_answers_dict_is_emitted_unanswered(self, tool_use_result):
        records = [ask_record([question_spec("Which?")]), ask_answer_record(tool_use_result=tool_use_result, timestamp=ts(6))]

        line = only_line(records)

        assert line["answered"] is False
        assert [entry["answer"] for entry in line["questions"]] == [None]

    @pytest.mark.parametrize(
        ("content", "expected"),
        [
            pytest.param("The user declined.", "The user declined.", id="string-content"),
            pytest.param(
                [text_block("first"), {"type": "text", "text": 5}, {"type": "image"}, text_block("second")], "first second",
                id="list-of-text-blocks-skipping-a-non-string-text",
            ),
            pytest.param("", None, id="empty-string"),
            pytest.param([{"type": "image"}], None, id="no-text-blocks"),
            pytest.param(7, None, id="non-string-non-list"),
        ],
    )
    def test_declined_call_result_text_comes_from_the_tool_result_content(self, content, expected):
        records = [
            ask_record([question_spec("Which?")]),
            ask_answer_record(tool_use_result="declined", content=content, timestamp=ts(6)),
        ]

        assert only_line(records)["result_text"] == expected

    def test_question_before_any_exchange_opening_has_exchange_zero_and_text_from_the_files_start(self):
        records = [
            assistant_text("opening remark", timestamp=ts(1)),
            ask_record([question_spec("Which?")]),
            ask_answer_record(answers={"Which?": "Yes"}, timestamp=ts(6)),
        ]

        line = only_line(records)

        assert line["exchange"] == 0
        assert line["preceding_assistant_text"] == "opening remark\n\nasking now"

    def test_answered_call_has_no_result_text(self):
        records = [ask_record([question_spec("Which?")]), ask_answer_record(answers={"Which?": "Yes"}, timestamp=ts(6))]

        assert only_line(records)["result_text"] is None

    def test_missing_result_counts_unanswered_question(self):
        candidates, counts = scan([ask_record([question_spec("Which?")])])

        assert candidates == []
        assert (counts["unanswered_question"], counts["ask_user_question_calls"]) == (1, 1)

    def test_two_later_results_for_one_tool_use_id_pair_with_the_first(self):
        records = [
            ask_record([question_spec("Which?")]),
            ask_answer_record(answers={"Which?": "First"}, timestamp=ts(6)),
            ask_answer_record(answers={"Which?": "Second"}, timestamp=ts(7)),
        ]

        assert only_line(records)["questions"][0]["answer"] == "First"

    def test_a_result_before_and_one_after_the_asking_record_pair_with_the_later(self):
        records = [
            ask_answer_record(answers={"Which?": "Earlier"}, timestamp=ts(1)),
            ask_record([question_spec("Which?")]),
            ask_answer_record(answers={"Which?": "Later"}, timestamp=ts(6)),
        ]

        assert only_line(records)["questions"][0]["answer"] == "Later"

    def test_result_before_the_asking_record_is_not_its_answer(self):
        records = [ask_answer_record(answers={"Which?": "Yes"}, timestamp=ts(1)), ask_record([question_spec("Which?")])]

        _candidates, counts = scan(records)

        assert counts["unanswered_question"] == 1

    @pytest.mark.parametrize(
        "raw_input",
        [
            pytest.param({"questions": "text"}, id="non-list-questions"),
            pytest.param({"questions": []}, id="empty-questions"),
            pytest.param({"questions": ["text"]}, id="non-dict-question"),
            pytest.param({"questions": [{"header": "x"}]}, id="no-question-text"),
            pytest.param(
                {"questions": [{"question": "Fine?"}, {"header": "no question text"}]}, id="one-bad-entry-of-two",
            ),
            pytest.param([], id="non-dict-input"),
            pytest.param({}, id="no-questions"),
        ],
    )
    def test_malformed_input_counts_malformed_question(self, raw_input):
        block = ask_user_question_block([], raw_input=raw_input)

        candidates, counts = scan([assistant_record([block], timestamp=ts(1))])

        assert candidates == []
        assert counts["malformed_question"] == 1

    def test_block_without_a_string_id_counts_malformed_question(self):
        block = with_fields(ask_user_question_block([question_spec("Which?")]), id=5)

        _candidates, counts = scan([assistant_record([block], timestamp=ts(1))])

        assert counts["malformed_question"] == 1

    def test_unrelated_tool_result_and_a_typed_prompt_between_the_ask_and_the_answer_do_not_break_the_pairing(self):
        records = [
            ask_record([question_spec("Which?")]),
            with_fields(tool_result_record(), timestamp=ts(6)),
            prompt("a typed prompt in between", 7, uuid="between"),
            ask_answer_record(answers={"Which?": "Yes"}, timestamp=ts(8)),
        ]

        question = next(line for line in emitted(records) if line["kind"] == "question")

        assert question["answered"] is True
        assert question["questions"][0]["answer"] == "Yes"

    def test_two_blocks_answered_in_reverse_order_each_carry_their_own_answer(self):
        record = assistant_record(
            [
                ask_user_question_block([question_spec("A?")], tool_use_id="toolu_a"),
                ask_user_question_block([question_spec("B?")], tool_use_id="toolu_b"),
            ],
            timestamp=ts(1),
        )
        answers = [
            ask_answer_record(tool_use_id="toolu_b", answers={"B?": "No"}, timestamp=ts(2)),
            ask_answer_record(tool_use_id="toolu_a", answers={"A?": "Yes"}, timestamp=ts(3)),
        ]

        lines = emitted([record, *answers])

        assert [(line["id"], line["questions"][0]["answer"]) for line in lines] == [
            ("sess-a:toolu_a", "Yes"), ("sess-a:toolu_b", "No"),
        ]

    def test_a_sidechain_record_holding_the_matching_tool_use_id_is_not_the_answer(self):
        records = [
            ask_record([question_spec("Which?")]),
            sidechain(ask_answer_record(answers={"Which?": "Yes"}, timestamp=ts(6))),
        ]

        candidates, counts = scan(records)

        assert candidates == []
        assert counts["unanswered_question"] == 1
