# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/redaction.py`); 1 carried an in-scope comment change (one added docstring).

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/redaction.py:195`

Offending text: `"""Apply a run-scoped session-id redact map; fails closed to a fixed token on a miss."""`

Issue: Every clause restates what the code and its neighbours show.
- "Apply a run-scoped session-id redact map" restates the function name, its `session_redact_map` parameter, and the `_assign_session_redact_label` docstring at line 183 ("the first time it's seen this run").
- "fails closed to a fixed token on a miss" restates the body at line 196, `session_redact_map.get(session_id, _REDACT_SESSION_MISS_TOKEN)`. The fallback value is named by the `_REDACT_SESSION_MISS_TOKEN` constant at line 179.

The docstring states no decision with a reason that static analysis cannot find. "Fails closed" names the decision but gives no reason, and the rule says a shorter or corrected restatement still restates.

Failure mode: none at runtime. The docstring adds nothing the code does not show, and it can drift if the miss behaviour changes.

Required property: delete the docstring.

To keep the miss behaviour as a documented decision, replace it with one sentence naming the decision and the outside-the-code reason. That reason would be that an unmapped session id must never reach output as the raw id. Add it only if the reason is confirmed as the author's intent. The reviewer could not find that reason stated anywhere in the repository.
