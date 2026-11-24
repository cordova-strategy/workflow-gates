"""Tests for the `no_retry_reasons` a timed-out run is judged by. `test_replay_bench_smoke.py` covers `smoke`'s own use of
it. No test launches `claude`.
"""
from __future__ import annotations

import pytest
from replay_bench import arms, attempt
from replay_bench.runner import execute_run
from review_bench import runner as review_runner
from test_replay_bench_campaign import CampaignEnv
from test_replay_bench_runner_support import Scenario, build_replay_world, make_block, make_settings, spend_lines


@pytest.fixture
def campaign_env(tmp_path, monkeypatch):
    return CampaignEnv(build_replay_world(tmp_path, monkeypatch, task_count=1), monkeypatch)


class TestATimedOutAttempt:
    def test_a_campaign_retries_it_once(self, campaign_env):
        """`run_campaign` builds its own `RunSettings`, so this guards the set it passes."""
        launch_stub = campaign_env.world.launch(lambda _attempt_number, _agent_name: Scenario(timed_out=True, cost=None))

        campaign_env.run(launch_stub, arm_names=(arms.TOOLKIT.name,))

        assert len(launch_stub.calls) == 2

    def test_settings_that_list_a_timeout_as_no_retry_stop_after_one_attempt(self, world):
        no_retry_reasons = attempt.NO_RETRY_REASONS | {review_runner.MISSING_REASON_TIMEOUT}

        launch_stub = world.launch(lambda _attempt_number, _agent_name: Scenario(timed_out=True, cost=None))
        settings = make_settings(world, launch_stub, no_retry_reasons=no_retry_reasons)

        outcome = execute_run(settings, make_block(world), arms.BARE.name, 0)

        assert (outcome.record.missing_reason, outcome.record.attempts) == (review_runner.MISSING_REASON_TIMEOUT, 1)
        assert len(launch_stub.calls) == 1
        assert len(spend_lines(settings)) == 1
