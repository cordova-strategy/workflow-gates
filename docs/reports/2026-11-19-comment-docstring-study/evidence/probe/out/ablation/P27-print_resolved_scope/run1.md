# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/scope.py`); 1 comment change in scope (the new `print_resolved_scope` docstring, lines 680-686). No prompt text was set aside.

## R1 [CONCERN] Prose restating the code
scope.py:680 — "Print the one-line resolved-scope header cmd_skill_invocation already uses,"
Issue: The clause restates the function name and its one-line body (`print(_resolved_scope_header(...))`). "Already uses" is also a temporal claim about a caller. `skill_invocation.py:164` shows the caller, and the grep shows about 50 other callers, so naming one is arbitrary.
Failure mode: The docstring drifts from the code and misleads a reader about who the callers are.
Required property: Delete the clause. `_resolved_scope_header`'s own docstring (scope.py:661-675) already holds the header's shape and contract.

## R2 [CONCERN] Prose restating the code
scope.py:681 — "so machine-wide vs. --this-repo output is never scope-ambiguous."
Issue: This states the purpose of the header, and the header text built by `_resolved_scope_header` (scope.py:676) shows that purpose. Its `--this-repo` / machine-wide framing is a call-site concern, and the helper's docstring (scope.py:665-674) already covers the root-count rationale.
Failure mode: A second, looser statement of the header's purpose competes with the canonical one.
Required property: Delete the clause.

## R3 [CONCERN] Prose restating the code
scope.py:681-682 — "`file` defaults to stdout"
Issue: The signature `file=None` and the body `file or sys.stdout` show this directly.
Required property: Delete the clause.

## R4 [CONCERN] Prose restating the code
scope.py:682-684 — "(resolved at call time, not import time — a `sys.stdout` default value would bind the stream object process startup captured, bypassing test capture and any later reassignment)"
Issue: This explains Python default-argument binding and how pytest/stdout reassignment interacts with it. Both are standard-library and language semantics that static analysis finds, and `file or sys.stdout` in the body shows the call-time resolution. Deleting it under the rule is mandatory even though it is true and reads as a decision. The clause is also a multi-fact sentence (dash, parenthetical and a three-part effect chain). The "bypassing test capture" cause-and-effect claim names no source.
Failure mode: A reader mistakes it for a repo-specific constraint, when it is general Python behavior.
Required property: Delete the clause. If the `None` sentinel is worth keeping, the kept-decision form is a one-line "`file=None` rather than `file=sys.stdout` so the stream resolves at call time". That is a subject-bearing decision sentence, and it must not carry the capture and reassignment narration.

## R5 [CONCERN] Prose restating the code
scope.py:684-686 — "audit-routing-samples routes it to stderr instead, since its stdout is a JSON (or curation-markdown) data stream a header line would corrupt."
Issue: A repo search finds this: `audit_routing.py:615` passes `file=sys.stderr`, and `audit_routing.py:776` and `:783` print the markdown or JSON stream to stdout. The sentence is also partial. Other callers route to stderr for the same reason, including `sessions.py:42`, `pr_cost_export.py:359`, `turn_shape.py:288` and `:348`, and `analyze-context.py:229`, `:304` and `:313`. Naming only audit-routing-samples reads as the sole case. It is a caller's decision documented in the callee, and it goes stale as callers change.
Failure mode: The docstring understates which callers use `file=`, and a later caller change leaves it wrong.
Required property: Delete the clause. A comment at `audit_routing.py:615` is the right home if the stdout-stream reason is worth recording at all.

Net: after R1-R5 the docstring is empty, so delete it entirely. The signature `file=None` and the body carry everything that remains.
