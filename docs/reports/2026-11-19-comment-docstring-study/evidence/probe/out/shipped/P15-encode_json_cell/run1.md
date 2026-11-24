# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/pr_cost_ledger.py`); 1 carried an in-scope comment change (one added docstring on `_encode_json_cell`, line 201).

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/pr_cost_ledger.py:201`

Issue: The docstring `"""The one canonical encoding of a decoded JSON-cell value (model_breakdown or review_rounds)."""` says what the function name `_encode_json_cell` already says, so it restates the code.

Production failure mode: None at runtime. The docstring leaves out the one fact a reader needs, which is what "canonical" means here (`sort_keys=True`, compact `(",", ":")` separators, `ensure_ascii=True`). Those settings are visible in the body, so naming them would restate the code too.

Required property: Delete the docstring. If a non-obvious constraint is meant, state that constraint and not the label "canonical". Examples are "the encoded text is compared and length-bounded byte-for-byte, so changing these options changes persisted cells", or whatever the persisted-contract comment at lines 150-152 supports. The claim itself is true. I read the module and its callers and found no other encoder of these cells: `json.dumps` appears once in `pr_cost_ledger.py` (line 202), and `pr_cost.py:295,396` and `pr_cost_export.py` call this function.

## R2 [FYI] Restating the code / single source of truth

File: `claude/.claude/scripts/transcript_analysis/pr_cost_ledger.py:201`

Issue: The parenthetical `(model_breakdown or review_rounds)` hand-lists the JSON columns. The authoritative list is `_PR_COST_JSON_COLUMN_DECODERS` (line 362), which `_render_*` at line 522 iterates. It is accurate today (both keys are present at lines 363-364). It becomes false once a column is appended, and lines 150-152 say new cell shapes arrive as appended columns.

Required property: Drop the parenthetical, or refer to `_PR_COST_JSON_COLUMN_DECODERS` instead of listing the names. Deleting the whole docstring (R1) resolves this too.

Prior decisions: none supplied.
