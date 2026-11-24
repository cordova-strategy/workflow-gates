# comment-discipline-reviewer

Scope note: the only text set aside was the `python-environment-conventions.md` rule file loaded mid-session. It governs Python dependency installs and has no bearing on this review. Reviewed 1 file, `transcript_analysis/scope.py`. It carries one new docstring, on `print_resolved_scope` (lines 680-686), reviewed against the replacement "Don't restate the code" bullet. The docstring has six clauses. Five are deleted and one is kept, trimmed and corrected.

## R1 [CONCERN] Prose restating the code
scope.py:680. "Print the one-line resolved-scope header"

Issue: the function name and its body (`print(_resolved_scope_header(...))`) already show this. `_resolved_scope_header`'s own docstring at scope.py:661 describes the header.

Required property: delete the clause.

## R2 [CONCERN] Prose restating the code
scope.py:680. "...cmd_skill_invocation already uses,"

Issue: this restates a call site, which a repo search finds (skill_invocation.py:164). It also singles out one of roughly 50 callers. It is a prior-usage comparison with no decision behind it.

Required property: delete the clause.

## R3 [CONCERN] Prose restating the code
scope.py:680-681. "so machine-wide vs. --this-repo output is never scope-ambiguous"

Issue: this states what the header is for. Reading `_resolved_scope_header` (scope.py:660) and its tests (test_transcript_scope.py:834-851) shows that.

Required property: delete the clause.

## R4 [CONCERN] Prose restating the code
scope.py:681. "`file` defaults to stdout"

Issue: the signature (`file=None`) and body (`file or sys.stdout`, line 687) show this.

Required property: delete the clause as a standalone statement. Its subject stays inside the R5 decision sentence.

## R5 [CONCERN] Prose restating the code, with a False claim inside the kept decision
scope.py:681-684. "(resolved at call time, not import time — a `sys.stdout` default value would bind the stream object process startup captured, bypassing test capture and any later reassignment)"

Issue: this is the one kept decision. It says why `file=None` is resolved inside the body, and the reason comes from Python's default-binding semantics, which the repository's code cannot show.
- The wording is loose. A default value is bound when the `def` executes at module import, not at "process startup".
- "Resolved at call time, not import time" repeats itself.

Required property: keep one sentence that names the decision and its reason. For example: "`file=None` resolves to `sys.stdout` inside the body because a `sys.stdout` default would bind the stream present at import time, bypassing pytest capture and later reassignment." This is the docstring's only remaining content.

## R6 [CONCERN] Prose restating the code
scope.py:684-686. "audit-routing-samples routes it to stderr instead, since its stdout is a JSON (or curation-markdown) data stream a header line would corrupt."

Issue: this describes a caller's behavior, which a repo search finds (audit_routing.py:615). The call site already carries the reason at audit_routing.py:614, "stderr, not stdout: stdout is this subcommand's JSON/markdown data stream." The docstring also names only one of at least 9 callers passing `file=sys.stderr`. Others are sessions.py:42, turn_shape.py:288 and :348, pr_cost_export.py:359, and analyze-context.py:229, :304 and :313. That makes the sentence read as if audit-routing-samples were the lone exception.

Required property: delete the clause. The decision lives at each call site.
