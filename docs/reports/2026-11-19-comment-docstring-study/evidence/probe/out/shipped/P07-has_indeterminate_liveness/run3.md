# comment-discipline-reviewer

Set aside: a system-reminder carrying `python-environment-conventions.md`. It names no site or scope for this review, so I did not apply it.

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/post-crash-sessions.py:1048-1051`

Issue: the new docstring reads "True when any entry in `entries` carries indeterminate liveness under `source_name` in `liveness`". The one-line body `any(liveness[(source_name, e.pid)] == "indeterminate" for e in entries)` shows exactly this, and the function name states it too. That is a restatement, so it is deleted rather than reworded.

Its second half ("used to withhold Confirmed-clean-exit promotion when a same-session sibling from the *other* evidence source hasn't resolved to live or dead") describes the caller's purpose, not this function's behavior. Three problems:

- The comment at lines 1234-1236 already carries that rationale at the only call site (`:1237`, `lookup_entries`, `"lookup"`), and `dead_after_boot_fully_confirmed` (`:1238-1243`) shows the withholding. The same fact now has two homes.
- "The *other* evidence source" is relative to `registry_entries`. The helper takes any `source_name` and its signature accepts `RegistryEntry` lists, so the docstring's framing doesn't match what the function can do.
- A purpose tied to one caller goes stale when a second caller appears.

Checked against the code: the claim is true of the single caller, so it is not a False-claim finding. Grep for `_has_indeterminate_liveness` shows one call site, `:1237`, plus tests.

Required property: delete the docstring. The call-site comment at `:1234-1236` stays as the home for the rationale. If a docstring is wanted, it should state only a non-obvious constraint, such as the `KeyError` when `liveness` lacks a `(source_name, pid)` key. That constraint is not stated today.
