# comment-discipline-reviewer

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/post-crash-sessions.py:1048-1051` (new docstring on `_has_indeterminate_liveness`).

Offending text: """True when any entry in `entries` carries indeterminate liveness under `source_name` in `liveness` -- used to withhold Confirmed-clean-exit promotion when a same-session sibling from the *other* evidence source hasn't resolved to live or dead."""

Issue:
- The first clause restates the one-line body (`any(liveness[(source_name, e.pid)] == "indeterminate" for e in entries)`) and the function name and signature.
- The "used to withhold ... promotion" clause describes the caller. Static analysis finds it: the only call site is `post-crash-sessions.py:1237-1243`, where `lookup_sibling_indeterminate` feeds `dead_after_boot_fully_confirmed`.
- The decision behind that use, that a cross-source sibling with unresolved liveness must block promotion because the registry-only partition ignores it, is already recorded in the comment at lines 1234-1236. The docstring adds no reason static analysis cannot find, and no pointer to a decision that lives elsewhere.
- I found no false claim: `Grep` shows one caller, and it passes `lookup_entries` with `"lookup"`.

Production failure mode: a restating docstring drifts from the caller. A second caller, or a change to the promotion rule, makes the docstring false, and the caller's comment stays the authoritative home.

Required property: delete the docstring. The call-site comment at 1234-1236 carries the decision. Do not replace it with a shorter paraphrase, because a shorter restatement still restates.
