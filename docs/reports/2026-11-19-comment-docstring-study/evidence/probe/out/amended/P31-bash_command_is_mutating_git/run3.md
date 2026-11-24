# comment-discipline-reviewer

## R1 [CONCERN] Restating the code

File: claude/.claude/scripts/transcript_analysis/turn_shape.py:62-64 (the new docstring on `_bash_command_is_mutating_git`)

Issue: The docstring reads "Return True iff any &&/;/|/||-chained segment of `command` invokes a mutating git subcommand (see _command_segment_is_mutating_git)." It states no design decision and no reason static analysis can't find. Every clause is visible in the body, which is `any(_command_segment_is_mutating_git(segment) for segment in corpus.split_command_segments(command))`:
- "Return True iff any ... segment" restates the `any(...)` and the `-> bool` signature.
- The operator list `&&/;/|/||` restates `corpus.split_command_segments` (corpus.py:257-282, `_SHELL_OPERATOR_TOKENS`). That list is a second copy of knowledge with its own home, so it can drift.
- "mutating git subcommand" restates the callee's name.
- The "see _command_segment_is_mutating_git" pointer leads to no kept decision. The pointer rule keeps a pointer to a symbol that holds a decision. The callee's own docstring (turn_shape.py:41-47) describes mechanics, so the pointer adds nothing the call expression doesn't already show.

Failure mode: The operator list goes stale if `_SHELL_OPERATOR_TOKENS` changes, and the docstring then misstates behavior. The two-line docstring on a one-expression wrapper also adds noise.

Required property: Delete the docstring. A shorter or corrected version would still restate the code. Keep a comment only if a non-obvious decision exists, such as why chained segments are scanned with `any` rather than only the first segment. State that reason alone, and only if a reason exists that static analysis can't find.
