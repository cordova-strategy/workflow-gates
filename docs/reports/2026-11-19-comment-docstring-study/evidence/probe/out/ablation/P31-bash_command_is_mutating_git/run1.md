# comment-discipline-reviewer

Scope note: the python-environment-conventions rules-file text in the session context concerns installing Python dependencies. It has no bearing on this diff, so I set it aside.

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/turn_shape.py`). It carries 1 added docstring in scope, with 2 clauses.

## R1 [CONCERN] Prose restating the code

`claude/.claude/scripts/transcript_analysis/turn_shape.py:62-63` (added in the diff)

Issue: the clause `Return True iff any &&/;/|/||-chained segment of `command` invokes a mutating git subcommand` restates what the function shows. The name `_bash_command_is_mutating_git`, the `-> bool` signature and the `any(...)` over `corpus.split_command_segments(command)` already say this. The operator list matches `_SHELL_OPERATOR_TOKENS` at `corpus.py:254`, so static analysis finds it, and it is true. It states no design decision and no reason that static analysis cannot find. The rule says a true restatement still gets deleted.

Production failure mode: if `_SHELL_OPERATOR_TOKENS` changes, the hand-copied operator list drifts. The same list is already restated in the `split_command_segments` docstring.

Required property: delete this clause. No kept decision remains in the docstring, so delete the whole docstring.

## R2 [CONCERN] Prose restating the code

`claude/.claude/scripts/transcript_analysis/turn_shape.py:63` (added in the diff)

Issue: the clause `(see _command_segment_is_mutating_git)` points at a callee that the body already names at line 66. The pointer does not lead to a held decision. The target's docstring (`turn_shape.py:41-47`) only narrates its own steps: env-prefix strip, `sudo` strip, flag-value drop and the subcommand check. Each of those is visible in its code. The rule keeps a pointer only when it points to a doc or symbol that holds a decision.

Production failure mode: if the callee is renamed, the docstring pointer goes stale. Nothing in the pointer is information the body lacks.

Required property: delete this clause along with R1's. The finished fix leaves the function with no docstring.
