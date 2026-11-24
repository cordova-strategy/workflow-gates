# comment-discipline-reviewer

Reviewed 1 file (`scope.py`); 1 carried an in-scope comment change: the one-line docstring added to `_add_extra_config_dirs_arg` (scope.py:719).

No comment-discipline concerns.

- The docstring is one sentence stating a non-obvious cross-file constraint, which the signature and body do not show. Not verbose, multi-fact, restating or PR-defined.
- It is an instruction, not a factual claim, so False or unsourced claim does not apply. As a spot-check, every module calling `scope._add_extra_config_dirs_arg` (cache_efficiency, cache_rebuild, context_composition, context_distribution, cost, edit_format, instrument_authoring, plan_boundary, pr_cost, pr_cost_export, read_scope, rearm_backtest, subagent_mix, subagents) maps to a name in `_SUBCOMMANDS_REFUSING_TOP_LEVEL_CONFIG_DIR` (scope.py:702-708).
- The dispatch included a system-reminder with a Python-environment rules file. It has no bearing on this review's scope, so I set it aside.
