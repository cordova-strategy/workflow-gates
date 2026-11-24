# comment-discipline-reviewer

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/review_rounds.py:852-856` (the new docstring on `_pooled_branch_aggregates`)

Issue: The docstring is two clauses, and both state what static analysis of this repository finds.
- "Elementwise-sum a list of _PooledBranchTotals into one pooled total" repeats the function's name, its `Sequence[_PooledBranchTotals] -> _PooledBranchTotals` signature and its body. The body is a field-by-field `sum(b.<field> for b in per_branch)`.
- "reused identically for the true sample (point estimate) and for every bootstrap resample's own draw, so every reported statistic is computed the same way" is visible from the two call sites. Line 922 calls `_pooled_shares(_pooled_branch_aggregates(per_branch))` for the point estimate. Line 927 calls `_pooled_shares(_pooled_branch_aggregates(draw))` for each resample. It records no decision and no outside constraint that forced it.

Required property: Delete the whole docstring. Both clauses are restatements under the rule, so a shorter or corrected version would still restate. Nothing in the docstring is a non-obvious design decision with a reason static analysis cannot find. The function then needs no docstring.

Checks run:
- **Other angles:** The same text also trips Comment verbosity (the second clause's rationale), and deletion fixes that too.
- **Wrong-altitude relocation:** No relocation target applies. The caller-side behavior already sits at lines 922 and 927.
- **Cross-reference:** `_PooledBranchTotals`'s own docstring (line 736) already names this function, so the pointer is kept there and not here.
