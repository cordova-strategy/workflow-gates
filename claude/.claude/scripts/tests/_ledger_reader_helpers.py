"""Fixtures shared by the tests of the ledger reader: lines that make json.loads raise past a decode error, and a
placeholder transcript path."""
from pathlib import Path

import pytest

OVER_LIMIT_INTEGER_LINE = '{"id": ' + "1" * 5000 + "}"
# Nested far past any interpreter's recursion limit, so no stack size or version change makes this line parse.
DEEPLY_NESTED_LINE = "[" * 3_000_000 + "]" * 3_000_000
_CASES = [
    ("deeply-nested", DEEPLY_NESTED_LINE, RecursionError),
    ("integer-over-the-digit-limit", OVER_LIMIT_INTEGER_LINE, ValueError),
]
LINES_OVER_DECODER_LIMITS = [pytest.param(line, error, id=case_id) for case_id, line, error in _CASES]
HOSTILE_LINES = [pytest.param(line, id=case_id) for case_id, line, _ in _CASES]


def fake_transcript_path(config_dir_root: Path, session_id: str) -> Path:
    """A placeholder transcript path: the ledger lookup reads only its stem
    (the session id) and walks three parents up to the config-dir root."""
    jsonl = config_dir_root / "projects" / "-home-user-testrepo" / f"{session_id}.jsonl"
    jsonl.parent.mkdir(parents=True, exist_ok=True)
    jsonl.write_text("")
    return jsonl
