# comment-discipline-reviewer

Set aside: a system-reminder (`python-environment-conventions.md`) arrived mid-review. It is unrelated to this scope and changed nothing.

Scope: 1 file in the diff (`claude/.claude/scripts/transcript_analysis/scope.py`), 1 comment change in scope (the new `print_resolved_scope` docstring, lines 680-686).

## R1 [CONCERN] Restating the code

scope.py:680-682. Text: "Print the one-line resolved-scope header cmd_skill_invocation already uses, so machine-wide vs. --this-repo output is never scope-ambiguous."

Issue: The clause restates the function's name and its one-line body (`print(_resolved_scope_header(...))`). The purpose clause repeats what `_resolved_scope_header`'s docstring and the call sites already carry. "cmd_skill_invocation already uses" is a point-in-time comparison. It names 1 of about 35 callers (`grep print_resolved_scope` finds it in skill_invocation.py:164 plus every other `transcript_analysis` subcommand), so it will read oddly once a second caller exists. It states no decision and no reason static analysis cannot find.

Fix: delete the sentence.

## R2 [CONCERN] Restating the code

scope.py:683-686. Text: "audit-routing-samples routes it to stderr instead, since its stdout is a JSON (or curation-markdown) data stream a header line would corrupt."

Issue: Which callers pass `file=sys.stderr` is findable from the call sites, and the reason is already commented there (audit_routing.py:614 "stderr, not stdout: stdout is this subcommand's JSON/markdown data stream"). The sentence is also an incomplete list. Other callers pass `file=sys.stderr` too: sessions.py:42, turn_shape.py:288 and :348, pr_cost_export.py:359, and analyze-context.py:229, :304 and :313. Naming one caller as if it were the only one is a stale-prone claim about other files. The reason lives at each call site, so no pointer is needed.

Fix: delete the sentence.

## R3 [CONCERN] Multi-fact comment structure, with imprecise wording

scope.py:682-684. Text: "`file` defaults to stdout (resolved at call time, not import time — a `sys.stdout` default value would bind the stream object process startup captured, bypassing test capture and any later reassignment); ..."

Issue: One sentence chains the decision, a parenthetical, a dash, and a list of consequences, so the reader has to parse the whole thing to find the one decision it carries. "Process startup captured" is also imprecise: a `sys.stdout` default binds when `def` is evaluated at module import, not at process startup. The decision is real and the `file or sys.stdout` line does not show its reason, so keep it, trimmed to the decision and its reason.

Fix: replace the whole docstring (after deleting R1 and R2) with:

```python
    """`file` defaults to None, not `sys.stdout`, so the stream is looked up at call time;
    a `sys.stdout` default would bind at import and bypass test capture."""
```

If the repo's convention is no docstring when the body is one line, a `#` comment above the `print` call carrying the same two clauses is equivalent.
