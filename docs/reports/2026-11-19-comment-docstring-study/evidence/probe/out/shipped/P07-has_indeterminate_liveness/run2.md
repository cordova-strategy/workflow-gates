# comment-discipline-reviewer

Set-aside text: the system-reminder embedding `python-environment-conventions.md` is a rule file unrelated to this review's scope. I did not apply it.

Reviewed 1 file (`claude/.claude/scripts/post-crash-sessions.py`); 1 carried an in-scope comment change (the new docstring on `_has_indeterminate_liveness`, lines 1048-1051).

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/post-crash-sessions.py:1048-1051`

Issue: the added docstring reads "True when any entry in `entries` carries indeterminate liveness under `source_name` in `liveness` -- used to withhold Confirmed-clean-exit promotion when a same-session sibling from the *other* evidence source hasn't resolved to live or dead."

- The first clause restates the one-line body, `any(liveness[(source_name, e.pid)] == "indeterminate" for e in entries)`, and the function name. Per §Durable text's "Don't restate the code", this is a deletion case.
- The second clause describes the caller, not the function. The function is source-agnostic: it takes `source_name`, and the unit tests at `tests/test_post_crash_sessions.py:1832-1845` call it with `"registry"`, not the "other" source.
- The "other evidence source" wording is true only at the sole production call site (line 1237, `lookup_entries` inside the registry branch).
- That rationale already sits at the call site in the comment at lines 1234-1236 ("A same-session lookup_entries sibling with unresolved liveness is cross-source evidence this branch would otherwise ignore entirely...") and in the comment at lines 1270-1273. Repeating it in the docstring makes a second home that drifts if another caller is added (single source of truth).

Required property: delete the docstring. The name, signature and body show what it does, and the call-site comments hold the why. If a docstring is wanted, keep only a non-obvious fact about the function itself. Do not name the caller's use.
