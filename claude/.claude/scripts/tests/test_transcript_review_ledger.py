"""Tests for transcript_analysis/review_ledger.py."""
import json
import os
import subprocess
import uuid
from pathlib import Path

import pytest
from helpers import HOOKS_DIR, SCRIPTS_DIR, init_git_repo_with_commit
from hooks.tests.conftest import _seed_session
from transcript_analysis import author_outcome, review_ledger

from ._ledger_reader_helpers import fake_transcript_path
from .conftest import _ledger_row, _write_branch_ledger_file, _write_ledger_file

_REVIEW_LEDGER_SH = SCRIPTS_DIR / "review-ledger.sh"
_LIB_SH = HOOKS_DIR / "_lib.sh"


class TestConfigDirRootForSession:
    def test_derives_the_owning_root_for_two_distinct_config_dir_roots(self, tmp_path):
        """test_author_outcome.py's TestMultiRootLedgerLookup pins the same invariant through
        compute_author_outcomes' full pipeline; this pins it directly on
        _config_dir_root_for_session, the cheaper unit underneath it."""
        root_a = tmp_path / "acct-a"
        root_b = tmp_path / "acct-b"
        jsonl_a = root_a / "projects" / "-home-user-repo1" / "sess-a.jsonl"
        jsonl_b = root_b / "projects" / "-home-user-repo2" / "sess-b.jsonl"
        jsonl_a.parent.mkdir(parents=True)
        jsonl_b.parent.mkdir(parents=True)
        jsonl_a.write_text("")
        jsonl_b.write_text("")

        assert review_ledger._config_dir_root_for_session(jsonl_a) == root_a
        assert review_ledger._config_dir_root_for_session(jsonl_b) == root_b


def _grow_keeping_mtime(ledger_path: Path, before: os.stat_result) -> None:
    """Change only the size half of the index signature."""
    with ledger_path.open("a") as ledger_file:
        ledger_file.write(json.dumps(_ledger_row(round=2, disposition="DEFER")) + "\n")
    os.utime(ledger_path, ns=(before.st_atime_ns, before.st_mtime_ns))


def _rewrite_at_same_size_with_newer_mtime(ledger_path: Path, before: os.stat_result) -> None:
    """Change only the mtime half of the index signature."""
    original_text = ledger_path.read_text()
    rewritten_text = original_text.replace('"round": 1', '"round": 7')
    assert rewritten_text != original_text
    ledger_path.write_text(rewritten_text)
    os.utime(ledger_path, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000_000))


class TestListLedgerFiles:
    def test_lists_jsonl_files_sorted_by_filename_and_skips_lock_files(self, tmp_path):
        ledger_dir = tmp_path / "review-narrative-ledger"
        ledger_dir.mkdir()
        second = ledger_dir / ("1" * 64 + ".sess-1.jsonl")
        first = ledger_dir / ("0" * 64 + ".sess-1.jsonl")
        second.write_text("")
        first.write_text("")
        (ledger_dir / ("0" * 64 + ".sess-1.jsonl.lock")).write_text("")

        assert review_ledger._list_ledger_files(ledger_dir) == [first, second]

    def test_missing_directory_lists_nothing(self, tmp_path):
        assert review_ledger._list_ledger_files(tmp_path / "review-narrative-ledger") == []


class TestLedgerRowAttribution:
    """Which session a ledger row belongs to: its own `session_id`, else
    the session id in its file's name."""

    def test_row_without_session_id_belongs_to_the_session_in_its_filename(self, tmp_path):
        _write_ledger_file(tmp_path, "sess-1", [_ledger_row(round=1, disposition="ADDRESS")])
        _write_ledger_file(tmp_path, "sess-2", [_ledger_row(round=1, disposition="DEFER")], repo_hash="1" * 64)

        entries, any_file_found = review_ledger._read_ledger_row_entries_for_session(fake_transcript_path(tmp_path, "sess-1"))

        assert [row["disposition"] for _file_index, row in entries] == ["ADDRESS"]
        assert any_file_found is True

    def test_row_with_session_id_in_a_branch_file_belongs_to_that_session_only(self, tmp_path):
        _write_branch_ledger_file(tmp_path, "b" * 64, [
            _ledger_row(round=1, disposition="ADDRESS", schema_version=3, session_id="sess-1"),
            _ledger_row(round=2, disposition="DEFER", schema_version=3, session_id="sess-2"),
        ])

        entries_1, found_1 = review_ledger._read_ledger_row_entries_for_session(fake_transcript_path(tmp_path, "sess-1"))
        entries_2, _found_2 = review_ledger._read_ledger_row_entries_for_session(fake_transcript_path(tmp_path, "sess-2"))

        assert [row["round"] for _file_index, row in entries_1] == [1]
        assert [row["round"] for _file_index, row in entries_2] == [2]
        assert found_1 is False, "a branch file is not a session-keyed file for sess-1"

    @pytest.mark.parametrize("session_id_value", ["", "../escape", "has space", 7, None])
    def test_row_naming_an_invalid_session_id_is_ignored(self, tmp_path, session_id_value):
        row = _ledger_row(round=1, disposition="ADDRESS", schema_version=3)
        row["session_id"] = session_id_value
        _write_ledger_file(tmp_path, "sess-1", [row])

        entries, any_file_found = review_ledger._read_ledger_row_entries_for_session(fake_transcript_path(tmp_path, "sess-1"))

        assert entries == []
        assert any_file_found is True

    def test_row_naming_another_session_in_this_sessions_own_file_is_not_attributed_to_this_session(
        self, tmp_path,
    ):
        _write_ledger_file(tmp_path, "sess-1", [
            _ledger_row(round=1, disposition="DEFER", schema_version=3, session_id="sess-9"),
        ])

        entries, _any_file_found = review_ledger._read_ledger_row_entries_for_session(fake_transcript_path(tmp_path, "sess-1"))

        assert entries == []

    def test_a_sessions_rows_across_a_branch_file_and_its_own_file_get_distinct_file_indexes(self, tmp_path):
        _write_ledger_file(tmp_path, "sess-1", [_ledger_row(round=1, disposition="DEFER")], repo_hash="0" * 64)
        _write_branch_ledger_file(
            tmp_path, "b" * 64,
            [_ledger_row(round=2, disposition="DEFER", schema_version=3, session_id="sess-1",
                         event_time="2026-08-01T10:05:00Z")],
        )

        entries, _any_file_found = review_ledger._read_ledger_row_entries_for_session(fake_transcript_path(tmp_path, "sess-1"))

        file_index_by_round = {row["round"]: file_index for file_index, row in entries}
        assert set(file_index_by_round) == {1, 2}
        assert file_index_by_round[1] != file_index_by_round[2]


class TestReadLedgerRowEntriesForSession:
    """_write_ledger_file/_ledger_row (the conftest fixtures other
    tests in this file use) can only ever produce valid-JSON lines, so they
    can't exercise the malformed-line/unreadable-file tolerance
    _read_ledger_rows_from_file's own docstring claims -- the
    tests here that exercise that tolerance write the ledger file directly instead."""

    def test_malformed_line_is_skipped_not_fatal(self, tmp_path):
        config_dir_root = tmp_path
        ledger_dir = config_dir_root / "review-narrative-ledger"
        ledger_dir.mkdir(parents=True)
        ledger_path = ledger_dir / ("a" * 64 + ".sess-1.jsonl")
        ledger_path.write_text(
            '{"round":1,"disposition":"ADDRESS"}\n'
            "this is not json at all\n"
            '{"round":2,"disposition":"DEFER"}\n'
        )
        jsonl = config_dir_root / "projects" / "-home-user-testrepo" / "sess-1.jsonl"
        jsonl.parent.mkdir(parents=True)
        jsonl.write_text("")

        entries, any_file_found = review_ledger._read_ledger_row_entries_for_session(jsonl)
        rows = [row for _file_index, row in entries]

        assert [r["round"] for r in rows] == [1, 2], (
            "the malformed line must be dropped, and the surrounding valid "
            "rows must still be returned in file order"
        )
        assert any_file_found is True

    def test_non_dict_json_line_is_skipped_not_fatal(self, tmp_path):
        """A bare JSON array parses cleanly but isn't a row.
        Distinct from the JSONDecodeError branch
        test_malformed_line_is_skipped_not_fatal exercises above."""
        config_dir_root = tmp_path
        ledger_dir = config_dir_root / "review-narrative-ledger"
        ledger_dir.mkdir(parents=True)
        ledger_path = ledger_dir / ("a" * 64 + ".sess-1.jsonl")
        ledger_path.write_text('[1,2,3]\n{"round":1,"disposition":"ADDRESS"}\n')
        jsonl = config_dir_root / "projects" / "-home-user-testrepo" / "sess-1.jsonl"
        jsonl.parent.mkdir(parents=True)
        jsonl.write_text("")

        entries, any_file_found = review_ledger._read_ledger_row_entries_for_session(jsonl)
        rows = [row for _file_index, row in entries]

        assert [r["round"] for r in rows] == [1], (
            "the non-dict line must be dropped, and the surrounding valid "
            "row must still be returned"
        )
        assert any_file_found is True

    def test_a_line_that_is_not_valid_utf8_is_skipped_like_a_malformed_line(self, tmp_path):
        ledger_path = tmp_path / "0.sess-1.jsonl"
        good_row = json.dumps(_ledger_row(round=1, disposition="DEFER")).encode()
        ledger_path.write_bytes(
            good_row + b"\n" + b'{"finding": "\xff\xfe torn"}\n' + b"{not json\n" + good_row + b"\n",
        )

        rows, opened = review_ledger._read_ledger_rows_from_file(ledger_path)

        assert opened is True
        assert len(rows) == 2

    def test_unreadable_ledger_path_returns_empty_list_and_is_not_found(self, tmp_path):
        """A directory where a ledger file is expected raises OSError
        (IsADirectoryError) on open() -- the same branch a permission
        error or other unreadable-file condition would hit. A file that
        was listed but couldn't be opened at all must not count
        toward any_file_found (see _read_ledger_rows_from_file's own
        opened=False contract): it's indistinguishable here from the file
        never having existed, which is exactly what makes it a possibly-
        swept signal rather than a present-but-empty one."""
        config_dir_root = tmp_path
        ledger_dir = config_dir_root / "review-narrative-ledger"
        ledger_dir.mkdir(parents=True)
        (ledger_dir / ("a" * 64 + ".sess-1.jsonl")).mkdir()
        jsonl = config_dir_root / "projects" / "-home-user-testrepo" / "sess-1.jsonl"
        jsonl.parent.mkdir(parents=True)
        jsonl.write_text("")

        assert review_ledger._read_ledger_row_entries_for_session(jsonl) == ([], False)

    def test_file_vanishing_between_listing_and_open_is_not_found(self, tmp_path, monkeypatch):
        """A file present when _list_ledger_files listed it, but gone by
        the time _read_ledger_rows_from_file actually opens it (e.g. a
        concurrent review-ledger.sh clear-stale sweep), must not count
        toward any_file_found. Simulated here by having the listing stub
        return a path that was never created, which raises the identical
        OSError branch a real mid-read deletion would."""
        config_dir_root = tmp_path
        ledger_dir = config_dir_root / "review-narrative-ledger"
        ledger_dir.mkdir(parents=True)
        vanished_path = ledger_dir / ("a" * 64 + ".sess-1.jsonl")
        jsonl = config_dir_root / "projects" / "-home-user-testrepo" / "sess-1.jsonl"
        jsonl.parent.mkdir(parents=True)
        jsonl.write_text("")
        listed_dirs = []

        def _stub_listing(listed_dir):
            listed_dirs.append(listed_dir)
            return [vanished_path]

        monkeypatch.setattr(review_ledger, "_list_ledger_files", _stub_listing)

        assert review_ledger._read_ledger_row_entries_for_session(jsonl) == ([], False)
        assert listed_dirs == [ledger_dir]

    def test_one_file_vanishing_does_not_suppress_a_surviving_siblings_rows(self, tmp_path, monkeypatch):
        """The realistic multi-worktree race: two files listed, one
        opens fine, the other gets evicted (e.g. by a concurrent
        clear-stale sweep) before its own open(). Guards against
        `any_file_opened = any_file_opened or opened` regressing to `and`,
        which would silently report any_file_found=False and misroute a
        live session into the possibly-swept bucket even though a real
        file's rows were read fine."""
        config_dir_root = tmp_path
        ledger_dir = config_dir_root / "review-narrative-ledger"
        ledger_dir.mkdir(parents=True)
        surviving_path = ledger_dir / ("a" * 64 + ".sess-1.jsonl")
        surviving_path.write_text('{"round":1,"disposition":"ADDRESS"}\n')
        vanished_path = ledger_dir / ("b" * 64 + ".sess-1.jsonl")
        jsonl = config_dir_root / "projects" / "-home-user-testrepo" / "sess-1.jsonl"
        jsonl.parent.mkdir(parents=True)
        jsonl.write_text("")
        listed_dirs = []

        def _stub_listing(listed_dir):
            listed_dirs.append(listed_dir)
            return [surviving_path, vanished_path]

        monkeypatch.setattr(review_ledger, "_list_ledger_files", _stub_listing)

        entries, any_file_found = review_ledger._read_ledger_row_entries_for_session(jsonl)

        assert any_file_found is True
        assert [row["round"] for _file_index, row in entries] == [1]
        assert listed_dirs == [ledger_dir]

    def test_a_file_with_no_session_slot_yields_no_rows_for_the_session_named_like_its_stem(self, tmp_path):
        """`notes.jsonl` has no session-id slot, so rows without a `session_id` belong to no session,
        including the one whose id equals the file's stem."""
        ledger_dir = tmp_path / "review-narrative-ledger"
        ledger_dir.mkdir(parents=True)
        (ledger_dir / "notes.jsonl").write_text('{"round":1,"disposition":"ADDRESS"}\n')
        jsonl = tmp_path / "projects" / "-home-user-testrepo" / "notes.jsonl"
        jsonl.parent.mkdir(parents=True)
        jsonl.write_text("")

        entries, _any_file_found = review_ledger._read_ledger_row_entries_for_session(jsonl)

        assert entries == []

    def test_unreadable_ledger_path_prints_an_author_outcome_labeled_diagnostic_to_stderr(
        self, tmp_path, capsys,
    ):
        config_dir_root = tmp_path
        ledger_dir = config_dir_root / "review-narrative-ledger"
        ledger_dir.mkdir(parents=True)
        ledger_path = ledger_dir / ("a" * 64 + ".sess-1.jsonl")
        ledger_path.mkdir()
        jsonl = config_dir_root / "projects" / "-home-user-testrepo" / "sess-1.jsonl"
        jsonl.parent.mkdir(parents=True)
        jsonl.write_text("")

        review_ledger._read_ledger_row_entries_for_session(jsonl)

        captured = capsys.readouterr()
        assert captured.err.startswith("author-outcome: ")
        assert str(ledger_path) in captured.err
        assert captured.out == ""

    def test_merge_sorts_by_event_time_not_file_glob_order(self, tmp_path):
        """Two of the session's files, with real (fixture-
        supplied, not the shared constant default) event_time values that
        invert filename/glob order -- repo_hash "0"*64 sorts first by
        filename, but carries the LATER event_time, while "f"*64 sorts last
        by filename and carries the EARLIER one. A fixture row that supplies no
        event_time of its own shares one fixed event_time, which makes
        Python's stable sort fall back to file-encounter order and would
        silently mask a broken sort key. Mirrors
        test_show_merges_the_branch_and_session_files_in_event_time_order
        in test_review_ledger_script.py, which pins the same invariant on
        the shell side."""
        config_dir_root = tmp_path
        _write_ledger_file(
            config_dir_root, "sess-1",
            [_ledger_row(round=2, disposition="DEFER", event_time="2026-08-01T10:05:00Z")],
            repo_hash="0" * 64,
        )
        _write_ledger_file(
            config_dir_root, "sess-1",
            [_ledger_row(round=1, disposition="ADDRESS", event_time="2026-08-01T10:00:00Z")],
            repo_hash="f" * 64,
        )
        jsonl = config_dir_root / "projects" / "-home-user-testrepo" / "sess-1.jsonl"
        jsonl.parent.mkdir(parents=True)
        jsonl.write_text("")

        entries, any_file_found = review_ledger._read_ledger_row_entries_for_session(jsonl)

        assert any_file_found is True
        assert [row["round"] for _file_index, row in entries] == [1, 2], (
            "the merged order must follow event_time (the 'f'*64 file's "
            "earlier row first), not file-encounter order (the "
            "'0'*64 file sorts first alphabetically but is read second here)"
        )


class TestSessionIdPatternMatchesLibSh:
    _CORPUS = [
        str(uuid.UUID(int=1)),
        "test_session-1",
        "a.b",
        "abc\n",
        "",
        "a/b",
        "..",
        "sess\u00e9",  # accented letter
        "\uff41bc",  # fullwidth letter
    ]

    @pytest.mark.parametrize("session_id", _CORPUS, ids=repr)
    def test_python_and_shell_validators_agree(self, session_id):
        """_SESSION_ID_PATTERN is duplicated independently of
        _lib_valid_session_id_component. If the shell allow-list widened,
        the Python reader would drop every branch-file row for the widened
        ids, so each corpus entry must get the same verdict from both."""
        shell_result = subprocess.run(
            ["bash", "-c", f'. "{_LIB_SH}"; _lib_valid_session_id_component "$1"', "_", session_id],
            capture_output=True, text=True, check=False,
        )
        shell_accepts = shell_result.returncode == 0
        python_accepts = review_ledger._SESSION_ID_PATTERN.fullmatch(session_id) is not None
        assert shell_accepts == python_accepts, (
            f"shell accepts={shell_accepts}, python accepts={python_accepts} for {session_id!r}"
        )


class TestReviewLedgerSubprocessIntegration:
    """Runs the real review-ledger.sh append subprocess and reads it back
    through the same reader functions other tests exercise only against a
    hand-maintained fixture, pinning writer/reader schema agreement by
    actual execution instead of two independently maintained copies.
    Some tests also classify the rows with author_outcome._classify_round,
    so they pin the reader-to-classifier hand-off as well."""

    SESSION_ID = "subprocess-integration-session"

    # Each test pins branch="main": a session-keyed ledger file only lands on the
    # default branch, so the branch must not depend on the host's init.defaultBranch.

    def _run_append(self, args: list[str], *, cwd: Path, home: Path) -> subprocess.CompletedProcess:
        env = {**os.environ, "HOME": str(home)}
        env.pop("CLAUDE_CONFIG_DIR", None)
        return subprocess.run(
            ["bash", str(_REVIEW_LEDGER_SH), "append", "code-review", *args],
            cwd=cwd, env=env, capture_output=True, text=True,
        )

    def _fake_transcript_path(self, home: Path) -> Path:
        # _read_ledger_row_entries_for_session only reads jsonl.stem (the
        # session id) and walks three parents up to the config-dir root -- see
        # _config_dir_root_for_session's own docstring for that resolution.
        # A placeholder transcript path with the right stem and depth under
        # $HOME/.claude is therefore enough.
        # The real ledger files are found under the config-dir root's own
        # review-narrative-ledger directory, not by this path itself.
        return home / ".claude" / "projects" / "-fake-project" / f"{self.SESSION_ID}.jsonl"

    def test_real_address_append_classifies_as_failure(self, tmp_path):
        home = tmp_path / "home"
        home.mkdir()
        repo = init_git_repo_with_commit(tmp_path / "repo", branch="main")
        _seed_session(home, self.SESSION_ID)

        result = self._run_append(
            [
                "--finding", "Missing error handling in foo()",
                "--disposition", "ADDRESS",
                "--rationale", "fixed inline",
                "--source", "foo.py:12",
                "--round", "1",
                "--reviewer", "staff-sdet",
                "--authoring-agent", "code-writer",
            ],
            cwd=repo, home=home,
        )
        assert result.returncode == 0, result.stderr

        jsonl = self._fake_transcript_path(home)
        entries, any_file_found = review_ledger._read_ledger_row_entries_for_session(jsonl)
        rows = [row for _file_index, row in entries]
        assert len(rows) == 1
        assert any_file_found is True
        data_quality = author_outcome.Counter({key: 0 for key in author_outcome._DATA_QUALITY_KEYS})
        (round_1_rows,) = author_outcome._round_blocks(entries)
        classification, matching = author_outcome._classify_round(round_1_rows, has_marker_write=False, data_quality=data_quality)
        assert classification == author_outcome._OUTCOME_FAILURE
        assert matching == rows

    def test_real_append_on_a_feature_branch_is_attributed_to_its_session_by_session_id(self, tmp_path):
        """On a feature branch review-ledger.sh writes a branch-keyed file,
        whose name carries no session id: the row's own session_id field is
        what attributes it."""
        home = tmp_path / "home"
        home.mkdir()
        repo = init_git_repo_with_commit(tmp_path / "repo", branch="main")
        subprocess.run(["git", "checkout", "-q", "-b", "feature"], cwd=repo, check=True)
        _seed_session(home, self.SESSION_ID)

        result = self._run_append(
            ["--finding", "Missing error handling in foo()", "--disposition", "ADDRESS",
             "--rationale", "fixed inline", "--source", "foo.py:12", "--round", "1", "--reviewer", "staff-sdet"],
            cwd=repo, home=home,
        )
        assert result.returncode == 0, result.stderr

        entries, any_file_found = review_ledger._read_ledger_row_entries_for_session(self._fake_transcript_path(home))
        assert [row["disposition"] for _file_index, row in entries] == ["ADDRESS"]
        assert entries[0][1]["session_id"] == self.SESSION_ID
        assert any_file_found is False, "the row lives in a branch-keyed file, not a session-keyed one"

    def test_real_round_cap_verdict_append_belongs_to_no_block(self, tmp_path):
        home = tmp_path / "home"
        home.mkdir()
        repo = init_git_repo_with_commit(tmp_path / "repo", branch="main")
        _seed_session(home, self.SESSION_ID)

        result = self._run_append(["--disposition", "CONSULT", "--rationale", "noise", "--round", "1"], cwd=repo, home=home)
        assert result.returncode == 0, result.stderr

        entries, any_file_found = review_ledger._read_ledger_row_entries_for_session(self._fake_transcript_path(home))
        assert [row["disposition"] for _file_index, row in entries] == ["CONSULT"]
        assert any_file_found is True
        assert author_outcome._round_blocks(entries) == []

    def test_real_clean_append_classifies_as_pass(self, tmp_path):
        home = tmp_path / "home"
        home.mkdir()
        repo = init_git_repo_with_commit(tmp_path / "repo", branch="main")
        _seed_session(home, self.SESSION_ID)

        result = self._run_append(["--disposition", "CLEAN", "--round", "1"], cwd=repo, home=home)
        assert result.returncode == 0, result.stderr

        jsonl = self._fake_transcript_path(home)
        entries, any_file_found = review_ledger._read_ledger_row_entries_for_session(jsonl)
        rows = [row for _file_index, row in entries]
        assert len(rows) == 1
        assert any_file_found is True
        data_quality = author_outcome.Counter({key: 0 for key in author_outcome._DATA_QUALITY_KEYS})
        (round_1_rows,) = author_outcome._round_blocks(entries)
        classification, _matching = author_outcome._classify_round(
            round_1_rows, has_marker_write=False, data_quality=data_quality,
        )
        assert classification == author_outcome._OUTCOME_PASS

    def test_real_engineer_settled_and_its_carry_classify_as_pass_rounds_and_count_as_settled(self, tmp_path):
        """The writer's SETTLED and carry rows reach the reader's round
        classification: each round is a PASS, and each counts under the
        settled-PASS data-quality key, the carry by its own disposition."""
        home = tmp_path / "home"
        home.mkdir()
        # The seed must be file.txt: the --source/--cited-line args cite file.txt:1, whose text is the content below.
        repo = init_git_repo_with_commit(tmp_path / "repo", branch="main", file_name="file.txt", content="first\n")
        _seed_session(home, self.SESSION_ID)
        settled = self._run_append(
            ["--finding", "Missing error handling in foo()", "--disposition", "SETTLED",
             "--rationale", "kept as written", "--decided-by", "engineer", "--engineer-quote", "keep it",
             "--carry-forward", "--source", "file.txt:1", "--round", "1", "--reviewer", "staff-sdet"],
            cwd=repo, home=home,
        )
        assert settled.returncode == 0, settled.stderr
        transcript = self._fake_transcript_path(home)
        decision_id = review_ledger._read_ledger_row_entries_for_session(transcript)[0][0][1]["id"]

        carry = self._run_append(
            ["--finding", "foo() still lacks error handling", "--disposition", "SETTLED",
             "--rationale", "same failure mode", "--decided-by", "carry", "--ref", decision_id,
             "--cited-line", "file.txt:1", "--source", "file.txt:1", "--round", "2", "--reviewer", "staff-sdet"],
            cwd=repo, home=home,
        )
        assert carry.returncode == 0, carry.stderr

        entries, _any_file_found = review_ledger._read_ledger_row_entries_for_session(transcript)
        rows = [row for _file_index, row in entries]
        assert [(row["decided_by"], row["ref"]) for row in rows] == [("engineer", ""), ("carry", decision_id)]
        data_quality = author_outcome.Counter({key: 0 for key in author_outcome._DATA_QUALITY_KEYS})
        classifications = [
            author_outcome._classify_round(round_rows, has_marker_write=False, data_quality=data_quality)[0]
            for round_rows in author_outcome._round_blocks(entries)
        ]
        assert classifications == [author_outcome._OUTCOME_PASS, author_outcome._OUTCOME_PASS]
        assert data_quality[author_outcome._DQ_SETTLED_PASS_ROUNDS] == 2


class TestLedgerIndex:
    """_LedgerIndex.refresh: cache invalidation and file selection."""

    def _index_over(self, config_dir_root: Path):
        return review_ledger._LedgerIndex(config_dir_root / "review-narrative-ledger")

    def test_a_file_whose_last_open_failed_is_retried_on_the_next_refresh(self, tmp_path, monkeypatch):
        _write_ledger_file(tmp_path, "sess-1", [_ledger_row(round=1, disposition="DEFER")])
        real_read = review_ledger._read_ledger_rows_from_file
        read_paths: list[Path] = []

        def _fails_on_first_read(ledger_path, **reader_options):
            read_paths.append(ledger_path)
            return ([], False) if len(read_paths) == 1 else real_read(ledger_path, **reader_options)

        monkeypatch.setattr(review_ledger, "_read_ledger_rows_from_file", _fails_on_first_read)
        index = self._index_over(tmp_path)

        index.refresh()
        assert index.entries_for_session("sess-1") == ([], False)
        index.refresh()

        entries, session_file_opened = index.entries_for_session("sess-1")
        assert len(read_paths) == 2, "the unchanged file must be re-read after a failed open"
        assert len(entries) == 1
        assert session_file_opened is True

    def test_a_non_string_event_time_does_not_abort_the_sort_and_sorts_before_the_dated_rows(self, tmp_path):
        """A number, list or boolean `event_time` (a foreign or hand-edited
        row) reads as "", like a missing one, so it sorts first in file order
        ahead of the string-timed rows instead of raising TypeError."""
        rows = [
            _ledger_row(round=1, disposition="DEFER", finding="late", event_time="2026-08-03T10:00:00Z"),
            _ledger_row(round=1, disposition="DEFER", finding="number", event_time=20260801),
            _ledger_row(round=1, disposition="DEFER", finding="early", event_time="2026-08-01T10:00:00Z"),
            _ledger_row(round=1, disposition="DEFER", finding="list", event_time=["2026-08-01"]),
            _ledger_row(round=1, disposition="DEFER", finding="bool", event_time=True),
        ]
        _write_ledger_file(tmp_path, "sess-1", rows)
        index = self._index_over(tmp_path)
        index.refresh()

        entries, _session_file_opened = index.entries_for_session("sess-1")

        assert [row["finding"] for _file_index, row in entries] == ["number", "list", "bool", "early", "late"]

    def test_a_file_removed_between_refreshes_drops_its_rows(self, tmp_path):
        ledger_path = _write_ledger_file(tmp_path, "sess-1", [_ledger_row(round=1, disposition="DEFER")])
        index = self._index_over(tmp_path)
        index.refresh()
        assert len(index.entries_for_session("sess-1")[0]) == 1

        ledger_path.unlink()
        index.refresh()

        assert index.entries_for_session("sess-1") == ([], False)

    def test_an_index_shared_across_lookups_sees_a_new_file_and_appended_rows_and_parses_an_unchanged_file_once(
        self, tmp_path, monkeypatch,
    ):
        ledger_dir = tmp_path / "review-narrative-ledger"
        ledger_dir.mkdir(parents=True)
        first_path = _write_ledger_file(tmp_path, "sess-1", [_ledger_row(round=1, disposition="ADDRESS")])
        jsonl = fake_transcript_path(tmp_path, "sess-1")
        real_read = review_ledger._read_ledger_rows_from_file
        parsed_paths = []

        def _counting_read(ledger_path, **reader_options):
            parsed_paths.append(ledger_path)
            return real_read(ledger_path, **reader_options)

        monkeypatch.setattr(review_ledger, "_read_ledger_rows_from_file", _counting_read)
        ledger_indexes = {}

        first_entries, _ = review_ledger._read_ledger_row_entries_for_session(jsonl, ledger_indexes)
        unchanged_entries, _ = review_ledger._read_ledger_row_entries_for_session(jsonl, ledger_indexes)
        assert parsed_paths == [first_path]
        assert len(unchanged_entries) == len(first_entries) == 1

        with first_path.open("a") as ledger_file:
            ledger_file.write(json.dumps(_ledger_row(round=2, disposition="DEFER")) + "\n")
        second_path = _write_branch_ledger_file(
            tmp_path, "b" * 64, [_ledger_row(round=3, disposition="DEFER", session_id="sess-1")],
        )
        grown_entries, _ = review_ledger._read_ledger_row_entries_for_session(jsonl, ledger_indexes)

        assert sorted(row["round"] for _file_index, row in grown_entries) == [1, 2, 3]
        assert sorted(parsed_paths, key=str) == sorted([first_path, first_path, second_path], key=str)

    @pytest.mark.parametrize(
        ("change_one_signature_half", "expected_rounds"),
        [
            pytest.param(_grow_keeping_mtime, [1, 2], id="grown-same-mtime"),
            pytest.param(_rewrite_at_same_size_with_newer_mtime, [7], id="same-size-newer-mtime"),
        ],
    )
    def test_a_changed_signature_half_alone_makes_the_index_re_read_the_file(
        self, tmp_path, change_one_signature_half, expected_rounds,
    ):
        first_path = _write_ledger_file(tmp_path, "sess-1", [_ledger_row(round=1, disposition="ADDRESS")])
        jsonl = fake_transcript_path(tmp_path, "sess-1")
        ledger_indexes = {}
        entries, _ = review_ledger._read_ledger_row_entries_for_session(jsonl, ledger_indexes)
        assert [row["round"] for _file_index, row in entries] == [1]
        before = first_path.stat()

        change_one_signature_half(first_path, before)
        entries, _ = review_ledger._read_ledger_row_entries_for_session(jsonl, ledger_indexes)

        assert sorted(row["round"] for _file_index, row in entries) == expected_rounds
