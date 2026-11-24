# comment-discipline-reviewer

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/cursor-adapter/hook-shim.py:1158`

Issue: the added docstring `"""True when `mapping` holds a key outside `known`, or a known key of another type. A null value counts as absent."""` restates the function body. The body at line 1159 shows each clause:
- `key not in known` is "a key outside `known`".
- `not _is_known(value, known[key])` is "a known key of another type".
- `value is not None and ...` is "a null value counts as absent".

The docstring gives no reason for these rules. It names no outside constraint that forces them and no design decision a reader could not find by reading the function. The "null counts as absent" clause is the only candidate for a decision. It is visible in the `value is not None` guard, and the docstring gives no reason for it.

Production failure mode: the docstring will drift from the code the next time the predicate changes. It also gives a reader nothing the three-line body doesn't already show.

Required property: delete the docstring. A shorter or corrected restatement still restates. If the null-as-absent choice has a non-obvious reason, such as a Cursor output contract that emits explicit nulls, state that reason in one sentence. Otherwise leave the function uncommented.

Files reviewed: 1. Files with an in-scope comment change: 1.
