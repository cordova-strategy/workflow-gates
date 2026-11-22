"""The reviewer-reads command: how reviewer subagents' whole-file Reads of files came back (complete, partial or
refused), whether the reviewer read on, what share of reviewer spend went to Read, the review ledger's terminal
dispositions, and the harness versions and models behind the reviewer windows -- plus its subparser registration.

Every printed figure is an aggregate. Nothing printed carries a path, session identifier, project name, ledger id,
error text, version, model or untracked agent-type name that the corpus supplied: a model and an agent type print only
after a match against a closed set of names, a version only after a match against a bounded shape, and everything else
prints as a count. Stderr can also carry an API request id through pricing's two request-id notices, the exception
read-cost's stderr has too. Stderr is for the session running the command and is never published.

Imports sibling modules by module (attribute access, not by name) -- see scope.py's own top-of-file comment for why.
"""
from __future__ import annotations

import argparse
import heapq
import re
import sys
from collections import Counter
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import NamedTuple

from transcript_analysis import (
    author_outcome,
    corpus,
    ledger_dispositions,
    pricing,
    publication_scope,
    read_cost,
    redaction,
    render,
    review_rounds,
    reviewer_yield,
    scope,
    subagent_mix,
)

_COMMAND_LABEL = "reviewer-reads"

# Outcome classes of a whole-file call, in the order a call takes the first that fits.
_OUTCOME_REFUSED_OVER_LIMIT = "refused_over_limit"
_OUTCOME_OTHER_ERROR = "other_error"
_OUTCOME_SIZE_UNKNOWN = "size_unknown"
_OUTCOME_PARTIAL_TOKEN_CAP = "partial_token_cap"
_OUTCOME_COMPLETE_ALLOW_LARGE = "complete_allow_large"
_OUTCOME_COMPLETE = "complete"
_OUTCOME_PARTIAL_UNFLAGGED = "partial_unflagged"
_OUTCOMES = (
    _OUTCOME_REFUSED_OVER_LIMIT, _OUTCOME_OTHER_ERROR, _OUTCOME_SIZE_UNKNOWN, _OUTCOME_PARTIAL_TOKEN_CAP,
    _OUTCOME_COMPLETE_ALLOW_LARGE, _OUTCOME_COMPLETE, _OUTCOME_PARTIAL_UNFLAGGED,
)
_PARTIAL_OUTCOMES = (_OUTCOME_PARTIAL_TOKEN_CAP, _OUTCOME_PARTIAL_UNFLAGGED)

# Reasons a success is `size_unknown` beyond the structured-field checks read-cost names.
_REASON_START_AFTER_FIRST_LINE = "start_after_first_line"
_REASON_LINES_EXCEED_TOTAL = "lines_exceed_total"
_SIZE_UNKNOWN_REASONS = (
    read_cost._STRUCTURED_MULTI_RESULT_RECORD,
    read_cost._STRUCTURED_TOOL_USE_RESULT_NOT_A_DICT,
    read_cost._STRUCTURED_FILE_NOT_A_DICT,
    read_cost._STRUCTURED_FILE_PATH_MISMATCH,
    read_cost._STRUCTURED_LINE_FIELD_INVALID,
    read_cost._STRUCTURED_TRUNCATION_FLAG_INVALID,
    _REASON_START_AFTER_FIRST_LINE,
    _REASON_LINES_EXCEED_TOTAL,
)

# The Read tool's default line limit and its per-call token cap. A whole-file call on a file over the first, or one
# whose estimated tokens reach the second, was larger than one default Read call.
_DEFAULT_LINE_LIMIT = 2000
# The lower size-bucket edge, the rough size of one Read call's page.
_PAGE_LINES = 1000
_ONE_CALL_TOKEN_CAP = 25_000
# Estimates within 5,000 tokens of the cap, where the 4 chars/token estimate alone decides a call's denominator.
_TOKEN_ESTIMATE_BAND = (20_000, 30_000)

_BUCKET_UP_TO_PAGE = "up_to_1000"
_BUCKET_UP_TO_DEFAULT_LIMIT = "1001_to_2000"
_BUCKET_OVER_DEFAULT_LIMIT = "over_2000"
_BUCKET_UNKNOWN = "unknown"
_BUCKETS = (_BUCKET_UP_TO_PAGE, _BUCKET_UP_TO_DEFAULT_LIMIT, _BUCKET_OVER_DEFAULT_LIMIT, _BUCKET_UNKNOWN)
_BUCKETS_OVER_PAGE = (_BUCKET_UP_TO_DEFAULT_LIMIT, _BUCKET_OVER_DEFAULT_LIMIT)

_ROLE_CODE_OR_OTHER = read_cost._KIND_CODE_OR_OTHER
_ROLE_PROSE = "prose"
_ROLE_DIFF_HANDOFF = "diff_handoff"
_REVIEWED_ROLES = (_ROLE_CODE_OR_OTHER, _ROLE_PROSE)
_ROLES = (*_REVIEWED_ROLES, _ROLE_DIFF_HANDOFF)
# The two directories pr-diff-against-base.sh writes the review diff into.
_DIFF_HANDOFF_DIRECTORY_NAMES = frozenset({"code-review-diff-markers", "cumulative-review-diff-markers"})

_SKILL_FIDELITY_AGENT_TYPE = "skill-fidelity-reviewer"

# A count denominator, or a window count behind a weight share, below this prints as insufficient. Reviewer-yield's own
# floor is a separate constant, so a change there cannot move this baseline's comparison.
_RATE_FLOOR = 10

# A finding count a reviewer reports past this prints as the ceiling, a display bound with no external source.
_FINDINGS_PRINT_CEILING = 1_000_000

_VALUE_UNKNOWN = "unknown"
_VALUE_OTHER = "other"
# A version prints only when it has this shape: two to four dot-separated groups of one to four digits.
_VERSION_PATTERN = re.compile(r"[0-9]{1,4}(?:\.[0-9]{1,4}){1,3}")

_FOLLOW_UP_NEITHER_LABEL = "neither (no later offset Read, and not covered by later Reads)"


class _ReadFacts(NamedTuple):
    """What a later Read of a path contributes to a follow-up and coverage decision."""

    call_order: int
    has_offset: bool
    interval: tuple[int, int] | None


class _Call(NamedTuple):
    """A whole-file Read call with its outcome. `reason` is set for `size_unknown` alone."""

    tool_use_id: str
    path: str
    role: str
    outcome: str
    reason: str | None
    unrecognised_limit_error: bool
    bucket: str
    total_lines: int | None
    tokens: int
    call_order: int


class _WindowReads(NamedTuple):
    calls: list[_Call]
    reads_by_path: dict[str, list[_ReadFacts]]
    # Every successful Read's event and the bucket of the file it read, whole-file or targeted.
    sized_events: list[tuple[read_cost._ReadEvent, str, str]]


@dataclass
class _RoundTotals:
    windows: int = 0
    whole_file_calls: int = 0
    targeted_calls: int = 0
    diff_handoff_whole_file_calls: int = 0
    outcomes: Counter = field(default_factory=Counter)
    buckets: Counter = field(default_factory=Counter)


@dataclass
class _Totals:
    sessions: int = 0
    reviewer_windows: int = 0
    skill_fidelity_windows_left_out: int = 0
    windows_without_timestamp: int = 0
    round_windows_without_timestamp: int = 0
    invalid_usage_turns: int = 0
    billed_weight: float = 0.0
    read_weight: float = 0.0
    read_weight_over_page: float = 0.0
    read_weight_over_page_code_or_other: float = 0.0
    read_weight_over_page_diff_handoff: float = 0.0
    read_weight_unknown_size: float = 0.0
    # (role, outcome, bucket) -> whole-file calls in reviewer windows.
    outcome_calls: Counter = field(default_factory=Counter)
    # (role, "calls" | "later_offset_read" | "covered_after" | "neither") -> partial or refused calls.
    follow_up: Counter = field(default_factory=Counter)
    # (role, "denominator" | "partial" | "refused") over reviewed files; ("band",) is the estimate-decided count.
    headline: Counter = field(default_factory=Counter)
    size_unknown_reasons: Counter = field(default_factory=Counter)
    unrecognised_limit_errors: int = 0
    unexplained_partials: int = 0
    notices_missing_for_partial_token_cap: int = 0
    notices_naming_other_calls: int = 0
    notices_naming_size_unknown_calls: int = 0
    # Label -> windows, partial, refused and larger_than_one_call counts, after the untracked-name fold.
    type_rows: dict[str, Counter] = field(default_factory=dict)
    version_counts: Counter = field(default_factory=Counter)
    model_counts: Counter = field(default_factory=Counter)
    rounds: dict[str, _RoundTotals] = field(
        default_factory=lambda: {skill: _RoundTotals() for skill in review_rounds.REVIEW_SKILLS},
    )
    scanned_session_ids: set[str] = field(default_factory=set)
    scan_gaps: Counter = field(default_factory=Counter)


def _size_bucket(total_lines: int | None) -> str:
    if total_lines is None:
        return _BUCKET_UNKNOWN
    if total_lines <= _PAGE_LINES:
        return _BUCKET_UP_TO_PAGE
    return _BUCKET_UP_TO_DEFAULT_LIMIT if total_lines <= _DEFAULT_LINE_LIMIT else _BUCKET_OVER_DEFAULT_LIMIT


def _role(path: str) -> str:
    if PurePosixPath(path).parent.name in _DIFF_HANDOFF_DIRECTORY_NAMES:
        return _ROLE_DIFF_HANDOFF
    return _ROLE_CODE_OR_OTHER if read_cost._file_kind(path) == read_cost._KIND_CODE_OR_OTHER else _ROLE_PROSE


def _classify_event(event: read_cost._ReadEvent) -> tuple[str, str | None]:
    if event.structured_status != read_cost._STRUCTURED_OK:
        return _OUTCOME_SIZE_UNKNOWN, event.structured_status
    if event.truncated_by_token_cap:
        return _OUTCOME_PARTIAL_TOKEN_CAP, None
    if event.start_line > 1:
        return _OUTCOME_SIZE_UNKNOWN, _REASON_START_AFTER_FIRST_LINE
    if event.num_lines > event.total_lines:
        return _OUTCOME_SIZE_UNKNOWN, _REASON_LINES_EXCEED_TOTAL
    if event.num_lines == event.total_lines:
        return (_OUTCOME_COMPLETE_ALLOW_LARGE if event.allow_large else _OUTCOME_COMPLETE), None
    return _OUTCOME_PARTIAL_UNFLAGGED, None


def _event_interval(event: read_cost._ReadEvent) -> tuple[int, int] | None:
    if event.start_line is None or not event.num_lines:
        return None
    last_line = event.start_line + event.num_lines - 1
    # A result flagged as cut short stopped before the end of the file,
    # so a range reported through the file's last line overstates what came back.
    # `total_lines` is set whenever `start_line` is (`read_cost._structured_read`).
    if event.truncated_by_token_cap and last_line >= event.total_lines:
        return None
    return event.start_line, last_line


def _read_window(scan: read_cost._WindowScan) -> _WindowReads:
    """Classifies every Read of one window. A call without its own `totalLines` takes the largest any call saw for its path."""
    largest_total_by_path: dict[str, int] = {}
    for event in scan.events:
        if event.total_lines is not None and event.total_lines > largest_total_by_path.get(event.path, -1):
            largest_total_by_path[event.path] = event.total_lines
    calls: list[_Call] = []
    reads_by_path: dict[str, list[_ReadFacts]] = {}
    sized_events: list[tuple[read_cost._ReadEvent, str, str]] = []
    for event in scan.events:
        total_lines = event.total_lines if event.total_lines is not None else largest_total_by_path.get(event.path)
        bucket = _size_bucket(total_lines)
        role = _role(event.path)
        sized_events.append((event, role, bucket))
        reads_by_path.setdefault(event.path, []).append(
            _ReadFacts(event.call_order, event.offset is not None, _event_interval(event)),
        )
        if event.whole_file:
            outcome, reason = _classify_event(event)
            calls.append(_Call(
                event.tool_use_id, event.path, role, outcome, reason, False, bucket, total_lines, event.tokens,
                event.call_order,
            ))
    for failed in scan.failed_reads:
        reads_by_path.setdefault(failed.path, []).append(_ReadFacts(failed.call_order, failed.offset is not None, None))
        if not failed.whole_file:
            continue
        refused = failed.limit_refusal == read_cost._LIMIT_REFUSAL_RECOGNISED
        total_lines = largest_total_by_path.get(failed.path)
        calls.append(_Call(
            failed.tool_use_id, failed.path, _role(failed.path),
            _OUTCOME_REFUSED_OVER_LIMIT if refused else _OUTCOME_OTHER_ERROR, None,
            failed.limit_refusal == read_cost._LIMIT_REFUSAL_UNRECOGNISED, _size_bucket(total_lines), total_lines, 0,
            failed.call_order,
        ))
    for reads in reads_by_path.values():
        reads.sort(key=lambda read: read.call_order)
    return _WindowReads(calls, reads_by_path, sized_events)


def _is_larger_than_one_call(call: _Call) -> bool:
    """A refused or partial call, a complete one on a file over the default limit, or an allow_large one at the token cap."""
    if call.outcome in (*_PARTIAL_OUTCOMES, _OUTCOME_REFUSED_OVER_LIMIT):
        return True
    if call.outcome in (_OUTCOME_COMPLETE, _OUTCOME_COMPLETE_ALLOW_LARGE) and call.bucket == _BUCKET_OVER_DEFAULT_LIMIT:
        return True
    return call.outcome == _OUTCOME_COMPLETE_ALLOW_LARGE and call.tokens >= _ONE_CALL_TOKEN_CAP


def _is_in_estimate_band(call: _Call) -> bool:
    """An allow_large call on a file of up to the default limit whose token estimate alone decides its denominator."""
    return (
        call.outcome == _OUTCOME_COMPLETE_ALLOW_LARGE
        and call.bucket in (_BUCKET_UP_TO_PAGE, _BUCKET_UP_TO_DEFAULT_LIMIT)
        and _TOKEN_ESTIMATE_BAND[0] <= call.tokens < _TOKEN_ESTIMATE_BAND[1]
    )


def _later_read_state_by_call_order(reads: Sequence[_ReadFacts]) -> dict[int, tuple[bool, int]]:
    """For each read of one path, (a read at or after it has an offset, the first line the reads at or after it leave uncovered).

    Takes the reads latest first and merges their intervals into the unbroken run from line 1, so a huge `totalLines` costs
    nothing and each path is processed once whatever its number of calls.
    """
    state_by_call_order: dict[int, tuple[bool, int]] = {}
    any_offset = False
    first_uncovered_line = 1
    intervals_beyond_the_run: list[tuple[int, int]] = []
    for read in reversed(reads):
        any_offset = any_offset or read.has_offset
        if read.interval is not None:
            heapq.heappush(intervals_beyond_the_run, read.interval)
            while intervals_beyond_the_run and intervals_beyond_the_run[0][0] <= first_uncovered_line:
                first_uncovered_line = max(first_uncovered_line, heapq.heappop(intervals_beyond_the_run)[1] + 1)
        state_by_call_order[read.call_order] = (any_offset, first_uncovered_line)
    return state_by_call_order


def _record_epoch(rec: dict) -> float | None:
    timestamp = rec.get("timestamp")
    if not isinstance(timestamp, str):
        return None
    return corpus._parse_ts(timestamp)


def _first_epoch(records: Iterable[dict]) -> float | None:
    return next((epoch for epoch in map(_record_epoch, records) if epoch is not None), None)


def _window_version(records: Iterable[dict]) -> str:
    for rec in records:
        if "version" not in rec:
            continue
        version = rec["version"]
        return version if isinstance(version, str) and _VERSION_PATTERN.fullmatch(version) else _VALUE_OTHER
    return _VALUE_UNKNOWN


def _window_model(records: Iterable[dict]) -> str:
    """The first assistant record's model by name when it is a model pricing names, `other` when it holds anything else."""
    for rec in records:
        if rec.get("type") != "assistant":
            continue
        message = rec.get("message")
        if not isinstance(message, dict) or "model" not in message:
            return _VALUE_UNKNOWN
        model = message["model"]
        return model if isinstance(model, str) and model in pricing._MODEL_BASE_INPUT_RATES else _VALUE_OTHER
    return _VALUE_UNKNOWN


def _usage_overflows_float(usage: object) -> bool:
    if not isinstance(usage, dict):
        return False
    nested = usage.get("cache_creation")
    for count in (*usage.values(), *(nested.values() if isinstance(nested, dict) else ())):
        if isinstance(count, int):
            try:
                float(count)
            except OverflowError:
                return True
    return False


def _usable_block(block: object) -> object:
    if not isinstance(block, dict):
        return block
    usable = block
    if not isinstance(block.get("name", ""), str):
        usable = {**usable, "name": None}
    if block.get("type") == "text" and not isinstance(block.get("text", ""), str):
        usable = {**usable, "text": ""}
    return usable


def _usable_content(content: object) -> object:
    """`content` itself when it is a string, None or a list of usable blocks, else the reduced copy."""
    if content is None or isinstance(content, str):
        return content
    if not isinstance(content, list):
        return []
    usable = [_usable_block(block) for block in content]
    return content if all(new is old for new, old in zip(usable, content, strict=True)) else usable


def _usable_record(rec: object) -> dict | None:
    """The record with each field its shared consumers would hash, convert, iterate or join reduced to an accepted shape, or None.

    The consumers are read-cost's scan, pricing's request-id deduplication, review-round detection and the text join they
    share. None is returned for a non-object record or a non-string `type`. These are reduced, and nothing else is:
    - a non-object `message` becomes `{}`;
    - a non-string `requestId` or `message.id` becomes None;
    - a usage that is truthy and not an object, or holds a count too large for a float, becomes an invalid usage, which
      read-cost counts and skips;
    - `message.content` that is not a string, None or a list becomes `[]`;
    - a content block's non-string `name` becomes None;
    - a text block's non-string `text` becomes the empty string.
    The yield pass reads further fields and is guarded in `_yield_pass` instead.
    """
    if not isinstance(rec, dict) or not isinstance(rec.get("type", ""), str):
        return None
    usable = rec
    if not isinstance(rec.get("requestId", ""), str):
        usable = {**usable, "requestId": None}
    message = rec.get("message")
    if "message" in rec and not isinstance(message, dict):
        usable = {**usable, "message": {}}
    elif isinstance(message, dict):
        changes: dict[str, object] = {}
        if not isinstance(message.get("id", ""), str):
            changes["id"] = None
        usage = message.get("usage")
        if (usage and not isinstance(usage, dict)) or _usage_overflows_float(usage):
            changes["usage"] = {"output_tokens": -1}
        content = _usable_content(message.get("content"))
        if content is not message.get("content"):
            changes["content"] = content
        if changes:
            usable = {**usable, "message": {**message, **changes}}
    return usable


def _usable_records(records: Iterable[object]) -> list[dict]:
    return [usable for usable in map(_usable_record, records) if usable is not None]


def _usable_record_sessions(
    sessions: Iterator[tuple[Path, list[dict]]],
) -> Iterator[tuple[Path, list[dict]]]:
    for jsonl, records in sessions:
        yield jsonl, _usable_records(records)


def _agent_type_label(agent_type: str, tracked_agent_types: frozenset[str]) -> str:
    return agent_type if agent_type in tracked_agent_types else subagent_mix._WITHHELD_AGENT_TYPE_LABEL


def _accumulate_headline(totals: _Totals, call: _Call, type_row: Counter) -> None:
    if call.role == _ROLE_DIFF_HANDOFF or not _is_larger_than_one_call(call):
        return
    totals.headline[(call.role, "denominator")] += 1
    type_row["larger_than_one_call"] += 1
    if call.outcome in _PARTIAL_OUTCOMES:
        totals.headline[(call.role, "partial")] += 1
        type_row["partial"] += 1
    elif call.outcome == _OUTCOME_REFUSED_OVER_LIMIT:
        totals.headline[(call.role, "refused")] += 1
        type_row["refused"] += 1


def _accumulate_follow_ups(totals: _Totals, calls: Sequence[_Call], reads_by_path: dict[str, list[_ReadFacts]]) -> None:
    """Counts what later Reads of the path did after each partial or refused call, in the same window."""
    state_by_path: dict[str, dict[int, tuple[bool, int]]] = {}
    for call in calls:
        if call.outcome not in (*_PARTIAL_OUTCOMES, _OUTCOME_REFUSED_OVER_LIMIT):
            continue
        if call.path not in state_by_path:
            state_by_path[call.path] = _later_read_state_by_call_order(reads_by_path[call.path])
        later_offset_read, first_uncovered_line = state_by_path[call.path][call.call_order]
        covered_after = call.total_lines is not None and first_uncovered_line > call.total_lines
        totals.follow_up[(call.role, "calls")] += 1
        totals.follow_up[(call.role, "later_offset_read")] += later_offset_read
        totals.follow_up[(call.role, "covered_after")] += covered_after
        totals.follow_up[(call.role, "neither")] += not (later_offset_read or covered_after)


def _accumulate_notice_agreement(totals: _Totals, scan: read_cost._WindowScan, calls: Sequence[_Call]) -> None:
    notice_ids = scan.truncation_notice_tool_use_ids
    outcome_by_tool_use_id = {call.tool_use_id: call.outcome for call in calls}
    totals.notices_missing_for_partial_token_cap += sum(
        1 for call in calls if call.outcome == _OUTCOME_PARTIAL_TOKEN_CAP and call.tool_use_id not in notice_ids
    )
    for notice_id in notice_ids:
        notice_outcome = outcome_by_tool_use_id.get(notice_id)
        if notice_outcome == _OUTCOME_SIZE_UNKNOWN:
            totals.notices_naming_size_unknown_calls += 1
        elif notice_outcome != _OUTCOME_PARTIAL_TOKEN_CAP:
            totals.notices_naming_other_calls += 1


def _accumulate_read_weight(totals: _Totals, window: _WindowReads, weights: dict[str, float]) -> None:
    for event, role, bucket in window.sized_events:
        weight = read_cost._read_weight(event, weights)
        totals.read_weight += weight
        if bucket in _BUCKETS_OVER_PAGE:
            totals.read_weight_over_page += weight
            if role == _ROLE_CODE_OR_OTHER:
                totals.read_weight_over_page_code_or_other += weight
            elif role == _ROLE_DIFF_HANDOFF:
                totals.read_weight_over_page_diff_handoff += weight
        elif bucket == _BUCKET_UNKNOWN:
            totals.read_weight_unknown_size += weight


def _accumulate_reviewer_window(
    totals: _Totals, label: str, records: list[dict], scan: read_cost._WindowScan, billed: float, weights: dict[str, float],
) -> None:
    window = _read_window(scan)
    type_row = totals.type_rows.setdefault(label, Counter())
    type_row["windows"] += 1
    totals.reviewer_windows += 1
    totals.billed_weight += billed
    totals.version_counts[_window_version(records)] += 1
    totals.model_counts[_window_model(records)] += 1
    _accumulate_read_weight(totals, window, weights)
    _accumulate_notice_agreement(totals, scan, window.calls)
    for call in window.calls:
        totals.outcome_calls[(call.role, call.outcome, call.bucket)] += 1
        if call.outcome == _OUTCOME_SIZE_UNKNOWN:
            totals.size_unknown_reasons[call.reason] += 1
        totals.unrecognised_limit_errors += call.unrecognised_limit_error
        if call.outcome == _OUTCOME_PARTIAL_UNFLAGGED and call.bucket != _BUCKET_OVER_DEFAULT_LIMIT:
            totals.unexplained_partials += 1
        if call.role in _REVIEWED_ROLES and _is_in_estimate_band(call):
            totals.headline[("band",)] += 1
        _accumulate_headline(totals, call, type_row)
    _accumulate_follow_ups(totals, window.calls, window.reads_by_path)


def _read_call_blocks(turn: dict) -> Iterator[read_cost._ReadCall]:
    """Each Read call in the turn's content, by the predicate `read_cost._scan_window` applies."""
    message = turn.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, list):
        return
    for block in content:
        read_call = read_cost._read_call(block) if isinstance(block, dict) else None
        if read_call is not None:
            yield read_call


def _accumulate_round_reads(
    totals: _Totals, main_thread_records: list[dict], main_calls: Sequence[_Call], since_ts: float, until_epoch: float,
) -> None:
    """Joins the Read blocks inside each round window opened in the window to their classified calls by tool_use id."""
    call_by_tool_use_id = {call.tool_use_id: call for call in main_calls}
    turns = pricing.dedup_turns_by_request_id(main_thread_records)
    for open_index, window_end, skill in review_rounds.detect_round_windows(turns):
        opened_at = _record_epoch(turns[open_index])
        if opened_at is None:
            totals.round_windows_without_timestamp += 1
            continue
        if not since_ts <= opened_at < until_epoch:
            continue
        round_totals = totals.rounds[skill]
        round_totals.windows += 1
        counted_tool_use_ids: set[str] = set()
        for turn in turns[open_index:window_end]:
            for read_call in _read_call_blocks(turn):
                tool_id = read_call.tool_use_id
                if tool_id in counted_tool_use_ids:
                    continue
                counted_tool_use_ids.add(tool_id)
                if not read_call.whole_file:
                    round_totals.targeted_calls += 1
                    continue
                round_totals.whole_file_calls += 1
                if _role(read_call.path) == _ROLE_DIFF_HANDOFF:
                    round_totals.diff_handoff_whole_file_calls += 1
                elif tool_id in call_by_tool_use_id:
                    round_totals.outcomes[call_by_tool_use_id[tool_id].outcome] += 1
                    round_totals.buckets[call_by_tool_use_id[tool_id].bucket] += 1


def _accumulate_session(
    totals: _Totals,
    seen: read_cost._SeenIds,
    main_records: Sequence[dict],
    subagent_windows: Iterable[tuple[str, list[dict]]],
    weights: dict[str, float],
    since_ts: float,
    until_epoch: float,
    tracked_agent_types: frozenset[str],
) -> None:
    totals.sessions += 1
    main_thread_records = [rec for rec in _usable_records(main_records) if not rec.get("isSidechain")]
    main_scan = read_cost._scan_window(main_thread_records, seen.tool_use_ids, seen.failed_tool_use_ids)
    read_cost._new_billed_weight(main_scan, seen.message_ids, weights)
    totals.invalid_usage_turns = read_cost._count_invalid_usage_turns(seen, main_scan)
    _accumulate_round_reads(totals, main_thread_records, _read_window(main_scan).calls, since_ts, until_epoch)

    for agent_type, agent_records in subagent_windows:
        if not reviewer_yield._is_reviewer_subagent_type(agent_type):
            continue
        records = _usable_records(agent_records)
        opened_at = _first_epoch(records)
        if opened_at is None:
            totals.windows_without_timestamp += 1
            continue
        if not since_ts <= opened_at < until_epoch:
            continue
        if agent_type == _SKILL_FIDELITY_AGENT_TYPE:
            totals.skill_fidelity_windows_left_out += 1
            continue
        scan = read_cost._scan_window(records, seen.tool_use_ids, seen.failed_tool_use_ids)
        billed, _calls = read_cost._new_billed_weight(scan, seen.message_ids, weights)
        totals.invalid_usage_turns = read_cost._count_invalid_usage_turns(seen, scan)
        _accumulate_reviewer_window(
            totals, _agent_type_label(agent_type, tracked_agent_types), records, scan, billed, weights,
        )


def _rate(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "no data (0/0)"
    if denominator < _RATE_FLOOR:
        return f"{reviewer_yield._REVIEWER_YIELD_INSUFFICIENT} ({numerator:,}/{denominator:,})"
    return f"{100 * numerator / denominator:.1f}% ({numerator:,}/{denominator:,})"


def _weight_share(part: float, whole: float, windows: int) -> str:
    if whole == 0:
        return "no data (0/0)"
    figures = f"{part:,.1f}/{whole:,.1f}"
    if windows < _RATE_FLOOR:
        return f"{reviewer_yield._REVIEWER_YIELD_INSUFFICIENT} ({figures})"
    return f"{100 * part / whole:.1f}% ({figures})"


def _role_title(role: str) -> str:
    if role == _ROLE_PROSE:
        return "prose (instruction and other_prose; instruction is matched by path, whatever the extension)"
    if role == _ROLE_DIFF_HANDOFF:
        return "diff handoff (the review diff, not a reviewed file)"
    return _ROLE_CODE_OR_OTHER


def _headline_counts(totals: _Totals, roles: Sequence[str]) -> tuple[int, int, int]:
    return tuple(sum(totals.headline[(role, name)] for role in roles) for name in ("denominator", "partial", "refused"))


def _print_headline(totals: _Totals) -> None:
    print("\n## Whole-file reads of reviewed files larger than one Read call")
    print(
        "partial is partial_token_cap or partial_unflagged and refused is refused_over_limit. A refused read is never"
        " counted as partial. The denominator is calls that were partial or refused, complete on a file over 2,000"
        " lines, or allow_large at an estimated 25,000 tokens or more (4 chars/token)."
    )
    for title, roles in (
        (_role_title(_ROLE_CODE_OR_OTHER), (_ROLE_CODE_OR_OTHER,)),
        (_role_title(_ROLE_PROSE), (_ROLE_PROSE,)),
        ("pooled", _REVIEWED_ROLES),
    ):
        denominator, partial, refused = _headline_counts(totals, roles)
        print(
            f"{title}: partial {_rate(partial, denominator)}; refused {_rate(refused, denominator)};"
            f" partial or refused {_rate(partial + refused, denominator)}"
        )
    print(
        f"complete_allow_large calls on files of up to {_DEFAULT_LINE_LIMIT:,} lines with an estimate from"
        f" {_TOKEN_ESTIMATE_BAND[0]:,} to {_TOKEN_ESTIMATE_BAND[1] - 1:,} tokens, where the estimate alone decides"
        f" the denominator: {totals.headline[('band',)]:,}"
    )
    out_of_denominator = {
        outcome: sum(totals.outcome_calls[(role, outcome, bucket)] for role in _REVIEWED_ROLES for bucket in _BUCKETS)
        for outcome in (_OUTCOME_OTHER_ERROR, _OUTCOME_SIZE_UNKNOWN)
    }
    print(
        "outside the denominator, reviewed files only:"
        + "".join(f" {outcome}={count:,}" for outcome, count in out_of_denominator.items())
    )


def _print_outcome_tables(totals: _Totals) -> None:
    print("\n## Whole-file calls in reviewer windows, by outcome and file size (lines)")
    for role in _ROLES:
        print(f"{_role_title(role)}:")
        for outcome in _OUTCOMES:
            by_bucket = {bucket: totals.outcome_calls[(role, outcome, bucket)] for bucket in _BUCKETS}
            print(
                f"  {outcome}: total={sum(by_bucket.values()):,}"
                + "".join(f" {bucket}={count:,}" for bucket, count in by_bucket.items())
            )


def _print_follow_up(totals: _Totals) -> None:
    print("\n## After a partial or refused whole-file call, in the same reviewer window")
    print(
        "The command sees Read calls only, so the neither figure is an upper bound on calls after which the reviewer"
        " made no further attempt to read on: a Grep, Bash or diff read that recovered the content is not seen."
    )
    for role in _ROLES:
        calls = totals.follow_up[(role, "calls")]
        print(
            f"{_role_title(role)}: calls={calls:,}"
            f" later_offset_read {_rate(totals.follow_up[(role, 'later_offset_read')], calls)};"
            f" covered_after {_rate(totals.follow_up[(role, 'covered_after')], calls)};"
            f" {_FOLLOW_UP_NEITHER_LABEL} {_rate(totals.follow_up[(role, 'neither')], calls)}"
        )


def _print_read_share(totals: _Totals) -> None:
    windows = totals.reviewer_windows
    print(f"\n## Read share of reviewer spend, a share of modeled billed weight and not of tokens ({windows:,} reviewer windows)")
    print(f"Read weight over billed weight: {_weight_share(totals.read_weight, totals.billed_weight, windows)}")
    for title, weight in (
        ("files over 1,000 lines", totals.read_weight_over_page),
        ("code/other reviewed files over 1,000 lines", totals.read_weight_over_page_code_or_other),
        ("diff handoffs over 1,000 lines", totals.read_weight_over_page_diff_handoff),
        ("files of unknown size", totals.read_weight_unknown_size),
    ):
        print(f"  of Read weight, {title}: {_weight_share(weight, totals.read_weight, windows)}")
    print(f"sums: billed_weight={totals.billed_weight:,.1f} read_weight={totals.read_weight:,.1f}")


def _ordered_rows(rows: dict[str, Counter]) -> list[tuple[str, Counter]]:
    """TOTAL first, then tracked names in order, then the withheld row last."""
    total: Counter = Counter()
    for row in rows.values():
        total.update(row)
    withheld = subagent_mix._WITHHELD_AGENT_TYPE_LABEL
    named = sorted((label, row) for label, row in rows.items() if label != withheld)
    return [("TOTAL", total), *named, *([(withheld, rows[withheld])] if withheld in rows else [])]


def _print_type_rows(totals: _Totals) -> None:
    print(
        "\n## By reviewer type, counts only (windows counts every reviewer window and the other counts cover reviewed"
        " files, not diff handoffs; agent types this repo does not track are folded into one withheld row)"
    )
    for label, row in _ordered_rows(totals.type_rows):
        print(
            f"{label}: windows={row['windows']:,} partial={row['partial']:,} refused={row['refused']:,}"
            f" larger_than_one_call={row['larger_than_one_call']:,}"
        )


def _print_round_reads(totals: _Totals) -> None:
    print("\n## Main-thread Reads inside review-round windows, counts only")
    for skill in review_rounds.REVIEW_SKILLS:
        round_totals = totals.rounds[skill]
        print(
            f"{skill}: round_windows={round_totals.windows:,}"
            f" read_calls={round_totals.whole_file_calls + round_totals.targeted_calls:,}"
            f" whole_file={round_totals.whole_file_calls:,} targeted={round_totals.targeted_calls:,}"
        )
        print(
            "  reviewed-file whole-file calls by outcome:"
            + "".join(f" {outcome}={round_totals.outcomes[outcome]:,}" for outcome in _OUTCOMES)
        )
        print(
            "  reviewed-file whole-file calls by file size:"
            + "".join(f" {bucket}={round_totals.buckets[bucket]:,}" for bucket in _BUCKETS)
        )
        print(f"  diff-handoff whole-file calls: {round_totals.diff_handoff_whole_file_calls:,}")


@dataclass
class _YieldPass:
    rows: dict[str, Counter]
    skipped_input_total: int
    meta_read_errors: int
    transcript_read_errors: int
    completed: bool = True


def _yield_pass(
    args: argparse.Namespace, roots: Sequence[Path], since_ts: float, until_epoch: float,
    tracked_agent_types: frozenset[str],
) -> _YieldPass:
    gaps: Counter = Counter()
    session_iter, _scope_label = scope._resolve_project_scope(
        args, _COMMAND_LABEL, include_subagents=True, roots=roots, scan_gaps=gaps,
    )
    try:
        data = reviewer_yield.compute_reviewer_yield_data(
            _usable_record_sessions(session_iter), since_ts=since_ts, until_ts=until_epoch,
        )
    except (AttributeError, TypeError, ValueError, RecursionError):
        # reviewer_yield and corpus read some record and sidecar fields unguarded. ValueError covers an integer over the
        # interpreter's digit limit and, as UnicodeEncodeError's base, a lone surrogate in a hashed path. RecursionError
        # covers JSON nested past the decoder's stack. The exception text can hold record content, so it is dropped and
        # the section prints a fixed notice.
        return _YieldPass({}, 0, 0, 0, completed=False)
    pricing._warn_if_subagent_format_drift(data["subagent_spawns"], data["sidechain_turns"])
    rows: dict[str, Counter] = {}
    for agent_type, counts in data["agg"].items():
        rows.setdefault(_agent_type_label(agent_type, tracked_agent_types), Counter()).update(counts)
    for (agent_type, bucket), counts in data["agg2"].items():
        row = rows.setdefault(_agent_type_label(agent_type, tracked_agent_types), Counter())
        for name, value in counts.items():
            row[(bucket, name)] += value
    return _YieldPass(rows, sum(gaps.values()), data["meta_read_errors"], data["transcript_read_errors"])


def _bounded_findings(findings: int) -> str:
    """The count, or the ceiling's name past it, so a reviewer's own text cannot set the width of a printed figure."""
    return f"{findings:,}" if findings <= _FINDINGS_PRINT_CEILING else f"over {_FINDINGS_PRINT_CEILING:,}"


def _print_yield(yield_pass: _YieldPass, until_epoch: float) -> None:
    print(
        "\n## Reviewer-yield: main-thread reviewer dispatches in the window"
        " (agent types this repo does not track are folded into one withheld row)"
    )
    print(
        f"(--until {render._fmt_date(until_epoch - 86400)} does not bound the cited, active and edited counts:"
        " their tool-result and edit indexes are bounded by --since alone.)"
    )
    if not yield_pass.completed:
        print(
            "reviewer-yield pass: not completed, because the shared reviewer-yield code raised an AttributeError,"
            " TypeError, ValueError or RecursionError, so no yield rows are printed"
        )
        return
    print(
        f"reviewer-yield pass: skipped_input_total={yield_pass.skipped_input_total:,}"
        f" meta_read_errors={yield_pass.meta_read_errors:,}"
        f" reviewer_transcript_read_errors={yield_pass.transcript_read_errors:,}"
    )
    for label, row in _ordered_rows(yield_pass.rows):
        print(
            f"{label}: dispatches={row['dispatches']:,} findings_found={row['findings_found']:,}"
            f" zero_finding={row['zero_finding']:,} unclassified={row['unclassified']:,}"
            f" findings={_bounded_findings(row['total_findings'])}"
        )
        for bucket, dispatches in (
            (reviewer_yield._REVIEWER_VERDICT_FINDINGS_FOUND, row["findings_found"]),
            (reviewer_yield._REVIEWER_VERDICT_ZERO_FINDING, row["zero_finding"]),
        ):
            if dispatches:
                active, edited = row[(bucket, "active")], row[(bucket, "edited")]
                print(
                    f"  {bucket}: cited={row[(bucket, 'cited')]:,} active={active:,} edited={edited:,}"
                    f" edited_rate {_rate(edited, active)}"
                )


def _print_ledger(counts: ledger_dispositions.LedgerDispositionCounts) -> None:
    terminal_total = sum(counts.terminal_by_disposition.values())
    print(
        "\n## Review-ledger terminal disposition rows in the window"
        " (disposition rows, not distinct findings: a finding re-raised without --ref counts again)"
    )
    print(
        "terminal rows:"
        + "".join(f" {disposition}={count:,}" for disposition, count in counts.terminal_by_disposition.items())
        + f" total={terminal_total:,}"
    )
    for disposition in (author_outcome._DISPOSITION_ADDRESS, author_outcome._DISPOSITION_DEFER):
        print(f"{disposition} share of terminal rows: {_rate(counts.terminal_by_disposition[disposition], terminal_total)}")
    print(
        f"sessions with a disposition row={counts.sessions_with_disposition_row:,}"
        f" covered by the transcript scan={counts.sessions_covered_by_scan:,}"
    )
    print(
        f"ledger files: directory={counts.directory_state} read={counts.files_read:,}"
        f" unreadable={counts.unreadable_files:,}"
    )
    print(
        f"ledger rows set aside, in the window: id_less_disposition_rows={counts.id_less_disposition_rows:,}"
        f" unknown_disposition_rows={counts.unknown_disposition_rows:,}"
    )
    print(
        "ledger rows left out of every file read, whatever the row's date or disposition:"
        + "".join(f" left_out_{field_name}={count:,}" for field_name, count in counts.left_out_by_field.items())
    )


def _print_comparability(totals: _Totals) -> None:
    print("\n## Comparability: reviewer windows by harness version and by model")
    for title, counts in (("harness version", totals.version_counts), ("model", totals.model_counts)):
        ordered = sorted(counts.items())
        print(f"{title}:" + "".join(f" {name}={count:,}" for name, count in ordered))


def _print_diagnostics(totals: _Totals) -> None:
    print("\n## Diagnostics (calls are counted over every role, diff handoffs included)")
    print(
        f"unexplained partials (partial_unflagged on files of up to {_DEFAULT_LINE_LIMIT:,} lines):"
        f" {totals.unexplained_partials:,}"
    )
    print(
        "notice agreement:"
        f" partial_token_cap calls with no read_truncation_notice={totals.notices_missing_for_partial_token_cap:,};"
        " notices naming neither a partial_token_cap nor a size_unknown call="
        f"{totals.notices_naming_other_calls:,}; notices naming a size_unknown call="
        f"{totals.notices_naming_size_unknown_calls:,}"
    )
    print(
        "size_unknown by reason:"
        + "".join(f" {reason}={totals.size_unknown_reasons[reason]:,}" for reason in _SIZE_UNKNOWN_REASONS)
    )
    other_errors = sum(
        count for (_role_name, outcome, _bucket), count in totals.outcome_calls.items() if outcome == _OUTCOME_OTHER_ERROR
    )
    print(f"all roles: other_error={other_errors:,} unrecognised_limit_error={totals.unrecognised_limit_errors:,}")
    print(f"skill-fidelity-reviewer windows left out, in the window: {totals.skill_fidelity_windows_left_out:,}")
    print(
        "reviewer windows with no timestamped record, whatever the window:"
        f" {totals.windows_without_timestamp:,}"
    )
    print(
        "review-round windows whose opening record has no parsable timestamp, whatever the window:"
        f" {totals.round_windows_without_timestamp:,}"
    )


def _print_report(
    totals: _Totals, weights: dict[str, float], since_ts: float, until_epoch: float, yield_pass: _YieldPass,
    ledger_counts: ledger_dispositions.LedgerDispositionCounts,
) -> None:
    read_cost._print_unit_caption(weights)
    print(f"\nwindow: {render._fmt_date(since_ts)} to {render._fmt_date(until_epoch - 86400)} (UTC, both days included)")
    print(
        f"sessions={totals.sessions:,} reviewer_windows={totals.reviewer_windows:,}"
        " (sessions and the skipped input line's scan gaps count every retained in-scope transcript, whatever the window;"
        " its invalid_usage_turns counts every main-thread turn and only the reviewer windows in the window)"
    )
    print(read_cost._skipped_input_line(totals.scan_gaps, totals.invalid_usage_turns))
    _print_headline(totals)
    _print_outcome_tables(totals)
    _print_follow_up(totals)
    _print_read_share(totals)
    _print_type_rows(totals)
    _print_round_reads(totals)
    _print_yield(yield_pass, until_epoch)
    _print_ledger(ledger_counts)
    _print_comparability(totals)
    _print_diagnostics(totals)


def _exit_with_usage_error(message: str) -> None:
    print(f"{_COMMAND_LABEL}: {message}", file=sys.stderr)
    sys.exit(2)


def _window_bounds(args: argparse.Namespace) -> tuple[float, float]:
    """(since_ts, until_epoch), exiting 2 for a missing or unparsable date or a window that is empty or reversed."""
    since_ts, until_epoch = scope._parse_absolute_window_args(args, _COMMAND_LABEL)
    if since_ts is None:
        _exit_with_usage_error("--since is required and must be a zero-padded YYYY-MM-DD date")
    if until_epoch is None:
        _exit_with_usage_error("--until is required and must be a zero-padded YYYY-MM-DD date")
    if since_ts >= until_epoch:
        _exit_with_usage_error("--since must not be after --until")
    return since_ts, until_epoch


def cmd_reviewer_reads(args: argparse.Namespace) -> None:
    """See docs/transcript-analysis.md's `reviewer-reads` section for the flags, the outcome classes and the publication scope."""
    _reviewer_reads_report(args, publication_scope._single_account_roots(_COMMAND_LABEL))


def _reviewer_reads_report(args: argparse.Namespace, roots: Sequence[Path]) -> None:
    publication_scope._refuse_wider_scope(args, roots, _COMMAND_LABEL)
    since_ts, until_epoch = _window_bounds(args)
    weights = pricing._cache_read_equivalent_weights()
    tracked_agent_types = redaction._repo_tracked_agent_type_names()

    worktree_paths = scope._repo_worktree_paths(_COMMAND_LABEL)
    args._this_repo_slugs = [scope._path_to_project_slug(path) for path in worktree_paths]
    totals = _Totals()
    session_iter, scope_label = scope._resolve_project_scope(args, _COMMAND_LABEL, roots=roots, scan_gaps=totals.scan_gaps)
    print(publication_scope._scope_header(scope_label, _COMMAND_LABEL))

    seen = read_cost._SeenIds()
    for main_jsonl, main_records in session_iter:
        totals.scanned_session_ids.add(main_jsonl.stem)
        _accumulate_session(
            totals, seen, main_records, read_cost._read_subagent_windows(main_jsonl, totals.scan_gaps), weights,
            since_ts, until_epoch, tracked_agent_types,
        )

    yield_pass = _yield_pass(args, roots, since_ts, until_epoch, tracked_agent_types)
    ledger_counts = ledger_dispositions.count_ledger_dispositions(
        roots[0].parent, worktree_paths, since_ts, until_epoch, totals.scanned_session_ids,
    )
    _print_report(totals, weights, since_ts, until_epoch, yield_pass, ledger_counts)


def _add_reviewer_reads_subparser(subparsers: argparse._SubParsersAction) -> None:
    p_reviewer_reads = subparsers.add_parser(
        "reviewer-reads",
        help=(
            "How reviewer subagents' whole-file Reads came back, the Read share of their spend, and the review"
            " ledger's terminal dispositions, over an explicit date window. Requires --this-repo, --since and"
            " --until; reads one account and refuses a wider scope. Aggregate-only output."
        ),
    )
    scope._add_project_scope_args(p_reviewer_reads)
    for flag, edge in (("--since", "first"), ("--until", "last")):
        p_reviewer_reads.add_argument(
            flag, metavar="DATE", type=scope._iso_date,
            help=f"Required. The {edge} day of the window, as a zero-padded UTC YYYY-MM-DD date (both days are included).",
        )
    p_reviewer_reads.set_defaults(func=cmd_reviewer_reads)
