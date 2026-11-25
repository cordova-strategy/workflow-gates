"""Tests for the skill-reinjection command: window pairing, boundary dedupe, truncation and length counting, the
tracked-name fold, malformed-record gaps, output privacy, argparse wiring and scope refusal."""
import argparse
import dataclasses
import json
import os
import time

import pytest
from transcript_analysis import redaction, scope, skill_reinjection

from ._compaction_context_helpers import automatic_compaction_records, manual_compaction_records
from ._publication_scope_helpers import (
    labelled_counts,
    refusal_with_several_roots,
    refusal_without_this_repo,
    scope_header,
    unreadable,
)
from ._skill_reinjection_helpers import (
    CONTENT_CANARY,
    CUT_LENGTH,
    DIRECTORY_CANARY,
    PATH_CANARY,
    SESSION_ID_CANARY,
    TRACKED_PLUGIN_SKILL,
    TRACKED_SKILL,
    UNSET,
    UNTRACKED_SKILL,
    attachment,
    boundary,
    cut_content,
    skill_entry,
    stub_tracked_skill_names,
)
from .conftest import (
    _PROJECT_SLUG,
    OTHER_REPOSITORY_CANARY_SKILL,
    _this_repo_args,
    _write_jsonl,
    _write_subagent_jsonl,
    first_skill_directory_on_disk,
    init_repository_tracking_canary_skill,
)

_NO_GAPS = {
    "unpaired_attachments": 0, "boundaries_without_uuid": 0, "unmarked_long_copies": 0, "non_object_records": 0,
    "non_object_attachments": 0, "bad_skills_lists": 0, "non_object_skill_entries": 0, "bad_skill_fields": 0,
    "unconvertible_timestamps": 0,
}
_NO_SKIPPED_INPUT = {"unreadable_roots": 0, "unreadable_project_dirs": 0, "unreadable_main_files": 0}
_HOOK_CONTEXT_ATTACHMENT = {"type": "attachment", "attachment": {"type": "hook_additional_context", "content": "x"}}


def _count(*session_files: list) -> skill_reinjection.ReinjectionTotals:
    """Counts each list as one session file, in order, sharing one boundary-uuid set as a run does."""
    totals = skill_reinjection.ReinjectionTotals()
    counted_uuids: set[str] = set()
    for records in session_files:
        skill_reinjection.count_session(records, counted_uuids, totals)
    return totals


def _report_text(capsys) -> str:
    skill_reinjection.cmd_skill_reinjection(_this_repo_args())
    return capsys.readouterr().out


def _run_report(fake_projects, capsys, records: list, *, monkeypatch, tracked=(TRACKED_SKILL, TRACKED_PLUGIN_SKILL)):
    stub_tracked_skill_names(monkeypatch, *tracked)
    _write_jsonl(fake_projects / f"{SESSION_ID_CANARY}.jsonl", records)
    skill_reinjection.cmd_skill_reinjection(_this_repo_args())
    return capsys.readouterr()


class TestPairing:
    def test_attachment_after_two_boundaries_pairs_with_the_second_and_leaves_the_first_without_one(self):
        totals = _count([boundary("b1"), boundary("b2"), attachment(skill_entry(TRACKED_SKILL))])

        assert totals.compactions == 2
        assert totals.compactions_with_attachment == 1
        assert totals.reattached == {TRACKED_SKILL: 1}

    def test_second_attachment_in_one_window_pairs_with_nothing_and_records_a_gap(self):
        first, second = skill_entry(TRACKED_SKILL), skill_entry(UNTRACKED_SKILL)

        totals = _count([boundary("b1"), attachment(first), attachment(second), boundary("b2")])

        assert totals.reattached == {TRACKED_SKILL: 1}
        assert totals.compactions_with_attachment == 1
        assert totals.scan_gaps["unpaired-attachment"] == 1

    def test_attachment_before_any_boundary_pairs_with_nothing_and_records_a_gap(self):
        totals = _count([attachment(skill_entry(TRACKED_SKILL)), boundary("b1")])

        assert totals.reattached == {}
        assert totals.compactions == 1
        assert totals.compactions_with_attachment == 0
        assert totals.scan_gaps["unpaired-attachment"] == 1

    def test_attachment_that_is_not_invoked_skills_pairs_with_nothing_and_records_no_gap(self):
        totals = _count([boundary("b1"), _HOOK_CONTEXT_ATTACHMENT])

        assert totals.compactions_with_attachment == 0
        assert totals.scan_gaps == {}

    def test_attachment_that_is_not_invoked_skills_before_the_first_boundary_records_no_gap(self):
        totals = _count([_HOOK_CONTEXT_ATTACHMENT, boundary("b1"), attachment(skill_entry(TRACKED_SKILL))])

        assert totals.compactions_with_attachment == 1
        assert totals.reattached == {TRACKED_SKILL: 1}
        assert totals.scan_gaps == {}

    def test_attachment_that_is_not_invoked_skills_between_a_boundary_and_its_skills_attachment_leaves_it_paired(self):
        totals = _count([boundary("b1"), _HOOK_CONTEXT_ATTACHMENT, attachment(skill_entry(TRACKED_SKILL))])

        assert totals.compactions_with_attachment == 1
        assert totals.reattached == {TRACKED_SKILL: 1}
        assert totals.scan_gaps == {}

    def test_compaction_with_no_attachment_raises_the_without_total_and_no_skill_count(self):
        totals = _count([boundary("b1")])

        assert (totals.compactions, totals.compactions_with_attachment) == (1, 0)
        assert totals.reattached == {}

    def test_attachment_with_an_empty_skills_list_counts_as_an_attachment_with_no_skill_and_no_gap(self):
        totals = _count([boundary("b1"), attachment()])

        assert totals.compactions == 1
        assert totals.compactions_with_attachment == 1
        assert totals.reattached == {}
        assert totals.scan_gaps == {}

    @pytest.mark.parametrize(
        "recorded_sequence", [manual_compaction_records(), automatic_compaction_records()], ids=["manual", "automatic"],
    )
    def test_recorded_compaction_sequence_pairs_its_one_boundary_with_its_one_skill_copy(self, recorded_sequence):
        recorded_boundary, *records_after_it = recorded_sequence
        identified_boundary = {**recorded_boundary, "uuid": "b1", "timestamp": "2026-01-02T03:04:05.000Z"}

        totals = _count([identified_boundary, *records_after_it])

        assert totals.compactions == 1
        assert totals.compactions_with_attachment == 1
        assert sum(totals.reattached.values()) == 1
        assert totals.scan_gaps == {}

    def test_window_spans_records_between_a_boundary_and_its_attachment(self):
        filler = {"type": "user", "message": {"role": "user", "content": "text"}}

        totals = _count([boundary("b1"), filler, filler, attachment(skill_entry(TRACKED_SKILL))])

        assert totals.compactions_with_attachment == 1


class TestSidechain:
    def test_sidechain_boundary_and_attachment_between_a_main_boundary_and_its_attachment_change_nothing(self):
        main_only = [boundary("b1"), attachment(skill_entry(TRACKED_SKILL))]
        with_sidechain = [
            boundary("b1"),
            boundary("sidechain-boundary", sidechain=True),
            attachment(skill_entry(UNTRACKED_SKILL), sidechain=True),
            attachment(skill_entry(TRACKED_SKILL)),
        ]

        assert _count(with_sidechain) == _count(main_only)

    def test_subagent_file_under_the_session_is_never_read(self, fake_projects, capsys, monkeypatch):
        stub_tracked_skill_names(monkeypatch, TRACKED_SKILL)
        _write_jsonl(fake_projects / "sess.jsonl", [boundary("b1"), attachment(skill_entry(TRACKED_SKILL))])
        _write_subagent_jsonl(
            fake_projects, "sess", "agent-1", [boundary("b2"), attachment(skill_entry(TRACKED_SKILL))],
        )

        skill_reinjection.cmd_skill_reinjection(_this_repo_args())

        out = capsys.readouterr().out
        assert "sessions=1 compactions=1 with_attachment=1" in out
        assert f"{TRACKED_SKILL}: reattached=1 truncated=0" in out


class TestDedupe:
    _FIRST_FILE = [boundary("b1"), attachment(skill_entry(TRACKED_SKILL))]

    def test_second_file_replaying_the_same_boundary_and_attachment_changes_no_count(self):
        replayed = _count(self._FIRST_FILE, list(self._FIRST_FILE))

        assert replayed.sessions == 2
        assert dataclasses.replace(replayed, sessions=1) == _count(self._FIRST_FILE)

    def test_replay_followed_by_a_new_compaction_counts_exactly_the_new_attachment(self):
        replay_and_new = [
            *self._FIRST_FILE, boundary("b2"), attachment(skill_entry(TRACKED_SKILL), skill_entry(UNTRACKED_SKILL)),
        ]

        totals = _count(self._FIRST_FILE, replay_and_new)

        assert totals.compactions == 2
        assert totals.compactions_with_attachment == 2
        assert totals.reattached == {TRACKED_SKILL: 2, UNTRACKED_SKILL: 1}

    def test_replayed_boundary_still_closes_its_window_so_pairing_does_not_shift(self):
        replay_then_unattached_boundary = [boundary("b1"), boundary("b2")]

        totals = _count(self._FIRST_FILE, replay_then_unattached_boundary)

        assert totals.compactions == 2
        assert totals.compactions_with_attachment == 1

    def test_boundary_uuid_repeated_inside_one_file_counts_once_with_its_first_attachment(self):
        totals = _count([
            boundary("b1"), attachment(skill_entry(TRACKED_SKILL)),
            boundary("b1"), attachment(skill_entry(UNTRACKED_SKILL)),
        ])

        assert totals.compactions == 1
        assert totals.reattached == {TRACKED_SKILL: 1}

    def test_attachment_after_a_replayed_boundary_that_follows_a_counted_one_is_skipped_not_paired_with_the_counted_one(
        self,
    ):
        first_file = [boundary("b1"), attachment(skill_entry(TRACKED_SKILL))]
        second_file = [
            boundary("b2"), attachment(skill_entry(TRACKED_PLUGIN_SKILL)),
            boundary("b1"), attachment(skill_entry(UNTRACKED_SKILL)),
        ]

        totals = _count(first_file, second_file)

        assert totals.compactions == 2
        assert totals.compactions_with_attachment == 2
        assert totals.reattached == {TRACKED_SKILL: 1, TRACKED_PLUGIN_SKILL: 1}
        assert totals.scan_gaps == {}

    def test_attachment_after_a_new_boundary_and_a_replayed_one_belongs_to_the_replayed_one_and_counts_nothing(self):
        first_file = [boundary("b1")]
        second_file = [boundary("b2"), boundary("b1"), attachment(skill_entry(TRACKED_SKILL))]

        totals = _count(first_file, second_file)

        assert totals.compactions == 2
        assert totals.compactions_with_attachment == 0
        assert totals.reattached == {}
        assert totals.scan_gaps == {}

    def test_second_session_file_replaying_the_first_adds_only_its_new_compaction_to_the_printed_report(
        self, fake_projects, capsys, monkeypatch,
    ):
        stub_tracked_skill_names(monkeypatch, TRACKED_SKILL, TRACKED_PLUGIN_SKILL)
        _write_jsonl(
            fake_projects / "a-first.jsonl", [boundary("b1"), attachment(skill_entry(TRACKED_SKILL))],
        )
        _write_jsonl(
            fake_projects / "b-second.jsonl",
            [
                boundary("b1"), attachment(skill_entry(TRACKED_SKILL)),
                boundary("b2"), attachment(skill_entry(TRACKED_PLUGIN_SKILL)),
            ],
        )

        skill_reinjection.cmd_skill_reinjection(_this_repo_args())

        out = capsys.readouterr().out
        assert "sessions=2 compactions=2 with_attachment=2 without_attachment=0" in out
        assert f"\n{TRACKED_SKILL}: reattached=1 truncated=0\n" in out
        assert f"\n{TRACKED_PLUGIN_SKILL}: reattached=1 truncated=0\n" in out

    @pytest.mark.parametrize("uuid", [UNSET, 7, None, ""], ids=["missing", "integer", "null", "empty"])
    def test_boundary_without_a_usable_uuid_counts_once_and_records_a_gap(self, uuid):
        totals = _count([boundary(uuid), attachment(skill_entry(TRACKED_SKILL))])

        assert totals.compactions == 1
        assert totals.reattached == {TRACKED_SKILL: 1}
        assert totals.scan_gaps["boundary-without-uuid"] == 1


class TestCompactionDates:
    def test_first_and_last_compaction_are_the_earliest_and_latest_boundary_dates(self):
        totals = _count([
            boundary("b2", "2026-03-05T10:00:00Z"), boundary("b1", "2026-01-02T23:59:59Z"),
            boundary("b3", "2026-02-01T00:00:00Z"),
        ])

        assert (totals.first_compaction.isoformat(), totals.last_compaction.isoformat()) == ("2026-01-02", "2026-03-05")

    @pytest.mark.parametrize(
        ("timestamp", "expected_utc_date"),
        [
            ("2026-03-04T23:30:00-05:00", "2026-03-05"),
            ("2026-03-05T00:30:00+05:00", "2026-03-04"),
        ],
        ids=["offset-behind-utc-lands-on-the-next-day", "offset-ahead-of-utc-lands-on-the-previous-day"],
    )
    def test_boundary_date_is_the_utc_date_of_its_timestamp(self, timestamp, expected_utc_date):
        totals = _count([boundary("b1", timestamp)])

        assert totals.first_compaction.isoformat() == expected_utc_date
        assert totals.last_compaction.isoformat() == expected_utc_date
        assert totals.scan_gaps == {}

    @pytest.fixture()
    def local_timezone_behind_utc(self):
        """Pins the process-local zone five hours behind UTC, so a naive 23:30 would land on the next UTC day if the
        code treated it as local time. A runner whose zone is UTC would hide that.

        The POSIX zone form needs no tz database, which a minimal image can lack.
        """
        try:
            with pytest.MonkeyPatch.context() as timezone_patch:
                timezone_patch.setenv("TZ", "EST5")
                time.tzset()
                assert time.timezone == 5 * 3600, "the TZ pin did not take effect, so the test would prove nothing"
                yield
        finally:
            time.tzset()

    @pytest.mark.usefixtures("local_timezone_behind_utc")
    def test_naive_boundary_timestamp_keeps_its_date_whatever_the_local_timezone(self):
        totals = _count([boundary("b1", "2026-03-04T23:30:00")])

        assert totals.first_compaction.isoformat() == "2026-03-04"
        assert totals.last_compaction.isoformat() == "2026-03-04"
        assert totals.scan_gaps == {}

    @pytest.mark.parametrize(
        "timestamp",
        [None, 5, "not a date", "", "0001-01-01T00:00:00+05:00", "9999-12-31T23:59:59-05:00"],
        ids=["null", "integer", "unparseable", "empty", "overflow-at-year-1", "overflow-at-year-9999"],
    )
    def test_boundary_with_a_timestamp_that_gives_no_date_still_counts_and_records_a_gap(self, timestamp):
        totals = _count([boundary("b1", timestamp), attachment(skill_entry(TRACKED_SKILL))])

        assert totals.compactions == 1
        assert totals.reattached == {TRACKED_SKILL: 1}
        assert totals.first_compaction is None
        assert totals.last_compaction is None
        assert totals.scan_gaps == {"unconvertible-timestamp": 1}

    def test_boundary_that_gives_no_date_leaves_the_range_of_the_other_boundaries_unchanged(self):
        totals = _count([
            boundary("b1", "2026-01-02T00:00:00Z"), boundary("b2", "0001-01-01T00:00:00+05:00"),
            boundary("b3", "2026-03-05T00:00:00Z"),
        ])

        assert (totals.first_compaction.isoformat(), totals.last_compaction.isoformat()) == ("2026-01-02", "2026-03-05")
        assert totals.compactions == 3
        assert totals.scan_gaps == {"unconvertible-timestamp": 1}


class TestTruncation:
    def _truncated_after(self, content: str) -> int:
        totals = _count([boundary("b1"), attachment(skill_entry(TRACKED_SKILL, content))])
        return totals.truncated[TRACKED_SKILL]

    def test_marker_at_the_end_counts(self):
        assert self._truncated_after("body\n" + skill_reinjection.TRUNCATION_MARKER) == 1

    def test_marker_followed_by_trailing_whitespace_counts(self):
        assert self._truncated_after("body\n" + skill_reinjection.TRUNCATION_MARKER + " \n\n") == 1

    def test_marker_mid_body_does_not_count(self):
        assert self._truncated_after(f"{skill_reinjection.TRUNCATION_MARKER}\nmore body") == 0

    def test_marker_text_claude_code_2_1_330_writes_is_the_marker_that_counts(self):
        """Claude Code writes this text, so it is spelled out here and not read from the constant under test."""
        marker_as_measured = (
            "[... skill content truncated for compaction; use Read on the skill path if you need the full text]"
        )

        assert marker_as_measured == skill_reinjection.TRUNCATION_MARKER
        assert self._truncated_after("body\n" + marker_as_measured) == 1

    def test_body_ending_in_a_near_miss_of_the_marker_text_does_not_count(self):
        near_miss = "[... skill content truncated for compaction; use Read on the skill path if you need the full text.]"

        assert self._truncated_after("body\n" + near_miss) == 0

    def test_unmarked_copy_over_the_cut_length_records_a_gap(self):
        totals = _count([boundary("b1"), attachment(skill_entry(TRACKED_SKILL, "x" * (CUT_LENGTH + 1)))])

        assert totals.truncated[TRACKED_SKILL] == 0
        assert totals.reattached[TRACKED_SKILL] == 1
        assert totals.scan_gaps["unmarked-long-copy"] == 1

    def test_unmarked_copy_of_exactly_the_cut_length_records_no_gap(self):
        totals = _count([boundary("b1"), attachment(skill_entry(TRACKED_SKILL, "x" * CUT_LENGTH))])

        assert totals.scan_gaps == {}

    def test_unmarked_copy_over_the_cut_length_in_utf16_units_only_records_no_gap(self):
        astral_copy = "\U0001f600" * (CUT_LENGTH // 2 + 1)
        assert len(astral_copy) <= CUT_LENGTH < skill_reinjection.copy_lengths(astral_copy).utf16_units

        totals = _count([boundary("b1"), attachment(skill_entry(TRACKED_SKILL, astral_copy))])

        assert totals.scan_gaps == {}

    def test_unmarked_copy_of_exactly_the_cut_length_in_code_points_with_astral_characters_records_no_gap(self):
        astral_copy = "\U0001f600" * CUT_LENGTH
        assert len(astral_copy) == CUT_LENGTH < skill_reinjection.copy_lengths(astral_copy).utf16_units

        totals = _count([boundary("b1"), attachment(skill_entry(TRACKED_SKILL, astral_copy))])

        assert totals.scan_gaps == {}


class TestCopyLengths:
    def test_astral_character_gives_different_code_point_and_utf16_figures(self):
        text = "a\U0001f600"

        assert skill_reinjection.copy_lengths(text) == (2, 3, 5)

    def test_bmp_multibyte_character_counts_one_code_point_one_utf16_unit_and_several_bytes(self):
        assert skill_reinjection.copy_lengths("é€") == (2, 2, 5)

    def test_copy_ending_in_a_lone_high_surrogate_yields_all_three_lengths(self):
        lone_high_surrogate = "ab\ud83d"

        assert skill_reinjection.copy_lengths(lone_high_surrogate) == (3, 3, 5)

    def test_cut_range_tracks_each_unit_independently_across_truncated_copies(self):
        ascii_cut = cut_content(CUT_LENGTH)
        multibyte_shorter_cut = "€" * 1_000 + cut_content(18_000)
        entries = [skill_entry(TRACKED_SKILL, ascii_cut), skill_entry(TRACKED_SKILL, multibyte_shorter_cut)]

        totals = _count([boundary("b1"), attachment(*entries)])

        assert totals.cut_ranges[TRACKED_SKILL].shortest == (19_000, 19_000, CUT_LENGTH)
        assert totals.cut_ranges[TRACKED_SKILL].longest == (CUT_LENGTH, CUT_LENGTH, 21_000)

    def test_lone_surrogate_in_a_cut_copy_does_not_raise_and_is_measured_in_every_unit(self):
        totals = _count([boundary("b1"), attachment(skill_entry(TRACKED_SKILL, "\ud83d" + cut_content()))])

        assert totals.truncated[TRACKED_SKILL] == 1
        assert totals.cut_ranges[TRACKED_SKILL] == ((CUT_LENGTH + 1, CUT_LENGTH + 1, CUT_LENGTH + 3),) * 2
        assert totals.scan_gaps == {}


class TestNames:
    def test_bare_and_plugin_tracked_names_print_and_foreign_and_untracked_names_fold_into_the_withheld_row(
        self, fake_projects, capsys, monkeypatch,
    ):
        foreign_spelling = "other-plugin:" + TRACKED_SKILL
        records = [
            boundary("b1"),
            attachment(
                skill_entry(TRACKED_SKILL, cut_content()), skill_entry(TRACKED_PLUGIN_SKILL),
                skill_entry(foreign_spelling, cut_content()), skill_entry(UNTRACKED_SKILL, cut_content()),
            ),
            boundary("b2"), attachment(skill_entry(UNTRACKED_SKILL)),
        ]

        out = _run_report(fake_projects, capsys, records, monkeypatch=monkeypatch).out

        assert f"\n{TRACKED_SKILL}: reattached=1 truncated=1\n" in out
        assert f"\n{TRACKED_PLUGIN_SKILL}: reattached=1 truncated=0\n" in out
        assert "\n(withheld — untracked skill): reattached=3 truncated=2\n" in out
        assert foreign_spelling not in out
        assert UNTRACKED_SKILL not in out

    def test_empty_tracked_set_prints_the_unavailable_lines_the_withheld_row_and_the_totals_and_no_name(
        self, fake_projects, capsys, monkeypatch,
    ):
        records = [boundary("b1"), attachment(skill_entry(TRACKED_SKILL, cut_content()), skill_entry(UNTRACKED_SKILL))]

        out = _run_report(fake_projects, capsys, records, tracked=(), monkeypatch=monkeypatch).out

        assert "Every skill name is withheld because the list of skills this repository tracks is unavailable." in out
        assert "\ntruncated copies of tracked skills: unavailable\n" in out
        assert "truncated copies of tracked skills: none" not in out
        assert "(withheld — untracked skill): reattached=2 truncated=1" in out
        assert "sessions=1 compactions=1 with_attachment=1" in out
        assert TRACKED_SKILL not in out
        assert UNTRACKED_SKILL not in out

    def test_tracked_list_that_is_available_prints_no_unavailable_line(self, fake_projects, capsys, monkeypatch):
        out = _run_report(fake_projects, capsys, [boundary("b1")], monkeypatch=monkeypatch).out

        assert "unavailable" not in out


class TestRowOrder:
    def test_rows_print_by_reattached_count_descending_then_by_name(self, fake_projects, capsys, monkeypatch):
        names = ("zeta-skill", "beta-skill", "alpha-skill", "gamma-skill")
        records = [
            boundary("b1"), attachment(*(skill_entry(name) for name in names)),
            boundary("b2"), attachment(skill_entry("gamma-skill")),
            boundary("b3"), attachment(skill_entry("gamma-skill"), skill_entry("zeta-skill")),
        ]

        out = _run_report(fake_projects, capsys, records, tracked=names, monkeypatch=monkeypatch).out

        printed = [line.split(":")[0] for line in out.splitlines() if ": reattached=" in line]
        assert printed == ["gamma-skill", "zeta-skill", "alpha-skill", "beta-skill"]


class TestNoSessions:
    def test_corpus_with_no_sessions_prints_the_header_and_zero_totals_and_exits_zero(
        self, fake_projects, capsys, monkeypatch,
    ):
        stub_tracked_skill_names(monkeypatch, TRACKED_SKILL)

        skill_reinjection.cmd_skill_reinjection(_this_repo_args())

        out = capsys.readouterr().out
        assert out.splitlines()[0].startswith("SKILL REINJECTION SOURCES (this repo (1 project dirs);")
        assert "sessions=0 compactions=0 with_attachment=0 without_attachment=0" in out
        assert "first_compaction=none last_compaction=none" in out
        assert "truncated copies of tracked skills: none" in out


class TestMalformedInput:
    _GOOD = [boundary("b1"), attachment(skill_entry(TRACKED_SKILL, cut_content(), path=PATH_CANARY))]

    def _baseline(self) -> skill_reinjection.ReinjectionTotals:
        return _count(self._GOOD)

    @pytest.mark.parametrize(
        ("bad_records", "gap_kind", "expected_gaps", "extra_compactions"),
        [
            (["not an object", 7, None, ["list"]], "non-object-record", 4, 0),
            ([{"type": "attachment", "attachment": "not an object"}], "non-object-attachment", 1, 0),
            ([{"type": "attachment"}], "non-object-attachment", 1, 0),
            ([boundary("b2"), {"type": "attachment", "attachment": {"type": "invoked_skills"}}], "bad-skills-list", 1, 1),
            (
                [boundary("b2"), {"type": "attachment", "attachment": {"type": "invoked_skills", "skills": "x"}}],
                "bad-skills-list", 1, 1,
            ),
            (
                [boundary("b2"), {"type": "attachment", "attachment": {"type": "invoked_skills", "skills": {}}}],
                "bad-skills-list", 1, 1,
            ),
        ],
        ids=[
            "non-object-records", "attachment-not-an-object", "attachment-key-missing",
            "skills-missing", "skills-a-string", "skills-an-object",
        ],
    )
    def test_each_bad_record_shape_records_its_gap_and_leaves_the_good_counts_unchanged(
        self, bad_records, gap_kind, expected_gaps, extra_compactions,
    ):
        baseline = self._baseline()

        totals = _count([*self._GOOD, *bad_records])

        assert totals.scan_gaps == {gap_kind: expected_gaps}
        assert totals.compactions == baseline.compactions + extra_compactions
        assert totals.compactions_with_attachment == baseline.compactions_with_attachment
        assert totals.reattached == baseline.reattached
        assert totals.truncated == baseline.truncated
        assert totals.cut_ranges == baseline.cut_ranges

    @pytest.mark.parametrize(
        ("bad_entry", "gap_kind"),
        [
            ("junk", "non-object-skill-entry"),
            (None, "non-object-skill-entry"),
            ({"path": PATH_CANARY, "content": CONTENT_CANARY}, "bad-skill-fields"),
            ({"name": 7, "path": PATH_CANARY, "content": CONTENT_CANARY}, "bad-skill-fields"),
            ({"name": UNTRACKED_SKILL, "path": PATH_CANARY}, "bad-skill-fields"),
            ({"name": UNTRACKED_SKILL, "path": PATH_CANARY, "content": ["not", "text"]}, "bad-skill-fields"),
        ],
        ids=["string-entry", "null-entry", "name-missing", "name-an-integer", "content-missing", "content-a-list"],
    )
    def test_each_bad_skill_entry_records_one_gap_and_leaves_the_good_entry_counted(self, bad_entry, gap_kind):
        good_entry = skill_entry(TRACKED_SKILL, cut_content())

        totals = _count([boundary("b1"), attachment(bad_entry, good_entry)])

        assert totals.scan_gaps[gap_kind] == 1
        assert totals.compactions_with_attachment == 1
        assert totals.reattached == {TRACKED_SKILL: 1}
        assert totals.truncated == {TRACKED_SKILL: 1}

    def test_malformed_line_in_the_file_changes_no_count_and_records_no_gap(self, fake_projects, capsys, monkeypatch):
        stub_tracked_skill_names(monkeypatch, TRACKED_SKILL)
        _write_jsonl(fake_projects / "clean.jsonl", self._GOOD)
        clean_out = _report_text(capsys)
        (fake_projects / "clean.jsonl").unlink()
        good_lines = "".join(json.dumps(record) + "\n" for record in self._GOOD)
        (fake_projects / "damaged.jsonl").write_text(
            '{"type": "system", "subtype": "compact_boundary", broken\n' + good_lines + "not json at all\n",
        )

        assert _report_text(capsys) == clean_out

    _CANARY_FIELDS = {"path": PATH_CANARY, "content": CONTENT_CANARY}
    _BAD_SHAPES_CARRYING_CANARIES = {
        "non-object-record": [CONTENT_CANARY, [PATH_CANARY]],
        "non-object-attachment": [{"type": "attachment", "attachment": PATH_CANARY}],
        "skills-not-a-list": [
            boundary("b2"), {"type": "attachment", "attachment": {"type": "invoked_skills", "skills": CONTENT_CANARY}},
        ],
        "non-object-skill-entry": [boundary("b2"), attachment(PATH_CANARY)],
        "name-missing": [boundary("b2"), attachment(_CANARY_FIELDS)],
        "name-not-a-string": [boundary("b2"), attachment({"name": 7, **_CANARY_FIELDS})],
        "content-missing": [boundary("b2"), attachment({"name": UNTRACKED_SKILL, "path": PATH_CANARY})],
        "unpaired-attachment": [attachment(skill_entry(UNTRACKED_SKILL, CONTENT_CANARY))],
        "boundary-without-uuid": [boundary(UNSET), attachment(skill_entry(UNTRACKED_SKILL, CONTENT_CANARY))],
        "unmarked-long-copy": [boundary("b2"), attachment(skill_entry(UNTRACKED_SKILL, CONTENT_CANARY * 500))],
    }

    @pytest.mark.parametrize("bad_records", _BAD_SHAPES_CARRYING_CANARIES.values(), ids=_BAD_SHAPES_CARRYING_CANARIES.keys())
    def test_each_bad_shape_prints_none_of_its_canaries_and_still_prints_the_good_counts(
        self, fake_projects, capsys, monkeypatch, bad_records,
    ):
        captured = _run_report(
            fake_projects, capsys, [*self._GOOD, *bad_records], tracked=(TRACKED_SKILL,), monkeypatch=monkeypatch,
        )

        output = captured.out + captured.err
        for canary in (SESSION_ID_CANARY, DIRECTORY_CANARY, CONTENT_CANARY, UNTRACKED_SKILL, _PROJECT_SLUG):
            assert canary not in output
        assert f"{TRACKED_SKILL}: reattached=1 truncated=1" in captured.out


class TestPrivacy:
    def test_session_id_project_slug_path_content_prefix_and_untracked_name_never_reach_stdout_or_stderr(
        self, fake_projects, capsys, monkeypatch,
    ):
        prefixed_cut_copy = CONTENT_CANARY + "\n\n" + cut_content()
        records = [
            boundary("b1"),
            attachment(
                skill_entry(TRACKED_SKILL, prefixed_cut_copy), skill_entry(UNTRACKED_SKILL, prefixed_cut_copy),
            ),
        ]

        captured = _run_report(fake_projects, capsys, records, monkeypatch=monkeypatch)

        output = captured.out + captured.err
        for canary in (SESSION_ID_CANARY, _PROJECT_SLUG, DIRECTORY_CANARY, CONTENT_CANARY, UNTRACKED_SKILL):
            assert canary not in output
        assert f"{TRACKED_SKILL}: reattached=1 truncated=1" in captured.out


class TestReportLines:
    def test_report_prints_the_dates_and_zero_for_every_gap_and_skipped_input_count(
        self, fake_projects, capsys, monkeypatch,
    ):
        records = [boundary("b1", "2026-04-05T00:00:00Z"), attachment(skill_entry(TRACKED_SKILL, cut_content()))]

        out = _run_report(fake_projects, capsys, records, monkeypatch=monkeypatch).out

        assert "first_compaction=2026-04-05 last_compaction=2026-04-05" in out
        assert labelled_counts(out, "scan gaps:") == _NO_GAPS
        assert labelled_counts(out, "skipped input:") == _NO_SKIPPED_INPUT

    def test_report_prints_the_compactions_without_an_attachment_and_the_earliest_and_latest_compaction_dates(
        self, fake_projects, capsys, monkeypatch,
    ):
        records = [
            boundary("b1", "2026-03-05T10:00:00Z"), attachment(skill_entry(TRACKED_SKILL)),
            boundary("b2", "2026-01-02T10:00:00Z"),
            boundary("b3", "2026-02-01T10:00:00Z"),
        ]

        out = _run_report(fake_projects, capsys, records, monkeypatch=monkeypatch).out

        assert "\nsessions=1 compactions=3 with_attachment=1 without_attachment=2\n" in out
        assert "\nfirst_compaction=2026-01-02 last_compaction=2026-03-05\n" in out

    def test_each_cut_length_unit_prints_under_its_own_label_for_the_shortest_and_the_longest_copy(
        self, fake_projects, capsys, monkeypatch,
    ):
        astral_cut_copy = "\U0001f600" * 100 + cut_content(19_000)
        mixed_cut_copy = "€" * 1_000 + "\U0001f600" * 50 + cut_content(17_900)
        assert skill_reinjection.copy_lengths(astral_cut_copy) == (19_100, 19_200, 19_400)
        assert skill_reinjection.copy_lengths(mixed_cut_copy) == (18_950, 19_000, 21_100)
        records = [
            boundary("b1"), attachment(skill_entry(TRACKED_SKILL, astral_cut_copy), skill_entry(TRACKED_SKILL, mixed_cut_copy)),
        ]

        out = _run_report(fake_projects, capsys, records, monkeypatch=monkeypatch).out

        assert "\ntruncated copy of a tracked skill, shortest: code_points=18,950 utf16_units=19,000 utf8_bytes=19,400\n" in out
        assert "\ntruncated copy of a tracked skill, longest:  code_points=19,100 utf16_units=19,200 utf8_bytes=21,100\n" in out

    def test_cut_range_takes_each_extreme_from_whichever_tracked_skill_holds_it(
        self, fake_projects, capsys, monkeypatch,
    ):
        ascii_cut_copy = cut_content(19_500)
        multibyte_cut_copy = "€" * 500 + cut_content(18_800)
        assert skill_reinjection.copy_lengths(ascii_cut_copy) == (19_500, 19_500, 19_500)
        assert skill_reinjection.copy_lengths(multibyte_cut_copy) == (19_300, 19_300, 20_300)
        records = [
            boundary("b1"),
            attachment(
                skill_entry(TRACKED_SKILL, ascii_cut_copy), skill_entry(TRACKED_PLUGIN_SKILL, multibyte_cut_copy),
            ),
        ]

        out = _run_report(fake_projects, capsys, records, monkeypatch=monkeypatch).out

        assert "\ntruncated copy of a tracked skill, shortest: code_points=19,300 utf16_units=19,300 utf8_bytes=19,500\n" in out
        assert "\ntruncated copy of a tracked skill, longest:  code_points=19,500 utf16_units=19,500 utf8_bytes=20,300\n" in out

    def test_cut_range_leaves_out_an_untracked_skills_copy_that_would_set_the_extremes(
        self, fake_projects, capsys, monkeypatch,
    ):
        tracked_cut_copy = cut_content(CUT_LENGTH)
        untracked_cut_copy = "€" * 1_000 + cut_content(18_000)
        assert skill_reinjection.copy_lengths(untracked_cut_copy) == (19_000, 19_000, 21_000)
        records = [
            boundary("b1"),
            attachment(skill_entry(TRACKED_SKILL, tracked_cut_copy), skill_entry(UNTRACKED_SKILL, untracked_cut_copy)),
        ]

        out = _run_report(fake_projects, capsys, records, monkeypatch=monkeypatch).out

        assert "\ntruncated copy of a tracked skill, shortest: code_points=20,000 utf16_units=20,000 utf8_bytes=20,000\n" in out
        assert "\ntruncated copy of a tracked skill, longest:  code_points=20,000 utf16_units=20,000 utf8_bytes=20,000\n" in out

    def test_cut_range_prints_none_when_only_an_untracked_skill_was_cut(self, fake_projects, capsys, monkeypatch):
        records = [boundary("b1"), attachment(skill_entry(UNTRACKED_SKILL, cut_content()))]

        out = _run_report(fake_projects, capsys, records, monkeypatch=monkeypatch).out

        assert "\ntruncated copies of tracked skills: none\n" in out

    def test_every_gap_kind_prints_under_its_own_label_with_its_own_count(self, fake_projects, capsys, monkeypatch):
        bad_timestamp = "not a date"
        overflowing_timestamp = "0001-01-01T00:00:00+05:00"
        records: list = [
            *["not an object"] * 4,
            *[{"type": "attachment", "attachment": "not an object"}] * 5,
            attachment(skill_entry(TRACKED_SKILL)),
            boundary(UNSET, bad_timestamp),
            attachment(
                *[skill_entry(TRACKED_SKILL, "x" * (CUT_LENGTH + 1))] * 3, *["not an object"] * 7, *[{"name": 7}] * 8,
            ),
            boundary(UNSET, bad_timestamp),
            *[
                record
                for index in range(6)
                for record in (
                    boundary(f"no-skills-{index}", bad_timestamp),
                    {"type": "attachment", "attachment": {"type": "invoked_skills"}},
                )
            ],
            boundary("overflow", overflowing_timestamp),
        ]

        out = _run_report(fake_projects, capsys, records, monkeypatch=monkeypatch).out

        assert labelled_counts(out, "scan gaps:") == {
            "unpaired_attachments": 1, "boundaries_without_uuid": 2, "unmarked_long_copies": 3,
            "non_object_records": 4, "non_object_attachments": 5, "bad_skills_lists": 6,
            "non_object_skill_entries": 7, "bad_skill_fields": 8, "unconvertible_timestamps": 9,
        }
        assert labelled_counts(out, "skipped input:") == _NO_SKIPPED_INPUT

    @pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses file permission bits")
    def test_unreadable_projects_directory_prints_as_one_unreadable_root(self, fake_projects, capsys, monkeypatch):
        stub_tracked_skill_names(monkeypatch, TRACKED_SKILL)
        with unreadable(fake_projects.parent):
            skill_reinjection.cmd_skill_reinjection(_this_repo_args())

        counts = labelled_counts(capsys.readouterr().out, "skipped input:")
        assert counts == {**_NO_SKIPPED_INPUT, "unreadable_roots": 1}

    @pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses file permission bits")
    def test_unreadable_project_directory_prints_as_one_unreadable_project_dir(self, fake_projects, capsys, monkeypatch):
        stub_tracked_skill_names(monkeypatch, TRACKED_SKILL)
        with unreadable(fake_projects):
            skill_reinjection.cmd_skill_reinjection(_this_repo_args())

        counts = labelled_counts(capsys.readouterr().out, "skipped input:")
        assert counts == {**_NO_SKIPPED_INPUT, "unreadable_project_dirs": 1}

    @pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses file permission bits")
    def test_unreadable_main_transcript_prints_as_one_unreadable_main_file(self, fake_projects, capsys, monkeypatch):
        stub_tracked_skill_names(monkeypatch, TRACKED_SKILL)
        main_transcript = fake_projects / "sess.jsonl"
        _write_jsonl(main_transcript, [boundary("b1")])
        with unreadable(main_transcript):
            skill_reinjection.cmd_skill_reinjection(_this_repo_args())

        out = capsys.readouterr().out
        assert labelled_counts(out, "skipped input:") == {**_NO_SKIPPED_INPUT, "unreadable_main_files": 1}
        assert "sessions=0 " in out


class TestArgparseWiring:
    """Round-trips the real registrar; a hand-built Namespace misses `dest=` typos, missing `set_defaults`, and flag drift."""

    def test_skill_reinjection_wires_to_cmd_skill_reinjection_with_this_repo(self):
        parser = argparse.ArgumentParser()
        skill_reinjection._add_skill_reinjection_subparser(parser.add_subparsers())
        parsed = parser.parse_args(["skill-reinjection", "--this-repo"])
        assert parsed.func is skill_reinjection.cmd_skill_reinjection
        assert parsed.this_repo is True


@pytest.mark.usefixtures("scrubbed_git_environment")
class TestTrackedNamesFromRealGit:
    """Runs the command with the allowlist unstubbed, so the printable names come from this checkout's `git ls-files`."""

    @pytest.fixture(autouse=True)
    def _clear_tracked_name_cache(self):
        redaction._repo_tracked_skill_names.cache_clear()
        yield
        redaction._repo_tracked_skill_names.cache_clear()

    def _report_run_from(self, repository, fake_projects, monkeypatch, capsys, skill_name):
        monkeypatch.chdir(repository)
        project_directory = fake_projects.parent / scope._path_to_project_slug(str(repository.resolve()))
        project_directory.mkdir()
        _write_jsonl(
            project_directory / f"{SESSION_ID_CANARY}.jsonl", [boundary("b1"), attachment(skill_entry(skill_name))],
        )
        skill_reinjection.cmd_skill_reinjection(argparse.Namespace(this_repo=True, projects="*"))
        return capsys.readouterr()

    def test_second_repository_tracking_a_canary_skill_never_has_the_canary_name_printed(
        self, fake_projects, tmp_path, monkeypatch, capsys,
    ):
        other_repository = init_repository_tracking_canary_skill(tmp_path / "other-repository")

        captured = self._report_run_from(
            other_repository, fake_projects, monkeypatch, capsys, OTHER_REPOSITORY_CANARY_SKILL,
        )

        assert OTHER_REPOSITORY_CANARY_SKILL not in captured.out + captured.err
        assert "\n(withheld — untracked skill): reattached=1 truncated=0\n" in captured.out

    def test_skill_this_checkout_tracks_prints_by_name_when_run_from_this_checkout(
        self, fake_projects, monkeypatch, capsys,
    ):
        assert redaction._REPO_ROOT is not None
        assert redaction._repo_tracked_skill_names(), (
            "git could not list this checkout's tracked files (ownership, or a checkout without .git)"
        )

        tracked_skill_on_disk = first_skill_directory_on_disk()

        captured = self._report_run_from(
            redaction._REPO_ROOT, fake_projects, monkeypatch, capsys, tracked_skill_on_disk,
        )

        assert f"\n{tracked_skill_on_disk}: reattached=1 truncated=0\n" in captured.out


class TestScopeRefusal:
    def test_refusal_without_this_repo_exits_2_with_exactly_one_stderr_line_and_nothing_else(self, fake_projects, capsys):
        with pytest.raises(SystemExit) as raised:
            skill_reinjection._skill_reinjection_report(_this_repo_args(this_repo=False), [fake_projects.parent])
        assert raised.value.code == 2
        captured = capsys.readouterr()
        assert captured.err == refusal_without_this_repo("skill-reinjection")
        assert captured.out == ""

    def test_refusal_with_a_projects_glob_exits_2_with_exactly_one_stderr_line_and_nothing_else(
        self, fake_projects, capsys,
    ):
        # The parser's mutually exclusive group never yields this Namespace.
        # The `projects ... not in (None, "*")` test in `_refuse_wider_scope` is defense-in-depth for direct callers.
        # The explicit `this_repo=True` keeps the other refusal leg out of play, so only the projects leg can refuse.
        with pytest.raises(SystemExit) as raised:
            skill_reinjection._skill_reinjection_report(
                _this_repo_args(projects="-home-*", this_repo=True), [fake_projects.parent],
            )
        assert raised.value.code == 2
        captured = capsys.readouterr()
        assert captured.err == refusal_without_this_repo("skill-reinjection")
        assert captured.out == ""

    def test_refusal_with_two_roots_exits_2_with_exactly_one_stderr_line_and_nothing_else(
        self, fake_projects, tmp_path, capsys,
    ):
        other_root = tmp_path / "other-account" / "projects"
        other_root.mkdir(parents=True)
        with pytest.raises(SystemExit) as raised:
            skill_reinjection._skill_reinjection_report(_this_repo_args(), [fake_projects.parent, other_root])
        assert raised.value.code == 2
        captured = capsys.readouterr()
        assert captured.err == refusal_with_several_roots("skill-reinjection")
        assert captured.out == ""

    def test_cmd_scans_the_active_account_alone_even_when_other_roots_are_declared(
        self, fake_projects, tmp_path, monkeypatch, capsys,
    ):
        stub_tracked_skill_names(monkeypatch, TRACKED_SKILL)
        declared = tmp_path / "declared-account"
        (declared / "projects" / _PROJECT_SLUG).mkdir(parents=True)
        roots_file = tmp_path / "roots"
        roots_file.write_text(f"{declared}\n")
        monkeypatch.setenv("TRANSCRIPT_CONFIG_DIRS_FILE", str(roots_file))
        _write_jsonl(fake_projects / "sess.jsonl", [boundary("b1")])
        _write_jsonl(declared / "projects" / _PROJECT_SLUG / "other.jsonl", [boundary("b2"), boundary("b3")])

        skill_reinjection.cmd_skill_reinjection(_this_repo_args())

        assert "sessions=1 compactions=1 " in capsys.readouterr().out

    def test_unresolvable_config_dir_exits_2_with_one_skill_reinjection_stderr_line_and_no_stdout(
        self, monkeypatch, capsys,
    ):
        def unresolvable_config_dir():
            raise ValueError("CLAUDE_CONFIG_DIR is not absolute")

        monkeypatch.setattr(scope, "config_dir", unresolvable_config_dir)
        with pytest.raises(SystemExit) as raised:
            skill_reinjection.cmd_skill_reinjection(_this_repo_args())
        assert raised.value.code == 2
        captured = capsys.readouterr()
        assert captured.err == "skill-reinjection: CLAUDE_CONFIG_DIR is not absolute\n"
        assert captured.out == ""

    def test_header_states_the_active_account_the_working_directorys_repository_and_the_unconsulted_roots_file(
        self, fake_projects, monkeypatch, capsys,
    ):
        stub_tracked_skill_names(monkeypatch, TRACKED_SKILL)

        skill_reinjection.cmd_skill_reinjection(_this_repo_args())

        assert capsys.readouterr().out.splitlines()[0] == scope_header("skill-reinjection", "this repo (1 project dirs)")

