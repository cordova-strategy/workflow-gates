# comment-discipline-reviewer

## R1 [CONCERN] Restating the code
File: claude/.claude/scripts/transcript_analysis/turn_shape.py:62-64

Offending text: `"""Return True iff any &&/;/|/||-chained segment of `command` invokes a mutating git subcommand (see _command_segment_is_mutating_git)."""`

Issue: The docstring describes what the function already shows. The body is `any(_command_segment_is_mutating_git(segment) for segment in corpus.split_command_segments(command))`, and the name and signature say the same. The operator list repeats `_SHELL_OPERATOR_TOKENS` in `corpus.py:254`. The docstring states no design decision and no reason static analysis can't find. A shorter or corrected version would still restate.

Production failure mode: none at runtime. The operator list is a second copy of `_SHELL_OPERATOR_TOKENS` and can drift from it.

Required property: Delete the docstring. The "check every segment, not just the first" decision is kept by `test_mutating_git_only_in_later_chained_segment_still_classifies_as_mutating`, and `_command_segment_is_mutating_git`'s docstring (turn_shape.py:41-47) already holds the per-segment contract. The "see _command_segment_is_mutating_git" pointer adds nothing, because the call is visible in the body.
