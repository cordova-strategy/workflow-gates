# comment-discipline-reviewer

## R1 [CONCERN] Prose restating the code

File: `claude/.claude/scripts/transcript_analysis/pr_cost_ledger.py:201` (added docstring on `_encode_json_cell`)

Issue: The added docstring reads `"""The one canonical encoding of a decoded JSON-cell value (model_breakdown or review_rounds)."""`. Its clauses restate what the code shows:
- "encoding of a decoded JSON-cell value" repeats the function name `_encode_json_cell` and its `value: dict` and `-> str` signature.
- "the one canonical encoding" restates the single `json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=True)` call.
- "(model_breakdown or review_rounds)" lists the function's callers, which a grep of the repository finds.

None of these clauses names a decision with a reason that static analysis cannot find. Under the Don't-restate-the-code rule, a docstring keeps only such decisions and deletes every other clause, even a true one.

Production failure mode: The caller list goes stale when a third JSON cell is added, and nothing flags it. A reader then trusts a wrong list.

Required property: Delete the docstring, leaving `_encode_json_cell` with no docstring. Keep a comment only if it states why the encoding is fixed this way, for example a byte-stable output that something outside this repository compares or hashes. Nothing in the diff shows such a reason.
