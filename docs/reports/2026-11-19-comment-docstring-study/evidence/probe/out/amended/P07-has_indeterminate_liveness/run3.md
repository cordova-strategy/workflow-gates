# comment-discipline-reviewer

## R1 [CONCERN] Restating the code

File: claude/.claude/scripts/post-crash-sessions.py:1048-1051 (new docstring on `_has_indeterminate_liveness`).

Issue: The docstring is "True when any entry in `entries` carries indeterminate liveness under `source_name` in `liveness` -- used to withhold Confirmed-clean-exit promotion when a same-session sibling from the *other* evidence source hasn't resolved to live or dead."

- The first clause restates the function's name, signature and `any(... == "indeterminate" ...)` body.
- The "used to withhold ... promotion" clause describes the caller. Static analysis finds it: `Grep` shows one call site, line 1237, feeding `lookup_sibling_indeterminate` into `dead_after_boot_fully_confirmed` at 1238-1243.
- The reason for that use is already stated at the call site (1234-1236), so repeating it here duplicates it.
- The docstring is also narrower than the signature in one way: `source_name` is a parameter, but "the *other* evidence source" is true only for the single current caller.
- No clause records a design decision with a reason static analysis cannot find, such as an external constraint.

Failure mode: a second copy of the call-site rationale can drift from it. It already over-specifies "other source" for a function that takes any source name.

Required property: delete the docstring. A shorter or corrected version would still restate the code. If a pointer is wanted, the existing comment at the call site (1234-1236) already holds the decision.

Prior decisions: none supplied.
