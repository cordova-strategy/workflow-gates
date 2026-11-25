# comment-discipline-reviewer

Scope: 1 file in the diff (`claude/.claude/scripts/transcript_analysis/scope.py`), 1 added docstring (`print_resolved_scope`). No prior decisions were supplied.

## R1 [CONCERN] Multi-fact comment structure
scope.py:680-686, second sentence of the `print_resolved_scope` docstring.

Issue: One sentence chains four independent facts through a parenthetical, an em-dash, a semicolon and a trailing "since" clause:
- `file` defaults to stdout.
- The default is resolved at call time, not import time.
- A `sys.stdout` default would bind the startup stream, which bypasses test capture and later reassignment.
- audit-routing-samples sends the header to stderr because its stdout is a data stream.

A reader has to parse the whole run to find where each fact ends.

Required property: one sentence per fact. Suggested split:
1. "`file` defaults to stdout, resolved at call time."
2. "A `sys.stdout` default value would bind the stream captured at import, bypassing test capture and later reassignment."
3. "Pass `file=sys.stderr` when stdout carries a data stream the header would corrupt."

## R2 [CONCERN] Wrong altitude / duplicated knowledge
scope.py:684-686, "audit-routing-samples routes it to stderr instead, since its stdout is a JSON (or curation-markdown) data stream a header line would corrupt."

Issue: The helper's docstring describes one caller's choice. That caller already carries the rationale at its own call site (audit_routing.py:614, "stderr, not stdout: stdout is this subcommand's JSON/markdown data stream"), so the fact lives in two places.
- Six or more other callers also pass `file=sys.stderr`, so singling out one reads as the only case. Greps found:
  - sessions.py:42
  - pr_cost_export.py:359
  - turn_shape.py:288 and turn_shape.py:348
  - analyze-context.py:229, 304 and 313
- The claim is true for the one caller named, which is why this is not a False-claim finding.

Required property: delete the caller-specific clause. Keep the general rule in the `file` sentence, as in R1's third sentence. Callers carry their own reasons.

## R3 [FYI] "Used to be X" framing / reference to one caller
scope.py:680, "the one-line resolved-scope header cmd_skill_invocation already uses".

Issue:
- "already uses" is temporal framing. It describes the state before this helper existed, which only the PR history explains.
- `cmd_skill_invocation` is real, and skill_invocation.py:164 calls this function.
- That makes it one of about 50 callers, and it is the only one named as the model.
- The reference gives a future reader nothing the helper's own behavior doesn't.

Required property: drop the reference. Suggested wording: "Print the one-line resolved-scope header so machine-wide vs. --this-repo output is never scope-ambiguous."
