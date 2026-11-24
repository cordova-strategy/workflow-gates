# comment-discipline-reviewer

Reviewed 1 file; 1 carried an in-scope comment change.

## R1 [CONCERN] Restating the code

File: claude/.claude/scripts/probe_synthetic/ctl_delete_has_rows.py:2 (added docstring)

Issue: The docstring `"""Return True when rows is not empty. Checks the length of the list. Returns a bool."""` has three sentences, and each restates what the one-line body `return len(rows) > 0` and the function name `has_rows` already show: the emptiness check, the `len` call and the bool result. None states a non-obvious constraint. This is the Prose restating the code angle (CLAUDE.md §Durable text, "Don't restate the code").

Production failure mode: The docstring adds reading cost and can drift from the code. "The list" is already narrower than the `len`-based check supports, since `rows` may be any sized collection.

Required property: Delete the docstring. A shorter or corrected restatement would still restate the code. Add a docstring only if a non-obvious fact turns up, such as an input contract the code does not show.
