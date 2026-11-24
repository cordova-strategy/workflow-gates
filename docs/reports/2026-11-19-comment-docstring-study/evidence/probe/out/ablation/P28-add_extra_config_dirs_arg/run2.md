# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/scope.py`); 1 carried an in-scope comment change (one added docstring clause).

## R1 [CONCERN] Prose restating the code

- **File:line:** `claude/.claude/scripts/transcript_analysis/scope.py:719`
- **Offending text:** `"""A subcommand calling this must also be in _SUBCOMMANDS_REFUSING_TOP_LEVEL_CONFIG_DIR."""`
- **Issue:** The docstring's only clause states a call-site-to-tuple membership relationship. Static analysis of this repository finds that relationship without the docstring:
  - Every caller of `_add_extra_config_dirs_arg` is in the tuple at `scope.py:702-708`. I grepped the callers in `cache_efficiency.py`, `cache_rebuild.py`, `context_composition.py`, `context_distribution.py`, `cost.py` (`cost` and `cost-trend`), `edit_format.py`, `instrument_authoring.py`, `plan_boundary.py`, `pr_cost.py`, `pr_cost_export.py`, `read_scope.py`, `rearm_backtest.py`, `subagent_mix.py` and `subagents.py`.
  - `test_transcript_cli.py:98` parametrizes over `scope._SUBCOMMANDS_REFUSING_TOP_LEVEL_CONFIG_DIR`.
  - The comment above the tuple (`scope.py:694-701`) already states why the members refuse the top-level flag.
- **Claim accuracy:** The clause is true at this diff's state, so there is no False-claim finding. The rule under test deletes a true clause that static analysis finds, so truth does not save it.
- **Production failure mode:** None at runtime. The clause is a third place that restates the tuple's membership contract, and it will drift if the tuple is renamed.
- **Required property:** Delete the docstring clause and leave the function with no docstring. The tuple and its leading comment stay the single home of the contract.
