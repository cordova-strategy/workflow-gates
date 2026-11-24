# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/cursor-adapter/hook-shim.py`); 1 carried an in-scope comment change.

## R1 [CONCERN] Restating the code

hook-shim.py:1158 (added docstring on `_off_table`)

Issue: The docstring reads "True when `mapping` holds a key outside `known`, or a known key of another type. A null value counts as absent." Every clause is visible in the one-line body at line 1159:
- `key not in known` is the "key outside `known`" clause.
- `not _is_known(value, known[key])` is the "known key of another type" clause.
- `value is not None and ...` is the "null counts as absent" clause.

Nothing in it gives a reason static analysis cannot find: no why, and no outside constraint that forces the null handling. Under the amended "Don't restate the code" rule, a restatement is deleted, and a shorter or corrected version still restates.

Production failure mode: None at runtime. The docstring would drift from the body when the predicate changes, and it adds reading cost without adding a fact.

Required property: Delete the docstring. Add a comment back only if the author records why null is treated as absent, for example which hook output contract emits null for omitted fields. Such a comment would name that decision and its reason.
