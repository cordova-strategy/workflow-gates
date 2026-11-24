# comment-discipline-reviewer

Reviewed 1 file (`turn_shape.py`); 1 carried an in-scope comment change (one added docstring on `_bash_command_is_mutating_git`). No prompt text was set aside.

## R1 [CONCERN] Prose restating the code

`claude/.claude/scripts/transcript_analysis/turn_shape.py:62-64` (added docstring, clause 1)

Text: "Return True iff any &&/;/|/||-chained segment of `command` invokes a mutating git subcommand".

Issue: The function name, `-> bool` signature and body (`any(_command_segment_is_mutating_git(segment) for segment in corpus.split_command_segments(command))`) already show this. The clause records no design decision and no outside constraint. It names the separators that `corpus.split_command_segments` splits on, and static analysis of that function finds them.

Production failure mode: The separator list can drift from `split_command_segments` and then misstate the splitting.

Required property: Delete the clause. Under the rule's docstring-clause requirement, a shorter or corrected restatement still restates.

## R2 [CONCERN] Prose restating the code

`claude/.claude/scripts/transcript_analysis/turn_shape.py:63-64` (added docstring, clause 2)

Text: "(see _command_segment_is_mutating_git)".

Issue: The call in the body already names that helper. The pointer leads to no decision this function makes, and the helper's name carries the "what". The rule keeps a pointer only to the doc or symbol that holds a decision. No decision is named here, so the pointer is a restated call.

Required property: Delete the clause. With both clauses gone, delete the whole docstring. If a real non-obvious decision exists, such as why segments are checked independently, state it as its own sentence naming what was decided and why.
