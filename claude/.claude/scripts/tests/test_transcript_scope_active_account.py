"""The scope helpers that let a narrowed command read the active account alone: _narrows_to_active_account,
resolve_scan_roots's active_account_only keyword, the one-root header clause, and _add_all_accounts_arg."""
import argparse

import pytest
from transcript_analysis import scope

from ._account_scope_helpers import ACTIVE_ACCOUNT_CLAUSE
from .conftest import _two_declared_roots


def _narrowing_args(**overrides) -> argparse.Namespace:
    """A namespace with none of the three scope-widening controls set; each override names one that is."""
    values = {"this_repo": False, "all_accounts": False, "config_dir": None}
    values.update(overrides)
    return argparse.Namespace(**values)


class TestNarrowsToActiveAccount:
    def test_true_when_no_widening_control_is_set(self):
        assert scope._narrows_to_active_account(_narrowing_args()) is True

    @pytest.mark.parametrize("overrides", [
        {"this_repo": True},
        {"all_accounts": True},
        {"config_dir": "/some/account"},
    ])
    def test_false_when_any_widening_control_is_set(self, overrides):
        assert scope._narrows_to_active_account(_narrowing_args(**overrides)) is False

    def test_true_for_a_hand_built_namespace_without_the_attributes(self):
        assert scope._narrows_to_active_account(argparse.Namespace()) is True


class TestResolveScanRootsActiveAccountOnly:
    def test_keyword_returns_the_active_root_alone_without_reading_the_declared_roots_file(
        self, tmp_path, monkeypatch,
    ):
        active_root, _declared_root = _two_declared_roots(tmp_path, monkeypatch)

        def _fail_if_read():
            raise AssertionError("declared_transcript_roots must not be read under active_account_only")

        monkeypatch.setattr(scope, "declared_transcript_roots", _fail_if_read)
        assert scope.resolve_scan_roots(_narrowing_args(), active_account_only=True) == [active_root]

    def test_top_level_config_dir_wins_over_the_keyword(self, tmp_path, monkeypatch):
        _two_declared_roots(tmp_path, monkeypatch)
        named_account = tmp_path / "named-account"
        parsed = _narrowing_args(config_dir=str(named_account))
        assert scope.resolve_scan_roots(parsed, active_account_only=True) == [named_account / "projects"]


class TestRootCountDescActiveAccountOnly:
    def test_names_the_active_account_clause_for_a_roots_file_listing_a_root(self, tmp_path, monkeypatch):
        (active_root, _declared_root) = _two_declared_roots(tmp_path, monkeypatch)
        assert scope._root_count_desc([active_root], active_account_only=True) == ACTIVE_ACCOUNT_CLAUSE

    def test_names_the_active_account_clause_for_an_empty_roots_file(self, tmp_path, monkeypatch):
        roots_file = tmp_path / "roots"
        roots_file.write_text("")
        monkeypatch.setenv("TRANSCRIPT_CONFIG_DIRS_FILE", str(roots_file))
        assert scope._root_count_desc([tmp_path / "acct-a" / "projects"], active_account_only=True) == (
            ACTIVE_ACCOUNT_CLAUSE
        )

    def test_absent_roots_file_wording_is_unchanged_under_the_keyword(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TRANSCRIPT_CONFIG_DIRS_FILE", str(tmp_path / "does-not-exist"))
        assert scope._root_count_desc([tmp_path / "acct-a" / "projects"], active_account_only=True) == (
            "1 root (no ~/.claude/transcript-config-dirs declared)"
        )

    def test_unreadable_roots_file_wording_is_unchanged_under_the_keyword(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TRANSCRIPT_CONFIG_DIRS_FILE", str(tmp_path / "roots"))
        monkeypatch.setattr(scope, "declared_roots_file_state", lambda: "unreadable")
        assert scope._root_count_desc([tmp_path / "acct-a" / "projects"], active_account_only=True) == (
            "1 root (~/.claude/transcript-config-dirs present but unreadable)"
        )

    def test_two_roots_still_read_two_roots_under_the_keyword(self, tmp_path, monkeypatch):
        roots = _two_declared_roots(tmp_path, monkeypatch)
        assert scope._root_count_desc(roots, active_account_only=True) == "2 roots"

    def test_the_scope_header_helpers_pass_the_keyword_through(self, tmp_path, monkeypatch):
        (active_root, _declared_root) = _two_declared_roots(tmp_path, monkeypatch)
        header = scope._resolved_scope_header("buckets", "*", [active_root], active_account_only=True)
        assert header == f"BUCKETS SOURCES (*; {ACTIVE_ACCOUNT_CLAUSE})"

    def test_print_resolved_scope_passes_the_keyword_through(self, tmp_path, monkeypatch, capsys):
        (active_root, _declared_root) = _two_declared_roots(tmp_path, monkeypatch)
        scope.print_resolved_scope("buckets", "*", [active_root], active_account_only=True)
        assert capsys.readouterr().out == f"BUCKETS SOURCES (*; {ACTIVE_ACCOUNT_CLAUSE})\n"


class TestAddAllAccountsArg:
    @staticmethod
    def _parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser()
        scope._add_project_scope_args(parser)
        scope._add_all_accounts_arg(parser)
        return parser

    def test_flag_present_parses_to_true(self):
        assert self._parser().parse_args(["--all-accounts"]).all_accounts is True

    def test_flag_absent_parses_to_false(self):
        assert self._parser().parse_args([]).all_accounts is False

    def test_flag_beside_this_repo_raises_no_mutual_exclusion_error(self):
        parsed = self._parser().parse_args(["--all-accounts", "--this-repo"])
        assert parsed.all_accounts is True
        assert parsed.this_repo is True

    def test_flag_beside_a_projects_glob_raises_no_mutual_exclusion_error(self):
        parsed = self._parser().parse_args(["--all-accounts", "--projects", "repo-*"])
        assert parsed.all_accounts is True
        assert parsed.projects == "repo-*"
