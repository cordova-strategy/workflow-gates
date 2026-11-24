# comment-discipline-reviewer

## R1 [CONCERN] False or unsourced claim

- **File:line:** `claude/.claude/scripts/transcript_analysis/render.py:130` (added docstring).
- **Text:** `"""Strip ASCII control characters from a --deny-summary table cell value."""`
- **Issue:** The docstring scopes the helper to `--deny-summary`. That scope is false. The subject contradicts it: `_sanitize_table_cell` is also called from these places:
  - `redaction.py:20` (import) and `redaction.py:246`
  - `review_rounds.py:1436`
  - `subagent_mix.py:254`, `266`, `550` and `570`
  - `subagents.py:185` and `225`
  - Only the `review_trace.py` calls (`78`–`134`) serve `--deny-summary`. The same file's `review_trace.py:2`, `48` and `52` references show that flag is one consumer among several.
- **Why it matters:** A future contributor reading "--deny-summary" will assume the helper is private to that flag. They may change its behaviour without checking the other commands, including the redaction path that builds `account-<n>/…` labels.
- **Supported part:** "ASCII control characters" matches `_CONTROL_CHAR_RE = r"[\x00-\x1f\x7f]"` (`render.py:126`).
- **Required property and fix:** Remove the `--deny-summary` scoping. The narrowest accurate statement is "strip ASCII control characters from a table cell value, shared by several transcript-analysis commands". The "strip control characters" half only restates the regex and function name, which is a Prose-restating-the-code finding. The non-obvious fact is that many commands share the helper, and the docstring doesn't need to list them. The cleanest outcome is to delete the docstring. If a comment is kept, it should say only why cells are sanitised, for example to stop control characters in transcript-derived values breaking the table layout. Mark that rationale unverified unless the cause is confirmed in the code.
