# comment-discipline-reviewer

Reviewed 1 file (`review_rounds.py`); 1 carried an in-scope comment change (new docstring on `_pooled_compute_review_round_costs`, lines 1286-1290).

## R1 [CONCERN] Wrong altitude / Restating the code

`claude/.claude/scripts/transcript_analysis/review_rounds.py:1286-1290`

Issue: the docstring's first line, "compute_review_round_costs, routed through _pooled_filtered_stderr_call.", restates the one-line body (`return _pooled_filtered_stderr_call(compute_review_round_costs, ...)`). Static analysis of the function shows it, so under the session's rule it is deleted, even though it is true and short.

Second sentence, "--pooled must never print the resolved root count (see _pooled_resolved_scope_header)", is the kept decision: a non-disclosure policy the code can't show. As written it names the constraint but not what was decided, so the reason for the wrapper is missing. The pointer is to the header builder, which handles `print_resolved_scope`. The stderr leak this wrapper closes is scope's "scanning root N/M..." diagnostic (see the comment at ~1393 and the test docstring at test_transcript_review_rounds.py:6213-6218).

Required property: delete the first line. Keep one sentence that names the decision and its reason, with the subject inside it. For example: "Filters stderr because --pooled must never disclose the resolved root count, which scope's multi-root diagnostics would print (see _pooled_resolved_scope_header for the stdout side)." The result must not restate that the function calls `_pooled_filtered_stderr_call`.

No other angles apply: no PR-defined labels, no prior-version framing, no unsourced claims. The claims I checked match the repo (root-count disclosure in `scope`, `_pooled_resolved_scope_header` docstring at lines 1047-1052).
