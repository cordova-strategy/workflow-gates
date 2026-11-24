# comment-discipline-reviewer

Scope: 1 file reviewed (`pr_cost_ledger.py`), 1 added docstring in scope. I set aside the later `python-environment-conventions.md` rule text: it governs Python installs and does not change this review's scope.

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/pr_cost_ledger.py:201`

Issue: the added docstring `"""The one canonical encoding of a decoded JSON-cell value (model_breakdown or review_rounds)."""` restates what the function name `_encode_json_cell` and its one-line `json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=True)` body already show. The claims in it are true, so it draws no False-or-unsourced-claim finding:
- Single encoder: `json.dumps` is called nowhere else in `pr_cost_ledger.py`, and the only callers are `pr_cost_ledger.py:523` plus `pr_cost.py:295` and `pr_cost.py:396`.
- The two named columns match the two keys of `_PR_COST_JSON_COLUMN_DECODERS` at `pr_cost_ledger.py:362-365`.

Production failure mode: the parenthetical column list duplicates `_PR_COST_JSON_COLUMN_DECODERS`, which is the authoritative set. A third JSON column added to that dict leaves this docstring stale and wrong. This is a single-source-of-truth drift risk.

Required property: delete the docstring. If a comment stays, it states only a non-obvious fact the code doesn't show. One candidate is that `_decode_model_breakdown_cell` accepts whitespace and key-order variants, and this encoder is what re-writes them canonically (the `_decode_model_breakdown_cell` docstring at `pr_cost_ledger.py:226-227` already says this). Any kept comment must not enumerate the column names.
