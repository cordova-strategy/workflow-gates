# comment-discipline-reviewer

Reviewed 1 file (hook-shim.py), 1 carried an in-scope comment change (the new `_off_table` docstring).

## R1 [CONCERN] False or unsourced claim

File: `claude/.claude/scripts/cursor-adapter/hook-shim.py:1158`

Text: `"""True when `mapping` holds a key outside `known`, or a known key of another type. A null value counts as absent."""`

Issue: "A null value counts as absent" is only partly true. The function at line 1159 tests `key not in known or (value is not None and not _is_known(...))`. The `value is not None` guard sits on the second operand only, so a null value under a key outside `known` still returns True, as in `{"unexpectedKey": None}`. A null counts as absent only for a key in `known`. The subject (the expression at line 1159) supports the claim in part, so the claim fails under "False: supports only in part".

Production failure mode: a future contributor reads the docstring and expects null-valued unknown keys to be ignored. In `carries_unknown_field` (lines 1162-1166) they would be flagged as unknown fields.

Required property: the null sentence is scoped to known keys. For example: "A null value on a known key counts as absent; a null under an unknown key is still off-table."

The first sentence ("True when mapping holds a key outside known, or a known key of another type") only restates the expression in the line below it, which is the Prose restating the code angle. Keep the corrected null sentence and delete the first one.

Other checks: `type_ok` (line 829-830) and `_is_known` (lines 1128-1131) confirm that "another type" holds. The `"any"` kind accepts every type.
