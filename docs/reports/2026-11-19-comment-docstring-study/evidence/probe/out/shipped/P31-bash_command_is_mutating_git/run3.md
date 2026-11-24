# comment-discipline-reviewer

## R1 [CONCERN] Restating the code

- File: `claude/.claude/scripts/transcript_analysis/turn_shape.py:62-64`
- Text: `"""Return True iff any &&/;/|/||-chained segment of `command` invokes a mutating git subcommand (see _command_segment_is_mutating_git)."""`
- Issue: the function name `_bash_command_is_mutating_git`, its `any(_command_segment_is_mutating_git(segment) for segment in corpus.split_command_segments(command))` body, and the callee's own docstring already state this. The docstring adds no non-obvious fact, so it restates the code under §Durable text's "Don't restate the code".
- Accuracy check: the claim is true. `_SHELL_OPERATOR_TOKENS` at `corpus.py:254` is `{"&&", "||", ";", "|"}`, and `split_command_segments` at `corpus.py:257-282` splits on exactly those. This is not a False-claim finding.
- Required fix: delete the docstring. A shorter or corrected restatement would still restate. If a non-obvious fact belongs here, such as quoted operators not splitting segments, that fact lives in `corpus.split_command_segments`'s docstring and should stay there.
