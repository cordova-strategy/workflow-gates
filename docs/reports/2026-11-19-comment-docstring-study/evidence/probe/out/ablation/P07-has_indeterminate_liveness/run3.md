# comment-discipline-reviewer

Scope: 1 file reviewed (`claude/.claude/scripts/post-crash-sessions.py`), 1 carried an in-scope change (one added docstring on `_has_indeterminate_liveness`, lines 1048-1051). No prompt text was set aside.

## R1 [CONCERN] Prose restating the code

`post-crash-sessions.py:1048-1049`

Issue: The first docstring clause is "True when any entry in `entries` carries indeterminate liveness under `source_name` in `liveness`". It restates the function's name, signature and one-line body (`any(liveness[(source_name, e.pid)] == "indeterminate" for e in entries)`). Static analysis of the function finds all of it, so it is not a design decision.

Production failure mode: The clause adds a second statement that has to be kept in sync with the body, and it tells the reader nothing the body doesn't.

Required property: Delete this clause.

## R2 [CONCERN] Prose restating the code

`post-crash-sessions.py:1049-1051`

Issue: The second docstring clause is "used to withhold Confirmed-clean-exit promotion when a same-session sibling from the *other* evidence source hasn't resolved to live or dead". It describes the call site at lines 1237-1243, where `lookup_sibling_indeterminate` gates `dead_after_boot_fully_confirmed`. Reading the caller finds all of it, and the caller's own comments at lines 1234-1236 and 1270-1274 already state the decision. It names no reason that lies outside the repository's code and tests. "Hasn't resolved to live or dead" only repeats `== "indeterminate"`, whose meaning `_classify_liveness` (around lines 517-540) documents.

I checked the clause against the code and it is accurate: the helper has one caller, and that caller passes `lookup_entries`. A true restatement is still a restatement under the session rule.

Production failure mode: The clause names a single caller. It goes stale if the helper gains a second caller, such as the `lock_entries` path near line 1402, which currently uses an inline comprehension.

Required property: Delete this clause. With R1, that removes the whole docstring, and nothing else is left to keep. The function name and the caller's comments carry the intent.
