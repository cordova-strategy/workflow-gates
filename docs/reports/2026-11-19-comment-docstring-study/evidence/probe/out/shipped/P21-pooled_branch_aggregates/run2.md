# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/review_rounds.py`); 1 carried an in-scope comment change (one added docstring on `_pooled_branch_aggregates`).

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/review_rounds.py:852-856` (added docstring on `_pooled_branch_aggregates`).

Issue: The docstring reads "Elementwise-sum a list of _PooledBranchTotals into one pooled total -- reused identically for the true sample (point estimate) and for every bootstrap resample's own draw, so every reported statistic is computed the same way regardless of which list it was handed."

- The first clause restates the function name, its `Sequence[_PooledBranchTotals] -> _PooledBranchTotals` signature, and the body (`sum(...)` per field, over `REVIEW_SKILLS` for the dict fields).
- The second clause restates the call sites at lines 922 and 927 (`_bootstrap_share_intervals`). I read both and the claim is true, so it is not a false claim. It is the caller's behavior, though, and the caller shows it.
- The same fact is already stated at the type's own home. The `_PooledBranchTotals` docstring (lines 736-738) says it is the "elementwise sum of several -- the true pool, or one bootstrap resample's own draw". That makes this docstring a second statement of it, against single-source-of-truth.

Production failure mode: A future change to the callers, such as a third caller or a different resampling scheme, leaves this docstring describing the old call pattern. The class docstring would then need the same edit.

Required property: Delete the docstring. The name, signature and body show the elementwise sum. The class docstring already carries the true-pool vs. resample-draw fact. Keep nothing, since a shorter restatement still restates. The dash-chained "reused ... so ..." sentence would otherwise also draw a Multi-fact comment structure finding.
