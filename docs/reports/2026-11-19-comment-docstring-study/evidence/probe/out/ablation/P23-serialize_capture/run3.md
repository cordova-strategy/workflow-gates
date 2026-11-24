# comment-discipline-reviewer

Scope: 1 file reviewed (`routing_guard.py`), 1 carried an in-scope comment change (one added docstring). No prompt text was set aside.

## R1 [CONCERN] Prose restating the code

- **File:line:** `claude/.claude/scripts/transcript_analysis/routing_guard.py:693`
- **Issue:** The added docstring `"""ASCII-only, so the text encodes the same under any locale."""` states the output's encoding. `json.dumps` is called at lines 694-708 without `ensure_ascii`, so the ASCII-only output comes from the standard library default (`ensure_ascii=True`). Static analysis of the call and the standard library finds both the ASCII-only property and its locale independence. Under the session's "Don't restate the code" rule, that is a restatement even though it is true.
- **Production failure mode:** None at runtime. The docstring presents a library default as a design decision. A later reader may take it for a guarantee this function enforces. A caller could then pass `ensure_ascii=False` in a refactor, and the claim would go stale with no signal.
- **Required property:** Delete the docstring clause. Nothing is left to keep, because the function sets no non-default option for ASCII and the clause names no decision the code makes. If the ASCII-only output is a deliberate contract, for example because the text is hashed or compared across machines, pass `ensure_ascii=True` explicitly. Document in a comment only what outside this repository forces that, and name the consumer.
