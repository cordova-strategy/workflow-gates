"""Counts of the review ledger's terminal dispositions over this repository's ledger files.

Every returned figure is an aggregate: no ledger text, id, ref, path or session id, and no unknown `disposition`
value, reaches the result or any output stream.

Reads six fields of each row: `disposition`, `id`, `ref`, `decided_by`, `event_time` and `session_id`. Each row is
reduced to those fields as soon as its file is read, and a row with a wrong-typed one is left out under the first
such field in that order. An absent `id`, `ref` or `decided_by` reads as empty and an absent `session_id` as none.
`event_time` must be the writer's `YYYY-MM-DDTHH:MM:SSZ` form, and `session_id` comes from the row, never from the file name.

A disposition row is an ADDRESS, DEFER or SETTLED row that is not a carry. It is superseded when a later disposition row
in the same file, in file order, has an id and names its `id` as `ref`, with an `event_time` before the window's end.
A terminal row is an unsuperseded disposition row with an id whose `event_time` falls in the window.

Imports sibling modules by module (attribute access, not by name) -- see scope.py's own top-of-file comment for why.
"""
from __future__ import annotations

import contextlib
import io
import os
import re
import stat
from collections import Counter
from collections.abc import Collection, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

from transcript_analysis import author_outcome, corpus, publication_scope

_DIRECTORY_PRESENT = "present"
_DIRECTORY_ABSENT = "absent"
_DIRECTORY_UNREADABLE = "unreadable"

# The fields a row can be left out under, in the order they are checked.
_LEFT_OUT_FIELDS = ("disposition", "id", "ref", "decided_by", "event_time", "session_id")

_COUNTED_DISPOSITIONS = (
    author_outcome._DISPOSITION_ADDRESS, author_outcome._DISPOSITION_DEFER, author_outcome._DISPOSITION_SETTLED,
)
# Rows of these dispositions are valid but neither terminal nor superseders.
_UNCOUNTED_DISPOSITIONS = (author_outcome._DISPOSITION_CLEAN, author_outcome._DISPOSITION_CONSULT)

# The writer's own `event_time` shape: a looser string would admit the offset forms `corpus._parse_ts` converts.
_WRITER_EVENT_TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")


@dataclass(frozen=True)
class LedgerDispositionCounts:
    """`terminal_by_disposition` has exactly the ADDRESS, DEFER and SETTLED keys, and `left_out_by_field` one per read field.

    `directory_state` is "present", "absent" (no ledger directory) or "unreadable" (listing it failed).
    `left_out_by_field` counts every row of every date and disposition in the files read, CLEAN, CONSULT and carry rows
    included, because a row with a bad field cannot be windowed. Every other row counter is windowed.
    The two dicts are mutable: callers read them and never mutate them.
    """

    directory_state: str
    files_read: int
    unreadable_files: int
    terminal_by_disposition: dict[str, int]
    id_less_disposition_rows: int
    unknown_disposition_rows: int
    left_out_by_field: dict[str, int]
    sessions_with_disposition_row: int
    sessions_covered_by_scan: int


class _LedgerRow(NamedTuple):
    disposition: str
    row_id: str
    ref: str
    decided_by: str
    event_epoch: float
    session_id: str | None


@dataclass
class _Tally:
    terminal: Counter[str] = field(default_factory=Counter)
    left_out: Counter[str] = field(default_factory=Counter)
    id_less: int = 0
    unknown: int = 0
    sessions: set[str] = field(default_factory=set)


def _optional_text(row: dict, key: str) -> str | None:
    """The key's string value, empty when the key is absent, None when it holds a non-string."""
    value = row.get(key, "")
    return value if isinstance(value, str) else None


def _writer_event_epoch(value: object) -> float | None:
    if not isinstance(value, str) or not _WRITER_EVENT_TIME.fullmatch(value):
        return None
    return corpus._parse_ts(value)


def _reduce_row(row: dict) -> tuple[_LedgerRow | None, str | None]:
    """(the row's six fields, None), or (None, the first field whose value is missing or the wrong type)."""
    disposition = row.get("disposition")
    if not isinstance(disposition, str):
        return None, "disposition"
    row_id = _optional_text(row, "id")
    if row_id is None:
        return None, "id"
    ref = _optional_text(row, "ref")
    if ref is None:
        return None, "ref"
    decided_by = _optional_text(row, "decided_by")
    if decided_by is None:
        return None, "decided_by"
    event_epoch = _writer_event_epoch(row.get("event_time"))
    if event_epoch is None:
        return None, "event_time"
    session_id = row.get("session_id")
    if "session_id" in row and not isinstance(session_id, str):
        return None, "session_id"
    if not isinstance(session_id, str) or not author_outcome._SESSION_ID_PATTERN.fullmatch(session_id):
        session_id = None
    return _LedgerRow(disposition, row_id, ref, decided_by, event_epoch, session_id), None


def _read_file_rows(ledger_file: Path) -> list[dict] | None:
    """The file's rows, or None when it could not be read or is not a regular file.

    A point-in-time `lstat` by name refuses a symlink, FIFO or other non-regular entry unopened, as the writer's own
    check does. It does not detect a hard link or a swap between the check and the open, and neither does the writer's.
    The reader prints the file's path on an open failure, and that name carries the repository hash and a session id,
    so its stderr is held back and any output counts the file as unreadable. An exception out of the read does too.
    """
    try:
        if not stat.S_ISREG(os.lstat(ledger_file).st_mode):
            return None
    except OSError:
        return None
    reader_stderr = io.StringIO()
    try:
        with contextlib.redirect_stderr(reader_stderr):
            rows, opened = author_outcome._read_ledger_rows_from_file(ledger_file)
    except (ValueError, RecursionError):
        # json.loads raises ValueError for an integer over the interpreter's digit limit and RecursionError for a line
        # nested past the decoder's stack, and the reader catches neither. The exception is dropped, never reported.
        return None
    if not opened or reader_stderr.getvalue():
        return None
    # The rows of one file are held at once. That is bounded in practice: ledger files are per branch or session, and
    # the writer sweeps one that has been idle for at least 30 days.
    return rows


def _tally_file(rows: Iterable[dict], since_ts: float, until_epoch: float, tally: _Tally) -> None:
    disposition_rows: list[_LedgerRow] = []
    for raw_row in rows:
        reduced, left_out_field = _reduce_row(raw_row)
        if reduced is None:
            tally.left_out[left_out_field] += 1
            continue
        if reduced.decided_by == author_outcome._DECIDED_BY_CARRY or reduced.disposition in _UNCOUNTED_DISPOSITIONS:
            continue
        if reduced.disposition in _COUNTED_DISPOSITIONS:
            disposition_rows.append(reduced)
        elif since_ts <= reduced.event_epoch < until_epoch:
            tally.unknown += 1
    # A position later than a row's own supersedes it, so the last position naming an id is the only one that matters.
    last_superseder_position: dict[str, int] = {}
    for position, disposition_row in enumerate(disposition_rows):
        if disposition_row.row_id and disposition_row.ref and disposition_row.event_epoch < until_epoch:
            last_superseder_position[disposition_row.ref] = position
    for position, disposition_row in enumerate(disposition_rows):
        if not since_ts <= disposition_row.event_epoch < until_epoch:
            continue
        if disposition_row.session_id is not None:
            tally.sessions.add(disposition_row.session_id)
        if not disposition_row.row_id:
            tally.id_less += 1
        elif last_superseder_position.get(disposition_row.row_id, -1) <= position:
            tally.terminal[disposition_row.disposition] += 1


def _directory_state(ledger_dir: Path, listing_gaps: Counter[str]) -> str:
    if listing_gaps[publication_scope._GAP_LEDGER_DIR]:
        return _DIRECTORY_UNREADABLE
    return _DIRECTORY_PRESENT if ledger_dir.is_dir() else _DIRECTORY_ABSENT


def count_ledger_dispositions(
    config_dir_root: Path,
    worktree_paths: Iterable[str],
    since_ts: float,
    until_epoch: float,
    scanned_session_ids: Collection[str],
) -> LedgerDispositionCounts:
    """Count the terminal disposition rows of the ledger files named for `worktree_paths`, in [since_ts, until_epoch).

    `since_ts` and `until_epoch` are epoch seconds and must not be None. `scanned_session_ids` are the sessions the
    transcript scan covered, in the form rows carry (transcript file stems), because the match is exact string equality.
    The ledger directory's listing gaps are reported through `directory_state`, never to a caller's transcript gap counter.
    The result holds two mutable dicts, which callers read and never mutate.
    """
    ledger_dir = config_dir_root / author_outcome._REVIEW_LEDGER_DIRNAME
    listing_gaps: Counter[str] = Counter()
    ledger_files = publication_scope._this_repo_ledger_files(ledger_dir, worktree_paths, listing_gaps)
    tally = _Tally()
    files_read = 0
    for ledger_file in ledger_files:
        rows = _read_file_rows(ledger_file)
        if rows is None:
            continue
        files_read += 1
        _tally_file(rows, since_ts, until_epoch, tally)
    scanned = frozenset(scanned_session_ids)
    return LedgerDispositionCounts(
        directory_state=_directory_state(ledger_dir, listing_gaps),
        files_read=files_read,
        unreadable_files=len(ledger_files) - files_read,
        terminal_by_disposition={disposition: tally.terminal[disposition] for disposition in _COUNTED_DISPOSITIONS},
        id_less_disposition_rows=tally.id_less,
        unknown_disposition_rows=tally.unknown,
        left_out_by_field={left_out_field: tally.left_out[left_out_field] for left_out_field in _LEFT_OUT_FIELDS},
        sessions_with_disposition_row=len(tally.sessions),
        sessions_covered_by_scan=len(tally.sessions & scanned),
    )
