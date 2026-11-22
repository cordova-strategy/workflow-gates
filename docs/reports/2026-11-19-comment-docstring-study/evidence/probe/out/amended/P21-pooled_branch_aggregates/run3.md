# comment-discipline-reviewer

Scope: 1 file reviewed, 1 carried an in-scope comment change (the new docstring on `_pooled_branch_aggregates`, `review_rounds.py:852-856`).

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/review_rounds.py:852-856`

Issue: the added docstring reads "Elementwise-sum a list of _PooledBranchTotals into one pooled total -- reused identically for the true sample (point estimate) and for every bootstrap resample's own draw, so every reported statistic is computed the same way regardless of which list it was handed."

- The first clause restates the function's name, signature and body: it sums the `_PooledBranchTotals` fields and returns one `_PooledBranchTotals`.
- The second clause (reused for the point estimate and each bootstrap draw) is what the two call sites show. Both are in the same file, at lines 922 and 927 in the post-diff file.
- The "so every statistic is computed the same way" tail is a restatement of that reuse. It gives no reason static analysis cannot find and no outside constraint.
- `_PooledBranchTotals`'s own docstring (line 736-738) already states this point ("the true pool, or one bootstrap resample's own draw"), so the new text also duplicates a canonical home.

Production failure mode: the docstring adds nothing the code and class docstring don't show. It will drift if a third caller is added, because its caller list is a hand-maintained copy of what a grep finds.

Required property: delete the docstring. No non-obvious decision is left to keep. No kept-decision sentence exists, so nothing needs a subject preserved. A shorter or corrected version of the text would still restate, so don't rewrite it.

The same site also fails Multi-fact comment structure, because the dash chain carries three facts in one sentence. Deletion resolves that finding too.
