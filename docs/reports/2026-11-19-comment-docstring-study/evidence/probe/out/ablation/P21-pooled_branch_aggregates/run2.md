# comment-discipline-reviewer

Scope: 1 file in the diff (`claude/.claude/scripts/transcript_analysis/review_rounds.py`), 1 carried an in-scope change (the new docstring on `_pooled_branch_aggregates`, lines 852-855 at the diff's state). Set-aside prompt text: none. The session-supplied "Don't restate the code" bullet replaces CLAUDE.md's for this review. The unrelated Python-environment rules reminder has no bearing on the diff.

The docstring states no design decision: no choice made and no reason that static analysis can't find. All three clauses are findings, and the fix is to delete the whole docstring.

## R1 [CONCERN] Prose restating the code

review_rounds.py:852 — "Elementwise-sum a list of _PooledBranchTotals into one pooled total".

Issue: the function name, its `Sequence[_PooledBranchTotals]` parameter, its `_PooledBranchTotals` return type and the field-by-field `sum(...)` body (lines 857-866) already show this. The class docstring at line 736 also already says "elementwise sum of several".

Required property: delete this clause. No kept decision depends on it.

## R2 [CONCERN] Prose restating the code

review_rounds.py:852-854 — "reused identically for the true sample (point estimate) and for every bootstrap resample's own draw".

Issue: this is the call-site set. Static analysis finds it at review_rounds.py:922 (point estimate) and :927 (per-draw). It gives no reason that is invisible from this repository, and it repeats `_PooledBranchTotals`'s docstring (lines 736-738), which already names the true pool and the bootstrap draw.

Required property: delete this clause. A pointer to a doc or symbol that holds a decision may stay, but this clause points to none.

## R3 [CONCERN] Prose restating the code

review_rounds.py:854-855 — "so every reported statistic is computed the same way regardless of which list it was handed".

Issue: this is a consequence of the single function being called on both paths (lines 922 and 927), so a reader gets it from the code. The "Every stat's CI is drawn from the same resample set" rationale already sits in `_bootstrap_share_intervals`'s docstring (lines 919-920), which is where the decision lives.

Required property: delete this clause. Together with R1 and R2 this removes the docstring entirely.

## Checked, no finding

- False or unsourced claim: the reuse claim holds (:922, :927), and the "elementwise-sum" claim holds (:857-866).
- PR-defined terminology and "used to be X" framing: none found. A sweep of the file for `_pooled_branch_aggregates` found 4 hits (the class docstring, the definition, and 2 call sites), and none carries a PR-only label.
