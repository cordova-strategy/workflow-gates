# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/scope.py`); 1 carried an in-scope comment change (the new docstring at line 719).

Set aside: the system-reminder's `python-environment-conventions.md` text. It governs Python installs and has no bearing on this review.

## R1 [FYI] Restating the code (decision kept, reason pointer missing)

scope.py:719

Text: `"""A subcommand calling this must also be in _SUBCOMMANDS_REFUSING_TOP_LEVEL_CONFIG_DIR."""`

Issue:
- The docstring states a real design decision, not a restatement. Nothing in the helper's body shows that registering `--config-dir` couples to a tuple in the same module, and `cli.py:179` enforces that coupling from another file.
- The sentence gives no reason and no pointer to one.
- The rule under test says that when no reason is stated, the decision is kept with a pointer to where its reason lives.
- The reason lives in the comment above the tuple (scope.py:694-697) and in `cli.py:170-178`. A top-level `--config-dir` would validate a different account than the one the subcommand scans.

Claim check, no finding: the sentence is a rule, not a claim. It is also consistent with the code. All 16 `scope._add_extra_config_dirs_arg(` call sites are in subcommands the tuple lists:
- The 15 callers are in `cache_efficiency`, `cache_rebuild`, `context_composition`, `context_distribution`, `cost` (two calls, so `cost` and `cost-trend`), `edit_format`, `instrument_authoring`, `plan_boundary`, `pr_cost`, `pr_cost_export`, `read_scope`, `rearm_backtest`, `subagent_mix` and `subagents`.
- Every one of those names appears in the tuple at scope.py:702-708.

Required property: the docstring keeps the decision and points to where its reason lives.

Concrete fix: `"""A subcommand calling this must also be in _SUBCOMMANDS_REFUSING_TOP_LEVEL_CONFIG_DIR; the comment above that tuple gives why."""`

Not flagged: the one-sentence length, the absence of PR-defined labels or prior-version framing, and the survives-the-PR self-test, which it passes.
