# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/compaction-context.py`); 1 carried an in-scope comment change (the new `_prompt_text` docstring, line 111).

No comment-discipline concerns.

- The docstring is one sentence of a tightly coupled pair: what the function returns (NUL removed) and why (the closer and emptiness checks judge the text the block emits). The "why" is not visible from the body.
- The docstring is accurate against the file:
  - `_is_prompt_candidate` (line 207) runs the task-notification closer check on `_prompt_text(rec)`.
  - `_quoted_text` (lines 244-245) runs the emptiness check on `_prompt_text(rec)`.
  - `_quoted_text` then returns that same text, or text derived from it, for emission.
- It uses no PR-defined labels, prior-version framing or unsourced numeric/causal claims.
