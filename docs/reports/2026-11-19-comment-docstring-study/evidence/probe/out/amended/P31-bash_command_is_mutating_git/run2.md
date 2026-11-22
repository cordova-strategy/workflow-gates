# comment-discipline-reviewer

Reviewed 1 file (`turn_shape.py`); 1 carried an in-scope comment change (one added docstring).

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/turn_shape.py:62-64`

Offending text: `"""Return True iff any &&/;/|/||-chained segment of `command` invokes a mutating git subcommand (see _command_segment_is_mutating_git)."""`

Issue: The docstring restates the function body. The name `_bash_command_is_mutating_git` and the body `any(_command_segment_is_mutating_git(segment) for segment in corpus.split_command_segments(command))` already show "any segment is mutating git". The operator list `&&/;/|/||` repeats what `corpus.split_command_segments` finds (`corpus.py:257-258`, which splits on `&&/||/;/|`). The pointer to `_command_segment_is_mutating_git` names the callee the body already calls. It points to no decision, because the docstring records none: no why-it-is-this-way and no outside constraint. A shorter or corrected restatement would still restate.

Production failure mode: The operator list is a second copy of `split_command_segments`' separator set. It goes stale if that set changes.

Required property: Delete the docstring. Reasons for the segment split or the mutating-subcommand set belong with `split_command_segments` (`corpus.py:257`) and `_command_segment_is_mutating_git` (`turn_shape.py:40`), and both already carry docstrings.

**Request changes** (R1: delete the docstring.)
