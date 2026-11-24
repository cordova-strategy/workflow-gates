"""Tests for how a gate-denied call counts in reviewer-reads main-thread round windows."""
import pytest
from transcript_analysis import reviewer_reads

from ._reviewer_reads_helpers import _SINCE_TS, _UNTIL_EPOCH, _next_prompt, _reviewer_turn
from ._routing_guard_helpers import _routing_deny_record
from .conftest import _agent_use, _skill_block


class TestGateDeniedCallRoundWindows:
    @pytest.mark.parametrize("denial_shape", [
        pytest.param("legacy", id="a-hook-blocking-error-attachment"),
        pytest.param("current", id="an-errored-tool-result"),
    ])
    def test_a_gate_denied_skill_call_before_a_launched_spawn_opens_no_window_of_its_own(self, denial_shape):
        records = [
            _reviewer_turn("denied", [_skill_block("denied-skill", "plan-review")]),
            _routing_deny_record("denied-skill", shape=denial_shape),
            _reviewer_turn("launched", [_agent_use("launched-spawn", "review-orchestrator")]),
            _next_prompt(),
        ]
        totals = reviewer_reads._Totals()

        reviewer_reads._accumulate_round_reads(
            totals, reviewer_reads._usable_records(records), [], _SINCE_TS, _UNTIL_EPOCH,
        )

        assert totals.rounds["plan-review"].windows == 0
        assert totals.rounds["code-review"].windows == 1
