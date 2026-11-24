"""Reads the review-narrative-ledger files under a config-dir root and attributes their rows to sessions.

The ledger-file open-failure line carries the `author-outcome:` prefix, since author-outcome reports it.
ledger_dispositions counts a ledger file unreadable on any stderr output from the reader, whatever its prefix.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# review-narrative-ledger's own directory name, one level under a Claude
# Code config-dir root -- mirrors review-ledger.sh's own $LEDGER_DIR.
_REVIEW_LEDGER_DIRNAME = "review-narrative-ledger"


def _config_dir_root_for_session(jsonl: Path) -> Path:
    """The Claude Code config-dir root a transcript file lives under.

    jsonl is always <config_dir_root>/projects/<project-slug>/<session_id>.jsonl,
    scope.PROJECTS_DIR's own layout. Every other root scope.resolve_scan_roots
    can produce (a --config-dir root) shares that identical <dir>/projects
    layout. The config-dir root is therefore three parents up regardless of
    which root produced this path.
    """
    return jsonl.parent.parent.parent


# json.loads raises ValueError for an integer over the interpreter's digit limit. ValueError is also the base
# of JSONDecodeError and UnicodeDecodeError. json.loads raises RecursionError for a line nested past the
# decoder's stack.
_DECODER_LIMIT_ERRORS = (ValueError, RecursionError)


def _read_ledger_rows_from_file(
    ledger_path: Path, *, skip_lines_over_decoder_limits: bool = False,
) -> tuple[list[dict], bool]:
    """(every JSON row from one ledger file, in file order; whether the
    file itself could be opened at all). A malformed or undecodable line
    (e.g. a torn multibyte write) is skipped, not fatal, mirroring
    corpus._parse_jsonl_records' own per-line tolerance for a transcript
    file with a corrupted line. A file that opens successfully but yields
    zero valid rows still reports opened=True. opened=False only when open()
    itself raised OSError -- e.g. the file matched a caller's earlier
    directory listing but was deleted or became unreadable before this
    call.

    The default lets a line over the decoder's limits propagate its error:
    ledger_dispositions._read_file_rows relies on that to count the whole
    file unreadable."""
    skipped_line_errors = (
        (json.JSONDecodeError, UnicodeDecodeError, *_DECODER_LIMIT_ERRORS)
        if skip_lines_over_decoder_limits
        else (json.JSONDecodeError, UnicodeDecodeError)
    )
    rows: list[dict] = []
    try:
        # Binary mode so a line that is not valid UTF-8 fails on its own
        # json.loads call instead of aborting the whole file's iteration.
        with open(ledger_path, "rb") as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    row = json.loads(raw)
                except skipped_line_errors:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
    except OSError as exc:
        print(
            f"author-outcome: couldn't read ledger file {ledger_path}: {exc}",
            file=sys.stderr,
        )
        return [], False
    return rows, True


# Session ids are letters, digits, underscore and hyphen -- review-ledger.sh's
# own _lib_valid_session_id_component pattern. A row naming any other
# session_id is ignored rather than attributed.
_SESSION_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]+")


def _list_ledger_files(ledger_dir: Path) -> list[Path]:
    """Every ledger file directly under ledger_dir, sorted by filename for a
    deterministic read order. [] when the directory does not exist. This is
    the index's only directory listing, so a test can stand in for a file
    that vanishes between the listing and the read."""
    return sorted(ledger_dir.glob("*.jsonl"))


def _ledger_file_session_component(ledger_path: Path) -> str:
    """The session-id slot of a `<repo_hash>.<session_id>.jsonl` filename.
    The repo hash is hex, so the first dot ends it. A branch-keyed file's
    second slot is a branch hash, which no session id equals."""
    return ledger_path.name.removesuffix(".jsonl").partition(".")[2]


def _file_signature(path: Path) -> tuple[int, int] | None:
    """(mtime_ns, size), the change signature the index re-parses on. None
    when the file cannot be stat'ed."""
    try:
        stat_result = path.stat()
    except OSError:
        return None
    return stat_result.st_mtime_ns, stat_result.st_size


def _row_session_id(row: dict, ledger_path: Path) -> str | None:
    """The session a ledger row belongs to: its own `session_id` when it
    has one, else the session id in its file's name (a row with no
    `session_id`). None for a row naming an invalid session id."""
    if "session_id" not in row:
        return _ledger_file_session_component(ledger_path) or None
    session_id = row["session_id"]
    if isinstance(session_id, str) and _SESSION_ID_PATTERN.fullmatch(session_id):
        return session_id
    return None


def _event_time_sort_key(row: dict) -> str:
    """The row's `event_time` when it is a string, else "" (see
    _LedgerIndex.entries_for_session)."""
    event_time = row.get("event_time")
    return event_time if isinstance(event_time, str) else ""


class _LedgerIndex:
    """The parsed rows of every ledger file under one config-dir root,
    attributed to sessions by _row_session_id.

    refresh() re-lists the directory and re-parses only files whose
    (mtime_ns, size) changed since the previous refresh, so a file that
    appears or grows between two session lookups is seen, and an unchanged
    file is parsed once however many sessions read it. A file whose last
    open failed is retried on every refresh.
    """

    def __init__(self, ledger_dir: Path):
        self._ledger_dir = ledger_dir
        self._parsed_files: dict[Path, tuple[tuple[int, int] | None, list[dict], bool]] = {}
        self._rows_by_session: dict[str, list[tuple[Path, dict]]] = {}
        self._sessions_with_opened_file: set[str] = set()

    def refresh(self) -> None:
        parsed_files: dict[Path, tuple[tuple[int, int] | None, list[dict], bool]] = {}
        changed = False
        listed_files = _list_ledger_files(self._ledger_dir)
        for ledger_path in listed_files:
            signature = _file_signature(ledger_path)
            cached = self._parsed_files.get(ledger_path)
            if signature is not None and cached is not None and cached[0] == signature and cached[2]:
                parsed_files[ledger_path] = cached
                continue
            rows, opened = _read_ledger_rows_from_file(ledger_path, skip_lines_over_decoder_limits=True)
            parsed_files[ledger_path] = (signature, rows, opened)
            changed = True
        if changed or parsed_files.keys() != self._parsed_files.keys():
            self._parsed_files = parsed_files
            self._attribute_rows(listed_files)

    def _attribute_rows(self, listed_files: list[Path]) -> None:
        rows_by_session: dict[str, list[tuple[Path, dict]]] = {}
        sessions_with_opened_file: set[str] = set()
        for ledger_path in listed_files:
            _signature, rows, opened = self._parsed_files[ledger_path]
            if opened:
                sessions_with_opened_file.add(_ledger_file_session_component(ledger_path))
            for row in rows:
                session_id = _row_session_id(row, ledger_path)
                if session_id is not None:
                    rows_by_session.setdefault(session_id, []).append((ledger_path, row))
        self._rows_by_session = rows_by_session
        self._sessions_with_opened_file = sessions_with_opened_file

    def entries_for_session(self, session_id: str) -> tuple[list[tuple[int, dict]], bool]:
        """(the session's rows, each tagged with its source file's position
        among the files the session has rows in, in filename order; whether
        a session-keyed file `<repo_hash>.<session_id>.jsonl` was opened).

        Rows are stable-sorted by their own `event_time` (an ISO-8601 UTC
        string that sorts correctly lexically; missing or non-string -> "" so a
        legacy pre-event_time row, or a row a foreign writer typed oddly,
        sorts first). Python's sort is stability-guaranteed,
        so ties keep file-encounter order. review-ledger.sh's own `show`
        (`sort_by(.event_time // "")`) has no such guarantee from jq -- see
        that comment for the caveat.
        """
        file_positions: dict[Path, int] = {}
        entries = [
            (file_positions.setdefault(ledger_path, len(file_positions)), row)
            for ledger_path, row in self._rows_by_session.get(session_id, [])
        ]
        entries.sort(key=lambda entry: _event_time_sort_key(entry[1]))
        return entries, session_id in self._sessions_with_opened_file


def _read_ledger_row_entries_for_session(
    jsonl: Path, ledger_indexes: dict[Path, _LedgerIndex] | None = None,
) -> tuple[list[tuple[int, dict]], bool]:
    """Every ledger row attributed to this transcript's own session id, as
    (file_index, row) entries (see _LedgerIndex.entries_for_session), and
    whether a session-keyed ledger file for it was opened.

    ledger_indexes holds one index per config-dir root and is shared across
    a caller's lookups so an unchanged file is parsed once. None uses a
    private index, which parses every file it reads.

    The bool is what author_outcome._ledger_possibly_swept keys on: a session-keyed file
    that matched the directory listing but raised OSError on open -- e.g.
    evicted by review-ledger.sh clear-stale in the window between the
    listing and the read -- does not count. That distinguishes the eviction
    race from a file that opened and holds zero valid JSON rows.
    """
    config_dir_root = _config_dir_root_for_session(jsonl)
    indexes = {} if ledger_indexes is None else ledger_indexes
    index = indexes.get(config_dir_root)
    if index is None:
        index = indexes[config_dir_root] = _LedgerIndex(config_dir_root / _REVIEW_LEDGER_DIRNAME)
    index.refresh()
    return index.entries_for_session(jsonl.stem)
