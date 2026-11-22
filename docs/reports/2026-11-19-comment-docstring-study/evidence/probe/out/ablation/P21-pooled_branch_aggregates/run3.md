# comment-discipline-reviewer

Scope: 1 file reviewed (`review_rounds.py`), 1 carried an in-scope change (one added docstring on `_pooled_branch_aggregates`, diff lines 8-12). The docstring has three clauses, and each draws its own finding under the session's "Don't restate the code" rule. The function body itself is unchanged.

Text set aside: none. The python-environment rule file in the context does not bear on this diff.

## R1 [CONCERN] Prose restating the code

`review_rounds.py:852` (diff line 8): "Elementwise-sum a list of _PooledBranchTotals into one pooled total".

- Issue: The clause restates the signature (`Sequence[_PooledBranchTotals]` in, `_PooledBranchTotals` out) and the body (`sum(b.<field> for b in per_branch)` for every field, lines 857-866). It records no decision and no outside constraint.
- Production failure mode: A restated body drifts when a field is added to `_PooledBranchTotals`. Nothing marks the docstring as stale then.
- Required property: Delete the clause. It holds no kept decision, so nothing replaces it.

## R2 [CONCERN] Prose restating the code

`review_rounds.py:852-854` (diff lines 8-10): "reused identically for the true sample (point estimate) and for every bootstrap resample's own draw".

- Issue: The clause lists the function's call sites, and a grep of the repo finds them. I confirmed both: `_bootstrap_share_intervals` calls it at line 922 for the point estimate and at line 927 for each draw. The claim is true, so no false-claim finding applies. It is still a restatement of what static analysis of the repository finds.
- Production failure mode: A new caller or a removed one makes the list wrong without any signal.
- Required property: Delete the clause. The callers are the authority on how they use it.

## R3 [CONCERN] Prose restating the code

`review_rounds.py:854-855` (diff lines 10-11): "so every reported statistic is computed the same way regardless of which list it was handed".

- Issue: The clause restates the consequence of the function being one pure sum applied to any list, which the body and the two call sites already show. It names no reason static analysis cannot find and no outside force.
- Production failure mode: None beyond noise. The docstring is longer than the one non-obvious fact it could carry, and it carries none.
- Required property: Delete the clause. With R1 and R2 applied, the docstring is empty, so delete the whole docstring.
