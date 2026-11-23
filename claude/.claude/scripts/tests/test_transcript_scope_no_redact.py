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
