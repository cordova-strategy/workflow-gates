"""PATH is controlled so a host with `timeout` still exercises the `gtimeout` fallback."""
from __future__ import annotations

from pathlib import Path

import pytest
from helpers import which_tool


def _set_path_to_only(bin_dir: Path, monkeypatch: pytest.MonkeyPatch, binary_names: list[str]) -> None:
    for binary_name in binary_names:
        binary = bin_dir / binary_name
        binary.write_text("#!/bin/sh\n")
        binary.chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_dir))


@pytest.mark.parametrize(
    ("binaries_on_path", "expected_binary"),
    [
        pytest.param(["gtimeout"], "gtimeout", id="only-gtimeout-resolves-to-gtimeout"),
        pytest.param(["timeout", "gtimeout"], "timeout", id="both-resolves-to-timeout"),
        pytest.param([], None, id="neither-resolves-to-none"),
    ],
)
def test_which_tool_resolves_timeout_in_probe_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    binaries_on_path: list[str],
    expected_binary: str | None,
) -> None:
    _set_path_to_only(tmp_path, monkeypatch, binaries_on_path)

    assert which_tool("timeout") == (str(tmp_path / expected_binary) if expected_binary else None)


def test_which_tool_resolves_other_absent_name_to_none_beside_capping_binaries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_path_to_only(tmp_path, monkeypatch, ["timeout", "gtimeout"])

    assert which_tool("cp") is None
