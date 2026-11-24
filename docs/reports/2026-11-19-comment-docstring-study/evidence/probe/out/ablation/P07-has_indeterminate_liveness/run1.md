# comment-discipline-reviewer

Scope: 1 file in the diff (`claude/.claude/scripts/post-crash-sessions.py`), and it carries 1 in-scope change, the new docstring on `_has_indeterminate_liveness`. I applied the session's replacement "Don't restate the code" bullet, which supersedes the CLAUDE.md bullet of the same name.

## R1 [CONCERN] Prose restating the code

File: claude/.claude/scripts/post-crash-sessions.py:1048-1049 (first clause of the new docstring)

Issue: "True when any entry in `entries` carries indeterminate liveness under `source_name` in `liveness`" paraphrases `any(liveness[(source_name, e.pid)] == "indeterminate" for e in entries)`. The function name, signature and one-line body show all of it. It names no decision and no reason outside the repository.

Required property: delete this clause.

## R2 [CONCERN] Prose restating the code

File: claude/.claude/scripts/post-crash-sessions.py:1049-1051 (second clause: "used to withhold Confirmed-clean-exit promotion when a same-session sibling from the *other* evidence source hasn't resolved to live or dead")

Issue: This clause states the helper's purpose and sole caller. Grepping the repository finds the same thing at line 1237, where `lookup_sibling_indeterminate = _has_indeterminate_liveness(lookup_entries, liveness, "lookup")` feeds `dead_after_boot_fully_confirmed`. That is a static-analysis finding, even though it spans two functions. It is not a decision with a reason outside the repository. The call-site comment at lines 1234-1236 already holds the one design decision involved: a lookup sibling is cross-source evidence that the registry-only partition would otherwise ignore. The clause also describes a caller's use. It hard-codes "the *other* evidence source", but the helper takes any `source_name`.

Required property: delete this clause. Don't relocate it, because the call-site comment already carries the decision.

## Net effect

Both clauses go, so the function has no docstring. Nothing non-obvious is lost.
