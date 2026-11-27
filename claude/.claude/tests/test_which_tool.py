"""Contract tests for helpers.which_tool, on a controlled PATH so a host with `timeout` still reaches the `gtimeout` fallback."""
from __future__ import annotations

from pathlib import Path

import pytest
from helpers import which_tool


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
    for binary_name in binaries_on_path:
        binary = tmp_path / binary_name
        binary.write_text("#!/bin/sh\n")
        binary.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))

    assert which_tool("timeout") == (str(tmp_path / expected_binary) if expected_binary else None)
