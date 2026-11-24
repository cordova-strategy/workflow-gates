# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/pr_cost.py`); 1 docstring added in scope (`_usd_to_micros`).

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/pr_cost.py:235`

Text: `"""Integer micro-dollars the ledger's own six-decimal rendering of `dollars` denotes."""`

Issue: The docstring describes what the function returns, which its name (`_usd_to_micros`), its `-> int` signature and its `f"{dollars:.6f}"` / `scaleb(6)` body already show. The only clause beyond that, "the ledger's own six-decimal rendering", is a fact static analysis finds: `pr_cost_ledger.py:521` renders cells with `f"{value:.6f}"`, and `pr_cost_ledger.py:581` and `:657` name the ledger's six-decimal precision. It gives no reason for the decision, so it doesn't meet the rule's bar for a kept decision: it names the choice but not why the choice was made. It reads as a shorter restatement of the body.

Claim check (False or unsourced claim): the claim is true at the diff's state, so no finding on that angle. The `.6f` rendering is at `pr_cost_ledger.py:521`.

Production failure mode: none. This is documentation noise that restates the body, and it can drift if the ledger's precision changes.

Required property: Delete the docstring. Keep a comment only if it states why the conversion goes through the six-decimal string instead of scaling the float directly (for example, so the micros agree exactly with the ledger's stored scalar columns that `_check_model_breakdown_cell` compares them against). That reason has to be verified in the code before it is written down. If kept, lead with the decision and the reason, and drop the "Integer micro-dollars ... denotes" return description.
