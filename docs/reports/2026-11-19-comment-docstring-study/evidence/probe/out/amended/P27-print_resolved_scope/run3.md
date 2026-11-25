# comment-discipline-reviewer

Scope: 1 file in the diff (`claude/.claude/scripts/transcript_analysis/scope.py`), 1 comment change in scope (the new `print_resolved_scope` docstring, lines 680-686 at the diff's state). Reviewed under the session's replacement "Don't restate the code" bullet. No prompt text contradicted the agent file's scope, so none was set aside.

## R1 [CONCERN] Restating the code
scope.py:683-686 (diff lines 8-14).
Text: "audit-routing-samples routes it to stderr instead, since its stdout is a JSON (or curation-markdown) data stream a header line would corrupt."
Issue: The clause describes one caller's behavior. `audit_routing.py:615` shows the `file=sys.stderr` call. `audit_routing.py:776-783` shows the stdout JSON/markdown output. Static analysis of the repo finds both, so the rule says to delete the clause even though it is true and takes two files to find. It also covers only one of the callers that pass `file=sys.stderr`, because `sessions.py:42`, `turn_shape.py:288` and `:348`, `pr_cost_export.py:359` and `analyze-context.py:229` do the same. A shorter or corrected version of it would still restate.
Production failure mode: The list of stderr callers goes stale as callers change, and this docstring will not be updated with them.
Required property: Delete the clause. The `file` parameter is the interface, and each caller's stderr choice is visible at its own call site.

## R2 [CONCERN] Restating the code
scope.py:680-681 (diff lines 8-9).
Text: "Print the one-line resolved-scope header cmd_skill_invocation already uses, so machine-wide vs. --this-repo output is never scope-ambiguous."
Issue: "Print the one-line resolved-scope header" restates the name `print_resolved_scope` and its one-line body. "cmd_skill_invocation already uses" names one of about 50 callers (`skill_invocation.py:164`) and is not a decision. "already" is also prior-state framing. The header text is documented on `_resolved_scope_header`.
Production failure mode: The sentence implies `cmd_skill_invocation` is the reference caller, which nothing in the code supports.
Required property: Delete "Print the one-line resolved-scope header cmd_skill_invocation already uses". Keep only the reason the header exists, as a pointer or short clause, for example "Exists so machine-wide vs. --this-repo output is never scope-ambiguous; see `_resolved_scope_header`." Drop that clause too if it adds nothing the pointer doesn't carry.

## R3 [FYI] Multi-fact comment structure
scope.py:681-683 (diff lines 9-12).
Text: "`file` defaults to stdout (resolved at call time, not import time — a `sys.stdout` default value would bind the stream object process startup captured, bypassing test capture and any later reassignment)".
Issue: One kept decision is the `None` default, resolved at call time. The reason is non-obvious and worth keeping. It is packed into a parenthetical that also holds a dash aside, so the decision and its reason are hard to separate. "Defaults to stdout" and "the stream object process startup captured" restate what `file or sys.stdout` shows.
Production failure mode: None. This is readability only.
Required property: Keep the decision and its reason as one coupled sentence, for example: "`file` defaults to None, not `sys.stdout`, so the stream is looked up at call time. A `sys.stdout` default binds at import and bypasses test capture and later reassignment."

Prior decisions: none supplied. No PR-defined labels, "used to be" framing or false claims found. The docstring's factual claims hold: `skill_invocation.py:164` calls `print_resolved_scope`, `audit_routing.py:615` passes `file=sys.stderr`, and `audit_routing.py:776-783` prints markdown or JSON to stdout.
