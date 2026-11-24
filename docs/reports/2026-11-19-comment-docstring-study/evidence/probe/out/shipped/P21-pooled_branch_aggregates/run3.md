# comment-discipline-reviewer

Scope note: the Python-environment-conventions system reminder is unrelated to comment review, so I set it aside. 1 file reviewed, and 1 carried an in-scope comment change: the new docstring on `_pooled_branch_aggregates` in `review_rounds.py`.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/review_rounds.py:852-855`

Issue: the added docstring reads "Elementwise-sum a list of _PooledBranchTotals into one pooled total -- reused identically for the true sample (point estimate) and for every bootstrap resample's own draw, so every reported statistic is computed the same way regardless of which list it was handed."

Why it fails:
- The first clause restates the body (lines 857-866), where each field is a visible `sum(...)` over `per_branch`. The name and signature say the same thing.
- The rest of the sentence narrates the two call sites (`_bootstrap_share_intervals` at lines 922 and 927). I grepped, and those are the only callers, so the claim is true. It still describes callers, so it drifts when they change.
- The `_PooledBranchTotals` docstring at lines 736-738 already states the same content ("the elementwise sum of several -- the true pool, or one bootstrap resample's own draw"). The new text duplicates that single source and adds nothing the code does not show.
- It is also one dash-chained sentence carrying three ideas: what the function does, who calls it, and why. A reworded version would still restate the code or the class docstring.

Fix: delete the docstring. Nothing non-obvious remains. If a reader pointer is wanted, rely on the existing `_PooledBranchTotals` docstring (736-738) as the single home.

Prior decisions: none supplied.
