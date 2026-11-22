# comment-discipline-reviewer

Scope: 1 file reviewed, 1 carrying an in-scope comment change (`claude/.claude/scripts/post-crash-sessions.py`, one added docstring on `_has_indeterminate_liveness`). The diff has no prompt text that conflicts with the agent file, so none was set aside. The session's replacement "Don't restate the code" bullet is the rule applied to the Prose restating the code angle.

## R1 [CONCERN] Prose restating the code

`claude/.claude/scripts/post-crash-sessions.py:1048` (docstring first clause)

Issue: "True when any entry in `entries` carries indeterminate liveness under `source_name` in `liveness`" restates the one-line body at line 1052, `any(liveness[(source_name, e.pid)] == "indeterminate" for e in entries)`. It also restates the function name and signature. It states no design decision and no reason static analysis can't find.

Production failure mode: none at runtime. The clause is noise that can drift from the body, and the rule says a restatement is deleted, not shortened or corrected.

Required property: delete the clause. No kept decision has this clause as its subject, so nothing needs to survive in its place.

## R2 [CONCERN] Prose restating the code

`claude/.claude/scripts/post-crash-sessions.py:1049-1051` (docstring second clause)

Issue: "used to withhold Confirmed-clean-exit promotion when a same-session sibling from the *other* evidence source hasn't resolved to live or dead" describes how the helper is used. Static analysis of this repository finds that from its single call site at lines 1237-1243: the result feeds `lookup_sibling_indeterminate`, which gates `dead_after_boot_fully_confirmed`. I grepped the file and found no other caller. The reason for the gate is already stated at the call site (lines 1234-1236) and in the comment at lines 1270-1273. The clause is true and sits in the wrong place, but under the rule that does not keep it. A comment that only names a caller's purpose is a restatement, even when finding it takes more than one site.

Production failure mode: none at runtime. The clause hard-codes one caller's purpose and the "other source" framing into a helper that takes `source_name` as a parameter. A second caller would make it misleading.

Required property: delete the clause. With R1's clause also gone, the whole docstring is deleted. The helper then carries no docstring, and the existing call-site comments at lines 1234-1236 remain the one home for the decision.
