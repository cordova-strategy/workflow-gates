# comment-discipline-reviewer

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/review_rounds.py:1286` (the added docstring in `_pooled_compute_review_round_costs`)

Offending text: `"""compute_review_round_costs, routed through _pooled_filtered_stderr_call.` followed by `--pooled must never print the resolved root count (see _pooled_resolved_scope_header).`

Issue: The first line restates the one-line body at line 1291, which calls `_pooled_filtered_stderr_call(compute_review_round_costs, ...)`. The function name and body already show it. It states no decision and no reason.

Production failure mode: None at runtime. The line adds reading cost and will go stale if the routing changes.

Required property: Delete the first line and keep the second sentence. The second sentence names the decision (`--pooled` never discloses the root count) and points to `_pooled_resolved_scope_header`, where the reason lives (that function's docstring at line 1047 and the call-site comment at line 1388). Suggested replacement, as a one-line docstring: `"""--pooled must never print the resolved root count (see _pooled_resolved_scope_header)."""`

Checked against the other angles: the replacement is one sentence, has no PR-only labels and no prior-version framing, and the claim holds. `scope.resolve_scan_roots` and the test docstring at `test_transcript_review_rounds.py:6215-6218` show that the multi-root "scanning root N/M..." stderr diagnostic is what the filter suppresses.
