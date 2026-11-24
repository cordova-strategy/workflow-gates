# comment-discipline-reviewer

## R1 [CONCERN] Restating the code

File: claude/.claude/scripts/transcript_analysis/review_rounds.py:852-856 (added docstring on `_pooled_branch_aggregates`).

Issue: The docstring reads "Elementwise-sum a list of _PooledBranchTotals into one pooled total -- reused identically for the true sample (point estimate) and for every bootstrap resample's own draw, so every reported statistic is computed the same way regardless of which list it was handed." Every clause is something static analysis of this repository finds:
- The first clause restates the function name, its `Sequence[_PooledBranchTotals]` signature and its `sum(...)` body (lines 857-866).
- The second clause restates the two call sites in `_bootstrap_share_intervals` (lines 922 and 927).
- The class docstring on `_PooledBranchTotals` (lines 736-738) already says the same thing: "the elementwise sum of several -- the true pool, or one bootstrap resample's own draw". That is a second statement of one fact, which breaks single-source-of-truth.

Nothing in it is a design decision with a reason that code and tests cannot show. The "computed the same way" clause only names what the shared call already shows.

The docstring also says "list" where the signature takes a `Sequence`. This is a minor imprecision, and it is moot once the docstring is deleted.

Required property: Delete the docstring. The `_PooledBranchTotals` class docstring is the one home for the "true pool or resample draw" fact. If the author wants a pointer, a short one to that class is the most that stays. Do not shorten or correct the restatement instead, because a shorter restatement still restates.
