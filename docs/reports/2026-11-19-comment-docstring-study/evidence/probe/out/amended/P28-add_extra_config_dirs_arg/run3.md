# comment-discipline-reviewer

No findings. The only change is one new docstring on `_add_extra_config_dirs_arg` (`scope.py:719`): "A subcommand calling this must also be in _SUBCOMMANDS_REFUSING_TOP_LEVEL_CONFIG_DIR."

- **Restating the code:** it is not a restatement. Nothing at the call sites shows the coupling. The helper's body registers `--config-dir`, and the tuple is consulted in `cli.py:179`. The reason sits in the comment above the tuple (`scope.py:694-701`): the top-level `--config-dir` must never validate against a different account than the one the subcommand resolves. The docstring points at that symbol, and a pointer to the symbol holding a decision stays.
- **Unsourced or false claim:** the sentence is a rule, not a factual claim. I also checked it against the code. The 15 callers of the helper (cache-efficiency, cache-rebuild, context-composition, context-distribution, cost, cost-trend, edit-format, instrument-authoring, plan-boundary, pr-cost, pr-cost-export, read-scope, rearm-backtest, subagent-mix, subagents) all have their names in the tuple at `scope.py:702-708`.
- **Verbosity, multi-fact, readability, PR-defined terms, "used to be", wrong altitude:** none apply. It is a single instruction sentence with no PR-narrative labels.

One loaded system reminder, the Python environment conventions rule file, does not touch this diff, so I set it aside.

**No comment-discipline concerns**
