# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/check-handoff.py`); 1 carried an in-scope comment change.

## R1 [CONCERN] Restating the code

- File:line: `claude/.claude/scripts/check-handoff.py:95-98` (the new `strip_code_spans` docstring)
- Issue: The docstring opens with "Remove fenced code blocks and inline code spans". The function name, its `_FENCED_BLOCK_RE` and `_INLINE_CODE_RE` calls and the sibling constants at lines 77-78 already show this. The same sentence then chains the actual non-obvious fact behind a dash, so a reader has to get through the restatement to reach it.
- Production failure mode: None at runtime. The restating clause is noise that has to be kept in sync with the regexes. It also pushes the one useful fact, why code spans are stripped, into a dash-joined tail.
- Required property: Delete the restating clause and keep only the rationale, as its own sentence. For example: "Callers scan for placeholders and anchor shapes. Quoted literals in code spans or fences are citations, not proposed next steps, so they must not trigger those scans." The rationale itself checks out. Its callers are `check_placeholder_text` (line 165) and the §3.5 anchor-shape check (line 191).

No other angles fired. The docstring has no PR-defined labels, no prior-version framing and no unsourced claims.
