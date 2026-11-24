# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/pr_cost_ledger.py`); 1 carried an in-scope comment change (one added docstring).

Set aside: the system reminder carrying `python-environment-conventions.md`. It concerns installing Python dependencies and does not bear on this review.

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/pr_cost_ledger.py:201`

Issue: the added docstring is `"""The one canonical encoding of a decoded JSON-cell value (model_breakdown or review_rounds)."""`. It states no design decision and gives no reason static analysis cannot find.
- The function name and body already show that it is the encoding of a JSON-cell value (`json.dumps` with `sort_keys`, compact separators, `ensure_ascii`).
- The parenthetical naming `model_breakdown` and `review_rounds` restates `_PR_COST_JSON_COLUMN_DECODERS` (lines 362-365). That registry is the single place that lists which columns are JSON cells.
- "The one canonical" is a uniqueness claim a grep settles. All three call sites route through this function: `pr_cost_ledger.py:523`, `pr_cost.py:295` and `pr_cost.py:396`. The claim is true, but it is also what static analysis finds, so it is a restatement rather than a decision.

Production failure mode: the column list goes stale when a third JSON column is added to the decoder registry, and a stale list in a docstring is a second source of truth. Nothing the docstring says tells a reader why the encoding is sorted, compact and ASCII.

Required property: delete the docstring. Keep a comment only if it names a decision with a reason from outside the code. One candidate is why the encoding must be byte-stable, such as a round-trip or ledger-compatibility requirement. The author must supply that reason. I did not find one in the repository and will not invent one. Any replacement should name what was decided (sorted keys, compact separators, ASCII-only) together with its reason, and should not list the columns.

Request changes is not warranted; this is a single low-severity concern.

**Approve with concerns** (R1).
