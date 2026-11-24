# comment-discipline-reviewer

## R1 [CONCERN] False or unsourced claim

File: claude/.claude/scripts/transcript_analysis/render.py:130

Issue: The added docstring `"""Strip ASCII control characters from a --deny-summary table cell value."""` scopes the helper to `--deny-summary`. The repository contradicts that scope. Only `review_trace.py:78-134` prints `--deny-summary` tables. The same function is also called from non-deny-summary paths:
- `subagent_mix.py:254`, `:266`, `:550`, `:570`
- `subagents.py:185`, `:225`
- `review_rounds.py:1436`
- `redaction.py:246` (`_root_scoped_display_label`)

Production failure mode: A contributor reads the docstring, concludes the helper is deny-summary-only, and skips it when adding cells to the other reports. Or they treat it as safe to change deny-summary-specific behaviour and break the other callers.

Required property: Drop the `--deny-summary` scoping. For example: "Strip ASCII control characters (C0 range and DEL) from a value printed in a table cell." `_CONTROL_CHAR_RE` at `render.py:126` is `[\x00-\x1f\x7f]`, so that wording matches what the regex does.

## R2 [FYI] Restating the code

File: claude/.claude/scripts/transcript_analysis/render.py:130

Issue: "Strip ASCII control characters" repeats what the function name `_sanitize_table_cell` and the `_CONTROL_CHAR_RE` pattern already show. The only non-obvious fact the docstring could carry is why cells are sanitized. The existing `TestSanitizeTableCell` docstring (`test_transcript_render.py:161`) describes that purpose as a defense-in-depth control-character strip against terminal escape injection.

Required property: Either delete the docstring, or replace it with the one non-obvious fact: why the strip exists (it keeps terminal escape sequences from reaching printed tables). Once R1 is fixed, the docstring should state only that reason.
