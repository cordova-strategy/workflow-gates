# comment-discipline-reviewer

Scope: 1 file in the diff (`scope.py`), 1 added docstring in scope. The `system-reminder` rules file on Python environments is unrelated to this review and was not applied.

Verified before judging:
- The claim is true. All 16 `scope._add_extra_config_dirs_arg(` call sites (`cost.py:1267` as `cost`, `cost.py:1324` as `cost-trend`, plus cache_efficiency, cache_rebuild, context_composition, context_distribution, edit_format, instrument_authoring, plan_boundary, pr_cost, pr_cost_export, read_scope, rearm_backtest, subagent_mix, subagents) register subcommands that appear in `_SUBCOMMANDS_REFUSING_TOP_LEVEL_CONFIG_DIR` (`scope.py:702-708`). No false-claim finding.
- The reverse does not hold, and the docstring does not claim it: `cost-counts`, `period-cost`, `review-cost-by-size` and `read-cost` are in the tuple without calling the helper (`scope.py:698-701`).

## R1 [FYI] Restating the code

`scope.py:719`

Text: `"""A subcommand calling this must also be in _SUBCOMMANDS_REFUSING_TOP_LEVEL_CONFIG_DIR."""`

Issue: Under the session's "Don't restate the code" rule, the docstring states a coupling that tests already enforce. `test_transcript_cli.py:195-201` (`test_subcommands_registering_their_own_config_dir_are_exactly_the_expected_set`) asserts that the set of subparsers registering `extra_config_dirs` equals the tuple minus the four non-registrants. Grepping the call sites also shows the coupling. The docstring gives no reason itself.

Why it still might stay: it names `_SUBCOMMANDS_REFUSING_TOP_LEVEL_CONFIG_DIR`, whose comment (`scope.py:694-701`) holds the reason, and the rule keeps a decision that carries a pointer to its reason. This is a judgement call, so it is FYI and not a blocker.

Required property: pick one.
- Keep it, and make the decision and its reason explicit in one sentence. For example: "Register `--config-dir` only on subcommands in `_SUBCOMMANDS_REFUSING_TOP_LEVEL_CONFIG_DIR`, so the top-level flag cannot validate against a different account (reason in the comment above that tuple)."
- Or delete it, since the test already fails on a mismatch and the tuple's own comment holds the reason.

No other angle applies: there is no PR-defined terminology and no "used to be" framing, and the docstring is one sentence.
