# comment-discipline-reviewer

Scope: 1 file in the diff (`review_rounds.py`), 1 with an in-scope change (one new docstring, two clauses).

## R1 [CONCERN] Restating the code
`claude/.claude/scripts/transcript_analysis/review_rounds.py:1286` (new docstring, first clause)

Issue: `"""compute_review_round_costs, routed through _pooled_filtered_stderr_call."""` restates the one-line body `return _pooled_filtered_stderr_call(compute_review_round_costs, *args, **kwargs)`.

Production failure mode: the clause adds nothing the call shows and goes stale if the wrapper changes.

Required property: delete this clause. It decides nothing and gives no reason.

## R2 [CONCERN] Restating the code
`claude/.claude/scripts/transcript_analysis/review_rounds.py:1288-1289` (new docstring, second clause)

Issue: `--pooled must never print the resolved root count (see _pooled_resolved_scope_header).` gives no reason for the constraint. The reason (root-count disclosure, and which stream leaks it) is already stated at its canonical sites:
- `_pooled_resolved_scope_header`'s docstring (line 1048).
- The comment in `cmd_review_round_cost` (lines 1388-1389).
- The comment at lines 1359-1360 on the `declared root N unreadable` warning.

The pooled-stderr filtering rule sits in `_pooled_filtered_stderr_call` (line 1260), whose docstring points at `_POOLED_STDERR_DIAGNOSTIC_RES`. A reader of the wrapper already reaches that rule through the call.

Production failure mode: a fourth statement of the same rule that must stay in sync with the others, which breaks single-source-of-truth.

Required property: delete the clause, so the whole docstring goes. If you keep a trace of the decision, keep only the pointer to `_pooled_resolved_scope_header`, and only if it is joined to a stated reason. A bare "must never print" names what was decided but not why.

Prior decisions: none handed in.
