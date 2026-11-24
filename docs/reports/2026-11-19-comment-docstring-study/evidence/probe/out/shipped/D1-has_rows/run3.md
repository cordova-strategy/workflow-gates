# comment-discipline-reviewer

Reviewed 1 file; 1 carried an in-scope comment change.

## R1 [CONCERN] Restating the code

- File: `claude/.claude/scripts/probe_synthetic/ctl_delete_has_rows.py:2` (added docstring)
- Text: `"""Return True when rows is not empty. Checks the length of the list. Returns a bool."""`
- Issue: All three sentences restate what the name `has_rows`, the body `len(rows) > 0` and the `> 0` comparison already show. The docstring states nothing non-obvious, so it fails CLAUDE.md §Durable text's "Don't restate the code" bullet.
- Production failure mode: None at runtime. The docstring adds reading cost and can drift from the code as it changes.
- Required property: Delete the docstring. A shorter or corrected restatement would still restate the code. Add a docstring only if a non-obvious fact turns up, such as what types `rows` may be or whether `None` is accepted.
