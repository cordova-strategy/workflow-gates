# comment-discipline-reviewer

Reviewed 1 file (`pr_cost.py`); 1 carried an in-scope comment change.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/pr_cost.py:235`

Issue: the added docstring `"""Integer micro-dollars the ledger's own six-decimal rendering of `dollars` denotes."""` describes what the function returns.
- The name `_usd_to_micros`, the `-> int` signature and the body (`f"{dollars:.6f}"`, `.scaleb(6)`) already show this.
- Its one candidate decision is "the ledger's own six-decimal rendering". Static analysis finds that: `pr_cost_ledger.py:521` formats cells with `f"{value:.6f}"`.
- No outside-the-repo force and no reason is stated for rounding through a string, such as why the code avoids `round(dollars * 1e6)`. Nothing here is a non-obvious decision whose reason static analysis cannot find.

Required property: delete the docstring. A shorter or corrected version would still restate. If the author wants a comment, it must state the actual decision and its reason. For example: the code rounds through the six-decimal string so micros match the ledger cell text, which keeps the tolerance reasoning at lines 314-315 sound. That reason is a pointer to a decision, not a description of the return value.
