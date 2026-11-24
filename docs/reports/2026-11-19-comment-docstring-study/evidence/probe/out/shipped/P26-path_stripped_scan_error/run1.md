# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/scope.py`); 1 comment site in scope (the new docstring on `_path_stripped_scan_error`, lines 207-215). The diff adds no other comments or docs. I set aside the unrelated Python-environment rule text that appeared mid-session. It does not bear on this diff.

## R1 [CONCERN] Comment verbosity

scope.py:207-215

Offending text: the first line "Same exception type, with any embedded absolute path removed from the message." and the last sentence "A caller matching on subclass still sees the same type."

Issue: Both state the same fact, that the exception type is preserved. The last sentence also depends on the `OSError(errno, strerror)` sentence just before it. The opening line mostly restates the function's name (`_path_stripped_...`) and its `-> OSError` signature.

Production failure mode: none at runtime. The docstring is longer than it needs to be, and its two type-preservation statements invite drift.

Required property: one sentence per distinct fact, with every fact kept. The non-obvious facts are:
- Why `strerror` is used rather than `str(exc)`.
- That it matches the root-level diagnostic at scope.py:425.
- That passing `errno` preserves the subclass for callers that match on it.

Suggested compression:
"Strip the path from `exc`'s message. Uses `exc.strerror or 'permission denied'`, as `_iter_scoped_sessions`' root-level diagnostic does, because `str(exc)` can embed the offending path. Passing `exc.errno` makes `OSError` rebuild the matching subclass (e.g. `PermissionError`), so callers matching on it are unaffected."

## R2 [FYI] False or unsourced claim

scope.py:207, 213-214 (code at scope.py:216)

Offending text: "Same exception type" and "A caller matching on subclass still sees the same type."

Issue: The claim holds only when `exc.errno` is set and maps to a subclass. Line 216 passes `exc.errno` straight through. For an `OSError` subclass raised with no errno (e.g. a bare `PermissionError()`, where `errno` is `None`), `OSError(None, ...)` yields a plain `OSError`. I did not run this, but it is standard CPython behavior. The `stat()`/`resolve()` callers at scope.py:261-264 normally set errno, so this is an edge case, not a live bug.

Required property: qualify the claim, e.g. "preserves the subclass whenever `exc.errno` maps to one". The R1 compression above already carries this wording.

## Other notes

- The "Mirrors _iter_scoped_sessions' own root-level diagnostic ... `exc.strerror or 'permission denied'`" claim checks out against scope.py:425. The `str(exc)` embeds-the-path claim is consistent with scope.py:396-397. No finding.
- The reason for stripping is already stated in `_dedup_new_project_dirs`' docstring (scope.py:254-257) and in `_iter_scoped_sessions`' docstring (scope.py:394-397). The new docstring restates part of it. Keeping a short pointer is acceptable.
