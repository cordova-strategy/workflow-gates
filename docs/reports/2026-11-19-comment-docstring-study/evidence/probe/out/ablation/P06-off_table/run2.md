# comment-discipline-reviewer

## R1 [CONCERN] Restating the code
File: claude/.claude/scripts/cursor-adapter/hook-shim.py:1158 (docstring of `_off_table`)
Issue: The clause "True when `mapping` holds a key outside `known`, or a known key of another type" restates the `any(...)` expression: `key not in known` is the first branch and `not _is_known(value, known[key])` is the second. Static analysis of this file finds it.
Production failure mode: The docstring drifts from the expression it paraphrases, and it adds a second copy for readers to maintain.
Required property: Delete the clause. The function name and expression already carry it.

## R2 [CONCERN] Restating the code
File: claude/.claude/scripts/cursor-adapter/hook-shim.py:1158 (docstring of `_off_table`)
Issue: The clause "A null value counts as absent" restates the `value is not None and ...` guard in the same expression. The docstring gives no reason the null exemption exists, such as what outside this repository forces it. The diff and the file context show none.
Production failure mode: Same as R1. The clause describes behavior without recording a decision.
Required property: Delete the clause. With both clauses gone, the whole docstring goes. Keep the null exemption only if a reason is added, such as the upstream hook contract that treats null as omitted. Name that contract in the sentence.
