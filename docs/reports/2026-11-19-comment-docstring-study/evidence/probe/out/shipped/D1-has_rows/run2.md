# comment-discipline-reviewer

## R1 [CONCERN] Restating the code

File: claude/.claude/scripts/probe_synthetic/ctl_delete_has_rows.py:2

Issue: The added docstring is `"""Return True when rows is not empty. Checks the length of the list. Returns a bool."""`. All three sentences restate what the code already shows. The name `has_rows` and the expression `len(rows) > 0` show "True when rows is not empty" and "checks the length". The comparison expression shows "returns a bool". The docstring carries no non-obvious fact such as a precondition, an accepted type, or a rationale.

Production failure mode: None at runtime. The docstring adds maintenance cost, because it can drift from the code. It also adds noise for the reader, which is the Prose restating the code angle of CLAUDE.md §Durable text, "Don't restate the code".

Required property: Delete the docstring. A shorter or corrected restatement still restates, so don't trim it to one sentence. Add a docstring only if a non-obvious fact exists, for example that `rows` must support `len()`, so a bare iterator or generator fails. No such fact is evident from the diff.
