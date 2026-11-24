# comment-discipline-reviewer

Reviewed 1 file (`transcript_analysis/scope.py`, from the diff); 1 carried an in-scope change (the new docstring on `print_resolved_scope`, diff lines 8-14). The docstring is five clauses, and each is a separate finding below. No clause states a decision whose reason sits outside this repository, so the whole docstring goes.

## R1 [CONCERN] Prose restating the code
scope.py:680 (diff line 8), first clause: "Print the one-line resolved-scope header cmd_skill_invocation already uses".
- Issue: the clause restates the function name and its one-line body (`print(_resolved_scope_header(...), file=...)`). "already uses" is a caller relationship that static analysis finds. It is also incomplete. `print_resolved_scope` has about 50 callers across `transcript_analysis/*.py`, `token-analyzer.py` and `analyze-context.py`. `skill_invocation.py:164` is one of them.
- Required property: delete the clause.

## R2 [CONCERN] Prose restating the code
scope.py:680 (diff lines 8-9), "so machine-wide vs. --this-repo output is never scope-ambiguous".
- Issue: this states what the header is for, not a decision with a reason static analysis cannot find. What the header contains is visible in `_resolved_scope_header`, and `scope_label` is passed in by each caller.
- Required property: delete the clause.

## R3 [CONCERN] Prose restating the code
scope.py:680 (diff line 9), "`file` defaults to stdout".
- Issue: the signature `file=None` and the body `file or sys.stdout` show this.
- Required property: delete the clause.

## R4 [CONCERN] Prose restating the code
scope.py:680 (diff lines 9-12), "(resolved at call time, not import time — a `sys.stdout` default value would bind the stream object process startup captured, bypassing test capture and any later reassignment)".
- Issue: the `None` sentinel and `sys.stdout` lookup in the body show the call-time resolution. The reason is Python's default-argument binding, a language and standard-library fact. The test-capture effect is findable from the tests, such as the `capsys` use in `test_transcript_scope.py:359`. The rule deletes anything the language, the standard library or this repository's tests show, even when it is true. "Process startup captured" is also imprecise, since the binding happens when the module is imported.
- Required property: delete the clause. If the author wants to guard the `None` default against a "simplify to `file=sys.stdout`" edit, a regression test that captures output with `capsys` already does that.

## R5 [CONCERN] Prose restating the code / False or unsourced claim (partial support)
scope.py:680 (diff lines 12-14), "audit-routing-samples routes it to stderr instead, since its stdout is a JSON (or curation-markdown) data stream a header line would corrupt".
- Issue: this restates a call site. `audit_routing.py:615` passes `file=sys.stderr`, and `audit_routing.py:783` prints the JSON. It describes a caller, so it can go stale when the caller changes. It also presents stderr routing as particular to audit-routing-samples. The same routing appears in `analyze-context.py:229,304,313`, `pr_cost_export.py:359`, `sessions.py:42` and `turn_shape.py:288,348`, so the sentence supports only part of the pattern.
- Required property: delete the clause. If a reason for stderr routing is worth keeping, it belongs at the call sites. A single sentence at the `file` parameter naming the stdout-data-stream constraint in general would also work.

## Net fix
Delete the whole docstring. The function body is `print(_resolved_scope_header(...), file=file or sys.stdout)`, and `_resolved_scope_header`'s own docstring at scope.py:661 already covers the header.
