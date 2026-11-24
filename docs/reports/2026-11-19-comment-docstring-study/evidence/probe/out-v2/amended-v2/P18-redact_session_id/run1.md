# comment-discipline-reviewer

## R1 [CONCERN] Restating the code

- **File:line:** `claude/.claude/scripts/transcript_analysis/redaction.py:195`
- **Offending text:** `"""Apply a run-scoped session-id redact map; fails closed to a fixed token on a miss."""`
- **Issue:** The docstring states only what the code already shows, so it fails "Don't restate the code".
  - "Apply a run-scoped session-id redact map" restates the function name and signature. The run scope is also stated in `_assign_session_redact_label`'s docstring (`redaction.py:183`).
  - "fails closed to a fixed token on a miss" restates `session_redact_map.get(session_id, _REDACT_SESSION_MISS_TOKEN)` on the next line.
  - The only candidate decision is "fail closed". The docstring gives no reason for it, and the reason is findable by static analysis. The test docstring at `tests/test_transcript_cost.py:501` says a miss returns an opaque token and never the raw session ID, and the assertion at line 505 checks that.
  - The docstring names no outside constraint and no trigger to revisit.
- **Production failure mode:** None at runtime. The docstring adds a line that can drift from the code, such as a changed default or a different miss behavior, and tells the reader nothing the body doesn't.
- **Required property / concrete fix:** Delete the docstring. No decision-plus-reason survives it. If a pointer is wanted, add one sentence naming the fail-closed decision and where its reason lives, for example "A miss returns `_REDACT_SESSION_MISS_TOKEN` rather than the raw ID; see `test_transcript_cost.py` for the contract." Deletion is the default.
