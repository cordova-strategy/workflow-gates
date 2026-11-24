# comment-discipline-reviewer

Reviewed 1 file; 1 carried an in-scope comment change.

## R1 [CONCERN] Restating the code

- **File and line:** `claude/.claude/scripts/probe_synthetic/ctl_delete_has_rows.py:2` (added docstring).
- **Offending text:** `"""Return True when rows is not empty. Checks the length of the list. Returns a bool."""`
- **Issue:** All three sentences restate what the code shows.
  - `len(rows) > 0` already shows the first two sentences: the function returns True when `rows` is non-empty, by checking its length.
  - The name and the comparison already show the third: the function returns a bool.
  - The docstring states no design decision and no reason that static analysis cannot find. No outside constraint is involved.
  - "The list" is also narrower than the code, which accepts any sized container. A corrected or shorter version would still restate.
- **Production failure mode:** The docstring adds nothing to the code, and it drifts from the code as the code changes.
- **Required property:** Delete the docstring. The function body is `return len(rows) > 0` and nothing else. Add a comment only if a non-obvious decision exists, such as why `len(rows) > 0` was chosen over truthiness. The diff gives no such decision.

**Request changes:** R1 (delete the docstring).
