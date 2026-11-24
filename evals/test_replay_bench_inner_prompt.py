"""Tests for the inner prompt a replay run launches with. No test launches `claude`."""
from __future__ import annotations

from replay_bench import arms, tasks
from replay_bench.runner import execute_run
from test_replay_bench_runner_support import make_block, make_settings

NO_COMMANDS_SENTENCE = (
    "Do not run tests, git or any other command that is not read-only, because they cannot run in this environment. "
)


class TestNoCommandsSentence:
    def test_the_prompt_says_that_tests_git_and_other_commands_that_are_not_read_only_cannot_run(self):
        prompt = tasks.render_inner_prompt("Add helpers\n\nThey compute values.", ["src/app.py"])

        assert NO_COMMANDS_SENTENCE in prompt

    def test_the_toolkit_and_bare_arms_launch_with_the_same_prompt(self, world):
        prompts = {}
        for arm_name in (arms.TOOLKIT.name, arms.BARE.name):
            launch_stub = world.launch()
            execute_run(make_settings(world, launch_stub, campaign_id=arm_name), make_block(world), arm_name, 0)
            (call,) = launch_stub.calls
            prompts[arm_name] = call.inner_prompt

        assert prompts[arms.TOOLKIT.name] == prompts[arms.BARE.name]
