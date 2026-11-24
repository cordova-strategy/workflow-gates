# comment-discipline-reviewer

Scope: 1 file reviewed, 1 carried an in-scope comment change (new docstring on `_off_table`). The prompt's rule-under-test replaces the "Don't restate the code" bullet; I applied it.

## R1 [CONCERN] Restating the code
File: claude/.claude/scripts/cursor-adapter/hook-shim.py:1158 (docstring of `_off_table`)
Issue: Clause "True when `mapping` holds a key outside `known`" restates the `key not in known` branch of the `any(...)` expression. Static analysis of the function body finds it.
Production failure mode: The docstring drifts from the code the next time the predicate changes, and it adds no reason.
Required property: Delete this clause. It gives no design decision or outside constraint.

## R2 [CONCERN] Restating the code
File: claude/.claude/scripts/cursor-adapter/hook-shim.py:1158
Issue: Clause "or a known key of another type" restates the `not _is_known(value, known[key])` branch.
Production failure mode: Same drift risk as R1.
Required property: Delete this clause. A shorter or corrected paraphrase still restates.

## R3 [CONCERN] Restating the code
File: claude/.claude/scripts/cursor-adapter/hook-shim.py:1158
Issue: Sentence "A null value counts as absent." restates the `value is not None and ...` guard. It names what the function does with None but gives no reason that static analysis can't find, such as an outside system that forces null to mean absent.
Production failure mode: Same drift risk as R1.
Required property: Delete this clause. Keep it only if a reason for the null handling is added, for example the external payload shape that sends nulls. Nothing in the diff supplies that reason, so deleting leaves the function with no docstring.

Prior decisions: none supplied.
