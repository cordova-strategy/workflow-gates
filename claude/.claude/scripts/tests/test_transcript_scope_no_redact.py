"""The shared --no-redact refusal: scope.resolve_redaction, scope._refuse_no_redact_above_one_root, and the
backstops in resolve_scan_roots and _resolve_cost_roots."""
import argparse
from pathlib import Path

import pytest
from transcript_analysis import scope

from .conftest import _two_declared_roots

SUBCOMMAND = "synthetic-subcommand"
REFUSAL_LINE = f"{SUBCOMMAND}: --no-redact is refused when more than one root is in scope; drop --no-redact\n"
ONE_ROOT = [Path("/synthetic/acct-a/projects")]
TWO_ROOTS = [Path("/synthetic/acct-a/projects"), Path("/synthetic/acct-b/projects")]


def _args(**overrides) -> argparse.Namespace:
    return argparse.Namespace(**overrides)


class TestResolveRedaction:
    def test_returns_false_at_one_root_with_the_flag(self):
        assert scope.resolve_redaction(_args(no_redact=True), ONE_ROOT, SUBCOMMAND) is False

    @pytest.mark.parametrize("args", [_args(no_redact=False), _args()], ids=["flag-unset", "no-such-attribute"])
    def test_returns_true_at_two_roots_without_the_flag(self, args):
        assert scope.resolve_redaction(args, TWO_ROOTS, SUBCOMMAND) is True

    def test_exits_2_with_the_line_on_stderr_alone_at_two_roots_with_the_flag(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            scope.resolve_redaction(_args(no_redact=True), TWO_ROOTS, SUBCOMMAND)

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert captured.err == REFUSAL_LINE
        assert captured.out == ""


class TestResolversBackstopTheRefusal:
    def test_resolve_scan_roots_refuses_two_roots_with_the_flag_naming_the_parsed_subcommand(
        self, tmp_path, monkeypatch, capsys,
    ):
        _two_declared_roots(tmp_path, monkeypatch)

        with pytest.raises(SystemExit) as exc_info:
            scope.resolve_scan_roots(_args(no_redact=True, subcommand=SUBCOMMAND))

        assert exc_info.value.code == 2
        assert capsys.readouterr().err == REFUSAL_LINE

    def test_resolve_scan_roots_labels_the_refusal_with_the_tool_name_when_no_subcommand_is_parsed(
        self, tmp_path, monkeypatch, capsys,
    ):
        _two_declared_roots(tmp_path, monkeypatch)

        with pytest.raises(SystemExit):
            scope.resolve_scan_roots(_args(no_redact=True))

        assert capsys.readouterr().err.startswith("transcript-analysis: --no-redact is refused")

    def test_resolve_scan_roots_passes_a_namespace_with_no_no_redact_attribute(self, tmp_path, monkeypatch):
        expected_roots = _two_declared_roots(tmp_path, monkeypatch)

        assert scope.resolve_scan_roots(_args(subcommand=SUBCOMMAND)) == expected_roots

    def test_resolve_scan_roots_keeps_one_root_with_the_flag_when_the_active_account_alone_is_read(
        self, tmp_path, monkeypatch,
    ):
        active_root = _two_declared_roots(tmp_path, monkeypatch)[0]

        roots = scope.resolve_scan_roots(_args(no_redact=True, subcommand=SUBCOMMAND), active_account_only=True)

        assert roots == [active_root]

    def test_resolve_cost_roots_refuses_two_roots_with_the_flag(self, tmp_path, monkeypatch, capsys):
        _two_declared_roots(tmp_path, monkeypatch)

        with pytest.raises(SystemExit) as exc_info:
            scope._resolve_cost_roots(_args(no_redact=True), subcommand=SUBCOMMAND)

        assert exc_info.value.code == 2
        assert capsys.readouterr().err == REFUSAL_LINE

    def test_resolve_cost_roots_passes_a_namespace_with_no_no_redact_attribute(self, tmp_path, monkeypatch):
        expected_roots = _two_declared_roots(tmp_path, monkeypatch)

        assert scope._resolve_cost_roots(_args(), subcommand=SUBCOMMAND) == expected_roots


class TestOneResolvedRootAllowsTheFlag:
    """Dedup by resolved path precedes the refusal, so a declared-roots file naming the active account is one root."""

    @pytest.fixture(params=["names-the-active-root", "names-a-symlink-alias-of-the-active-root"])
    def active_root_declared_by_the_roots_file(self, request, tmp_path, monkeypatch) -> Path:
        active_account = tmp_path / "acct-a"
        (active_account / "projects").mkdir(parents=True)
        declared_entry = active_account
        if request.param == "names-a-symlink-alias-of-the-active-root":
            declared_entry = tmp_path / "acct-a-alias"
            declared_entry.symlink_to(active_account, target_is_directory=True)
        roots_file = tmp_path / "roots"
        roots_file.write_text(f"{declared_entry}\n")
        monkeypatch.setattr(scope, "PROJECTS_DIR", active_account / "projects")
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(active_account))
        monkeypatch.setenv("TRANSCRIPT_CONFIG_DIRS_FILE", str(roots_file))
        # Control: the roots file yields an entry that resolves to the active root, so the dedup has two candidates.
        assert [entry.resolve() for entry in scope.declared_transcript_roots()] == [active_account.resolve()]
        return active_account / "projects"

    def test_resolve_scan_roots_keeps_one_root_and_returns_with_the_flag(self, active_root_declared_by_the_roots_file):
        roots = scope.resolve_scan_roots(_args(no_redact=True, subcommand=SUBCOMMAND))

        assert roots == [active_root_declared_by_the_roots_file]

    def test_resolve_cost_roots_keeps_one_root_and_returns_with_the_flag(self, active_root_declared_by_the_roots_file):
        roots = scope._resolve_cost_roots(_args(no_redact=True), subcommand=SUBCOMMAND)

        assert roots == [active_root_declared_by_the_roots_file]

    @pytest.mark.parametrize("extra_entry", ["the-active-root", "a-symlink-alias-of-the-active-root"])
    def test_resolve_cost_roots_keeps_one_root_and_returns_with_the_flag_when_a_config_dir_extra_names_the_active_root(
        self, extra_entry, tmp_path, monkeypatch,
    ):
        active_account = tmp_path / "acct-a"
        (active_account / "projects").mkdir(parents=True)
        extra_config_dir = active_account
        if extra_entry == "a-symlink-alias-of-the-active-root":
            extra_config_dir = tmp_path / "acct-a-alias"
            extra_config_dir.symlink_to(active_account, target_is_directory=True)
        empty_roots_file = tmp_path / "roots"
        empty_roots_file.write_text("")
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(active_account))
        monkeypatch.setenv("TRANSCRIPT_CONFIG_DIRS_FILE", str(empty_roots_file))
        # Control: the extra passes the is_dir and projects/ checks and resolves to the active root.
        assert extra_config_dir.is_dir()
        assert (extra_config_dir / "projects").is_dir()
        assert extra_config_dir.resolve() == active_account.resolve()

        roots = scope._resolve_cost_roots(
            _args(no_redact=True, extra_config_dirs=[str(extra_config_dir)]), subcommand=SUBCOMMAND,
        )

        assert roots == [active_account / "projects"]

    def test_resolve_scan_roots_keeps_the_one_top_level_config_dir_root_with_the_flag_despite_declared_roots(
        self, tmp_path, monkeypatch,
    ):
        _two_declared_roots(tmp_path, monkeypatch)
        named_account = tmp_path / "acct-c"
        (named_account / "projects").mkdir(parents=True)

        roots = scope.resolve_scan_roots(_args(no_redact=True, subcommand=SUBCOMMAND, config_dir=str(named_account)))

        assert roots == [named_account / "projects"]
