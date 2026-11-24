# comment-discipline-reviewer

Reviewed 1 file (`review_rounds.py`); 1 carried an in-scope comment change (the new `_pooled_branch_aggregates` docstring).

## R1 [CONCERN] Restating the code

File and line: `claude/.claude/scripts/transcript_analysis/review_rounds.py:852-856`

Issue: the added docstring is "Elementwise-sum a list of _PooledBranchTotals into one pooled total -- reused identically for the true sample (point estimate) and for every bootstrap resample's own draw, so every reported statistic is computed the same way regardless of which list it was handed."

- Clause 1 restates the function body. The body is a field-by-field `sum(... for b in per_branch)`, and the name and signature already say "pooled branch aggregates" of a `Sequence[_PooledBranchTotals]`.
- Clause 2 repeats `_PooledBranchTotals`'s own docstring at lines 736-738: "the elementwise sum of several -- the true pool, or one bootstrap resample's own draw". That is the same fact in a second home, which breaks single-source-of-truth.
- The call sites at lines 922 and 927 (`_bootstrap_share_intervals`) show the point-estimate and resample reuse, so the caller fact is also visible in the code.
- The trailing "so ... regardless of which list it was handed" clause adds nothing. A pure function of its argument is trivially "the same way" for any list.

I read the reuse claim against its subject and it holds. `Grep` for `_pooled_branch_aggregates(` finds exactly two production call sites, 922 (the true sample) and 927 (each resample), plus a test. Nothing in the docstring is false. The finding is about restatement, not accuracy.

Production failure mode: none at runtime. Two docstrings now carry the same account, and one can drift from the other if a third caller or a non-bootstrap use appears.

Required property: delete the docstring. The `_PooledBranchTotals` docstring is the canonical home for "sum of several = true pool or one resample draw". If a docstring is kept, it must state something the code does not show. Examples are an invariant on inputs, such as every branch's `skill_round_counts` carrying all `REVIEW_SKILLS` keys (the `b.skill_round_counts[s]` lookups raise `KeyError` otherwise), or the empty-sequence result (all zeros). It must then be split into one sentence per fact, with no dash-chained "so" tail.
