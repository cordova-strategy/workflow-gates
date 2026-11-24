# comment-discipline-reviewer

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/scope.py:1095-1097` (the new docstring on `_attribute_carried_branch`)

Offending text: "Apply only the pre-branch step to a branch a positional consumer carried forward from the main thread, using the record's own timestamp so a record with none is never remapped."

Issue: every clause is something static analysis of this repository finds, so the docstring fails the amended "Don't restate the code" rule.
- "Apply only the pre-branch step", "using the record's own timestamp": the one-line body is `_attribute_pre_branch(carried, _parse_ts(rec.get("timestamp")), ctx.pre_branch_run)` (scope.py:1098).
- "so a record with none is never remapped": `_attribute_pre_branch` already states and implements this (scope.py:1037-1044, `ts is None` returns `branch` unchanged and its docstring says "a None timestamp [is] never remapped").
- "a positional consumer carried forward from the main thread": the only callers are `review_rounds._session_record_branches` (review_rounds.py:245-264) and `review_trace` (review_trace.py:249, 308). `_session_record_branches` documents the carry-forward at review_rounds.py:240-247.

Production failure mode: the docstring duplicates the body and a callee's contract. It drifts if `_attribute_pre_branch` changes its None handling.

Required property: delete the docstring. A shorter or corrected restatement still restates, so don't rewrite it.

The only candidate decision is why this skips the timeline step (`_timeline_entry`) that `_attributed_branch` runs. The new text gives no reason for that choice, and the callers' docs already hold it. To keep it, state the reason (the carried value is already positional, so no timeline lookup applies) or point to `review_rounds._session_record_branches`. A bare "only the pre-branch step" does not qualify.

No other angle applies: no PR-defined labels, prior-version framing, or false claims. The "never remapped" claim checks out against scope.py:1042.
