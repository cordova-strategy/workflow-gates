# comment-discipline-reviewer

## R1 [CONCERN] Restating the code

File: claude/.claude/scripts/transcript_analysis/pr_cost_ledger.py:201

Issue: the added docstring `"""The one canonical encoding of a decoded JSON-cell value (model_breakdown or review_rounds)."""` states no design decision with a reason. "Canonical encoding" is what the name `_encode_json_cell` and the `json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=True)` call already show. The parenthetical naming `model_breakdown` and `review_rounds` lists the callers, which a grep finds (the single call site at line 523 dispatches on `_PR_COST_JSON_COLUMN_DECODERS`, whose keys are those two columns). "The one" is also true by grep (`json.dumps` appears only at line 202), so it adds nothing static analysis does not find.

Production failure mode: none at runtime. The docstring adds a second place that must track the set of JSON columns, so it goes stale when a third JSON column is added.

Required property: delete the docstring. Keep a comment only if it states a reason static analysis cannot find, e.g. why the encoding must be byte-stable (the persisted-contract comment at lines 150-152 and the `_decode_model_breakdown_cell` docstring's "re-encodes canonically on the next write" already point at the decision). If kept, name that decision and its reason, and drop the caller list.
