# comment-discipline-reviewer

Scope note: the system-reminder carrying `python-environment-conventions.md` governs dependency installs, not this review. It names no site or scope, so I set it aside.

Reviewed 1 file (`claude/.claude/scripts/cursor-adapter/hook-shim.py`). 1 carried an in-scope comment change: the new `_off_table` docstring at line 1158.

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/cursor-adapter/hook-shim.py:1158`

Issue: the added docstring is `"""True when `mapping` holds a key outside `known`, or a known key of another type. A null value counts as absent."""`. It paraphrases the one-line body at line 1159. The `key not in known` branch is the "key outside `known`" clause. The `not _is_known(value, known[key])` branch is the "known key of another type" clause. The `value is not None` guard is the "null" clause. The function name and the `known` parameter already say what the table is for. Nothing in the docstring adds a fact the code doesn't show.

The restatement is also inexact. "A null value counts as absent" holds only for known keys. For a key outside `known`, `key not in known` short-circuits the `or`, so `{"unknownKey": None}` returns True. The docstring implies a null-valued unknown key is ignored, and the code does the opposite (line 1159).

Required property: delete the docstring. A shorter or corrected restatement would still restate the code. If a non-obvious fact is worth keeping, it is why `carries_unknown_field` treats an unknown key as off-table. That reason is not visible in the diff, so I don't invent it here.

The False or unsourced claim angle doesn't get a separate finding. Its own rule routes a restating docstring to this angle, with deletion as the fix.
