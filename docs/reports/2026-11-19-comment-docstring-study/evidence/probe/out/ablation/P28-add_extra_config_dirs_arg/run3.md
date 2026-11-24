# comment-discipline-reviewer

## R1 [CONCERN] Prose restating the code

- **File:line:** claude/.claude/scripts/transcript_analysis/scope.py:719 (added docstring)
- **Issue:** `"""A subcommand calling this must also be in _SUBCOMMANDS_REFUSING_TOP_LEVEL_CONFIG_DIR."""` is the function's only docstring clause. It states a coupling between the helper's callers and the `_SUBCOMMANDS_REFUSING_TOP_LEVEL_CONFIG_DIR` membership. Static analysis of this repository finds that coupling: grepping the call sites and the tuple, and the parametrized test in `claude/.claude/scripts/tests/test_transcript_cli.py` (around lines 98 and 160) that iterates `scope._SUBCOMMANDS_REFUSING_TOP_LEVEL_CONFIG_DIR`. It names no reason, and no outside constraint forces it. It also doesn't qualify for the pointer exemption, because it gives a rule about membership and doesn't point to a doc or symbol that holds a decision.
- **Production failure mode:** None at runtime. The clause adds maintenance surface and drifts if the tuple is renamed.
- **Required property:** Delete the docstring. If the coupling needs enforcing, a test over the call sites does that, not prose. If a non-obvious reason exists for why such subcommands must refuse the top-level flag, state that reason at the tuple's definition, where the decision lives.
