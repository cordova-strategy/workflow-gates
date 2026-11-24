# comment-discipline-reviewer

Scope: 1 file in the diff, 1 carrying an in-scope comment change (`claude/.claude/scripts/transcript_analysis/turn_shape.py`).

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/turn_shape.py:62-64`

Issue: the new docstring on `_bash_command_is_mutating_git` reads "Return True iff any &&/;/|/||-chained segment of `command` invokes a mutating git subcommand (see _command_segment_is_mutating_git)." Everything in it is already visible in the code:
- The function name says it checks whether a Bash command is a mutating git command.
- The body is `any(_command_segment_is_mutating_git(segment) for segment in corpus.split_command_segments(command))`, which shows the per-segment check.
- The `bool` return type shows the return value.

Production failure mode: the operator list `&&/;/|/||` is a second copy of `_SHELL_OPERATOR_TOKENS` (`corpus.py:254`) and of the `split_command_segments` docstring (`corpus.py:258`). If the operator set changes, this copy goes stale. I checked it against the current set `{"&&", "||", ";", "|"}`, so today it is accurate and is not a false claim.

Required property: delete the docstring. It states nothing non-obvious, and a shorter or corrected version would still restate the code. The segment semantics already live in the `_command_segment_is_mutating_git` docstring (`turn_shape.py:41-47`) and the `split_command_segments` docstring.
