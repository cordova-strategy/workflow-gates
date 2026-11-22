"""The correction-candidates command: cmd_correction_candidates, which writes every main-session
AskUserQuestion exchange and every typed prompt, each with the agent text around it, as JSON Lines
to one owner-only file, and its subparser registration.

The typed-prompt definition is docs/transcript-analysis.md's "Terms" entry, and the record schema is
that doc's correction-candidates section.

Reaches every `transcript_analysis` module by attribute access, not by name; see `scope.py`'s top-of-file comment.
"""
from __future__ import annotations

import argparse
import json
import sys
from bisect import bisect_left, bisect_right
from collections import Counter
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from transcript_analysis import (
    corpus,
    ledger_common,
    pricing,
    redaction,
    render,
    review_rounds,
    scope,
    skill_invocation,
    user_input,
)

_COMMAND = "correction-candidates"
SCHEMA_VERSION = 1
DEFAULT_TRUNCATE_CHARS = 2000
_ASK_USER_QUESTION_TOOL = "AskUserQuestion"

KIND_PROMPT = "prompt"
KIND_QUESTION = "question"
KIND_SCOPE = "scope"

VERDICT_TYPED = "typed"
SKIP_INTERRUPT = "interrupt"
SKIP_SLASH_COMMAND = "slash_command"
SKIP_LOCAL_COMMAND = "local_command"
SKIP_BASH_MODE = "bash_mode"
SKIP_NON_HUMAN_ORIGIN = "non_human_origin"
SKIP_HEADLESS = "headless"
SKIP_NO_ORIGIN_AFTER_ORIGIN = "no_origin_after_origin"
SKIP_NOTIFICATION_TEXT = "notification_text"
SKIP_MALFORMED_QUESTION = "malformed_question"
SKIP_UNANSWERED_QUESTION = "unanswered_question"
SKIP_DUPLICATE_PROMPT = "duplicate_prompt"
SKIP_DUPLICATE_QUESTION = "duplicate_question"
SKIP_UNDATED = "undated"
SKIP_UNINTERPRETABLE = "uninterpretable"
SKIP_KINDS = (
    SKIP_INTERRUPT, SKIP_SLASH_COMMAND, SKIP_LOCAL_COMMAND, SKIP_BASH_MODE, SKIP_NON_HUMAN_ORIGIN, SKIP_HEADLESS,
    SKIP_NO_ORIGIN_AFTER_ORIGIN, SKIP_NOTIFICATION_TEXT, SKIP_MALFORMED_QUESTION, SKIP_UNANSWERED_QUESTION,
    SKIP_DUPLICATE_PROMPT, SKIP_DUPLICATE_QUESTION, SKIP_UNDATED, SKIP_UNINTERPRETABLE,
)

_CALLS_COUNT = "ask_user_question_calls"

# A prompt-shaped record that opens with one of these is the harness's record of a command, not typed text.
_COMMAND_OPENING_VERDICTS = (
    ("<command-message>", SKIP_SLASH_COMMAND),
    ("<command-name>", SKIP_SLASH_COMMAND),
    (render._COMMAND_ARGS_OPENER, SKIP_SLASH_COMMAND),
    ("<local-command-", SKIP_LOCAL_COMMAND),
    ("<bash-", SKIP_BASH_MODE),
)
_SLASH_COMMAND_OPENINGS = tuple(
    opening for opening, skip_kind in _COMMAND_OPENING_VERDICTS if skip_kind == SKIP_SLASH_COMMAND
)
# An interrupt marker, local-command output and a bash-mode record are harness echoes, so none starts an exchange.
_NON_OPENING_VERDICTS = frozenset({SKIP_INTERRUPT, SKIP_LOCAL_COMMAND, SKIP_BASH_MODE})
_INTERRUPT_TEXT_PREFIX = "[Request interrupted by user"
# compaction-context.py's `_is_prompt_candidate` applies the same literal inline to the same class of record.
_TASK_NOTIFICATION_CLOSER_FRAGMENT = "task-notification>"

_ABSENT_RESULT_TYPE = "absent"
_ASSISTANT_TEXT_SEPARATOR = "\n\n"
_MULTI_SELECT_SEPARATOR = ", "

_RELATION_ANSWERS_READ = "answers_read"
_RELATION_ANSWERS_KEYED = "answers_keyed"
_RELATION_LABELS_MATCHED = "labels_matched"


@dataclass(frozen=True)
class _Candidate:
    """One output line plus the facts about it that the record itself does not carry."""

    record: dict
    kind: str
    session_id: str
    family: str
    record_index: int
    block_position: int
    dedup_key: str | None
    result_type: str | None = None
    truncated_fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class _ReferenceRecord:
    model: str
    attribution_skill: str | None


@dataclass
class _FileTimeline:
    """Per-file facts the context fields read, indexed by record position."""

    record_count: int
    first_assistant_index: int | None = None
    openings: list[int] = field(default_factory=list)
    interrupts: list[int] = field(default_factory=list)
    text_indexes: list[int] = field(default_factory=list)
    texts: list[str] = field(default_factory=list)
    reference_indexes: list[int] = field(default_factory=list)
    references: list[_ReferenceRecord] = field(default_factory=list)

    def add_assistant(self, index: int, rec: dict) -> None:
        if self.first_assistant_index is None:
            self.first_assistant_index = index
        text = render._content_text(_message_content(rec))
        if text.strip():
            self.text_indexes.append(index)
            self.texts.append(text)
        message = rec.get("message")
        model = message.get("model") if isinstance(message, dict) else None
        if isinstance(model, str) and model != pricing._SYNTHETIC_MODEL_ID:
            raw_skill = rec.get("attributionSkill")
            skill = skill_invocation._normalize_skill_name(raw_skill) if isinstance(raw_skill, str) and raw_skill else None
            self.reference_indexes.append(index)
            self.references.append(_ReferenceRecord(model, skill))

    def has_assistant_before(self, index: int) -> bool:
        return self.first_assistant_index is not None and self.first_assistant_index < index

    def exchange_at(self, index: int) -> int:
        """The 1-based ordinal of the exchange record `index` sits in or opens, or 0 before the first opening."""
        return bisect_right(self.openings, index)

    def previous_opening(self, index: int) -> int:
        position = bisect_left(self.openings, index)
        return self.openings[position - 1] if position else -1

    def next_opening(self, index: int) -> int:
        position = bisect_right(self.openings, index)
        return self.openings[position] if position < len(self.openings) else self.record_count

    def interrupt_between(self, low_exclusive: int, high_exclusive: int) -> bool:
        position = bisect_right(self.interrupts, low_exclusive)
        return position < len(self.interrupts) and self.interrupts[position] < high_exclusive

    def assistant_text_between(self, low_exclusive: int, high_exclusive: int) -> str:
        start = bisect_right(self.text_indexes, low_exclusive)
        stop = bisect_left(self.text_indexes, high_exclusive)
        return _ASSISTANT_TEXT_SEPARATOR.join(self.texts[start:stop])

    def reference_at(self, index: int) -> _ReferenceRecord | None:
        position = bisect_right(self.reference_indexes, index) - 1
        return self.references[position] if position >= 0 else None


def _message_content(rec: dict) -> object:
    message = rec.get("message")
    return message.get("content") if isinstance(message, dict) else None


def _record_epoch(rec: dict) -> float | None:
    """The record's `timestamp` as epoch seconds, or None when it is absent, not a string, or cannot be converted.

    `corpus._parse_ts` catches `ValueError` and `TypeError`, and this function adds `OverflowError` and `OSError`.
    A record whose conversion raises any of them reads as undated, so it never aborts the run. A timestamp the
    conversion accepts but `_iso_utc` cannot format (a UTC year beyond 9999) emits `timestamp: null` and is not
    counted undated.
    """
    timestamp = rec.get("timestamp")
    if not isinstance(timestamp, str):
        return None
    try:
        return corpus._parse_ts(timestamp)
    except (OverflowError, OSError):
        return None


def _iso_utc(epoch: float | None) -> str | None:
    if epoch is None:
        return None
    try:
        return datetime.fromtimestamp(epoch, tz=UTC).isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def _in_window(epoch: float | None, since_ts: float | None, until_epoch: float | None) -> bool:
    if since_ts is None and until_epoch is None:
        return True
    if epoch is None:
        return False
    return (since_ts is None or epoch >= since_ts) and (until_epoch is None or epoch < until_epoch)


def _is_prompt_shaped(rec: dict) -> bool:
    return user_input._is_fresh_user_prompt_for_narrative(rec) and render._is_fresh_user_prompt(rec)


def _slash_command_args(text: str) -> tuple[str, str] | None:
    """A slash prompt's command name, with its leading `/`, and its stripped args, or None when `text` is not one.

    `text` is a prompt-shaped record's stripped text. It is a slash prompt only when it opens with a slash-command
    tag, names its command in a `<command-name>` tag, and carries non-empty args.
    """
    if not text.startswith(_SLASH_COMMAND_OPENINGS):
        return None
    name_match = review_rounds._SLASH_COMMAND_RE.search(text)
    args = render._first_command_args(text).strip()
    if name_match is None or not args:
        return None
    return f"/{name_match.group(1)}", args


def _prompt_verdict(rec: dict, origin_seen: bool) -> str:
    """The verdict for a prompt-shaped record: `typed`, or the skip kind that names why it is not a typed prompt.

    `origin_seen` is whether an earlier record in the same file carried an `origin`.
    """
    text = render._content_text(_message_content(rec)).strip()
    if render._is_interrupt_marker(rec) or text.startswith(_INTERRUPT_TEXT_PREFIX):
        return SKIP_INTERRUPT
    for opening, skip_kind in _COMMAND_OPENING_VERDICTS:
        if text.startswith(opening):
            is_slash_prompt = (
                skip_kind == SKIP_SLASH_COMMAND and render._has_human_origin(rec) and _slash_command_args(text) is not None
            )
            return VERDICT_TYPED if is_slash_prompt else skip_kind
    if rec.get("origin") is not None:
        return VERDICT_TYPED if render._has_human_origin(rec) else SKIP_NON_HUMAN_ORIGIN
    if render._has_headless_markers(rec):
        return SKIP_HEADLESS
    if origin_seen:
        return SKIP_NO_ORIGIN_AFTER_ORIGIN
    if _TASK_NOTIFICATION_CLOSER_FRAGMENT in text:
        return SKIP_NOTIFICATION_TEXT
    return VERDICT_TYPED


def _answer_is_free_text(answer: str | None, labels: Iterable[str], multi_select: bool) -> bool | None:
    """Whether the answer is typed text rather than a selection, or None when there is no answer text."""
    if answer is None or not answer.strip():
        return None
    label_set = {label for label in labels if label}
    if not multi_select:
        return answer not in label_set
    reached_positions = {0}
    pending_positions = [0]
    while pending_positions:
        position = pending_positions.pop()
        for label in label_set:
            if not answer.startswith(label, position):
                continue
            label_end = position + len(label)
            if label_end == len(answer):
                return False
            next_position = label_end + len(_MULTI_SELECT_SEPARATOR)
            if answer.startswith(_MULTI_SELECT_SEPARATOR, label_end) and next_position not in reached_positions:
                reached_positions.add(next_position)
                pending_positions.append(next_position)
    return True


class _Truncation:
    """Cuts free-text fields at `limit` characters and records the name of each field it cut. A limit of 0 cuts nothing."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.cut_fields: list[str] = []

    def _note_if_cut(self, field_name: str, value: str) -> bool:
        """Whether `value` exceeds the limit, recording `field_name` when it does."""
        is_cut = self.limit != 0 and len(value) > self.limit
        if is_cut:
            self.cut_fields.append(field_name)
        return is_cut

    def head(self, field_name: str, value: str) -> str:
        self._note_if_cut(field_name, value)
        return user_input._truncate_prompt_text(value, self.limit)

    def head_or_none(self, field_name: str, value: str | None) -> str | None:
        return None if value is None else self.head(field_name, value)

    def tail(self, field_name: str, value: str) -> str:
        """The last `limit` characters, with the truncation note in front."""
        if not self._note_if_cut(field_name, value):
            return value
        return f"(truncated, {len(value)} chars total) …{value[-self.limit:]}"


def _ask_blocks(rec: dict) -> list[tuple[int, dict]]:
    """Each AskUserQuestion tool_use block of an assistant record with its position in the record's content."""
    content = _message_content(rec)
    if not isinstance(content, list):
        return []
    return [
        (position, block)
        for position, block in enumerate(content)
        if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == _ASK_USER_QUESTION_TOOL
    ]


def _well_formed_questions(block: dict) -> list[dict] | None:
    """The block's `input.questions`, or None when the block has no string id or no non-empty list of question dicts."""
    tool_input = block.get("input")
    if not isinstance(block.get("id"), str) or not isinstance(tool_input, dict):
        return None
    questions = tool_input.get("questions")
    if not isinstance(questions, list) or not questions:
        return None
    if not all(isinstance(entry, dict) and isinstance(entry.get("question"), str) for entry in questions):
        return None
    return questions


def _option_entries(entry: dict) -> list[dict]:
    """The entry's well-formed options as `label` and `description` dicts."""
    options = entry.get("options")
    if not isinstance(options, list):
        return []
    return [
        {
            "label": option["label"],
            "description": option.get("description") if isinstance(option.get("description"), str) else None,
        }
        for option in options
        if isinstance(option, dict) and isinstance(option.get("label"), str)
    ]


def _result_text(result_block: dict) -> str | None:
    """The `tool_result` block's text content, or None when it holds none."""
    content = result_block.get("content")
    if isinstance(content, str):
        return content or None
    if isinstance(content, list):
        pieces = [
            piece["text"]
            for piece in content
            if isinstance(piece, dict) and piece.get("type") == "text" and isinstance(piece.get("text"), str)
        ]
        return " ".join(pieces) or None
    return None


def _tool_result_blocks(rec: dict) -> list[dict]:
    content = _message_content(rec)
    if not isinstance(content, list):
        return []
    return [
        block
        for block in content
        if isinstance(block, dict) and block.get("type") == "tool_result" and isinstance(block.get("tool_use_id"), str)
    ]


def _question_entries(
    questions: Sequence[dict], tool_use_result: object, answered: bool, truncation: _Truncation
) -> list[dict]:
    """The output entry for each asked question."""
    answers = tool_use_result["answers"] if answered else {}
    annotations = tool_use_result.get("annotations") if isinstance(tool_use_result, dict) else None
    entries: list[dict] = []
    for entry in questions:
        question = entry["question"]
        options = _option_entries(entry)
        multi_select = entry.get("multiSelect") is True
        answer = answers.get(question)
        answer = answer if isinstance(answer, str) else None
        annotation = annotations.get(question) if isinstance(annotations, dict) else None
        notes = annotation.get("notes") if isinstance(annotation, dict) else None
        header = entry.get("header")
        entries.append({
            "question": truncation.head("question", question),
            "header": truncation.head_or_none("header", header if isinstance(header, str) else None),
            "multi_select": multi_select,
            "options": [
                {
                    "label": truncation.head("label", option["label"]),
                    "description": truncation.head_or_none("description", option["description"]),
                }
                for option in options
            ],
            "answer": truncation.head_or_none("answer", answer),
            "answer_is_free_text": _answer_is_free_text(answer, (option["label"] for option in options), multi_select),
            "notes": truncation.head_or_none("notes", notes if isinstance(notes, str) else None),
        })
    return entries


def _common_fields(
    kind: str,
    line_id: str,
    session_id: str,
    family: str,
    epoch: float | None,
    exchange: int,
    preceding: str,
    following: str,
    reference: _ReferenceRecord | None,
    truncation: _Truncation,
) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": kind,
        "id": line_id,
        "session_id": session_id,
        "family": family,
        "timestamp": _iso_utc(epoch),
        "exchange": exchange,
        "preceding_assistant_text": truncation.tail("preceding_assistant_text", preceding),
        "following_assistant_text": truncation.head("following_assistant_text", following),
        "model_family": "unknown" if reference is None else render._fam(reference.model),
        "model": None if reference is None else truncation.head("model", reference.model),
        "attribution_skill": (
            None if reference is None else truncation.head_or_none("attribution_skill", reference.attribution_skill)
        ),
    }


def _prompt_candidate(
    timeline: _FileTimeline, index: int, rec: dict, epoch: float | None,
    session_id: str, family: str, truncate_chars: int,
) -> _Candidate:
    truncation = _Truncation(truncate_chars)
    previous_opening = timeline.previous_opening(index)
    fields = _common_fields(
        KIND_PROMPT, f"{session_id}:{index}", session_id, family, epoch, timeline.exchange_at(index),
        timeline.assistant_text_between(previous_opening, index),
        timeline.assistant_text_between(index, timeline.next_opening(index)),
        timeline.reference_at(index), truncation,
    )
    typed_text = render._content_text(_message_content(rec))
    slash_prompt = _slash_command_args(typed_text.strip())
    command, text = slash_prompt if slash_prompt is not None else (None, typed_text)
    fields["text"] = truncation.head("text", text)
    fields["command"] = truncation.head_or_none("command", command)
    fields["initial"] = not timeline.has_assistant_before(index)
    fields["after_interrupt"] = timeline.interrupt_between(previous_opening, index)
    uuid = rec.get("uuid")
    return _Candidate(
        record=fields, kind=KIND_PROMPT, session_id=session_id, family=family, record_index=index, block_position=0,
        dedup_key=uuid if isinstance(uuid, str) and uuid else None, truncated_fields=tuple(truncation.cut_fields),
    )


def _question_candidate(
    timeline: _FileTimeline, index: int, position: int, block: dict, epoch: float | None,
    results: Mapping[str, list[tuple[int, dict, dict]]], session_id: str, family: str, truncate_chars: int,
    counts: Counter[str],
) -> _Candidate | None:
    questions = _well_formed_questions(block)
    if questions is None:
        counts[SKIP_MALFORMED_QUESTION] += 1
        return None
    tool_use_id = block["id"]
    result = next((found for found in results.get(tool_use_id, ()) if found[0] > index), None)
    if result is None:
        counts[SKIP_UNANSWERED_QUESTION] += 1
        return None
    result_index, result_rec, result_block = result
    has_result = "toolUseResult" in result_rec
    tool_use_result = result_rec.get("toolUseResult")
    answered = isinstance(tool_use_result, dict) and isinstance(tool_use_result.get("answers"), dict)
    truncation = _Truncation(truncate_chars)
    entries = _question_entries(questions, tool_use_result, answered, truncation)
    fields = _common_fields(
        KIND_QUESTION, f"{session_id}:{tool_use_id}", session_id, family, epoch, timeline.exchange_at(index),
        timeline.assistant_text_between(timeline.previous_opening(index), index + 1),
        timeline.assistant_text_between(result_index, timeline.next_opening(result_index)),
        timeline.reference_at(index), truncation,
    )
    fields["answered"] = answered
    fields["result_text"] = None if answered else truncation.head_or_none("result_text", _result_text(result_block))
    fields["questions"] = entries
    return _Candidate(
        record=fields, kind=KIND_QUESTION, session_id=session_id, family=family, record_index=index,
        block_position=position, dedup_key=tool_use_id,
        result_type=type(tool_use_result).__name__ if has_result else _ABSENT_RESULT_TYPE,
        truncated_fields=tuple(truncation.cut_fields),
    )


def _session_candidates(
    records: Sequence[object],
    session_id: str,
    family: str,
    *,
    truncate_chars: int,
    since_ts: float | None,
    until_epoch: float | None,
) -> tuple[list[_Candidate], Counter[str]]:
    """One session file's in-window candidates and the counts of what it skipped."""
    counts: Counter[str] = Counter()
    timeline = _FileTimeline(record_count=len(records))
    prompt_shaped: list[tuple[int, dict, str, float | None]] = []
    asking: list[tuple[int, list[tuple[int, dict]], float | None]] = []
    results: dict[str, list[tuple[int, dict, dict]]] = {}
    origin_seen = False
    for index, rec in enumerate(records):
        if not isinstance(rec, dict):
            counts[SKIP_UNINTERPRETABLE] += 1
            continue
        if rec.get("isSidechain"):
            continue
        if not render._is_interpretable(rec):
            counts[SKIP_UNINTERPRETABLE] += 1
            continue
        record_type = rec.get("type")
        if record_type == "assistant":
            timeline.add_assistant(index, rec)
            blocks = _ask_blocks(rec)
            if blocks:
                asking.append((index, blocks, _record_epoch(rec)))
        elif record_type == "user":
            for result_block in _tool_result_blocks(rec):
                results.setdefault(result_block["tool_use_id"], []).append((index, rec, result_block))
            if _is_prompt_shaped(rec):
                verdict = _prompt_verdict(rec, origin_seen)
                prompt_shaped.append((index, rec, verdict, _record_epoch(rec)))
                if verdict not in _NON_OPENING_VERDICTS:
                    timeline.openings.append(index)
                if verdict == SKIP_INTERRUPT:
                    timeline.interrupts.append(index)
        if rec.get("origin") is not None:
            origin_seen = True

    windowed = since_ts is not None or until_epoch is not None
    candidates: list[_Candidate] = []
    for index, rec, verdict, epoch in prompt_shaped:
        if windowed and epoch is None:
            counts[SKIP_UNDATED] += 1
            continue
        if not _in_window(epoch, since_ts, until_epoch):
            continue
        if verdict != VERDICT_TYPED:
            counts[verdict] += 1
            continue
        candidates.append(_prompt_candidate(timeline, index, rec, epoch, session_id, family, truncate_chars))
    for index, blocks, epoch in asking:
        if windowed and epoch is None:
            counts[SKIP_UNDATED] += len(blocks)
            continue
        if not _in_window(epoch, since_ts, until_epoch):
            continue
        for position, block in blocks:
            counts[_CALLS_COUNT] += 1
            candidate = _question_candidate(
                timeline, index, position, block, epoch, results, session_id, family, truncate_chars, counts,
            )
            if candidate is not None:
                candidates.append(candidate)
    return candidates, counts


def _dedup_and_order(candidates: Iterable[_Candidate]) -> tuple[list[_Candidate], Counter[str]]:
    """The kept candidates in output order, and the counts of the duplicates dropped.

    The copy in the session whose id sorts first wins, then the lowest record index. A candidate with no
    dedup key is never a duplicate.
    """
    ordered = sorted(candidates, key=lambda c: (c.session_id, c.record_index, c.block_position, c.family))
    kept: list[_Candidate] = []
    duplicates: Counter[str] = Counter()
    seen_keys: set[tuple[str, str]] = set()
    for candidate in ordered:
        if candidate.dedup_key is not None:
            key = (candidate.kind, candidate.dedup_key)
            if key in seen_keys:
                duplicates[SKIP_DUPLICATE_PROMPT if candidate.kind == KIND_PROMPT else SKIP_DUPLICATE_QUESTION] += 1
                continue
            seen_keys.add(key)
        kept.append(candidate)
    return kept, duplicates


def _failed_relations(checks: Mapping) -> list[str]:
    """The sorted names of the count relations that do not hold."""
    answered_with_text = checks["answered_entries"] - checks["null_answers"]
    failed = []
    if "dict" in checks["result_types"] and checks["questions_answered"] == 0:
        failed.append(_RELATION_ANSWERS_READ)
    if checks["answered_entries"] > 0 and checks["null_answers"] >= checks["answered_entries"]:
        failed.append(_RELATION_ANSWERS_KEYED)
    if answered_with_text > 0 and checks["free_text_answers"] >= answered_with_text:
        failed.append(_RELATION_LABELS_MATCHED)
    return sorted(failed)


def _counts_and_checks(kept: Sequence[_Candidate], scan_counts: Mapping[str, int]) -> tuple[dict, dict]:
    """The scope record's `counts` and `checks`, from the kept candidates and the scan's skip counts."""
    prompts = [candidate for candidate in kept if candidate.kind == KIND_PROMPT]
    questions = [candidate for candidate in kept if candidate.kind == KIND_QUESTION]
    answered_questions = [candidate for candidate in questions if candidate.record["answered"]]
    answer_entries = [entry for candidate in answered_questions for entry in candidate.record["questions"]]
    all_entries = [entry for candidate in questions for entry in candidate.record["questions"]]
    counts = {
        "prompts": len(prompts),
        "slash_prompts": sum(1 for candidate in prompts if candidate.record["command"] is not None),
        "questions": len(questions),
        _CALLS_COUNT: scan_counts[_CALLS_COUNT],
        "skipped": {kind: scan_counts[kind] for kind in SKIP_KINDS},
    }
    checks = {
        "questions_answered": len(answered_questions),
        "result_types": dict(sorted(Counter(candidate.result_type for candidate in questions).items())),
        "answered_entries": len(answer_entries),
        "null_answers": sum(1 for entry in answer_entries if entry["answer"] is None),
        "free_text_answers": sum(1 for entry in answer_entries if entry["answer_is_free_text"]),
        "multi_select_entries": sum(1 for entry in all_entries if entry["multi_select"]),
        "truncated_fields": dict(sorted(Counter(
            field_name for candidate in kept for field_name in candidate.truncated_fields
        ).items())),
    }
    checks["failed_relations"] = _failed_relations(checks)
    return counts, checks


def _scope_record(
    *,
    header: str,
    generated_at: datetime,
    since: str | None,
    until: str | None,
    truncate_chars: int,
    families: Mapping[str, int],
    counts: Mapping,
    checks: Mapping,
) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND_SCOPE,
        "header": header,
        "do_not_publish": scope._DO_NOT_PUBLISH_BANNER,
        "generated_at": generated_at.astimezone(UTC).isoformat(timespec="seconds"),
        "since": since,
        "until": until,
        "truncate_chars": truncate_chars,
        "families": dict(sorted(families.items())),
        "counts": counts,
        "checks": checks,
    }


def _jsonl_text(records: Iterable[Mapping]) -> str:
    """The records as ASCII JSON Lines, each followed by one newline."""
    return "".join(json.dumps(record, ensure_ascii=True, separators=(",", ":")) + "\n" for record in records)


def _stderr_json_line(label: str, payload: Mapping) -> None:
    print(f"{_COMMAND}: {label} {json.dumps(payload, ensure_ascii=True, sort_keys=True)}", file=sys.stderr)


def _stderr_families_line(families: Mapping[str, int]) -> None:
    """Print the do-not-publish banner, then the families line, which names raw project directories."""
    print(scope._DO_NOT_PUBLISH_BANNER, file=sys.stderr)
    _stderr_json_line("families", families)


def _sessions_or_abort(session_iter: Iterator[tuple[Path, list[dict]]]) -> Iterator[tuple[Path, list[dict]]]:
    """Yield the corpus reader's sessions, turning its abort into exit 1 without echoing the exception's text."""
    while True:
        try:
            session = next(session_iter)
        except StopIteration:
            return
        except (ValueError, RecursionError) as exc:
            print(f"{_COMMAND}: the transcript scan aborted ({type(exc).__name__}); no file was written", file=sys.stderr)
            sys.exit(1)
        yield session


def _window_bounds_or_refuse(args: argparse.Namespace) -> tuple[float | None, float | None]:
    """The window's `(since_ts, until_epoch)`, exiting 2 when a supplied bound does not apply or the window is reversed.

    `scope._iso_date` accepts an unpadded month or day and `_parse_absolute_window_args` then yields no bound for it,
    which would write the whole history under a scope record that names a window. A reversed window would write an
    empty file under a scope record that names an impossible window. Neither message echoes a value.
    """
    since_ts, until_epoch = scope._parse_absolute_window_args(args, _COMMAND)
    unapplied = [
        flag
        for flag, supplied, bound in (("--since", args.since, since_ts), ("--until", args.until, until_epoch))
        if supplied and bound is None
    ]
    if unapplied:
        print(f"{_COMMAND}: {' and '.join(unapplied)} must be a zero-padded YYYY-MM-DD date", file=sys.stderr)
        sys.exit(2)
    # `until_epoch` is the start of the day after `--until`, so a one-day window has `since_ts` below it.
    if since_ts is not None and until_epoch is not None and since_ts >= until_epoch:
        print(f"{_COMMAND}: --since must not be after --until", file=sys.stderr)
        sys.exit(2)
    return since_ts, until_epoch


def _refuse_unusable_arguments(args: argparse.Namespace) -> tuple[float | None, float | None]:
    """Exit 2 on the first refusal that applies, before any read. Returns the window's bounds."""
    if not args.this_repo and not args.projects:
        print(
            f"{_COMMAND}: pass --projects GLOB or --this-repo (--projects '*' reads every project on this machine)",
            file=sys.stderr,
        )
        sys.exit(2)
    since_ts, until_epoch = _window_bounds_or_refuse(args)
    if not args.out and not args.preview:
        print(f"{_COMMAND}: pass --out PATH (a new file outside any git work tree) or --preview", file=sys.stderr)
        sys.exit(2)
    if args.out:
        ledger_common._refuse_unusable_out_path(args.out, _COMMAND)
    return since_ts, until_epoch


def _warn_when_no_session_matched(families: Mapping[str, int]) -> None:
    if not families:
        print(
            f"{_COMMAND}: warning: no session matched this scope; check that the checkout's directory name"
            " holds the repo name",
            file=sys.stderr,
        )


def cmd_correction_candidates(args: argparse.Namespace) -> None:
    """Write the main-session AskUserQuestion exchanges and typed prompts to one new owner-only JSONL file.

    --preview lists the project families the scope matches on stderr and writes nothing.
    """
    since_ts, until_epoch = _refuse_unusable_arguments(args)
    roots = scope.resolve_scan_roots(args)
    session_iter, scope_label = scope._resolve_project_scope(args, _COMMAND, roots=roots)
    scope.print_resolved_scope(_COMMAND, scope_label, roots, file=sys.stderr)

    families: Counter[str] = Counter()
    candidates: list[_Candidate] = []
    scan_counts: Counter[str] = Counter()
    for jsonl, records in _sessions_or_abort(session_iter):
        family = redaction._project_family(jsonl.parent.name)
        families[family] += 1
        if args.preview:
            continue
        session_candidates, session_counts = _session_candidates(
            records, jsonl.stem, family,
            truncate_chars=args.truncate_chars, since_ts=since_ts, until_epoch=until_epoch,
        )
        candidates.extend(session_candidates)
        scan_counts.update(session_counts)

    if args.preview:
        _stderr_families_line(families)
        _warn_when_no_session_matched(families)
        return

    kept, duplicate_counts = _dedup_and_order(candidates)
    scan_counts.update(duplicate_counts)
    counts, checks = _counts_and_checks(kept, scan_counts)
    scope_record = _scope_record(
        header=scope._resolved_scope_header(_COMMAND, scope_label, roots),
        generated_at=datetime.now(UTC),
        since=args.since, until=args.until, truncate_chars=args.truncate_chars,
        families=families, counts=counts, checks=checks,
    )
    ledger_common._publish_new_owner_file(
        args.out, _jsonl_text([scope_record, *(candidate.record for candidate in kept)]), _COMMAND,
    )

    print(args.out)
    _stderr_families_line(families)
    _stderr_json_line("counts", {"counts": counts, "checks": checks})
    _warn_when_no_session_matched(families)


def _non_negative_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not an integer: {value!r}") from None
    if parsed < 0:
        raise argparse.ArgumentTypeError(f"must be 0 or more: {value!r}")
    return parsed


def _add_correction_candidates_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Register the correction-candidates subparser on build_parser()'s subparsers action,
    binding cmd_correction_candidates through set_defaults(func=...).
    """
    p_cc = subparsers.add_parser(
        "correction-candidates",
        help=(
            "Write every main-session AskUserQuestion exchange and typed prompt, with the agent text around it,"
            " as JSON Lines to a new file named by --out."
        ),
        epilog=(
            "Scope is required: pass --projects GLOB ('*' reads every project on this machine) or --this-repo."
        ),
    )
    scope._add_project_scope_args(p_cc)
    # No machine-wide default: a run states its scope with --this-repo or --projects.
    p_cc.set_defaults(projects=None, func=cmd_correction_candidates)
    p_cc.add_argument("--since", metavar="DATE", type=scope._iso_date, help="Inclusive start date (zero-padded YYYY-MM-DD)")
    p_cc.add_argument("--until", metavar="DATE", type=scope._iso_date, help="Inclusive end date (zero-padded YYYY-MM-DD)")
    p_cc.add_argument(
        "--truncate-chars",
        type=_non_negative_int,
        default=DEFAULT_TRUNCATE_CHARS,
        metavar="N",
        help=f"Maximum characters for each free-text field, 0 for no limit (default: {DEFAULT_TRUNCATE_CHARS}).",
    )
    p_cc.add_argument(
        "--out",
        metavar="PATH",
        default=None,
        help="New file to write, in an existing directory outside any git work tree. Required unless --preview.",
    )
    p_cc.add_argument(
        "--preview",
        action="store_true",
        help="List the project families the scope matches on stderr and write nothing.",
    )
