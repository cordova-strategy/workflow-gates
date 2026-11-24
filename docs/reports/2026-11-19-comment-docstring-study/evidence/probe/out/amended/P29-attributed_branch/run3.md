# comment-discipline-reviewer

Scope: 1 file reviewed (`claude/.claude/scripts/transcript_analysis/scope.py`), 1 added docstring in scope (`_attributed_branch`). No prompt text was set aside.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/scope.py:1085-1090` (the added `_attributed_branch` docstring).

**Offending text:** "Resolve one record's branch for --branches filtering: the timeline step (_timeline_entry) followed by the pre-branch step (_attribute_pre_branch). Returns None — the "?" sentinel (see cmd_review_trace's docstring for the carry-forward convention this parallels) — for a main-thread record with no gitBranch, and for a sidechain record in a session with no branch-bearing main-thread record."

**Issue:** The docstring contains no non-obvious design decision. Each clause restates something static analysis of this repository finds:
- The first sentence restates the one-line body, `_attribute_pre_branch(*_timeline_entry(rec, ctx), ctx.pre_branch_run)`, and the function name.
- The `Returns None` clause restates the branches of `_timeline_entry` (scope.py:1074-1078) and `_branch_tag` (scope.py:970-974). The "?" rendering is done by callers (`cost.py:827`, `review_trace.py:308`). Tracing it takes several files, but the rule deletes it anyway.

**Failure mode:** The cross-reference is also misleading. It says the "?" sentinel parallels cmd_review_trace's carry-forward convention. `_attributed_branch` does no carry-forward. A main-thread record with no tag returns `(None, ts)` from `_timeline_entry` (scope.py:1075-1076) and stays None. cmd_review_trace carries the last non-empty value forward instead (review_trace.py docstring lines 767-775). The `_session_branch_index` docstring (scope.py:981-983) says the two differ. Because the docstring is deleted, this adds no separate false-claim finding. It does show that the pointer is not a "pointer to where a decision lives".

**Required property:** Delete the docstring. Nothing in it names a decision or an outside-forced constraint. The sub-steps are already documented on `_timeline_entry` and `_attribute_pre_branch`, where the behavior is decided.
