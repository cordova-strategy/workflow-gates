"""correction_candidates' counting seam: scope-record counters, count relations, and conservation under mutation."""
from collections import Counter
from datetime import UTC, datetime, timedelta, timezone

import pytest
from transcript_analysis import corpus, correction_candidates, render

from ._compaction_context_helpers import (
    ABSENT,
    bash_input,
    bash_stdout,
    headless_prompt,
    interrupt_marker,
    local_command_stdout,
    sidechain,
    slash_invocation,
    user_prompt,
)
from ._correction_candidates_helpers import (
    SONNET,
    ask_answer_record,
    ask_record,
    ask_user_question_block,
    assistant_record,
    assistant_text,
    field_mutations,
    only_line,
    prompt,
    question_spec,
    run_files,
    run_main,
    scan,
    scripted_session,
    seed,
    slash_prompt_session,
    stub_git_check,
    text_block,
    ts,
    window_bounds,
    with_fields,
    written_lines,
)

# --- counters -----------------------------------------------------------------------------------------------------

_COUNTER_FIXTURE_TRUNCATE_CHARS = 20
_COUNTER_FIXTURE_SINCE = "2026-05-15"


def _counter_fixture() -> dict[str, list]:
    """Under the `_COUNTER_FIXTURE_SINCE` window, three sessions whose every counter is non-zero.

    They also hold out-of-window records of each skip kind. Session `sess-c` holds only losing duplicates, each carrying
    a trigger for every counter taken over emitted lines.
    """
    clock = iter(range(1, 3600))

    def stamped(rec: dict) -> dict:
        second = next(clock)
        return with_fields(rec, timestamp=ts(second // 60, second % 60))

    def out_of_window(rec: dict) -> dict:
        return with_fields(rec, timestamp=ts(1, day=10))

    def typed(text: str, uuid) -> dict:
        return stamped(with_fields(user_prompt(text), uuid=uuid))

    def many(count: int, build) -> list[dict]:
        return [stamped(build(n)) for n in range(count)]

    def asking(tool_use_id: str, questions, *, raw_input=ABSENT) -> dict:
        return stamped(assistant_record(
            [ask_user_question_block(questions, tool_use_id=tool_use_id, raw_input=raw_input)], model=SONNET,
        ))

    long_note = "a rather long note text"
    session_a = [
        typed("initial one", "ua-1"),
        typed("initial two", "ua-2"),
        stamped(with_fields(slash_invocation("scratch", "a long slash prompt argument text"), uuid="ua-slash")),
        stamped(assistant_text("a reply", model=SONNET)),
        typed("later one is longer than twenty", "ua-3"),
        typed("later two is rather wordy", "ua-4"),
        typed("later three is also long", ABSENT),
        stamped(with_fields(slash_invocation("scratch", "second words"), uuid="ua-slash2")),
        *many(21, lambda n: interrupt_marker()),
        *many(22, lambda n: slash_invocation(args=None)),
        *many(23, lambda n: local_command_stdout()),
        *many(12, lambda n: bash_input()),
        *many(12, lambda n: bash_stdout()),
        *many(25, lambda n: user_prompt(f"peer {n}", origin={"kind": "peer"})),
        *many(26, lambda n: headless_prompt(f"headless {n}")),
        *many(27, lambda n: user_prompt(f"origin-less {n}", origin=ABSENT)),
        *[with_fields(user_prompt(f"undated {n}"), uuid=f"undated-{n}", timestamp=ABSENT) for n in range(33)],
        *["not a record"] * 33,
        asking(
            "toolu_q1",
            [
                question_spec("Pick one?"),
                question_spec("Pick many?", ("a", "b"), multi_select=True),
                question_spec("Unanswered entry?"),
            ],
        ),
        out_of_window(ask_record([question_spec("Pick one?")], tool_use_id="toolu_q1")),
        stamped(ask_answer_record(
            tool_use_id="toolu_q1",
            answers={"Pick one?": "Yes", "Pick many?": "a, b"},
            annotations={name: {"notes": long_note} for name in ("Pick one?", "Pick many?", "Unanswered entry?")},
        )),
        asking("toolu_q2", [question_spec("Name?", ("x", "y")), question_spec("Other?", ("x", "y"))]),
        stamped(ask_answer_record(
            tool_use_id="toolu_q2", answers={"Name?": "typed text that is long", "Other?": "more typed text, long"},
        )),
        asking("toolu_q3", [question_spec("Declined?")]),
        stamped(ask_answer_record(
            tool_use_id="toolu_q3", tool_use_result="declined", content="The user declined to answer.",
        )),
        *[asking(f"toolu_bad{n}", [], raw_input={}) for n in range(29)],
        *[asking(f"toolu_open{n}", [question_spec("Open?")]) for n in range(30)],
        out_of_window(interrupt_marker()),
        out_of_window(slash_invocation(args=None)),
        out_of_window(local_command_stdout()),
        out_of_window(bash_input()),
        out_of_window(user_prompt("old peer", origin={"kind": "peer"})),
        out_of_window(headless_prompt("old headless")),
        out_of_window(user_prompt("old origin-less", origin=ABSENT)),
        out_of_window(with_fields(user_prompt("old copy"), uuid="ua-1")),
        out_of_window(assistant_record([ask_user_question_block([], tool_use_id="toolu_old_bad", raw_input={})])),
        out_of_window(ask_record([question_spec("Old open?")], tool_use_id="toolu_old_open")),
        {"type": "user", "message": "text", "timestamp": ts(1, day=10)},
    ]
    session_b = [
        with_fields(typed("first no origin", "ub-1"), origin=ABSENT),
        stamped(assistant_text("b reply", model=SONNET)),
        with_fields(typed("second no origin", "ub-2"), origin=ABSENT),
        with_fields(typed("third no origin", ABSENT), origin=ABSENT),
        with_fields(typed("fourth no origin", "ub-4"), origin=ABSENT),
        *many(28, lambda n: user_prompt(f"see task-notification> {n}", origin=ABSENT)),
        out_of_window(user_prompt("old see task-notification> x", origin=ABSENT)),
    ]
    session_c = [
        *many(11, lambda n: with_fields(slash_invocation("scratch", "a long slash prompt argument text"), uuid="ua-slash")),
        *many(10, lambda n: with_fields(user_prompt("a copy that is far too long"), uuid="ua-4")),
        *many(10, lambda n: with_fields(user_prompt("initial one"), uuid="ua-1")),
        *[
            asking(
                "toolu_q1",
                [
                    question_spec("Pick many?", ("a", "b"), multi_select=True),
                    question_spec("Typed?", ("x", "y")),
                    question_spec("Nothing?"),
                ],
            )
            for _ in range(32)
        ],
        stamped(ask_answer_record(
            tool_use_id="toolu_q1", answers={"Typed?": "free text"}, annotations={"Typed?": {"notes": long_note}},
        )),
    ]
    return {"sess-a": session_a, "sess-b": session_b, "sess-c": session_c}


_WINDOWED_SKIPPED = {
    "interrupt": 21, "slash_command": 22, "local_command": 23, "bash_mode": 24, "non_human_origin": 25, "headless": 26,
    "no_origin_after_origin": 27, "notification_text": 28, "malformed_question": 29, "unanswered_question": 30,
    "duplicate_prompt": 31, "duplicate_question": 32, "undated": 33, "uninterpretable": 34,
}
_EXPECTED_CHECKS = {
    "questions_answered": 2,
    "result_types": {"dict": 2, "str": 1},
    "answered_entries": 5,
    "null_answers": 1,
    "free_text_answers": 2,
    "multi_select_entries": 1,
    "truncated_fields": {"answer": 2, "notes": 3, "result_text": 1, "text": 4},
    "failed_relations": [],
}


class TestCountersAndChecks:
    def test_one_fixture_gives_every_counter_a_non_zero_value_and_both_dicts_match_whole_under_a_window(self):
        _kept, counts, checks = run_files(
            _counter_fixture(), since=_COUNTER_FIXTURE_SINCE, truncate_chars=_COUNTER_FIXTURE_TRUNCATE_CHARS,
        )

        assert counts == {
            "prompts": 11,
            "slash_prompts": 2,
            "questions": 3,
            "ask_user_question_calls": 94,
            "skipped": _WINDOWED_SKIPPED,
        }
        assert checks == _EXPECTED_CHECKS

    def test_without_a_window_out_of_window_records_count_and_undated_ones_are_emitted(self):
        _kept, counts, checks = run_files(_counter_fixture(), truncate_chars=_COUNTER_FIXTURE_TRUNCATE_CHARS)

        assert counts == {
            "prompts": 44,
            "slash_prompts": 2,
            "questions": 3,
            "ask_user_question_calls": 97,
            "skipped": {
                **{kind: _WINDOWED_SKIPPED[kind] + 1 for kind in (
                    "interrupt", "slash_command", "local_command", "bash_mode", "non_human_origin", "headless",
                    "no_origin_after_origin", "notification_text", "malformed_question", "unanswered_question",
                    "duplicate_prompt", "duplicate_question",
                )},
                "undated": 0,
                "uninterpretable": 34,
            },
        }
        assert checks == _EXPECTED_CHECKS

    def test_emitted_line_count_per_kind_equals_the_counts_despite_cross_session_duplicates(self):
        kept, counts, _checks = run_files(
            _counter_fixture(), since=_COUNTER_FIXTURE_SINCE, truncate_chars=_COUNTER_FIXTURE_TRUNCATE_CHARS,
        )

        assert sum(1 for candidate in kept if candidate.kind == "prompt") == counts["prompts"]
        assert sum(1 for candidate in kept if candidate.kind == "question") == counts["questions"]

    def test_result_types_tallies_by_type_with_absent_for_a_missing_key(self):
        records = [
            ask_record([question_spec("A?")], tool_use_id="toolu_a"),
            ask_answer_record(tool_use_id="toolu_a", answers={"A?": "x"}, timestamp=ts(6)),
            ask_record([question_spec("B?")], tool_use_id="toolu_b", minute=7),
            with_fields(ask_answer_record(tool_use_id="toolu_b", timestamp=ts(8)), toolUseResult=ABSENT),
        ]

        _kept, _counts, checks = run_files({"sess-a": records})

        assert checks["result_types"] == {"absent": 1, "dict": 1}

    def test_a_slash_prompt_counts_as_a_prompt_and_a_slash_prompt(self):
        records = [
            with_fields(slash_invocation("plan-it", "draft"), timestamp=ts(1), uuid="s1"),
            assistant_text("reply", timestamp=ts(2)),
            prompt("typed", 3),
        ]

        _kept, counts, _checks = run_files({"sess-a": records})

        assert (counts["prompts"], counts["slash_prompts"]) == (2, 1)


class TestCommandScopeRecord:
    @pytest.mark.parametrize(
        ("window_flags", "since"),
        [
            pytest.param(("--since", _COUNTER_FIXTURE_SINCE), _COUNTER_FIXTURE_SINCE, id="windowed"),
            pytest.param((), None, id="unwindowed"),
        ],
    )
    def test_the_command_writes_the_counts_and_checks_the_per_file_pipeline_gives_for_the_counter_fixture(
        self, fake_projects, tmp_path, monkeypatch, capsys, window_flags, since,
    ):
        stub_git_check(monkeypatch)
        fixture = _counter_fixture()
        for session, records in fixture.items():
            seed(fake_projects, records, f"{session}.jsonl")
        out = tmp_path / "run.jsonl"
        _kept, expected_counts, expected_checks = run_files(
            fixture, since=since, truncate_chars=_COUNTER_FIXTURE_TRUNCATE_CHARS,
        )

        status, _stdout, _stderr = run_main(
            monkeypatch, capsys, "--projects", "*", *window_flags,
            "--truncate-chars", str(_COUNTER_FIXTURE_TRUNCATE_CHARS), "--out", str(out),
        )

        scope_record = written_lines(out)[0]
        assert status == 0
        assert scope_record["counts"] == expected_counts
        assert scope_record["checks"] == expected_checks


class TestScopeRecord:
    def test_generated_at_is_written_in_utc_whatever_the_offset_it_was_given(self):
        counts, checks = correction_candidates._counts_and_checks([], Counter())
        two_hours_ahead = timezone(timedelta(hours=2))

        record = correction_candidates._scope_record(
            header="HEADER", generated_at=datetime(2026, 5, 19, 12, 0, 7, tzinfo=two_hours_ahead), since=None, until=None,
            truncate_chars=2000, families={}, counts=counts, checks=checks,
        )

        assert record["generated_at"] == "2026-05-19T10:00:07+00:00"

    def test_fields_are_the_arguments_by_value(self):
        counts, checks = correction_candidates._counts_and_checks([], Counter())
        generated_at = datetime(2026, 5, 19, 10, 0, 7, 500000, tzinfo=UTC)

        record = correction_candidates._scope_record(
            header="HEADER", generated_at=generated_at, since="2026-05-01", until="2026-05-19", truncate_chars=2000,
            families={"b": 1, "a": 2}, counts=counts, checks=checks,
        )

        assert record == {
            "schema_version": 1,
            "kind": "scope",
            "header": "HEADER",
            "do_not_publish": correction_candidates._RAW_TEXT_NOTICE,
            "generated_at": "2026-05-19T10:00:07+00:00",
            "since": "2026-05-01",
            "until": "2026-05-19",
            "truncate_chars": 2000,
            "families": {"a": 2, "b": 1},
            "counts": counts,
            "checks": checks,
        }
        assert list(record["families"]) == ["a", "b"]


# --- relations ----------------------------------------------------------------------------------------------------


def _checks(**overrides) -> dict:
    healthy = {
        "questions_answered": 2, "result_types": {"dict": 2}, "answered_entries": 4, "null_answers": 1,
        "free_text_answers": 1,
    }
    return {**healthy, **overrides}


_RELATION_CASES = [
    pytest.param("answers_read", _checks(), [], id="answers_read-healthy"),
    pytest.param(
        "answers_read", _checks(result_types={}, questions_answered=0, answered_entries=0, null_answers=0,
                                free_text_answers=0),
        [], id="answers_read-zero-population",
    ),
    pytest.param(
        "answers_read", _checks(result_types={"dict": 1}, questions_answered=1, answered_entries=1, null_answers=0,
                                free_text_answers=0),
        [], id="answers_read-single-entry",
    ),
    pytest.param(
        "answers_read", _checks(questions_answered=0, answered_entries=0, null_answers=0, free_text_answers=0),
        ["answers_read"], id="answers_read-fails-alone",
    ),
    pytest.param("answers_keyed", _checks(), [], id="answers_keyed-healthy"),
    pytest.param(
        "answers_keyed", _checks(answered_entries=0, null_answers=0, free_text_answers=0), [],
        id="answers_keyed-zero-population",
    ),
    pytest.param(
        "answers_keyed", _checks(answered_entries=1, null_answers=0, free_text_answers=0), [],
        id="answers_keyed-single-entry",
    ),
    pytest.param(
        "answers_keyed", _checks(answered_entries=2, null_answers=2, free_text_answers=0), ["answers_keyed"],
        id="answers_keyed-fails-alone",
    ),
    pytest.param("labels_matched", _checks(), [], id="labels_matched-healthy"),
    pytest.param(
        "labels_matched", _checks(answered_entries=2, null_answers=2, free_text_answers=0), ["answers_keyed"],
        id="labels_matched-zero-population-leaves-only-answers_keyed",
    ),
    pytest.param(
        "labels_matched", _checks(answered_entries=1, null_answers=0, free_text_answers=0), [],
        id="labels_matched-single-entry-selected",
    ),
    pytest.param(
        "labels_matched", _checks(answered_entries=1, null_answers=0, free_text_answers=1), ["labels_matched"],
        id="labels_matched-single-typed-answer-fails",
    ),
    pytest.param(
        "labels_matched", _checks(answered_entries=4, null_answers=1, free_text_answers=3), ["labels_matched"],
        id="labels_matched-fails-alone",
    ),
]


class TestFailedRelations:
    @pytest.mark.parametrize(("_relation", "checks", "expected"), _RELATION_CASES)
    def test_each_input_fails_exactly_the_expected_relations(self, _relation, checks, expected):
        assert correction_candidates._failed_relations(checks) == expected

    def test_two_failures_are_reported_in_sorted_order(self):
        checks = _checks(questions_answered=0, answered_entries=2, null_answers=2, free_text_answers=0)

        assert correction_candidates._failed_relations(checks) == ["answers_keyed", "answers_read"]

    def test_an_empty_input_fails_nothing(self):
        _counts, checks = correction_candidates._counts_and_checks([], Counter())

        assert checks["failed_relations"] == []

    def test_a_prompts_only_run_fails_nothing(self):
        _kept, _counts, checks = run_files({"sess-a": [prompt("go", 1)]})

        assert checks["failed_relations"] == []

    @pytest.mark.parametrize("session", [scripted_session, slash_prompt_session], ids=["session-one", "session-two"])
    def test_each_scripted_session_fails_nothing(self, session):
        _kept, _counts, checks = run_files({"sess-a": session()})

        assert checks["failed_relations"] == []


# --- conservation under mutation ----------------------------------------------------------------------------------


def _counted_ask_blocks(records, *, windowed: bool) -> int:
    """AskUserQuestion blocks in in-window, interpretable, main-thread assistant records, counted independently of the module."""
    total = 0
    for rec in records:
        if not isinstance(rec, dict) or rec.get("isSidechain") or not render._is_interpretable(rec):
            continue
        if rec.get("type") != "assistant":
            continue
        if windowed:
            timestamp = rec.get("timestamp")
            if not isinstance(timestamp, str) or corpus._parse_ts(timestamp) is None:
                continue
        content = (rec.get("message") or {}).get("content")
        if isinstance(content, list):
            total += sum(
                1 for block in content
                if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "AskUserQuestion"
            )
    return total


_PROMPT_SKIP_KINDS = (
    "interrupt", "slash_command", "local_command", "bash_mode", "non_human_origin", "headless", "no_origin_after_origin",
    "notification_text", "duplicate_prompt",
)


def _prompt_shaped_records_to_account_for(records, window: dict) -> int:
    """Prompt-shaped records an emitted line, a prompt skip kind or `undated` must account for, by the module's own predicates."""
    since_ts, until_epoch = window_bounds(**window)
    total = 0
    for rec in records:
        if not isinstance(rec, dict) or rec.get("isSidechain") or not render._is_interpretable(rec):
            continue
        if rec.get("type") != "user" or not correction_candidates._is_prompt_shaped(rec):
            continue
        epoch = correction_candidates._record_epoch(rec)
        if (bool(window) and epoch is None) or correction_candidates._in_window(epoch, since_ts, until_epoch):
            total += 1
    return total


def _value_at(root, path: tuple):
    for step in path:
        root = root[step]
    return root


class TestConservationUnderMutation:
    def _base_session(self) -> list[dict]:
        return [
            prompt("go", 1),
            assistant_record(
                [text_block("asking"), ask_user_question_block([question_spec("Which?")]),
                 ask_user_question_block([question_spec("Other?")], tool_use_id="toolu_q2")],
                timestamp=ts(2), model=SONNET, attribution_skill="claude:plan-it",
            ),
            ask_answer_record(answers={"Which?": "Yes"}, timestamp=ts(3)),
            assistant_text("done", timestamp=ts(4)),
        ]

    @pytest.mark.parametrize("mutated_position", [0, 1, 2, 3], ids=["prompt", "asking", "answer", "assistant"])
    @pytest.mark.parametrize(
        "window",
        [{}, {"since": "2026-05-01"}, {"until": "2026-05-19"}],
        ids=["no-window", "since-only", "until-only"],
    )
    def test_no_mutation_raises_and_every_call_leaves_through_a_counted_path(self, mutated_position, window):
        base = self._base_session()
        walked_paths = []
        replacement_types = set()

        for path, mutated in field_mutations(base[mutated_position]):
            walked_paths.append(path)
            replacement_types.add(type(_value_at(mutated, path)))
            records = [*base[:mutated_position], mutated, *base[mutated_position + 1:]]
            failure_context = f"path {path!r} replaced by {mutated!r}"

            kept, counts, checks = run_files({"sess-a": records}, **window)
            scope_record = correction_candidates._scope_record(
                header="H", generated_at=datetime(2026, 5, 19, tzinfo=UTC), since=None, until=None, truncate_chars=2000,
                families={"f": 1}, counts=counts, checks=checks,
            )
            correction_candidates._jsonl_text([scope_record, *(candidate.record for candidate in kept)])

            skipped = counts["skipped"]
            calls = counts["ask_user_question_calls"]
            assert calls == _counted_ask_blocks(records, windowed=bool(window)), failure_context
            assert calls == (
                counts["questions"] + skipped["malformed_question"] + skipped["unanswered_question"]
                + skipped["duplicate_question"]
            ), failure_context
            undated_ask_blocks = (
                _counted_ask_blocks(records, windowed=False) - _counted_ask_blocks(records, windowed=True)
                if window else 0
            )
            assert (
                counts["prompts"] + sum(skipped[kind] for kind in _PROMPT_SKIP_KINDS) + skipped["undated"]
                == _prompt_shaped_records_to_account_for(records, window) + undated_ask_blocks
            ), failure_context

        assert replacement_types == {type(None), str, int, list, dict}
        if mutated_position == 1:
            assert any(
                path[:2] == ("message", "content") and path[3:] == ("input", "questions", 0) for path in walked_paths
            )

    def test_non_dict_record_and_non_dict_message_count_uninterpretable(self):
        records = [
            "junk", 5, None, {"type": "user", "message": "text"},
            {"type": "user", "message": {"content": [{"type": "text", "text": 5}]}},
        ]

        candidates, counts = scan(records)

        assert candidates == []
        assert counts["uninterpretable"] == 5

    def test_uninterpretable_record_changes_no_file_state(self):
        records = [
            {"type": "assistant", "message": "not a dict", "origin": {"kind": "human"}},
            with_fields(user_prompt("first", origin=ABSENT), timestamp=ts(1), uuid="u1"),
        ]

        line = only_line(records)

        assert line["initial"] is True

    def test_sidechain_record_with_an_origin_does_not_set_the_file_origin_state(self):
        records = [sidechain(prompt("side", 1)), with_fields(prompt("plain", 2), origin=ABSENT)]

        candidates, counts = scan(records)

        assert [candidate.record["text"] for candidate in candidates] == ["plain"]
        assert counts["no_origin_after_origin"] == 0

    def test_sidechain_record_is_ignored_not_counted(self):
        candidates, counts = scan([sidechain(prompt("side", 1))])

        assert candidates == []
        assert dict(counts) == {}
