# comment-discipline-reviewer

## R1 [CONCERN] Prose restating the code

File: `claude/.claude/scripts/cursor-adapter/hook-shim.py:1158` (added docstring of `_off_table`).

Offending text: `"""True when `mapping` holds a key outside `known`, or a known key of another type. A null value counts as absent."""`

Issue: Both clauses restate the one-line body. `key not in known` is "a key outside `known`". `not _is_known(value, known[key])` is "a known key of another type". `value is not None and ...` is "a null value counts as absent". The docstring gives no design decision and no reason that static analysis can't find. The function name, the body and the call sites in `carries_unknown_field` (lines 1163 and 1166) already show what it does.

Production failure mode: The docstring can drift from the body, and it adds reading cost without adding information.

Required property: Delete the whole docstring, both sentences. Keep a comment only if the reason for treating null as absent is a decision forced by something outside this repository, such as the Cursor hook output contract. In that case, write a comment that states that decision and its reason.
