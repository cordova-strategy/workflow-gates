"""Tests for ledger_dispositions: terminal-row counts over this repository's review-ledger files."""
import json
import logging
import os
import subprocess
import sys
import threading
import time
import warnings
from pathlib import Path

import pytest
from helpers import init_git_repo
from transcript_analysis import author_outcome, corpus, ledger_dispositions, publication_scope

from ._review_round_corpus_helpers import _LEAK_SENTINEL_PREFIX, _leak_sentinel
from .conftest import (
    _WINDOW_EDGE_TIMESTAMPS,
    _clean_env,
    _git,
    _ledger_row,
    _seed_session,
    _write_jsonl,
    _write_named_ledger_file,
    _write_this_repo_ledger_file,
)

# The window `_WINDOW_EDGE_TIMESTAMPS` is written for.
_WINDOW_START = corpus._parse_ts("2026-08-10T00:00:00Z")
_WINDOW_END = corpus._parse_ts("2026-08-12T00:00:00Z") + 86400
_IN_WINDOW = "2026-08-11T10:00:00Z"
_BEFORE_WINDOW = "2026-08-01T10:00:00Z"
_ADDRESS = author_outcome._DISPOSITION_ADDRESS
_DEFER = author_outcome._DISPOSITION_DEFER
_SETTLED = author_outcome._DISPOSITION_SETTLED
_ABSENT = object()
_REVIEW_LEDGER_SH = Path(__file__).parent.parent / "review-ledger.sh"
# An open of a FIFO with no writer blocks forever, so a read that opens one is told apart from a refusal by this deadline.
_FIFO_READ_DEADLINE_SECONDS = 10


def _row(disposition: str, row_id: str | None, *, ref: str = "", decided_by: str = "",
         event_time: str = _IN_WINDOW, session_id: str = "session-a") -> dict:
    """A row in the writer's full shape; a row_id of None omits the key."""
    return _ledger_row(
        round=1, disposition=disposition, id=row_id, ref=ref, decided_by=decided_by, reviewers=["staff-sdet"],
        session_id=session_id, event_time=event_time, schema_version=3,
    )


def _with_field(row: dict, field: str, value: object) -> dict:
    changed = dict(row)
    if value is _ABSENT:
        del changed[field]
    else:
        changed[field] = value
    return changed


def _printed_text(capsys) -> str:
    captured = capsys.readouterr()
    return captured.out + captured.err


def _captured_text(capfd) -> str:
    """Everything written to either file descriptor, which also catches a write that bypasses `sys.stderr`."""
    captured = capfd.readouterr()
    return captured.out + captured.err


def _leaking_row(label: str, disposition: str, *, with_id: bool = True, event_time: str = _IN_WINDOW, **changes) -> dict:
    """A row whose every string field holds a sentinel named for `label`."""
    row = _row(
        disposition, _leak_sentinel(f"{label}-id") if with_id else None, ref=_leak_sentinel(f"{label}-ref"),
        decided_by=_leak_sentinel(f"{label}-decided-by"), event_time=event_time,
        session_id=_leak_sentinel(f"{label}-session"),
    )
    row.update(
        finding=_leak_sentinel(f"{label}-finding"), rationale=_leak_sentinel(f"{label}-rationale"),
        engineer_quote=_leak_sentinel(f"{label}-engineer-quote"), source=_leak_sentinel(f"{label}-source"),
        authoring_agent=_leak_sentinel(f"{label}-authoring-agent"),
        authoring_effort=_leak_sentinel(f"{label}-authoring-effort"), reviewers=[_leak_sentinel(f"{label}-reviewer")],
    )
    return {**row, **changes}


def _every_row_class_rows() -> list[dict]:
    """One row of every class the reader tells apart, with a sentinel in each of its string fields."""
    after_window = "2026-08-13T00:00:00Z"
    superseded = _leaking_row("superseded-defer", _DEFER)
    rows = [
        _leaking_row("terminal-defer", _DEFER),
        superseded,
        _leaking_row("superseder-address", _ADDRESS, ref=superseded["id"]),
        _leaking_row("terminal-address", _ADDRESS),
        _leaking_row("terminal-settled", _SETTLED),
        _leaking_row("id-less", _ADDRESS, with_id=False),
        _leaking_row("clean", "CLEAN"),
        _leaking_row("consult", "CONSULT"),
        _leaking_row("carry-defer", _DEFER, decided_by=author_outcome._DECIDED_BY_CARRY),
        _leaking_row("carry-settled", _SETTLED, decided_by=author_outcome._DECIDED_BY_CARRY),
        _leaking_row("unknown", _leak_sentinel("unknown-disposition")),
        _leaking_row("unknown-before", _leak_sentinel("unknown-before-disposition"), event_time=_BEFORE_WINDOW),
    ]
    for disposition in (_ADDRESS, _DEFER, _SETTLED):
        rows.append(_leaking_row(f"before-{disposition}", disposition, event_time=_BEFORE_WINDOW))
        rows.append(_leaking_row(f"after-{disposition}", disposition, event_time=after_window))
    bad_values = {
        "disposition": [_leak_sentinel("left-out-disposition-value")],
        "id": [_leak_sentinel("left-out-id-value")],
        "ref": [_leak_sentinel("left-out-ref-value")],
        "decided_by": [_leak_sentinel("left-out-decided-by-value")],
        "event_time": _leak_sentinel("left-out-event-time-value"),
        "session_id": [_leak_sentinel("left-out-session-id-value")],
    }
    for field, bad_value in bad_values.items():
        rows.append({**_leaking_row(f"left-out-{field}", _ADDRESS), field: bad_value})
    return rows


def _terminal(*, address: int = 0, defer: int = 0, settled: int = 0) -> dict[str, int]:
    return {_ADDRESS: address, _DEFER: defer, _SETTLED: settled}


def _left_out(**by_field: int) -> dict[str, int]:
    return {field: by_field.get(field, 0) for field in ledger_dispositions._LEFT_OUT_FIELDS}


_BASELINE = {
    "directory_state": ledger_dispositions._DIRECTORY_PRESENT, "files_read": 1, "unreadable_files": 0,
    "terminal_by_disposition": _terminal(), "id_less_disposition_rows": 0, "unknown_disposition_rows": 0,
    "left_out_by_field": _left_out(), "sessions_with_disposition_row": 0, "sessions_covered_by_scan": 0,
}


def _expect(**changes) -> ledger_dispositions.LedgerDispositionCounts:
    return ledger_dispositions.LedgerDispositionCounts(**{**_BASELINE, **changes})


class _Ledger:
    """One config directory and the worktree path its ledger files are named for."""

    def __init__(self, config_root: Path, worktree: Path):
        self.config_root = config_root
        self.worktree = worktree
        self.directory = config_root / author_outcome._REVIEW_LEDGER_DIRNAME

    def write(self, slot: str, rows: list[dict]) -> Path:
        return _write_this_repo_ledger_file(self.config_root, self.worktree, slot, rows)

    def count(self, scanned=()) -> ledger_dispositions.LedgerDispositionCounts:
        return ledger_dispositions.count_ledger_dispositions(
            self.config_root, [str(self.worktree)], _WINDOW_START, _WINDOW_END, scanned,
        )


@pytest.fixture
def ledger(tmp_path) -> _Ledger:
    return _Ledger(tmp_path / "config", tmp_path / "checkout")


class TestTerminalRows:
    @pytest.mark.parametrize(
        ("disposition", "decided_by", "expected_terminal"),
        [
            (_ADDRESS, "", _terminal(address=1)),
            (_DEFER, "", _terminal(defer=1)),
            (_SETTLED, "engineer", _terminal(settled=1)),
            (_SETTLED, "plan-architect", _terminal(settled=1)),
        ],
    )
    def test_an_unsuperseded_disposition_row_in_the_window_is_terminal(
        self, ledger, disposition, decided_by, expected_terminal,
    ):
        ledger.write("session-a", [_row(disposition, "r1", decided_by=decided_by)])

        assert ledger.count() == _expect(terminal_by_disposition=expected_terminal, sessions_with_disposition_row=1)

    def test_a_relog_supersedes_the_row_it_names(self, ledger):
        ledger.write("session-a", [_row(_DEFER, "d1"), _row(_DEFER, "d2", ref="d1")])

        assert ledger.count() == _expect(terminal_by_disposition=_terminal(defer=1), sessions_with_disposition_row=1)

    def test_an_address_by_ref_supersedes_a_defer(self, ledger):
        ledger.write("session-a", [_row(_DEFER, "d1"), _row(_ADDRESS, "a1", ref="d1")])

        assert ledger.count() == _expect(terminal_by_disposition=_terminal(address=1), sessions_with_disposition_row=1)

    def test_a_chain_across_two_sessions_in_one_file_leaves_its_last_row(self, ledger):
        ledger.write("branch-1", [
            _row(_DEFER, "d1", session_id="session-a"),
            _row(_DEFER, "d2", ref="d1", session_id="session-b"),
            _row(_ADDRESS, "a3", ref="d2", session_id="session-a"),
        ])

        assert ledger.count() == _expect(terminal_by_disposition=_terminal(address=1), sessions_with_disposition_row=2)

    @pytest.mark.parametrize(
        ("carried_disposition", "decided_by", "expected_terminal"),
        [(_DEFER, "", _terminal(defer=1)), (_SETTLED, "engineer", _terminal(settled=1))],
        ids=["DEFER", "SETTLED"],
    )
    def test_a_carry_is_left_out_on_both_sides(self, ledger, carried_disposition, decided_by, expected_terminal):
        carry = _row(carried_disposition, "c1", ref="d1", decided_by="carry", session_id="session-carry")
        ledger.write("session-a", [_row(carried_disposition, "d1", decided_by=decided_by), carry])

        assert ledger.count() == _expect(terminal_by_disposition=expected_terminal, sessions_with_disposition_row=1)

    @pytest.mark.parametrize(
        ("carried_disposition", "decided_by"), [(_DEFER, ""), (_SETTLED, "engineer")], ids=["DEFER", "SETTLED"],
    )
    def test_a_carry_of_a_decision_made_before_the_window_counts_nothing(
        self, ledger, carried_disposition, decided_by,
    ):
        carry = _row(carried_disposition, "c1", ref="d1", decided_by="carry")
        ledger.write("session-a", [
            _row(carried_disposition, "d1", decided_by=decided_by, event_time=_BEFORE_WINDOW), carry,
        ])

        assert ledger.count() == _expect()


class TestSupersessionEdges:
    def test_a_self_ref_does_not_supersede_its_own_row(self, ledger):
        ledger.write("session-a", [_row(_DEFER, "d1", ref="d1")])

        assert ledger.count() == _expect(terminal_by_disposition=_terminal(defer=1), sessions_with_disposition_row=1)

    @pytest.mark.parametrize(
        ("later_disposition", "expected_terminal"),
        [(_DEFER, _terminal(defer=1)), (_ADDRESS, _terminal(address=1))],
    )
    def test_in_a_ref_cycle_only_the_later_row_supersedes(self, ledger, later_disposition, expected_terminal):
        earlier_disposition = _ADDRESS if later_disposition == _DEFER else _DEFER
        ledger.write("session-a", [
            _row(earlier_disposition, "x1", ref="x2"),
            _row(later_disposition, "x2", ref="x1"),
        ])

        assert ledger.count() == _expect(terminal_by_disposition=expected_terminal, sessions_with_disposition_row=1)

    @pytest.mark.parametrize(
        ("superseder_time", "expected_terminal"),
        [
            (_IN_WINDOW, _terminal(address=1)),
            ("2026-08-12T23:59:59Z", _terminal(address=1)),
            ("2026-08-13T00:00:00Z", _terminal(defer=1)),
        ],
        ids=["same second", "last second of the window", "after the window"],
    )
    def test_only_a_superseder_before_the_window_end_retires_a_row(self, ledger, superseder_time, expected_terminal):
        ledger.write("session-a", [_row(_DEFER, "d1"), _row(_ADDRESS, "a1", ref="d1", event_time=superseder_time)])

        assert ledger.count() == _expect(terminal_by_disposition=expected_terminal, sessions_with_disposition_row=1)

    def test_a_ref_resolves_within_its_own_file_only(self, ledger):
        ledger.write("session-a", [_row(_DEFER, "shared")])
        ledger.write("session-b", [_row(_DEFER, "shared"), _row(_ADDRESS, "a1", ref="shared")])

        assert ledger.count() == _expect(
            files_read=2, terminal_by_disposition=_terminal(address=1, defer=1), sessions_with_disposition_row=1,
        )

    def test_a_superseder_in_an_earlier_file_does_not_retire_a_row_in_a_later_file(self, ledger):
        ledger.write("session-a", [_row(_DEFER, "filler"), _row(_ADDRESS, "a1", ref="shared")])
        ledger.write("session-b", [_row(_DEFER, "shared")])

        assert ledger.count() == _expect(
            files_read=2, terminal_by_disposition=_terminal(address=1, defer=2), sessions_with_disposition_row=1,
        )

    def test_a_row_is_superseded_by_the_last_row_naming_it_not_the_first(self, ledger):
        ledger.write("session-a", [
            _row(_ADDRESS, "a1", ref="x1"),
            _row(_DEFER, "x1"),
            _row(_SETTLED, "s1", ref="x1", decided_by="engineer"),
        ])

        assert ledger.count() == _expect(
            terminal_by_disposition=_terminal(address=1, settled=1), sessions_with_disposition_row=1,
        )

    def test_a_superseder_is_positioned_by_file_order_not_event_time(self, ledger):
        ledger.write("session-a", [
            _row(_ADDRESS, "a1", ref="d1", event_time="2026-08-11T11:00:00Z"),
            _row(_DEFER, "d1", event_time="2026-08-11T09:00:00Z"),
        ])

        assert ledger.count() == _expect(
            terminal_by_disposition=_terminal(address=1, defer=1), sessions_with_disposition_row=1,
        )

    @pytest.mark.parametrize(
        ("superseder_time", "expected_terminal"),
        [
            ("2026-08-11T09:00:00Z", _terminal(address=1)),
            (_BEFORE_WINDOW, _terminal()),
        ],
        ids=["earlier in the window", "before the window"],
    )
    def test_a_later_in_file_superseder_retires_a_row_whatever_its_earlier_event_time(
        self, ledger, superseder_time, expected_terminal,
    ):
        ledger.write("session-a", [
            _row(_DEFER, "d1", event_time="2026-08-11T10:00:00Z"),
            _row(_ADDRESS, "a1", ref="d1", event_time=superseder_time),
        ])

        assert ledger.count() == _expect(terminal_by_disposition=expected_terminal, sessions_with_disposition_row=1)

    @pytest.mark.parametrize("neutral_disposition", ["CONSULT", "CLEAN"])
    def test_a_consult_or_clean_row_is_neither_terminal_nor_a_superseder(self, ledger, neutral_disposition):
        neutral = _row(neutral_disposition, "n1", ref="d1", session_id="session-neutral")
        ledger.write("session-a", [_row(_DEFER, "d1"), neutral])

        assert ledger.count() == _expect(terminal_by_disposition=_terminal(defer=1), sessions_with_disposition_row=1)

    @pytest.mark.parametrize("missing_id", [None, ""], ids=["no id key", "empty id"])
    def test_an_id_less_disposition_row_is_counted_apart_and_never_terminal(self, ledger, missing_id):
        ledger.write("session-a", [_row(_ADDRESS, missing_id)])

        assert ledger.count() == _expect(id_less_disposition_rows=1, sessions_with_disposition_row=1)

    @pytest.mark.parametrize(
        ("event_time", "expected_id_less_rows"),
        [
            ("2026-08-10T00:00:00Z", 1),
            ("2026-08-09T23:59:59Z", 0),
            ("2026-08-12T23:59:59Z", 1),
            ("2026-08-13T00:00:00Z", 0),
        ],
        ids=["at since_ts", "one second before since_ts", "one second before until_epoch", "at until_epoch"],
    )
    def test_an_id_less_disposition_row_is_counted_in_the_half_open_window_only(
        self, ledger, event_time, expected_id_less_rows,
    ):
        ledger.write("session-a", [_row(_ADDRESS, None, event_time=event_time)])

        assert ledger.count() == _expect(
            id_less_disposition_rows=expected_id_less_rows, sessions_with_disposition_row=expected_id_less_rows,
        )

    @pytest.mark.parametrize(
        ("unknown_event_time", "expected_unknown_rows"),
        [(_IN_WINDOW, 1), (_BEFORE_WINDOW, 0)],
        ids=["in the window", "before the window"],
    )
    def test_an_unknown_disposition_row_naming_a_terminal_row_does_not_supersede_it(
        self, ledger, unknown_event_time, expected_unknown_rows,
    ):
        unknown = _row("BANANA", "u1", ref="d1", session_id="session-unknown", event_time=unknown_event_time)
        ledger.write("session-a", [_row(_DEFER, "d1"), unknown])

        assert ledger.count() == _expect(
            terminal_by_disposition=_terminal(defer=1), unknown_disposition_rows=expected_unknown_rows,
            sessions_with_disposition_row=1,
        )

    def test_an_id_less_row_supersedes_nothing(self, ledger):
        ledger.write("session-a", [_row(_DEFER, "d1"), _row(_ADDRESS, None, ref="d1", session_id="session-b")])

        assert ledger.count() == _expect(
            terminal_by_disposition=_terminal(defer=1), id_less_disposition_rows=1, sessions_with_disposition_row=2,
        )


def _left_out_cases() -> list:
    wrong_types = {
        "disposition": [("absent", _ABSENT), ("null", None), ("int", 5), ("list", ["ADDRESS"])],
        "id": [("null", None), ("int", 5), ("list", ["r1"])],
        "ref": [("null", None), ("int", 5), ("dict", {"id": "r0"})],
        "decided_by": [("null", None), ("int", 5), ("bool", True)],
        "event_time": [
            ("absent", _ABSENT), ("null", None), ("int", 5), ("list", [_IN_WINDOW]),
            ("space separator", "2026-08-11 10:00:00Z"), ("no zone", "2026-08-11T10:00:00"),
            ("fractional seconds", "2026-08-11T10:00:00.000Z"), ("unpadded month", "2026-8-11T10:00:00Z"),
            ("trailing newline", "2026-08-11T10:00:00Z\n"), ("leading space", " 2026-08-11T10:00:00Z"),
            ("month 13", "2026-13-11T10:00:00Z"), ("fullwidth digits", "２０２６-08-11T10:00:00Z"),
            ("numeric offset", "2026-08-11T10:00:00+00:00"),
            ("no seconds", "2026-08-11T10:00Z"), ("hour only", "2026-08-11T10Z"),
            ("basic format", "20260811T100000Z"), ("lowercase t", "2026-08-11t10:00:00Z"),
        ],
        "session_id": [("null", None), ("int", 5), ("list", ["session-a"])],
    }
    return [
        pytest.param(field, value, id=f"{field}-{label}")
        for field, cases in wrong_types.items()
        for label, value in cases
    ]


# Pinned here, not read from the module, so reordering the module's own tuple fails the adjacent-pair test.
_READING_ORDER = ("disposition", "id", "ref", "decided_by", "event_time", "session_id")
_ADJACENT_FIELD_PAIRS = list(zip(_READING_ORDER, _READING_ORDER[1:], strict=False))
_ADJACENT_FIELD_PAIR_IDS = [f"{earlier}-before-{later}" for earlier, later in _ADJACENT_FIELD_PAIRS]


class TestFieldRules:
    @pytest.mark.parametrize(("field", "bad_value"), _left_out_cases())
    def test_a_row_with_a_wrong_typed_or_missing_field_is_left_out_under_that_field(self, ledger, field, bad_value):
        ledger.write("session-a", [_with_field(_row(_ADDRESS, "r1"), field, bad_value)])

        assert ledger.count() == _expect(left_out_by_field=_left_out(**{field: 1}))

    def test_the_published_left_out_counts_have_one_key_per_read_field(self, ledger):
        ledger.write("session-a", [_row(_ADDRESS, "r1")])

        assert set(ledger.count().left_out_by_field) == set(_READING_ORDER)

    def test_a_row_with_two_bad_fields_is_left_out_under_the_first_in_reading_order(self, ledger):
        row = _with_field(_with_field(_row(_ADDRESS, "r1"), "event_time", 5), "id", 5)
        ledger.write("session-a", [row, _row(_ADDRESS, "r2")])

        assert ledger.count() == _expect(
            left_out_by_field=_left_out(id=1), terminal_by_disposition=_terminal(address=1), sessions_with_disposition_row=1,
        )

    @pytest.mark.parametrize(("earlier_field", "later_field"), _ADJACENT_FIELD_PAIRS, ids=_ADJACENT_FIELD_PAIR_IDS)
    def test_a_row_bad_in_two_adjacent_fields_is_left_out_under_the_earlier(self, ledger, earlier_field, later_field):
        row = _with_field(_with_field(_row(_ADDRESS, "r1"), later_field, 5), earlier_field, 5)
        ledger.write("session-a", [row])

        assert ledger.count() == _expect(left_out_by_field=_left_out(**{earlier_field: 1}))

    @pytest.mark.parametrize(
        "bad_row",
        [
            _row("CLEAN", "x1"),
            _row("CONSULT", "x1"),
            _row(_DEFER, "x1", decided_by=author_outcome._DECIDED_BY_CARRY),
            _row(_ADDRESS, "x1", event_time=_BEFORE_WINDOW),
            _row(_ADDRESS, "x1", event_time="2026-08-13T00:00:00Z"),
            _row("BANANA", "x1"),
        ],
        ids=["CLEAN", "CONSULT", "carry", "before the window", "at until_epoch", "unknown disposition"],
    )
    def test_a_left_out_row_is_counted_whatever_its_disposition_or_date(self, ledger, bad_row):
        ledger.write("session-a", [_row(_ADDRESS, "r1"), _with_field(bad_row, "ref", 5)])

        assert ledger.count() == _expect(
            terminal_by_disposition=_terminal(address=1), left_out_by_field=_left_out(ref=1),
            sessions_with_disposition_row=1,
        )

    @pytest.mark.parametrize(
        "carried_disposition", [_ADDRESS, _DEFER, _SETTLED, "BANANA"], ids=["ADDRESS", "DEFER", "SETTLED", "unknown"],
    )
    def test_a_carry_row_is_counted_nowhere_whatever_its_disposition(self, ledger, carried_disposition):
        # A carry is skipped before the unknown-disposition check, so one with an unknown disposition counts as nothing.
        ledger.write("session-a", [_row(carried_disposition, "c1", decided_by=author_outcome._DECIDED_BY_CARRY)])

        assert ledger.count() == _expect()

    @pytest.mark.parametrize("absent_field", ["ref", "decided_by"])
    def test_an_absent_ref_or_decided_by_reads_as_empty(self, ledger, absent_field):
        ledger.write("session-a", [_with_field(_row(_ADDRESS, "r1"), absent_field, _ABSENT)])

        assert ledger.count() == _expect(terminal_by_disposition=_terminal(address=1), sessions_with_disposition_row=1)

    @pytest.mark.parametrize("slot", ["session-a", "0123abcd"], ids=["session file", "branch file"])
    @pytest.mark.parametrize("session_value", [_ABSENT, "", "bad/session"], ids=["no key", "empty", "invalid id"])
    def test_a_row_without_a_valid_session_id_counts_but_joins_no_session_line(self, ledger, slot, session_value):
        ledger.write(slot, [_with_field(_row(_ADDRESS, "r1"), "session_id", session_value)])

        assert ledger.count(scanned={"session-a", slot}) == _expect(terminal_by_disposition=_terminal(address=1))

    @pytest.mark.parametrize(
        ("event_time", "ledger_expectation", "_transcript_expectation"),
        [*_WINDOW_EDGE_TIMESTAMPS, ("2026-08-09T23:59:59Z", "out", "out")],
    )
    def test_event_time_decides_membership_by_the_writers_form(
        self, ledger, event_time, ledger_expectation, _transcript_expectation,
    ):
        ledger.write("session-a", [_row(_ADDRESS, "r1", event_time=event_time)])

        expected = {
            "in": _expect(terminal_by_disposition=_terminal(address=1), sessions_with_disposition_row=1),
            "out": _expect(),
            "event_time": _expect(left_out_by_field=_left_out(event_time=1)),
        }[ledger_expectation]
        assert ledger.count() == expected

    @pytest.mark.parametrize("unknown_disposition", ["BANANA", "address", "", "ADDRESS "])
    def test_an_unknown_disposition_is_counted_apart(self, ledger, unknown_disposition):
        ledger.write("session-a", [_row(unknown_disposition, "r1")])

        assert ledger.count() == _expect(unknown_disposition_rows=1)

    def test_an_unknown_disposition_and_its_decided_by_reach_neither_the_counts_nor_a_stream(
        self, ledger, capsys, caplog, recwarn,
    ):
        row = _row(_leak_sentinel("disposition"), "r1", decided_by=_leak_sentinel("decided-by"))
        ledger.write("session-a", [row])

        counts = ledger.count()

        assert counts == _expect(unknown_disposition_rows=1)
        assert _LEAK_SENTINEL_PREFIX not in repr(counts) + _printed_text(capsys)
        assert caplog.records == []
        assert not recwarn.list

    def test_a_left_out_rows_bad_value_reaches_neither_the_counts_nor_a_stream(
        self, ledger, capsys, caplog, recwarn,
    ):
        ledger.write("session-a", [_with_field(_row(_ADDRESS, "r2"), "ref", [_leak_sentinel("left-out-ref")])])

        counts = ledger.count()

        assert counts == _expect(left_out_by_field=_left_out(ref=1))
        assert _LEAK_SENTINEL_PREFIX not in repr(counts) + _printed_text(capsys)
        assert caplog.records == []
        assert not recwarn.list

    def test_a_counted_settled_rows_decided_by_reaches_neither_the_counts_nor_a_stream(
        self, ledger, capsys, caplog, recwarn,
    ):
        ledger.write("session-a", [_row(_SETTLED, "s1", decided_by=_leak_sentinel("decided-by"))])

        counts = ledger.count()

        assert counts == _expect(terminal_by_disposition=_terminal(settled=1), sessions_with_disposition_row=1)
        assert _LEAK_SENTINEL_PREFIX not in repr(counts) + _printed_text(capsys)
        assert caplog.records == []
        assert not recwarn.list

    def test_a_carry_rows_id_and_session_reach_neither_the_counts_nor_a_stream(
        self, ledger, capsys, caplog, recwarn,
    ):
        carry = _row(
            _SETTLED, _leak_sentinel("carry-id"), ref="s1", decided_by="carry", session_id=_leak_sentinel("carry-session"),
        )
        ledger.write("session-a", [_row(_SETTLED, "s1", decided_by="engineer"), carry])

        counts = ledger.count()

        assert counts == _expect(terminal_by_disposition=_terminal(settled=1), sessions_with_disposition_row=1)
        assert _LEAK_SENTINEL_PREFIX not in repr(counts) + _printed_text(capsys)
        assert caplog.records == []
        assert not recwarn.list

    def test_the_stream_check_detects_a_sentinel_printed_to_either_stream(self, capsys):
        print(_leak_sentinel("control-out"))
        print(_leak_sentinel("control-err"), file=sys.stderr)

        printed = _printed_text(capsys)

        assert _leak_sentinel("control-out") in printed
        assert _leak_sentinel("control-err") in printed

    def test_no_row_of_any_class_reaches_the_counts_a_stream_the_log_or_a_warning(
        self, ledger, capfd, caplog, recwarn,
    ):
        ledger.write(_leak_sentinel("file-slot"), _every_row_class_rows())
        scanned = {_leak_sentinel("terminal-defer-session"), _leak_sentinel("clean-session"), "session-never-seen"}

        counts = ledger.count(scanned=scanned)

        assert counts == _expect(
            terminal_by_disposition=_terminal(address=2, defer=1, settled=1), id_less_disposition_rows=1,
            unknown_disposition_rows=1, left_out_by_field=_left_out(**dict.fromkeys(_READING_ORDER, 1)),
            sessions_with_disposition_row=6, sessions_covered_by_scan=1,
        )
        assert _LEAK_SENTINEL_PREFIX not in repr(counts)
        assert _LEAK_SENTINEL_PREFIX not in _captured_text(capfd)
        assert caplog.records == []
        assert not recwarn.list

    @pytest.mark.parametrize("file_descriptor", [1, 2], ids=["stdout", "stderr"])
    def test_the_stream_check_detects_a_sentinel_written_to_a_file_descriptor_directly(self, capfd, file_descriptor):
        os.write(file_descriptor, _leak_sentinel("control-fd").encode())

        assert _leak_sentinel("control-fd") in _captured_text(capfd)

    def test_the_log_check_detects_a_logged_sentinel(self, caplog):
        logging.warning(_leak_sentinel("control-log"))

        assert [record.getMessage() for record in caplog.records] == [_leak_sentinel("control-log")]

    def test_the_warning_check_detects_a_warned_sentinel(self, recwarn):
        warnings.warn(_leak_sentinel("control-warning"), stacklevel=1)

        assert [str(recorded.message) for recorded in recwarn.list] == [_leak_sentinel("control-warning")]

    def test_an_unknown_disposition_outside_the_window_is_not_counted(self, ledger):
        ledger.write("session-a", [_row("BANANA", "r1", event_time=_BEFORE_WINDOW)])

        assert ledger.count() == _expect()

    @pytest.mark.parametrize(
        ("event_time", "expected_unknown_rows"),
        [
            ("2026-08-10T00:00:00Z", 1),
            ("2026-08-09T23:59:59Z", 0),
            ("2026-08-12T23:59:59Z", 1),
            ("2026-08-13T00:00:00Z", 0),
        ],
        ids=["at since_ts", "one second before since_ts", "one second before until_epoch", "at until_epoch"],
    )
    def test_an_unknown_disposition_is_counted_in_the_half_open_window_only(
        self, ledger, event_time, expected_unknown_rows,
    ):
        ledger.write("session-a", [_row("BANANA", "r1", event_time=event_time)])

        assert ledger.count() == _expect(unknown_disposition_rows=expected_unknown_rows)

    def test_unparseable_lines_and_empty_rows_do_not_raise(self, ledger):
        path = ledger.write("session-a", [])
        path.write_text("{broken\n[1, 2]\n\"text\"\n\n{}\n" + json.dumps(_row(_ADDRESS, "r1")) + "\n")

        assert ledger.count() == _expect(
            terminal_by_disposition=_terminal(address=1), left_out_by_field=_left_out(disposition=1),
            sessions_with_disposition_row=1,
        )


class TestFileSelection:
    @pytest.mark.parametrize(
        "decoy_name",
        [
            "{foreign}.session-a.jsonl",
            "{valid_prefix}.session-a.jsonl",
            "{foreign}.{valid}.jsonl",
            "{valid}.jsonl",
            "{valid}.session-a.jsonl.bak",
        ],
        ids=["foreign hash", "prefix of a valid hash", "valid hash in the slot position", "no slot", "not a jsonl name"],
    )
    def test_only_a_file_named_for_the_worktree_path_is_read(self, ledger, decoy_name):
        valid_hash = publication_scope._ledger_repo_hash(str(ledger.worktree))
        ledger.write("session-ctl", [_row(_ADDRESS, "control", session_id="session-ctl")])
        decoy = ledger.directory / decoy_name.format(foreign="f" * 64, valid=valid_hash, valid_prefix=valid_hash[:32])
        _write_jsonl(decoy, [_row(_ADDRESS, "decoy", session_id="session-a")])

        counts = ledger.count(scanned={"session-a"})

        assert counts == _expect(terminal_by_disposition=_terminal(address=1), sessions_with_disposition_row=1)

    def test_an_absent_ledger_directory_has_its_own_state(self, ledger):
        assert ledger.count() == _expect(directory_state=ledger_dispositions._DIRECTORY_ABSENT, files_read=0)

    @pytest.mark.parametrize(
        ("state_constant", "published_state"),
        [("_DIRECTORY_PRESENT", "present"), ("_DIRECTORY_ABSENT", "absent"), ("_DIRECTORY_UNREADABLE", "unreadable")],
    )
    def test_the_directory_states_are_the_documented_strings(self, state_constant, published_state):
        assert getattr(ledger_dispositions, state_constant) == published_state

    def test_an_empty_ledger_directory_is_present(self, ledger):
        ledger.directory.mkdir(parents=True)

        assert ledger.count() == _expect(files_read=0)

    def test_an_unreadable_ledger_directory_has_its_own_state(self, ledger, monkeypatch):
        ledger.write("session-a", [_row(_ADDRESS, "r1")])
        real_iterdir = Path.iterdir

        def refuse_the_ledger_directory(path):
            if path == ledger.directory:
                raise PermissionError("denied")
            return real_iterdir(path)

        monkeypatch.setattr(Path, "iterdir", refuse_the_ledger_directory)

        assert ledger.count() == _expect(directory_state=ledger_dispositions._DIRECTORY_UNREADABLE, files_read=0)

    @pytest.mark.parametrize(
        "file_bytes",
        [b"", b"\n\n", b'{broken\n[1, 2]\n"text"\n', b"\xff\xfe\n"],
        ids=["empty file", "blank lines only", "no line is a JSON object", "undecodable bytes"],
    )
    def test_a_file_that_opens_with_no_valid_rows_is_read_not_unreadable(self, ledger, file_bytes):
        # A file that opens with no valid rows counts as read.
        ledger.write("session-a", []).write_bytes(file_bytes)

        assert ledger.count() == _expect()

    def test_a_dangling_symlink_is_unreadable_and_its_path_reaches_neither_stream(self, ledger, tmp_path, capsys):
        ledger.write("session-a", [_row(_ADDRESS, "r1")])
        dangling = ledger.directory / f"{publication_scope._ledger_repo_hash(str(ledger.worktree))}.session-gone.jsonl"
        dangling.symlink_to(tmp_path / "missing-target")
        stderr_before = sys.stderr

        counts = ledger.count()

        assert counts == _expect(
            unreadable_files=1, terminal_by_disposition=_terminal(address=1), sessions_with_disposition_row=1,
        )
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == ""
        assert sys.stderr is stderr_before

    @pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses file permission bits")
    def test_a_regular_file_that_fails_to_open_is_unreadable_and_its_slot_reaches_neither_stream(
        self, ledger, capfd, caplog, recwarn,
    ):
        # The reader prints the failing path to stderr, so only the real reader's print-then-suppress path keeps the slot off it.
        ledger.write("session-a", [_row(_ADDRESS, "r1")])
        unopenable = ledger.write(_leak_sentinel("mode-zero-slot"), [_row(_ADDRESS, "r2")])
        os.chmod(unopenable, 0o000)
        try:
            counts = ledger.count()
        finally:
            os.chmod(unopenable, 0o644)  # restore before tmp_path teardown

        assert counts == _expect(
            unreadable_files=1, terminal_by_disposition=_terminal(address=1), sessions_with_disposition_row=1,
        )
        assert _LEAK_SENTINEL_PREFIX not in repr(counts) + _captured_text(capfd)
        assert caplog.records == []
        assert not recwarn.list

    def test_an_entry_whose_lstat_fails_is_unreadable_and_its_path_reaches_neither_stream(
        self, ledger, monkeypatch, capfd,
    ):
        ledger.write("session-a", [_row(_ADDRESS, "r1")])
        removed_slot = _leak_sentinel("removed-slot")
        ledger.write(removed_slot, [_row(_ADDRESS, "r2")])
        real_lstat = os.lstat

        def lstat_failing_for_the_removed_entry(path, *args, **kwargs):
            if removed_slot in str(path):
                raise FileNotFoundError(f"gone {path}")
            return real_lstat(path, *args, **kwargs)

        monkeypatch.setattr(os, "lstat", lstat_failing_for_the_removed_entry)

        counts = ledger.count()

        assert counts == _expect(
            unreadable_files=1, terminal_by_disposition=_terminal(address=1), sessions_with_disposition_row=1,
        )
        assert _LEAK_SENTINEL_PREFIX not in repr(counts) + _captured_text(capfd)

    def test_a_symlink_named_for_this_checkout_is_unreadable_and_contributes_no_row_of_its_target(self, ledger):
        ledger.write("session-a", [_row(_ADDRESS, "own")])
        foreign = _write_named_ledger_file(
            ledger.config_root, "f" * 64, "session-foreign", [_row(_DEFER, "foreign-1"), _row(_DEFER, "foreign-2")],
        )
        (ledger.directory / f"{publication_scope._ledger_repo_hash(str(ledger.worktree))}.session-link.jsonl").symlink_to(foreign)

        assert ledger.count() == _expect(
            unreadable_files=1, terminal_by_disposition=_terminal(address=1), sessions_with_disposition_row=1,
        )

    @pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="os.mkfifo is unavailable on this platform")
    def test_a_named_pipe_named_for_this_checkout_is_unreadable_and_never_opened(self, ledger):
        ledger.write("session-a", [_row(_ADDRESS, "own")])
        fifo = ledger.directory / f"{publication_scope._ledger_repo_hash(str(ledger.worktree))}.session-fifo.jsonl"
        os.mkfifo(fifo)
        outcome: dict[str, ledger_dispositions.LedgerDispositionCounts] = {}
        reader = threading.Thread(target=lambda: outcome.update(counts=ledger.count()), daemon=True)

        reader.start()
        reader.join(_FIFO_READ_DEADLINE_SECONDS)
        if reader.is_alive():
            # Open the write end so the blocked reader returns instead of outliving the test.
            os.close(os.open(fifo, os.O_WRONLY | os.O_NONBLOCK))
            reader.join(_FIFO_READ_DEADLINE_SECONDS)
            pytest.fail("reading the ledger blocked on a named pipe, so the entry was opened")

        assert outcome["counts"] == _expect(
            unreadable_files=1, terminal_by_disposition=_terminal(address=1), sessions_with_disposition_row=1,
        )

    def test_a_symlink_to_a_directory_named_for_this_checkout_is_dropped_without_being_counted(self, ledger, tmp_path):
        ledger.write("session-a", [_row(_ADDRESS, "own")])
        directory_target = tmp_path / "directory-target"
        directory_target.mkdir()
        (ledger.directory / f"{publication_scope._ledger_repo_hash(str(ledger.worktree))}.session-dir.jsonl").symlink_to(
            directory_target, target_is_directory=True,
        )

        assert ledger.count() == _expect(terminal_by_disposition=_terminal(address=1), sessions_with_disposition_row=1)

    def test_a_file_whose_read_printed_anything_is_unreadable(self, ledger, monkeypatch, capsys):
        ledger.write("session-a", [_row(_ADDRESS, "r1")])

        def reader_that_prints_then_returns_rows(path):
            print(f"read {path}", file=sys.stderr)
            return [_row(_ADDRESS, "r1")], True

        monkeypatch.setattr(author_outcome, "_read_ledger_rows_from_file", reader_that_prints_then_returns_rows)

        assert ledger.count() == _expect(files_read=0, unreadable_files=1)
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == ""


_OVER_LIMIT_INTEGER_LINE = '{"id": ' + "1" * 5000 + "}"
# Each line makes json.loads raise an exception the ledger reader does not catch.
_UNCAUGHT_DECODE_LINES = [
    pytest.param("[" * 3_000_000 + "]" * 3_000_000, RecursionError, id="deeply nested"),
    pytest.param(_OVER_LIMIT_INTEGER_LINE, ValueError, id="integer over the digit limit"),
]


@pytest.mark.usefixtures("default_int_str_digit_limit")
class TestUndecodableLines:
    @pytest.mark.parametrize(("line", "decoder_exception"), _UNCAUGHT_DECODE_LINES)
    def test_a_line_the_decoder_raises_on_makes_its_file_unreadable_and_its_error_reaches_no_stream(
        self, ledger, capsys, line, decoder_exception,
    ):
        with pytest.raises(decoder_exception) as decoder_error:
            json.loads(line)
        ledger.write("session-a", []).write_text(json.dumps(_row(_DEFER, "d1")) + "\n" + line + "\n")
        ledger.write("session-b", [_row(_ADDRESS, "a1")])

        counts = ledger.count()

        assert counts == _expect(
            files_read=1, unreadable_files=1, terminal_by_disposition=_terminal(address=1), sessions_with_disposition_row=1,
        )
        printed = _printed_text(capsys)
        assert printed == ""
        assert str(decoder_error.value) not in repr(counts) + printed

    def test_no_unreadable_files_path_reaches_the_counts_a_stream_the_log_or_a_warning(
        self, ledger, monkeypatch, capfd, caplog, recwarn,
    ):
        repo_hash = publication_scope._ledger_repo_hash(str(ledger.worktree))
        ledger.write("session-a", [_row(_ADDRESS, "a1")])
        dangling = ledger.directory / f"{repo_hash}.{_leak_sentinel('dangling-slot')}.jsonl"
        dangling.symlink_to(ledger.directory / "missing-target")
        ledger.write(_leak_sentinel("over-limit-slot"), []).write_text(_OVER_LIMIT_INTEGER_LINE + "\n")
        printing_slot = _leak_sentinel("printing-slot")
        ledger.write(printing_slot, [_row(_ADDRESS, "p1")])
        real_reader = author_outcome._read_ledger_rows_from_file

        def reader_that_prints_the_path_of_one_file(path):
            if printing_slot in path.name:
                print(f"read {path}", file=sys.stderr)
                return [_row(_ADDRESS, "p1")], True
            return real_reader(path)

        monkeypatch.setattr(author_outcome, "_read_ledger_rows_from_file", reader_that_prints_the_path_of_one_file)

        counts = ledger.count()

        assert counts == _expect(
            files_read=1, unreadable_files=3, terminal_by_disposition=_terminal(address=1),
            sessions_with_disposition_row=1,
        )
        assert _LEAK_SENTINEL_PREFIX not in repr(counts)
        assert _LEAK_SENTINEL_PREFIX not in _captured_text(capfd)
        assert caplog.records == []
        assert not recwarn.list


class TestSessionLines:
    def test_sessions_with_a_disposition_row_in_the_window_and_those_the_scan_covered(self, ledger):
        ledger.write("branch-1", [
            _row(_ADDRESS, "a1", session_id="session-a"),
            _row(_DEFER, "d1", session_id="session-a"),
            _row(_DEFER, "d2", session_id="session-b"),
            _row(_ADDRESS, "a2", ref="d2", session_id="session-b"),
            _row(_ADDRESS, "a3", session_id="session-before", event_time=_BEFORE_WINDOW),
            _row("CLEAN", "c1", session_id="session-clean"),
            _row(_DEFER, "k1", ref="d1", decided_by="carry", session_id="session-carry"),
            _row("BANANA", "u1", session_id="session-unknown"),
        ])
        ledger.write("session-c", [_row(_SETTLED, "s1", decided_by="engineer", session_id="session-c")])

        counts = ledger.count(scanned={"session-a", "session-c", "session-before", "session-clean", "session-never-seen"})

        assert counts.sessions_with_disposition_row == 3
        assert counts.sessions_covered_by_scan == 2

    def test_no_ledger_text_reaches_the_counts_or_either_stream(self, ledger, capsys):
        leaking = {
            "finding": _leak_sentinel("finding"), "rationale": _leak_sentinel("rationale"),
            "engineer_quote": _leak_sentinel("engineer_quote"),
        }
        first = {**_row(_DEFER, _leak_sentinel("id"), session_id=_leak_sentinel("session")), **leaking}
        second = {**_row(_ADDRESS, "a1", ref=_leak_sentinel("id")), **leaking}
        ledger.write("session-a", [first, second])

        counts = ledger.count()

        assert counts == _expect(terminal_by_disposition=_terminal(address=1), sessions_with_disposition_row=2)
        captured = capsys.readouterr()
        assert _LEAK_SENTINEL_PREFIX not in repr(counts) + captured.out + captured.err


class TestWriterToReader:
    """Rows the real review-ledger.sh appends, read back by the counting reader."""

    _SESSION_ID = "writer-reader-session"

    def _append(self, args: list[str], *, cwd: Path, home: Path) -> None:
        env = _clean_env(HOME=str(home), CLAUDE_CONFIG_DIR=None)
        result = subprocess.run(
            ["bash", str(_REVIEW_LEDGER_SH), "append", "code-review", *args],
            cwd=cwd, env=env, capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, result.stderr

    def _last_row_id(self, ledger_directory: Path) -> str:
        (ledger_file,) = ledger_directory.glob("*.jsonl")
        return json.loads(ledger_file.read_text().splitlines()[-1])["id"]

    def test_a_defer_relogged_and_closed_by_an_address_leaves_one_terminal_address(self, tmp_path):
        home = tmp_path / "home"
        home.mkdir()
        main_checkout = init_git_repo(tmp_path / "main-checkout", branch="main", env=_clean_env())
        _git(main_checkout, "commit", "--allow-empty", "-q", "-m", "init")
        linked_checkout = tmp_path / "linked-checkout"
        _git(main_checkout, "worktree", "add", "-q", "-b", "feature", str(linked_checkout))
        toplevel = _git(linked_checkout, "rev-parse", "--show-toplevel").strip()
        _seed_session(home, self._SESSION_ID)
        ledger_directory = home / ".claude" / author_outcome._REVIEW_LEDGER_DIRNAME
        common = ["--finding", "a finding", "--rationale", "a reason", "--source", "foo.py"]
        defer = [*common, "--disposition", "DEFER", "--defer-criterion", "orthogonal-scope"]

        self._append([*defer, "--round", "1", "--reviewer", "staff-sdet"], cwd=linked_checkout, home=home)
        deferred_id = self._last_row_id(ledger_directory)
        self._append([*defer, "--round", "2", "--ref", deferred_id, "--relog"], cwd=linked_checkout, home=home)
        relogged_id = self._last_row_id(ledger_directory)
        self._append(
            [*common, "--disposition", "ADDRESS", "--round", "3", "--ref", relogged_id, "--reviewer", "staff-sdet"],
            cwd=linked_checkout, home=home,
        )
        _write_named_ledger_file(home / ".claude", "f" * 64, self._SESSION_ID, [_row(_DEFER, "foreign-defer")])
        now = time.time()

        counts = ledger_dispositions.count_ledger_dispositions(
            home / ".claude", [toplevel], now - 86400, now + 86400, {self._SESSION_ID},
        )

        assert counts == _expect(
            terminal_by_disposition=_terminal(address=1), sessions_with_disposition_row=1, sessions_covered_by_scan=1,
        )
