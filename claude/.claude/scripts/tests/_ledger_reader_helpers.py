"""Ledger lines that make json.loads raise past a decode error, shared by the tests of the ledger reader."""
import pytest

OVER_LIMIT_INTEGER_LINE = '{"id": ' + "1" * 5000 + "}"
# 3,000,000 brackets nest well past the decoder's stack: 200,000 already raise RecursionError on CPython 3.14.
DEEPLY_NESTED_LINE = "[" * 3_000_000 + "]" * 3_000_000
LINES_OVER_DECODER_LIMITS = [
    pytest.param(DEEPLY_NESTED_LINE, RecursionError, id="deeply-nested"),
    pytest.param(OVER_LIMIT_INTEGER_LINE, ValueError, id="integer-over-the-digit-limit"),
]
HOSTILE_LINES = [
    pytest.param(DEEPLY_NESTED_LINE, id="deeply-nested"),
    pytest.param(OVER_LIMIT_INTEGER_LINE, id="integer-over-the-digit-limit"),
]
