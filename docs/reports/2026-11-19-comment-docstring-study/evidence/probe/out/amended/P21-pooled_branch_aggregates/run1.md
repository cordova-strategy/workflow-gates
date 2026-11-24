# comment-discipline-reviewer

Reviewed 1 file (`review_rounds.py`); 1 added docstring in scope (`_pooled_branch_aggregates`). Pre-existing comments elsewhere in the file are not in the diff and are out of scope.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/review_rounds.py:852-856` (added docstring on `_pooled_branch_aggregates`).

Offending text: "Elementwise-sum a list of _PooledBranchTotals into one pooled total -- reused identically for the true sample (point estimate) and for every bootstrap resample's own draw, so every reported statistic is computed the same way regardless of which list it was handed."

Issue: every clause is findable by static analysis of this repository, and none states a design decision.
- "Elementwise-sum a list of _PooledBranchTotals into one pooled total" restates the function body (lines 857-866: `sum(...)` over each field) and its signature and return type.
- "reused identically for the true sample ... and for every bootstrap resample's own draw" restates the two call sites in `_bootstrap_share_intervals` (lines 922 and 927; `Grep` for `_pooled_branch_aggregates` returns exactly those two non-test hits). It is a pointer to callers, not a decision.
- "so every reported statistic is computed the same way" is the consequence of having a single function. It is also visible in the code. No outside constraint forces it, and no reason is given that static analysis cannot find.
- The `_PooledBranchTotals` docstring (lines 736-738) already states "the elementwise sum of several -- the true pool, or one bootstrap resample's own draw", so this restates a second time as well.

Production failure mode: none at runtime. The comment adds maintenance surface that drifts when a third caller appears or a field is added, and the claims are currently true, so the cost is noise only.

Required property: delete the docstring. No clause names a decision with a reason outside the code, so nothing is left to keep. Do not replace it with a shorter or corrected restatement. The `_PooledBranchTotals` docstring stays the home for the "elementwise sum of several" fact. Deletion introduces no violation under any other angle.
