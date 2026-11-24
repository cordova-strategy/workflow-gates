# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/redaction.py`); 1 carried an in-scope comment change (one added docstring, two clauses).

## R1 [CONCERN] Prose restating the code

`claude/.claude/scripts/transcript_analysis/redaction.py:195`

Issue: the clause "Apply a run-scoped session-id redact map" in the added docstring `"""Apply a run-scoped session-id redact map; fails closed to a fixed token on a miss."""`.

Production failure mode: none. It adds a restatement the reader can already see, and it will go stale if the function changes.

Required property: the function's name (`_redact_session_id`) and its `session_redact_map` parameter already say this. `audit_routing.py:119`, `cost.py:787`, `handoff_signal_response.py:362` and `user_input.py:249` show that the map is built per run. Static analysis finds all of it. Fix: delete the clause.

## R2 [CONCERN] Prose restating the code

`claude/.claude/scripts/transcript_analysis/redaction.py:195`

Issue: the clause "fails closed to a fixed token on a miss" in the same docstring.

Production failure mode: none. It adds a restatement the reader can already see, and it will go stale if the function changes.

Required property: line 196, `session_redact_map.get(session_id, _REDACT_SESSION_MISS_TOKEN)`, shows this branch directly. The constant is defined at line 179 as `"session-unmapped"`. `test_redact_session_id_map_miss_returns_opaque_token_not_raw_id` in `tests/test_transcript_cost.py:498-505` also covers it. The clause names no reason that static analysis cannot find, such as why a raw ID must never fall through. Fix: delete the clause. With both clauses gone, the docstring is empty, so remove it entirely. If the author wants to keep the fail-closed decision, the docstring must state the external reason for it, and not only the behavior.
