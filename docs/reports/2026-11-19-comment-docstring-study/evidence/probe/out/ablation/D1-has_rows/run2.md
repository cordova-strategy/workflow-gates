# comment-discipline-reviewer

## R1 [CONCERN] Prose restating the code

File: `claude/.claude/scripts/probe_synthetic/ctl_delete_has_rows.py:2`

Issue: the added docstring is `"""Return True when rows is not empty. Checks the length of the list. Returns a bool."""`. All three clauses restate what the code and name already show:
- "Return True when rows is not empty" repeats `len(rows) > 0` and the name `has_rows`.
- "Checks the length of the list" repeats the `len(rows)` call.
- "Returns a bool" repeats the comparison's type.

None states a design decision, a reason static analysis cannot find, or an outside constraint.

Production failure mode: none at runtime. The docstring adds maintenance cost and can drift from the code it paraphrases.

Required property: delete the whole docstring, line 2, so the function body is `return len(rows) > 0`. Nothing is left to keep. A shorter or corrected restatement would still restate.
