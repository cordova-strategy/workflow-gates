"""The skill-reinjection command: how often each skill is re-attached after a compaction and how often that copy is
cut, plus its subparser registration.

Reads only records the harness writes: `compact_boundary` system records and `invoked_skills` attachments on the main
thread. It reads no user text and no tool call, so a quoted tag, a failed call or a built-in command cannot move a
count. The docs section for this command states what the counts do and do not cover.

Every printed figure is an aggregate: nothing printed carries a path, session identifier, project name, skill content
or skill name this repository does not track. The printed cut-length range spans only copies under names this
repository tracks. A copy's code-point, UTF-16 and byte lengths differ by its multi-byte and astral characters. The
three lengths together give its exact astral-character count and a weighted sum of its other multi-byte characters.
Both describe the skill's content, so an untracked skill's copy sets no extreme. A run from another repository takes a
shared name's copies from that repository.

`TRUNCATION_MARKER`, `CopyLengths`, `CutRange`, `copy_lengths`, `copy_is_truncated`, `ReinjectionTotals` and
`count_session` are public so a caller outside the package can reuse the marker, the length units and the
per-session counter.

Imports sibling modules by module (attribute access, not by name) -- see scope.py's own top-of-file comment for why.
"""
from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, date
from pathlib import Path
from typing import NamedTuple

from transcript_analysis import corpus, publication_scope, redaction, scope

_COMMAND_LABEL = "skill-reinjection"

_INVOKED_SKILLS_ATTACHMENT_TYPE = "invoked_skills"

# What Claude Code appends to a skill body it cuts when re-attaching skills after a compaction, measured on 2.1.330.
TRUNCATION_MARKER = (
    "[... skill content truncated for compaction; use Read on the skill path if you need the full text]"
)

# The length a cut copy lands on in 2.1.330. A copy past it without the marker means the cut or the marker moved.
_CUT_LENGTH_LIMIT = 20_000

_WITHHELD_SKILL_LABEL = "(withheld — untracked skill)"

# Scan-gap level tags for the record shapes this module reads itself. The project-directory and main-file tags come
# from scope. A key never holds a name, path or session id.
_GAP_UNPAIRED_ATTACHMENT = "unpaired-attachment"
_GAP_BOUNDARY_WITHOUT_UUID = "boundary-without-uuid"
_GAP_UNMARKED_LONG_COPY = "unmarked-long-copy"
_GAP_NON_OBJECT_RECORD = "non-object-record"
_GAP_NON_OBJECT_ATTACHMENT = "non-object-attachment"
_GAP_BAD_SKILLS_LIST = "bad-skills-list"
_GAP_NON_OBJECT_SKILL_ENTRY = "non-object-skill-entry"
_GAP_BAD_SKILL_FIELDS = "bad-skill-fields"
_GAP_UNCONVERTIBLE_TIMESTAMP = "unconvertible-timestamp"

_PRINTED_GAPS: tuple[tuple[str, str], ...] = (
    ("unpaired_attachments", _GAP_UNPAIRED_ATTACHMENT),
    ("boundaries_without_uuid", _GAP_BOUNDARY_WITHOUT_UUID),
    ("unmarked_long_copies", _GAP_UNMARKED_LONG_COPY),
    ("non_object_records", _GAP_NON_OBJECT_RECORD),
    ("non_object_attachments", _GAP_NON_OBJECT_ATTACHMENT),
    ("bad_skills_lists", _GAP_BAD_SKILLS_LIST),
    ("non_object_skill_entries", _GAP_NON_OBJECT_SKILL_ENTRY),
    ("bad_skill_fields", _GAP_BAD_SKILL_FIELDS),
    ("unconvertible_timestamps", _GAP_UNCONVERTIBLE_TIMESTAMP),
)


class CopyLengths(NamedTuple):
    code_points: int
    utf16_units: int
    utf8_bytes: int


class CutRange(NamedTuple):
    """The shortest and longest truncated copy seen, each unit tracked on its own."""

    shortest: CopyLengths
    longest: CopyLengths


def copy_lengths(text: str) -> CopyLengths:
    """A copy's length in each unit a cut could count. `surrogatepass` lets a cut inside a surrogate pair encode."""
    return CopyLengths(
        code_points=len(text),
        utf16_units=len(text.encode("utf-16-le", "surrogatepass")) // 2,
        utf8_bytes=len(text.encode("utf-8", "surrogatepass")),
    )


def copy_is_truncated(content: str) -> bool:
    """A marker elsewhere in the body is skill text, not a cut."""
    return content.rstrip().endswith(TRUNCATION_MARKER)


@dataclass
class ReinjectionTotals:
    """Counts across one run. `reattached`, `truncated` and `cut_ranges` are keyed by the raw names a transcript holds,
    foreign and untracked skill names included, so no caller may print or serialize them before `_fold_report`."""

    sessions: int = 0
    compactions: int = 0
    compactions_with_attachment: int = 0
    first_compaction: date | None = None
    last_compaction: date | None = None
    reattached: Counter[str] = field(default_factory=Counter)
    truncated: Counter[str] = field(default_factory=Counter)
    cut_ranges: dict[str, CutRange] = field(default_factory=dict)
    scan_gaps: Counter[str] = field(default_factory=Counter)


def _utc_date_of(timestamp: object) -> date | None:
    """The UTC date of an ISO timestamp, or None when the value is not a string, does not parse, or overflows.

    `astimezone` raises OverflowError for an offset timestamp at the edge of the supported years.
    """
    if not isinstance(timestamp, str):
        return None
    parsed = corpus._parse_iso_datetime(timestamp)
    if parsed is None:
        return None
    try:
        return (parsed.astimezone(UTC) if parsed.tzinfo else parsed).date()
    except OverflowError:
        return None


def _record_compaction_date(timestamp: object, totals: ReinjectionTotals) -> None:
    compaction_date = _utc_date_of(timestamp)
    if compaction_date is None:
        totals.scan_gaps[_GAP_UNCONVERTIBLE_TIMESTAMP] += 1
        return
    if totals.first_compaction is None or compaction_date < totals.first_compaction:
        totals.first_compaction = compaction_date
    if totals.last_compaction is None or compaction_date > totals.last_compaction:
        totals.last_compaction = compaction_date


def _count_boundary(record: dict, counted_uuids: set[str], totals: ReinjectionTotals) -> bool:
    """Count one compaction, returning False for a replay of one already counted earlier in the run, in any file."""
    uuid = record.get("uuid")
    if isinstance(uuid, str) and uuid:
        if uuid in counted_uuids:
            return False
        counted_uuids.add(uuid)
    else:
        totals.scan_gaps[_GAP_BOUNDARY_WITHOUT_UUID] += 1
    totals.compactions += 1
    _record_compaction_date(record.get("timestamp"), totals)
    return True


def _merge_cut_ranges(first: CutRange | None, second: CutRange) -> CutRange:
    if first is None:
        return second
    return CutRange(
        shortest=CopyLengths(*map(min, first.shortest, second.shortest, strict=True)),
        longest=CopyLengths(*map(max, first.longest, second.longest, strict=True)),
    )


def _count_attachment(attachment: dict, totals: ReinjectionTotals) -> None:
    skills = attachment.get("skills")
    if not isinstance(skills, list):
        totals.scan_gaps[_GAP_BAD_SKILLS_LIST] += 1
        return
    totals.compactions_with_attachment += 1
    for entry in skills:
        if not isinstance(entry, dict):
            totals.scan_gaps[_GAP_NON_OBJECT_SKILL_ENTRY] += 1
            continue
        name, content = entry.get("name"), entry.get("content")
        if not isinstance(name, str) or not isinstance(content, str):
            totals.scan_gaps[_GAP_BAD_SKILL_FIELDS] += 1
            continue
        totals.reattached[name] += 1
        lengths = copy_lengths(content)
        if copy_is_truncated(content):
            totals.truncated[name] += 1
            totals.cut_ranges[name] = _merge_cut_ranges(totals.cut_ranges.get(name), CutRange(lengths, lengths))
        elif lengths.code_points > _CUT_LENGTH_LIMIT:
            totals.scan_gaps[_GAP_UNMARKED_LONG_COPY] += 1


def count_session(records: Sequence[object], counted_uuids: set[str], totals: ReinjectionTotals) -> None:
    """Add one session file's compactions and re-attached skill copies to `totals`, before any name is withheld.

    Each boundary opens a window that the next boundary closes, and the first `invoked_skills` attachment in a window
    pairs with its boundary. A replayed boundary still opens and closes its window, so pairing never shifts.
    `counted_uuids` carries the boundary uuids already counted across the session files of one run.
    """
    totals.sessions += 1
    window_open = False
    window_counted = False
    window_paired = False
    for record in records:
        if not isinstance(record, dict):
            totals.scan_gaps[_GAP_NON_OBJECT_RECORD] += 1
            continue
        if record.get("isSidechain"):
            continue
        if record.get("type") == "system" and record.get("subtype") == "compact_boundary":
            window_open = True
            window_paired = False
            window_counted = _count_boundary(record, counted_uuids, totals)
        elif record.get("type") == "attachment":
            attachment = record.get("attachment")
            if not isinstance(attachment, dict):
                totals.scan_gaps[_GAP_NON_OBJECT_ATTACHMENT] += 1
                continue
            if attachment.get("type") != _INVOKED_SKILLS_ATTACHMENT_TYPE:
                continue
            if not window_open:
                totals.scan_gaps[_GAP_UNPAIRED_ATTACHMENT] += 1
            elif not window_counted:
                continue
            elif window_paired:
                totals.scan_gaps[_GAP_UNPAIRED_ATTACHMENT] += 1
            else:
                window_paired = True
                _count_attachment(attachment, totals)


class _SkillCounts(NamedTuple):
    reattached: int
    truncated: int


class _Report(NamedTuple):
    sessions: int
    compactions: int
    compactions_with_attachment: int
    first_compaction: date | None
    last_compaction: date | None
    tracked_cut_range: CutRange | None
    gaps: dict[str, int]
    named_rows: list[tuple[str, _SkillCounts]]
    withheld_row: _SkillCounts | None
    tracked_names_available: bool


def _fold_report(totals: ReinjectionTotals, tracked_skill_names: frozenset[str]) -> _Report:
    """Fold every name this repo does not track into one withheld row. The result holds no raw skill name.

    The cut-length range takes only tracked names' copies, so an untracked skill's content cannot set an extreme.
    """
    named: dict[str, _SkillCounts] = {}
    withheld: _SkillCounts | None = None
    tracked_cut_range: CutRange | None = None
    for name, reattached in totals.reattached.items():
        counts = _SkillCounts(reattached, totals.truncated[name])
        if name in tracked_skill_names:
            named[name] = counts
            if name in totals.cut_ranges:
                tracked_cut_range = _merge_cut_ranges(tracked_cut_range, totals.cut_ranges[name])
        elif withheld is None:
            withheld = counts
        else:
            withheld = _SkillCounts(withheld.reattached + counts.reattached, withheld.truncated + counts.truncated)
    ordered = sorted(named.items(), key=lambda item: (-item[1].reattached, item[0]))
    return _Report(
        sessions=totals.sessions,
        compactions=totals.compactions,
        compactions_with_attachment=totals.compactions_with_attachment,
        first_compaction=totals.first_compaction,
        last_compaction=totals.last_compaction,
        tracked_cut_range=tracked_cut_range,
        gaps={kind: totals.scan_gaps[kind] for kind in _all_gap_kinds()},
        named_rows=ordered,
        withheld_row=withheld,
        tracked_names_available=bool(tracked_skill_names),
    )


def _all_gap_kinds() -> list[str]:
    return [scope._SCAN_GAP_ROOT, scope._SCAN_GAP_PROJECT_DIR, scope._SCAN_GAP_SESSION_FILE] + [
        kind for _label, kind in _PRINTED_GAPS
    ]


def _fmt_date(value: date | None) -> str:
    return value.isoformat() if value is not None else "none"


def _fmt_cut_lengths(lengths: CopyLengths) -> str:
    return f"code_points={lengths.code_points:,} utf16_units={lengths.utf16_units:,} utf8_bytes={lengths.utf8_bytes:,}"


def _print_report(report: _Report) -> None:
    if not report.tracked_names_available:
        print(
            "\nEvery skill name is withheld because the list of skills this repository tracks is unavailable."
        )
    print(
        f"\nsessions={report.sessions:,} compactions={report.compactions:,}"
        f" with_attachment={report.compactions_with_attachment:,}"
        f" without_attachment={report.compactions - report.compactions_with_attachment:,}"
    )
    print(f"first_compaction={_fmt_date(report.first_compaction)} last_compaction={_fmt_date(report.last_compaction)}")
    if not report.tracked_names_available:
        print("truncated copies of tracked skills: unavailable")
    elif report.tracked_cut_range is None:
        print("truncated copies of tracked skills: none")
    else:
        print(f"truncated copy of a tracked skill, shortest: {_fmt_cut_lengths(report.tracked_cut_range.shortest)}")
        print(f"truncated copy of a tracked skill, longest:  {_fmt_cut_lengths(report.tracked_cut_range.longest)}")
    print(
        "skipped input:"
        f" unreadable_roots={report.gaps[scope._SCAN_GAP_ROOT]:,}"
        f" unreadable_project_dirs={report.gaps[scope._SCAN_GAP_PROJECT_DIR]:,}"
        f" unreadable_main_files={report.gaps[scope._SCAN_GAP_SESSION_FILE]:,}"
    )
    print("scan gaps: " + " ".join(f"{label}={report.gaps[kind]:,}" for label, kind in _PRINTED_GAPS))
    print(
        "\n## Re-attached copies by skill"
        " (skills this repo does not track are folded into one withheld row)"
    )
    for name, counts in report.named_rows:
        print(f"{name}: reattached={counts.reattached:,} truncated={counts.truncated:,}")
    if report.withheld_row is not None:
        print(
            f"{_WITHHELD_SKILL_LABEL}: reattached={report.withheld_row.reattached:,}"
            f" truncated={report.withheld_row.truncated:,}"
        )


def cmd_skill_reinjection(args: argparse.Namespace) -> None:
    """See docs/transcript-analysis.md's `skill-reinjection` section for the flags, the counts, and the publication scope."""
    _skill_reinjection_report(args, publication_scope._single_account_roots(_COMMAND_LABEL))


def _skill_reinjection_report(args: argparse.Namespace, roots: Sequence[Path]) -> None:
    publication_scope._refuse_wider_scope(args, roots, _COMMAND_LABEL)
    totals = ReinjectionTotals()
    session_iter, scope_label = scope._resolve_project_scope(
        args, _COMMAND_LABEL, roots=roots, scan_gaps=totals.scan_gaps,
    )
    print(publication_scope._scope_header(scope_label, _COMMAND_LABEL))

    counted_uuids: set[str] = set()
    for _main_jsonl, main_records in session_iter:
        count_session(main_records, counted_uuids, totals)

    _print_report(_fold_report(totals, redaction._repo_tracked_skill_names()))


def _add_skill_reinjection_subparser(subparsers: argparse._SubParsersAction) -> None:
    p_skill_reinjection = subparsers.add_parser(
        "skill-reinjection",
        help=(
            "How often each skill is re-attached after a compaction and how often that copy is cut. Requires"
            " --this-repo; reads one account and refuses a wider scope. Aggregate-only output."
        ),
    )
    scope._add_project_scope_args(p_skill_reinjection)
    p_skill_reinjection.set_defaults(func=cmd_skill_reinjection)
