"""correction_candidates' extraction seam: verdicts, exchanges, context text, questions, truncation, dedup and serialization."""
import json
import threading
from collections import Counter
from datetime import UTC, datetime

import pytest
from transcript_analysis import correction_candidates

from ._compaction_context_helpers import (
    ABSENT,
    HUMAN_ORIGIN,
    bash_input,
    bash_stdout,
    builtin_command,
    headless_prompt,
    interrupt_marker,
    local_command_stdout,
    pasted_prompt,
    sidechain,
    slash_invocation,
    task_notification,
    tool_result_record,
    user_prompt,
)
from ._correction_candidates_helpers import (
    FAMILY,
    OPUS,
    SONNET,
    ask_answer_record,
    ask_record,
    ask_user_question_block,
    assistant_record,
    assistant_text,
    emitted,
    iso,
    only_line,
    prompt,
    question_spec,
    run_files,
    scan,
    scripted_session,
    slash_prompt_session,
    text_block,
    thinking_block,
    tool_use_block,
    ts,
    with_fields,
)

_PARSE_JOIN_TIMEOUT_SECONDS = 5

# --- verdicts -----------------------------------------------------------------------------------------------------

_DANGLING_ARGS_COMMAND = (
    "<command-message>scratch</command-message>\n<command-name>/scratch</command-name>\n<command-args>no closer"
)

# Each row: the record, its verdict with no earlier `origin` in its file, with one, and whether it opens an exchange.
_VERDICT_SHAPES = [
    pytest.param(user_prompt(), "typed", "typed", True, id="typed-prompt"),
    pytest.param(pasted_prompt(), "typed", "typed", True, id="pasted-prompt"),
    pytest.param(
        user_prompt("<example-tag>quoted</example-tag> and more"), "typed", "typed", True,
        id="typed-prompt-opening-with-another-tag",
    ),
    pytest.param(slash_invocation(), "typed", "typed", True, id="skill-slash-invocation-with-args"),
    pytest.param(slash_invocation(args=None), "slash_command", "slash_command", True, id="bare-skill-slash-invocation"),
    pytest.param(
        with_fields(slash_invocation(), origin=ABSENT), "slash_command", "slash_command", True,
        id="skill-slash-invocation-with-args-and-no-origin",
    ),
    pytest.param(
        user_prompt(_DANGLING_ARGS_COMMAND), "slash_command", "slash_command", True,
        id="skill-slash-invocation-with-an-args-opener-and-no-closer",
    ),
    pytest.param(
        slash_invocation(args="  \n "), "slash_command", "slash_command", True,
        id="skill-slash-invocation-whose-args-are-whitespace",
    ),
    pytest.param(builtin_command(), "slash_command", "slash_command", True, id="builtin-command"),
    pytest.param(
        user_prompt("<command-args>words</command-args>"), "slash_command", "slash_command", True,
        id="hand-built-args-opener-with-a-human-origin",
    ),
    pytest.param(
        with_fields(slash_invocation(), origin={"kind": "peer"}), "slash_command", "slash_command", True,
        id="slash-shaped-record-with-a-peer-origin",
    ),
    pytest.param(local_command_stdout(), "local_command", "local_command", False, id="local-command-output"),
    pytest.param(
        with_fields(local_command_stdout(), origin=HUMAN_ORIGIN), "local_command", "local_command", False,
        id="local-command-output-with-a-human-origin",
    ),
    pytest.param(bash_input(), "bash_mode", "bash_mode", False, id="bash-input"),
    pytest.param(bash_stdout(), "bash_mode", "bash_mode", False, id="bash-output"),
    pytest.param(interrupt_marker(), "interrupt", "interrupt", False, id="interrupt-by-key"),
    pytest.param(
        interrupt_marker(interruptedMessageId=None), "interrupt", "interrupt", False, id="interrupt-by-null-valued-key",
    ),
    pytest.param(
        interrupt_marker(interruptedMessageId=ABSENT), "interrupt", "interrupt", False, id="interrupt-by-text-alone",
    ),
    pytest.param(
        interrupt_marker(interruptedMessageId=ABSENT, origin=HUMAN_ORIGIN), "interrupt", "interrupt", False,
        id="interrupt-text-with-a-human-origin",
    ),
    pytest.param(headless_prompt(), "headless", "headless", True, id="headless-prompt"),
    pytest.param(headless_prompt(origin=HUMAN_ORIGIN), "typed", "typed", True, id="human-origin-with-the-headless-markers"),
    pytest.param(
        headless_prompt(promptSource="typed"), "typed", "no_origin_after_origin", True,
        id="no-origin-prompt-with-a-partial-headless-marker-set",
    ),
    pytest.param(
        user_prompt(origin={"kind": "peer"}), "non_human_origin", "non_human_origin", True, id="peer-origin-record",
    ),
    pytest.param(user_prompt(origin=ABSENT), "typed", "no_origin_after_origin", True, id="plain-no-origin-prompt"),
    pytest.param(
        user_prompt("see task-notification> here", origin=ABSENT), "notification_text", "no_origin_after_origin", True,
        id="no-origin-prompt-holding-task-notification-closer",
    ),
    pytest.param(
        user_prompt([text_block("list content")], promptId="prompt-1"), "typed", "typed", True,
        id="list-content-with-prompt-id",
    ),
]


class TestPromptVerdict:
    @pytest.mark.parametrize(
        ("rec", "verdict_without_origin_seen", "verdict_with_origin_seen", "_opens_an_exchange"), _VERDICT_SHAPES,
    )
    def test_each_documented_shape_gets_its_exact_verdict_in_both_file_contexts(
        self, rec, verdict_without_origin_seen, verdict_with_origin_seen, _opens_an_exchange,
    ):
        assert correction_candidates._prompt_verdict(rec, origin_seen=False) == verdict_without_origin_seen
        assert correction_candidates._prompt_verdict(rec, origin_seen=True) == verdict_with_origin_seen

    @pytest.mark.parametrize(
        ("rec", "_verdict_without_origin_seen", "_verdict_with_origin_seen", "opens_an_exchange"), _VERDICT_SHAPES,
    )
    def test_each_shape_opens_an_exchange_or_not_as_the_next_prompt_shows(
        self, rec, _verdict_without_origin_seen, _verdict_with_origin_seen, opens_an_exchange,
    ):
        records = [
            assistant_text("before", timestamp=ts(1)),
            with_fields(rec, timestamp=ts(2), uuid="shape-uuid"),
            assistant_text("between", timestamp=ts(3)),
            prompt("probe", 4, uuid="probe-uuid"),
        ]

        probe = emitted(records)[-1]

        assert probe["text"] == "probe"
        assert probe["exchange"] == (2 if opens_an_exchange else 1)
        assert probe["preceding_assistant_text"] == ("between" if opens_an_exchange else "before\n\nbetween")

    @pytest.mark.parametrize(
        ("rec", "expected"),
        [
            pytest.param(user_prompt(), True, id="typed-prompt"),
            pytest.param(user_prompt([text_block("list content")], promptId="prompt-1"), True, id="list-content-with-prompt-id"),
            pytest.param(user_prompt([text_block("list content")]), False, id="list-content-without-prompt-id"),
            pytest.param(task_notification(), False, id="whole-task-notification"),
            pytest.param(tool_result_record(), False, id="tool-result"),
        ],
    )
    def test_prompt_shape_needs_both_predicates(self, rec, expected):
        assert correction_candidates._is_prompt_shaped(rec) is expected

    def test_a_record_that_is_not_prompt_shaped_counts_nowhere_and_opens_no_exchange(self):
        records = [
            with_fields(task_notification(), timestamp=ts(1)),
            with_fields(user_prompt([text_block("list content")]), timestamp=ts(2), uuid="list-uuid"),
            prompt("probe", 3, uuid="probe-uuid"),
        ]

        candidates, counts = scan(records)

        assert [candidate.record["text"] for candidate in candidates] == ["probe"]
        assert candidates[0].record["exchange"] == 1
        assert dict(counts) == {}


class TestSlashCommandArgs:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            pytest.param(
                "<command-message>plan-it</command-message>\n<command-name>/plan-it</command-name>"
                "\n<command-args>  add a thing\n</command-args>",
                ("/plan-it", "add a thing"), id="skill-with-args-stripped",
            ),
            pytest.param(
                "<command-name>/plan-it</command-name>\n<command-args>go</command-args>", ("/plan-it", "go"),
                id="name-tag-first",
            ),
            pytest.param(
                "<command-message>plan-it</command-message>\n<command-name>/plan-it</command-name>", None, id="no-args-tag",
            ),
            pytest.param(
                "<command-name>/plan-it</command-name><command-args>  </command-args>", None, id="whitespace-args",
            ),
            pytest.param("<command-args>go</command-args>", None, id="args-without-a-name-tag"),
            pytest.param(
                "just words <command-name>/plan-it</command-name><command-args>go</command-args>", None, id="not-opening",
            ),
        ],
    )
    def test_command_name_and_stripped_args_or_none(self, text, expected):
        assert correction_candidates._slash_command_args(text) == expected


class TestSlashPromptLine:
    def test_a_slash_prompt_carries_its_stripped_args_as_text_and_its_name_as_command(self):
        record = with_fields(slash_invocation("plan-it", "  add a thing  "), timestamp=ts(1), uuid="slash-uuid")

        line = only_line([record])

        assert (line["kind"], line["text"], line["command"], line["initial"]) == ("prompt", "add a thing", "/plan-it", True)

    def test_a_typed_prompt_carries_a_null_command(self):
        assert only_line([prompt("a typed ask", 1)])["command"] is None

    def test_a_bare_slash_command_emits_nothing_and_counts_slash_command(self):
        candidates, counts = scan([with_fields(slash_invocation(args=None), timestamp=ts(1))])

        assert candidates == []
        assert counts["slash_command"] == 1


# --- the scripted sessions ----------------------------------------------------------------------------------------


_SUMMARY_KEYS = (
    "kind", "id", "session_id", "exchange", "timestamp", "preceding_assistant_text", "following_assistant_text",
    "model_family", "model", "attribution_skill", "family", "text", "command", "initial", "after_interrupt", "answered",
)


def _line_summary(line: dict) -> dict:
    return {key: line[key] for key in _SUMMARY_KEYS if key in line}


class TestScriptedSession:
    def test_every_candidate_carries_its_exchange_context_and_reference_fields(self):
        lines = emitted(scripted_session())

        assert [_line_summary(line) for line in lines] == [
            {
                "kind": "prompt", "id": "sess-a:2", "session_id": "sess-a", "exchange": 2, "timestamp": iso(1),
                "preceding_assistant_text": "", "following_assistant_text": "reply one",
                "model_family": "unknown", "model": None, "attribution_skill": None, "family": FAMILY,
                "text": "first ask", "command": None, "initial": True, "after_interrupt": False,
            },
            {
                "kind": "prompt", "id": "sess-a:10", "session_id": "sess-a", "exchange": 3, "timestamp": iso(4),
                "preceding_assistant_text": "reply one",
                "following_assistant_text": "asking now\n\nthanks, proceeding",
                "model_family": "opus", "model": OPUS, "attribution_skill": None, "family": FAMILY,
                "text": "after interrupt", "command": None, "initial": False, "after_interrupt": True,
            },
            {
                "kind": "question", "id": "sess-a:toolu_q1", "session_id": "sess-a", "exchange": 3, "timestamp": iso(5),
                "preceding_assistant_text": "asking now", "following_assistant_text": "thanks, proceeding",
                "model_family": "opus", "model": OPUS, "attribution_skill": "skill-x", "family": FAMILY,
                "answered": True,
            },
            {
                "kind": "prompt", "id": "sess-a:14", "session_id": "sess-a", "exchange": 4, "timestamp": iso(8),
                "preceding_assistant_text": "asking now\n\nthanks, proceeding", "following_assistant_text": "",
                "model_family": "sonnet", "model": SONNET, "attribution_skill": "claude:plan-it", "family": FAMILY,
                "text": "last one", "command": None, "initial": False, "after_interrupt": False,
            },
        ]

    def test_the_bare_slash_command_opens_exchange_one_and_nothing_else_advances_an_ordinal(self):
        lines = emitted(scripted_session())

        assert [line["exchange"] for line in lines] == [2, 3, 3, 4]

    def test_sidechain_thinking_and_tool_only_records_add_no_text(self):
        lines = emitted(scripted_session())

        combined = " ".join(line["preceding_assistant_text"] + line["following_assistant_text"] for line in lines)
        assert "SIDECHAIN TEXT" not in combined
        assert "private reasoning" not in combined

    def test_skips_are_counted_by_kind(self):
        _candidates, counts = scan(scripted_session())

        assert {kind: counts[kind] for kind in ("slash_command", "interrupt", "local_command", "bash_mode")} == {
            "slash_command": 1, "interrupt": 1, "local_command": 1, "bash_mode": 2,
        }
        assert counts["uninterpretable"] == 1
        assert counts["ask_user_question_calls"] == 1

    def test_a_slash_prompt_opens_the_session_and_the_typed_prompt_after_it_is_not_initial(self):
        lines = emitted(slash_prompt_session())

        assert [_line_summary(line) for line in lines] == [
            {
                "kind": "prompt", "id": "sess-a:1", "session_id": "sess-a", "exchange": 1, "timestamp": iso(0),
                "preceding_assistant_text": "", "following_assistant_text": "working on it",
                "model_family": "unknown", "model": None, "attribution_skill": None, "family": FAMILY,
                "text": "draft the plan", "command": "/plan-it", "initial": True, "after_interrupt": False,
            },
            {
                "kind": "prompt", "id": "sess-a:4", "session_id": "sess-a", "exchange": 2, "timestamp": iso(3),
                "preceding_assistant_text": "working on it", "following_assistant_text": "",
                "model_family": "sonnet", "model": SONNET, "attribution_skill": None, "family": FAMILY,
                "text": "a correction", "command": None, "initial": False, "after_interrupt": False,
            },
        ]


# --- origin state is per file -------------------------------------------------------------------------------------


class TestOriginStatePerFile:
    def test_origin_less_file_after_an_origin_bearing_one_still_emits_its_non_initial_prompt(self):
        origin_bearing = [prompt("typed with origin", 1)]
        origin_less = [
            with_fields(user_prompt("first", origin=ABSENT), timestamp=ts(2), uuid="b1"),
            assistant_text("reply", timestamp=ts(3)),
            with_fields(user_prompt("second", origin=ABSENT), timestamp=ts(4), uuid="b2"),
        ]

        kept, counts, _checks = run_files({"sess-a": origin_bearing, "sess-b": origin_less})

        second = next(candidate.record for candidate in kept if candidate.record["id"] == "sess-b:2")
        assert second["initial"] is False
        assert counts["skipped"]["no_origin_after_origin"] == 0

    def test_origin_bearing_record_before_since_makes_an_in_window_origin_less_prompt_a_skip(self):
        records = [
            prompt("typed with origin", 1, day=10),
            with_fields(user_prompt("origin-less", origin=ABSENT), timestamp=ts(2), uuid="b1"),
        ]

        candidates, counts = scan(records, since="2026-05-19")

        assert candidates == []
        assert counts["no_origin_after_origin"] == 1


class TestInitialFlag:
    @pytest.mark.parametrize(
        ("textless_assistant_record", "expected_initial"),
        [
            pytest.param(assistant_record([thinking_block(), tool_use_block()], timestamp=ts(1)), False, id="main-thread"),
            pytest.param(
                sidechain(assistant_record([thinking_block(), tool_use_block()], timestamp=ts(1))), True, id="sidechain",
            ),
        ],
    )
    def test_a_main_thread_assistant_record_without_text_before_the_first_prompt_makes_it_not_initial(
        self, textless_assistant_record, expected_initial,
    ):
        line = only_line([textless_assistant_record, prompt("the resumed ask", 2)])

        assert line["initial"] is expected_initial


# --- window -------------------------------------------------------------------------------------------------------


class TestWindow:
    def test_prompt_whose_preceding_assistant_record_falls_before_since_keeps_that_text(self):
        records = [
            assistant_text("earlier reply", timestamp=ts(1, day=18)),
            prompt("in window", 2),
        ]

        line = only_line(records, since="2026-05-19")

        assert line["preceding_assistant_text"] == "earlier reply"
        assert line["initial"] is False

    def test_the_last_millisecond_of_the_until_day_is_in_and_the_next_midnight_is_out(self):
        last_in = with_fields(user_prompt("late"), timestamp="2026-05-19T23:59:59.999Z", uuid="late")
        first_out = with_fields(user_prompt("next day"), timestamp="2026-05-20T00:00:00.000Z", uuid="next")

        lines = emitted([last_in, first_out], until="2026-05-19")

        assert [line["text"] for line in lines] == ["late"]

    @pytest.mark.parametrize("timestamp", [ABSENT, 5, ["2026-05-19T10:00:00Z"], ""], ids=["absent", "int", "list", "empty"])
    def test_undated_prompt_counts_under_a_window_and_is_emitted_without_one(self, timestamp):
        records = [with_fields(user_prompt("undated"), timestamp=timestamp, uuid="u")]

        windowed_candidates, windowed_counts = scan(records, since="2026-05-01")
        line = only_line(records)

        assert windowed_candidates == []
        assert windowed_counts["undated"] == 1
        assert line["timestamp"] is None

    def test_question_asked_in_window_and_answered_after_until_is_answered_and_its_following_text_spans_the_edge(self):
        records = [
            prompt("go", 1),
            ask_record([question_spec("Which?")]),
            ask_answer_record(answers={"Which?": "Yes"}, timestamp=ts(0, day=21)),
            assistant_text("after the edge", timestamp=ts(1, day=21)),
        ]

        line = [line for line in emitted(records, until="2026-05-19") if line["kind"] == "question"][0]

        assert line["answered"] is True
        assert line["following_assistant_text"] == "after the edge"

    def test_question_asked_before_since_and_answered_in_window_counts_nowhere(self):
        records = [
            with_fields(ask_record([question_spec("Which?")]), timestamp=ts(5, day=10)),
            ask_answer_record(answers={"Which?": "Yes"}, timestamp=ts(6)),
        ]

        candidates, counts = scan(records, since="2026-05-19")

        assert candidates == []
        assert dict(counts) == {}

    def test_undated_asking_record_counts_once_per_block_under_a_window(self):
        two_blocks = assistant_record(
            [
                ask_user_question_block([question_spec("A?")], tool_use_id="toolu_a"),
                ask_user_question_block([question_spec("B?")], tool_use_id="toolu_b"),
            ],
            timestamp=ABSENT,
        )

        _candidates, counts = scan([two_blocks], since="2026-05-01")

        assert counts["undated"] == 2
        assert counts["ask_user_question_calls"] == 0

    def test_undated_prompt_and_asking_record_count_undated_under_an_until_only_window(self):
        undated_prompt = with_fields(user_prompt("undated"), timestamp=ABSENT, uuid="u")
        undated_asking = assistant_record(
            [ask_user_question_block([question_spec("A?")], tool_use_id="toolu_a")], timestamp=ABSENT,
        )

        candidates, counts = scan([undated_prompt, undated_asking], until="2026-05-19")

        assert candidates == []
        assert (counts["undated"], counts["ask_user_question_calls"]) == (2, 0)

    @pytest.mark.parametrize("timestamp", ["0001-01-01T00:00:00+14:00", "9999-12-31T23:59:59-14:00"])
    def test_a_timestamp_outside_the_utc_range_is_emitted_with_a_null_timestamp(self, timestamp):
        record = with_fields(user_prompt("far away"), timestamp=timestamp, uuid="u")

        assert only_line([record])["timestamp"] is None

    @pytest.mark.parametrize(
        ("window", "expected_texts"),
        [({"since": "2026-05-20"}, ["offset"]), ({"until": "2026-05-19"}, [])],
        ids=["since-the-utc-day", "until-the-local-day"],
    )
    def test_a_non_z_offset_timestamp_is_windowed_by_its_utc_day_and_emitted_in_utc(self, window, expected_texts):
        local_evening_is_the_next_utc_day = "2026-05-19T23:30:00-05:00"
        record = with_fields(user_prompt("offset"), timestamp=local_evening_is_the_next_utc_day, uuid="u")

        lines = emitted([record], **window)

        assert [line["text"] for line in lines] == expected_texts
        assert [line["timestamp"] for line in emitted([record])] == ["2026-05-20T04:30:00+00:00"]

    @pytest.mark.parametrize("converter_error", [OverflowError, OSError], ids=["overflow-error", "os-error"])
    def test_a_prompt_or_asking_record_whose_timestamp_conversion_raises_reads_as_undated_and_the_run_continues(
        self, monkeypatch, converter_error,
    ):
        def failing_converter(_timestamp):
            raise converter_error("out of range")

        monkeypatch.setattr(correction_candidates.corpus, "_parse_ts", failing_converter)
        two_blocks = assistant_record([
            ask_user_question_block([question_spec("A?")], tool_use_id="toolu_a"),
            ask_user_question_block([question_spec("B?")], tool_use_id="toolu_b"),
        ])
        records = [
            prompt("first", 1, uuid="u1"), prompt("second", 2, uuid="u2"), two_blocks,
            ask_answer_record(tool_use_id="toolu_a", answers={"A?": "Yes"}),
            ask_answer_record(tool_use_id="toolu_b", answers={"B?": "No"}),
        ]

        windowed_candidates, windowed_counts = scan(records, since="2026-05-01")
        lines = emitted(records)

        assert windowed_candidates == []
        assert (windowed_counts["undated"], windowed_counts["ask_user_question_calls"]) == (4, 0)
        assert [(line["kind"], line["timestamp"]) for line in lines] == [
            ("prompt", None), ("prompt", None), ("question", None), ("question", None),
        ]

    def test_surviving_candidates_keep_the_exchange_and_id_they_have_without_a_window(self):
        records = scripted_session()
        records[2] = with_fields(records[2], timestamp=ts(1, day=18))
        records[10] = with_fields(records[10], timestamp=ts(4, day=18))

        everything = {line["id"]: line["exchange"] for line in emitted(records)}
        windowed = {line["id"]: line["exchange"] for line in emitted(records, since="2026-05-19")}

        assert windowed == {"sess-a:toolu_q1": 3, "sess-a:14": 4}
        assert everything == {"sess-a:2": 2, "sess-a:10": 3, **windowed}


# --- reference model and attribution ------------------------------------------------------------------------------


class TestReferenceRecord:
    def test_synthetic_record_is_skipped_for_the_reference(self):
        records = [
            assistant_text("real", timestamp=ts(1), model=SONNET),
            assistant_text("synthetic", timestamp=ts(2), model="<synthetic>"),
            prompt("go", 3),
        ]

        line = only_line(records)

        assert (line["model_family"], line["model"]) == ("sonnet", SONNET)

    @pytest.mark.parametrize("model", [ABSENT, "<synthetic>", 5, None], ids=["absent", "synthetic", "non-string", "null"])
    def test_no_qualifying_record_gives_unknown_and_null_and_raises_nothing(self, model):
        records = [assistant_text("reply", timestamp=ts(1), model=model), prompt("go", 2)]

        line = only_line(records)

        assert (line["model_family"], line["model"]) == ("unknown", None)

    @pytest.mark.parametrize("skill", [ABSENT, "", 5, ["claude:plan-it"]], ids=["absent", "empty", "int", "list"])
    def test_unusable_attribution_skill_gives_null(self, skill):
        records = [assistant_text("reply", timestamp=ts(1), attribution_skill=skill), prompt("go", 2)]

        assert only_line(records)["attribution_skill"] is None

    @pytest.mark.parametrize(
        ("raw_skill", "expected"),
        [("dir/sub/skill-x", "skill-x"), ("claude:plan-it", "claude:plan-it")],
        ids=["path-prefix-dropped", "plugin-prefix-kept"],
    )
    def test_attribution_skill_is_normalized(self, raw_skill, expected):
        records = [assistant_text("reply", timestamp=ts(1), attribution_skill=raw_skill), prompt("go", 2)]

        assert only_line(records)["attribution_skill"] == expected


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

    def test_answered_call_has_no_result_text(self):
        records = [ask_record([question_spec("Which?")]), ask_answer_record(answers={"Which?": "Yes"}, timestamp=ts(6))]

        assert only_line(records)["result_text"] is None

    def test_missing_result_counts_unanswered_question(self):
        candidates, counts = scan([ask_record([question_spec("Which?")])])

        assert candidates == []
        assert (counts["unanswered_question"], counts["ask_user_question_calls"]) == (1, 1)

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


# --- truncation ---------------------------------------------------------------------------------------------------


class TestTruncation:
    def test_preceding_text_keeps_its_tail_and_every_other_cut_field_keeps_its_head(self):
        records = [
            assistant_text("0123456789", timestamp=ts(1), model=SONNET),
            prompt("abcdefghij", 2, uuid="u1"),
            assistant_text("ABCDEFGHIJ", timestamp=ts(3)),
        ]

        line = only_line(records, truncate_chars=5)

        assert line["preceding_assistant_text"] == "(truncated, 10 chars total) …56789"
        assert line["following_assistant_text"] == "ABCDE… (truncated, 10 chars total)"
        assert line["text"] == "abcde… (truncated, 10 chars total)"

    def test_each_cut_field_is_named_once_per_cut_value(self):
        records = [
            prompt("go", 1),
            ask_record([question_spec("A long question?", ("Alpha option", "Beta option"), header="A long header")]),
            ask_answer_record(
                answers={"A long question?": "Alpha option"},
                annotations={"A long question?": {"notes": "long notes"}},
                timestamp=ts(6),
            ),
        ]

        candidates, _counts = scan(records, truncate_chars=4)

        cut_by_kind = {candidate.kind: Counter(candidate.truncated_fields) for candidate in candidates}
        assert cut_by_kind["question"] == Counter({
            "model": 1, "question": 1, "header": 1, "label": 2, "description": 2, "answer": 1, "notes": 1,
            "preceding_assistant_text": 1,
        })
        assert cut_by_kind["prompt"] == Counter({"following_assistant_text": 1})

    def test_a_slash_prompts_command_and_text_are_cut_at_the_head(self):
        record = with_fields(slash_invocation("plan-it", "abcdefghij"), timestamp=ts(1), uuid="u")

        (candidate,), _counts = scan([record], truncate_chars=5)

        assert candidate.record["text"] == "abcde… (truncated, 10 chars total)"
        assert candidate.record["command"] == "/plan… (truncated, 8 chars total)"
        assert Counter(candidate.truncated_fields) == Counter({"text": 1, "command": 1})

    def test_zero_keeps_everything(self):
        long_text = "x" * 5000
        records = [assistant_text(long_text, timestamp=ts(1)), prompt(long_text, 2)]

        line = only_line(records, truncate_chars=0)

        assert (line["preceding_assistant_text"], line["text"]) == (long_text, long_text)

    def test_a_small_limit_leaves_id_session_id_and_family_whole(self):
        long_session = "session-" + "s" * 40
        long_family = FAMILY + "-" + "f" * 40

        (candidate,), _counts = scan([prompt("go", 1)], session=long_session, family=long_family, truncate_chars=5)

        assert candidate.record["id"] == f"{long_session}:0"
        assert candidate.record["session_id"] == long_session
        assert candidate.record["family"] == long_family

    def test_model_and_question_fields_are_cut_at_the_limit(self):
        records = [
            prompt("go", 1),
            ask_record([question_spec("A long question?", ("Alpha option", "Beta option"), header="A long header")]),
            ask_answer_record(
                answers={"A long question?": "Alpha option"},
                annotations={"A long question?": {"notes": "long notes"}},
                timestamp=ts(6),
            ),
        ]

        line = [line for line in emitted(records, truncate_chars=4) if line["kind"] == "question"][0]

        entry = line["questions"][0]
        assert line["model"].startswith("clau… (truncated")
        assert entry["question"].startswith("A lo… (truncated")
        assert entry["header"].startswith("A lo… (truncated")
        assert entry["options"][0]["label"].startswith("Alph… (truncated")
        assert entry["options"][0]["description"].startswith("Alph… (truncated")
        assert entry["answer"].startswith("Alph… (truncated")
        assert entry["notes"].startswith("long… (truncated")


# --- dedup and ordering -------------------------------------------------------------------------------------------


class TestDedupAndOrder:
    def test_uuid_less_prompts_are_all_emitted_and_counted(self):
        records = [with_fields(user_prompt(f"prompt {n}"), timestamp=ts(n), uuid=ABSENT) for n in range(3)]

        kept, counts, _checks = run_files({"sess-a": records})

        assert len(kept) == 3
        assert counts["skipped"]["duplicate_prompt"] == 0

    def test_uuid_repeated_in_one_file_keeps_the_first_copy(self):
        records = [prompt("first copy", 1, uuid="same"), prompt("second copy", 2, uuid="same")]

        kept, counts, _checks = run_files({"sess-a": records})

        assert [candidate.record["text"] for candidate in kept] == ["first copy"]
        assert counts["skipped"]["duplicate_prompt"] == 1

    @pytest.mark.parametrize("arrival_order", [("sess-a", "sess-b"), ("sess-b", "sess-a")])
    def test_uuid_in_two_sessions_keeps_the_copy_whose_session_id_sorts_first(self, arrival_order):
        files = {"sess-a": [prompt("in a", 1, uuid="same")], "sess-b": [prompt("in b", 1, uuid="same")]}

        kept, counts, _checks = run_files({session: files[session] for session in arrival_order})

        assert [candidate.record["id"] for candidate in kept] == ["sess-a:0"]
        assert counts["skipped"]["duplicate_prompt"] == 1

    @pytest.mark.parametrize("arrival_order", [("-first-family", "-second-family"), ("-second-family", "-first-family")])
    def test_one_session_stem_under_two_families_keeps_the_copy_of_the_family_that_sorts_first(self, arrival_order):
        records = [prompt("same text", 1, uuid="same")]
        candidates = [candidate for family in arrival_order for candidate in scan(records, family=family)[0]]

        kept, duplicates = correction_candidates._dedup_and_order(candidates)

        assert [candidate.record["family"] for candidate in kept] == ["-first-family"]
        assert duplicates == Counter({"duplicate_prompt": 1})

    def test_tool_use_id_in_two_sessions_dedups_the_question(self):
        question_records = [
            prompt("go", 1),
            ask_record([question_spec("Which?")]),
            ask_answer_record(answers={"Which?": "Yes"}, timestamp=ts(6)),
        ]

        kept, counts, _checks = run_files({"sess-a": question_records, "sess-b": question_records})

        assert [candidate.record["id"] for candidate in kept if candidate.kind == "question"] == ["sess-a:toolu_q1"]
        assert counts["skipped"]["duplicate_question"] == 1

    def test_output_order_is_session_then_record_index_then_block_position(self):
        two_blocks = assistant_record(
            [
                ask_user_question_block([question_spec("A?")], tool_use_id="toolu_a"),
                ask_user_question_block([question_spec("B?")], tool_use_id="toolu_b"),
            ],
            timestamp=ts(2),
        )
        answers = [
            ask_answer_record(tool_use_id="toolu_a", answers={"A?": "x"}, timestamp=ts(3)),
            ask_answer_record(tool_use_id="toolu_b", answers={"B?": "y"}, timestamp=ts(4)),
        ]
        later_session = [prompt("in b", 1, uuid="b-uuid")]
        earlier_session = [prompt("in a", 1, uuid="a-uuid"), two_blocks, *answers]

        kept, _counts, _checks = run_files({"sess-b": later_session, "sess-a": earlier_session})

        assert [candidate.record["id"] for candidate in kept] == [
            "sess-a:0", "sess-a:toolu_a", "sess-a:toolu_b", "sess-b:0",
        ]


# --- serialization and record schema ------------------------------------------------------------------------------


class TestJsonlText:
    def test_awkward_text_serializes_to_one_ascii_line_ending_in_a_newline(self):
        awkward = 'line\nbreak\rreturn     \u0085 lone \ud800 {"kind":"scope"}'

        text = correction_candidates._jsonl_text([{"text": awkward}])

        assert text.isascii()
        assert text.endswith("\n")
        assert text.count("\n") == 1
        assert len(text.splitlines()) == 1
        assert json.loads(text)["text"] == awkward

    def test_every_record_is_followed_by_exactly_one_newline_the_last_included(self):
        assert correction_candidates._jsonl_text([{"a": 1}, {"b": 2}]) == '{"a":1}\n{"b":2}\n'

    def test_no_records_serialize_to_the_empty_text(self):
        assert correction_candidates._jsonl_text([]) == ""


class TestKeySets:
    def _lines(self) -> dict[str, dict]:
        records = [
            prompt("go", 1),
            ask_record([question_spec("Which?")]),
            ask_answer_record(answers={"Which?": "Yes"}, timestamp=ts(6)),
        ]
        return {line["kind"]: line for line in emitted(records)}

    def test_prompt_line_keys(self):
        assert set(self._lines()["prompt"]) == {
            "schema_version", "kind", "id", "session_id", "family", "timestamp", "exchange", "preceding_assistant_text",
            "following_assistant_text", "model_family", "model", "attribution_skill", "text", "command", "initial",
            "after_interrupt",
        }

    def test_question_line_keys(self):
        assert set(self._lines()["question"]) == {
            "schema_version", "kind", "id", "session_id", "family", "timestamp", "exchange", "preceding_assistant_text",
            "following_assistant_text", "model_family", "model", "attribution_skill", "answered", "result_text", "questions",
        }

    def test_question_entry_and_option_keys(self):
        entry = self._lines()["question"]["questions"][0]

        assert set(entry) == {"question", "header", "multi_select", "options", "answer", "answer_is_free_text", "notes"}
        assert set(entry["options"][0]) == {"label", "description"}

    def test_scope_record_keys(self):
        counts, checks = correction_candidates._counts_and_checks([], Counter())

        record = correction_candidates._scope_record(
            header="HEADER", generated_at=datetime(2026, 5, 19, 10, 0, 0, tzinfo=UTC), since=None, until=None,
            truncate_chars=2000, families={}, counts=counts, checks=checks,
        )

        assert set(record) == {
            "schema_version", "kind", "header", "do_not_publish", "generated_at", "since", "until", "truncate_chars",
            "families", "counts", "checks",
        }
        assert set(record["counts"]) == {"prompts", "slash_prompts", "questions", "ask_user_question_calls", "skipped"}
