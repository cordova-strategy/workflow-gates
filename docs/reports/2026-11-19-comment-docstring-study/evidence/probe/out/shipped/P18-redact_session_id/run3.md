# comment-discipline-reviewer

Reviewed 1 file; 1 carried an in-scope comment change (one added docstring). The system-reminder rules file on Python environment conventions is unrelated to comment discipline, so I set it aside.

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/redaction.py:195`

Offending text: `"""Apply a run-scoped session-id redact map; fails closed to a fixed token on a miss."""`

Issue: The docstring restates what the one-line body at line 196 already shows. Both halves are visible without it:
- "Apply a ... redact map" repeats the function name `_redact_session_id` and its `session_redact_map` parameter.
- "fails closed to a fixed token on a miss" repeats `.get(session_id, _REDACT_SESSION_MISS_TOKEN)`. The constant's name (`_REDACT_SESSION_MISS_TOKEN`, defined at line 179 as `"session-unmapped"`) also says it.

The run-scoped nature of the map is already documented in the sibling `_assign_session_redact_label` docstring (lines 183-188).

I checked the claim itself against line 196 and the constant at line 179. It is accurate, so there is no false-claim finding. The failure is that it restates the code.

Required property: Delete the docstring. A shorter or corrected restatement would still restate. The "map miss returns an opaque token, not the raw id" guarantee is already pinned by `test_redact_session_id_map_miss_returns_opaque_token_not_raw_id` (`test_transcript_cost.py:498`).

Verdict: Approve with concerns.
