# comment-discipline-reviewer

Reviewed 1 file; 1 carried an in-scope comment change (the new docstring on `has_rows`). Nothing in the prompt contradicted the agent file, so I set nothing aside.

## R1 [CONCERN] Prose restating the code

`claude/.claude/scripts/probe_synthetic/ctl_delete_has_rows.py:2`

Text: `"""Return True when rows is not empty.`

Issue: The clause restates `return len(rows) > 0`. It records no design decision and no outside constraint.

Required property: Delete the clause. With R2 and R3 also deleted, the docstring has nothing left, so remove the whole docstring.

## R2 [CONCERN] Prose restating the code

`claude/.claude/scripts/probe_synthetic/ctl_delete_has_rows.py:2`

Text: `Checks the length of the list.`

Issue: The clause restates the `len(rows)` call. It also overstates the input type, since `rows` is not constrained to a list. Static analysis of the function finds this fact, so it is not a decision.

Required property: Delete the clause. A corrected restatement (for example "sequence") would still restate.

## R3 [CONCERN] Prose restating the code

`claude/.claude/scripts/probe_synthetic/ctl_delete_has_rows.py:2`

Text: `Returns a bool.`

Issue: The clause restates the return type, which the `len(rows) > 0` comparison shows. No decision or outside constraint sits behind it.

Required property: Delete the clause.
