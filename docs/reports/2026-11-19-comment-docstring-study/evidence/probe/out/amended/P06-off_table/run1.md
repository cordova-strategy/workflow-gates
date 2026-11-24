# comment-discipline-reviewer

## R1 [CONCERN] Restating the code

- **File:line:** claude/.claude/scripts/cursor-adapter/hook-shim.py:1158 (added docstring of `_off_table`)
- **Offending text:** `"""True when `mapping` holds a key outside `known`, or a known key of another type. A null value counts as absent."""`
- **Issue:** Both sentences restate what the one-line body shows. `key not in known` is the "key outside `known`" clause. `not _is_known(value, known[key])` is the "known key of another type" clause. `value is not None` is the "null counts as absent" clause. The docstring names no design decision and gives no reason that static analysis of the repository cannot find. Under the rule under test, a shorter or corrected restatement still restates.
- **Production failure mode:** None at runtime. The comment adds a second copy of the logic that has to be kept in step with the code, and nothing in it protects a reader from a mistake.
- **Required property:** Delete the docstring. Keep a comment only if the reason for treating null as absent is something this repository cannot show, such as Cursor emitting explicit nulls. In that case, state that reason and drop the rest.
