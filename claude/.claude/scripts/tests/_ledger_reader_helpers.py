"""Ledger lines that make json.loads raise past a decode error, shared by the tests of the ledger reader."""
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
