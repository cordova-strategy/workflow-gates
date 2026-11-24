# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/scope.py`); 1 carried an in-scope comment change: the new docstring on `_add_extra_config_dirs_arg` (line 719).

No comment-discipline concerns.

- The docstring is a pointer to `_SUBCOMMANDS_REFUSING_TOP_LEVEL_CONFIG_DIR`. That tuple (scope.py:694-708) holds the decision and its reason in the comment above it. The pointer exemption in the rule under test keeps it.
- It is a rule, not a claim, so False or unsourced claim does not apply. I checked it anyway. Every `scope._add_extra_config_dirs_arg(` caller is in `cost.py` (`cost`, `cost-trend`), `pr_cost_export.py` (`pr-cost-export`), or a module named for a tuple member. Each of those subcommands is in the tuple.
- It is one sentence, so the verbosity, multi-fact and readability angles do not apply. It uses no PR-defined labels and no "used to be" framing.
