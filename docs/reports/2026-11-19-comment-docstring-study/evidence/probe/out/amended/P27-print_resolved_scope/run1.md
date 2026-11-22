# comment-discipline-reviewer

Reviewed 1 file (`scope.py`), 1 docstring in scope: `print_resolved_scope`. No prompt text was set aside.

## R1 [CONCERN] Restating the code
scope.py:680-681 (docstring opening): "Print the one-line resolved-scope header cmd_skill_invocation already uses, so machine-wide vs. --this-repo output is never scope-ambiguous."
- Issue: the function name, signature and body (`print(_resolved_scope_header(...))`) already show that it prints the header. "already uses" also describes a caller (`skill_invocation.py:164`) that static analysis finds.
- Production failure mode: the sentence rots whenever another caller is added (there are many, e.g. `audit_routing.py:89`, `analyze-context.py:169`), and it records no decision.
- Required property: delete the sentence. The shared header text already has its home in `_resolved_scope_header`'s docstring (scope.py:661), so the pointer is already there.

## R2 [CONCERN] Restating the code / single source of truth
scope.py:681-684: "audit-routing-samples routes it to stderr instead, since its stdout is a JSON (or curation-markdown) data stream a header line would corrupt."
- Issue: the stderr routing is a decision made at the call sites, and `audit_routing.py:614` already carries the reason ("stderr, not stdout: stdout is this subcommand's JSON/markdown data stream"). The docstring repeats it in a second home. `analyze-context.py:229,304,313` also pass `file=sys.stderr`, so naming only one caller is partial and will drift.
- Required property: delete the clause. If a pointer is wanted, state the rule once and name no caller: "Pass `file=sys.stderr` when stdout carries data."

## R3 [CONCERN] Multi-fact comment structure
scope.py:680-684: the `file` sentence chains the default, the call-time-resolution rationale, a dash aside, a parenthetical, a semicolon, and the caller clause. A reader has to parse the whole sentence to find the single kept decision.
- Required property: after R1 and R2, keep only the decision and its reason, as one short sentence. Example: "`file` defaults to None and resolves to `sys.stdout` at call time, because a `sys.stdout` default value would bind the stream captured at import and bypass test capture and later reassignment." The call-time default is a non-obvious decision whose reason, Python's default-binding behavior combined with test capture, is not visible from the signature alone.
