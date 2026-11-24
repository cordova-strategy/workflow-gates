# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/turn_shape.py`); 1 carried an in-scope comment change (one added docstring).

Set aside: the `/home/<username>/MyCode/claude-config/.../python-environment-conventions.md` system reminder, which is loaded configuration about Python installs and does not widen or narrow this review's scope.

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/turn_shape.py:62-64`

Issue: The added docstring reads "Return True iff any &&/;/|/||-chained segment of `command` invokes a mutating git subcommand (see _command_segment_is_mutating_git)." The body is `any(_command_segment_is_mutating_git(segment) for segment in corpus.split_command_segments(command))`. The function name, the `-> bool` signature, the `any(...)` and the callee names already show every part of that sentence. The operator list repeats `_SHELL_OPERATOR_TOKENS` in `corpus.py:254`, so it is also a second copy of a fact with a canonical home.

Production failure mode: The operator list can drift from `_SHELL_OPERATOR_TOKENS`. It is also overbroad. `split_command_segments` (`corpus.py:267-282`) calls plain `shlex.split` and splits only on bare operator tokens, so an unspaced `a;b` or `a&&b` stays one token and is not split. The docstring's "any ... chained segment" therefore holds only for whitespace-separated operators.

Required property: Delete the docstring. Per §Durable text, a shorter or corrected restatement still restates. Nothing non-obvious remains to keep: the segment-splitting rationale and the "cd worktree && git commit" example already live at `corpus.py:248-254`, and the per-segment rules live in `_command_segment_is_mutating_git`'s docstring.

Request changes: none blocking; delete the docstring.
