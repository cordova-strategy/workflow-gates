# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/turn_shape.py`); it carries 1 in-scope comment change, the new docstring on `_bash_command_is_mutating_git`.

## R1 [CONCERN] Prose restating the code

turn_shape.py:62-64 (added docstring), clause 1.

Text: "Return True iff any &&/;/|/||-chained segment of `command` invokes a mutating git subcommand".

Issue: the clause restates the function body. `any(...)` over `corpus.split_command_segments(command)` calling `_command_segment_is_mutating_git`, plus the `-> bool` signature, show the same thing. It records no decision and gives no reason static analysis cannot find. The rule deletes every such clause, even a true one. The operator list is also a second copy of what `split_command_segments` splits on, so it can drift from that function.

Fix: delete the clause.

## R2 [CONCERN] Prose restating the code

turn_shape.py:63-64 (added docstring), clause 2.

Text: "(see _command_segment_is_mutating_git)".

Issue: this pointer names the helper the body already calls on the next line. It is not a pointer to a decision, because the docstring holds no kept decision for it to attach to. It points at nothing the code does not show.

Fix: delete the clause. With both clauses gone, remove the whole docstring.
