# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/redaction.py`); 1 carried an in-scope comment change (one added docstring). I set aside the injected Python-environment-conventions reminder: it concerns installing dependencies and does not change this review's scope.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/redaction.py:195`

- **Offending text:** `"""Apply a run-scoped session-id redact map; fails closed to a fixed token on a miss."""`
- **Issue:** The docstring restates the one-line body, `session_redact_map.get(session_id, _REDACT_SESSION_MISS_TOKEN)`. The function name, the parameter name and the `.get` default already show that a map lookup falls back to a fixed token on a miss. The constant's name (`_REDACT_SESSION_MISS_TOKEN`, line 179) and the test at `tests/test_transcript_cost.py:498-505` also cover it. "Run-scoped" is stated by the sibling `_assign_session_redact_label` docstring (lines 183-188), which says the map is written by each command's own single pass.
- **Accuracy check:** The claim is true, so this is not a False or unsourced claim finding. A miss returns `"session-unmapped"` (line 179), never the raw id (line 196).
- **Required property:** Delete the docstring. Per CLAUDE.md §Durable text, a shorter or corrected restatement still restates. If the intent that a miss must never leak the raw id is worth recording, put it once as a comment on `_REDACT_SESSION_MISS_TOKEN` at line 179, where the value is defined. Do not repeat it on this function.
