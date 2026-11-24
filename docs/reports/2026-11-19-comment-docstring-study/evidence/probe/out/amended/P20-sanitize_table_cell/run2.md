# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/render.py`); 1 carried an in-scope docstring change.

## R1 [CONCERN] Restating the code

- File:line: `claude/.claude/scripts/transcript_analysis/render.py:130`
- Offending text: `"""Strip ASCII control characters from a --deny-summary table cell value."""`
- Issue: The docstring restates the function name (`_sanitize_table_cell`) and its body (`_CONTROL_CHAR_RE.sub("", value)` with `_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")` at line 126). It states no design decision and no reason static analysis cannot find.
- Production failure mode: The "--deny-summary" scope is also wrong. Callers outside `--deny-summary` use the function: `review_rounds.py:1436`, `subagent_mix.py:254,266,550,570`, `subagents.py:185,225`, and `redaction.py:246`. A corrected scope would still restate the code, so correcting it is not the fix.
- Required property: Delete the docstring. Keep a comment only if it states why control characters are stripped, meaning a reason found outside this repository's code. The only such reason in the diff is the hook-output rationale at `denials.py:22`. If a pointer to that rationale is wanted, cite it there without a scope claim.

Prior decisions: none supplied.
