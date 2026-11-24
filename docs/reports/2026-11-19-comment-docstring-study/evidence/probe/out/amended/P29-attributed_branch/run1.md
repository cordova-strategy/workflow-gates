# comment-discipline-reviewer

Scope: 1 file reviewed (`claude/.claude/scripts/transcript_analysis/scope.py`), 1 comment/docstring change in scope. Text set aside: none; the dispatch carried no scope override.

## R1 [CONCERN] Prose restating the code

`claude/.claude/scripts/transcript_analysis/scope.py:1085-1090`, the new docstring on `_attributed_branch`.

Offending text: "Resolve one record's branch for --branches filtering: the timeline step (_timeline_entry) followed by the pre-branch step (_attribute_pre_branch). Returns None — the "?" sentinel (see cmd_review_trace's docstring for the carry-forward convention this parallels) — for a main-thread record with no gitBranch, and for a sidechain record in a session with no branch-bearing main-thread record."

Issue: every clause restates what static analysis of this repository finds, and none states a design decision with a reason.
- Sentence 1 repeats the one-line body, `_attribute_pre_branch(*_timeline_entry(rec, ctx), ctx.pre_branch_run)`. The function name and its callees' names already show it.
- The None cases restate `_timeline_entry`'s own docstring and branches (scope.py:1067-1072, 1076, 1078). The first case is `_branch_tag` returning None for a main-thread record. The second is `ctx.untimed_main_branch` being None for a sidechain record. `_attribute_pre_branch` passes a None branch through unchanged (scope.py:1042).
- The `cmd_review_trace` pointer does not qualify as a pointer to a kept decision. It annotates the restated None clause, not a decision made here. `_session_branch_index` (scope.py:981-984) already draws that contrast, with a reason.

The text is also partly false, which is one more reason not to keep a corrected version.
- `_attributed_branch` returns None, never "?".
- Most callers coerce None to `""` (buckets.py:35, duration.py:32, fail_seq.py:64, judgment_pair.py:73, pr_link.py:65, struggle.py:59, subagent_mix.py:186 and 358, subagents.py:135 and 149, user_input.py:181, skill_invocation.py:128, skill_pair.py:58).
- cost.py:107 and cost.py:176 branch on `is None`.
- Only cost.py:827 renders "?", for an excluded-turn bucket.
- review_trace.py:308 renders "?", but it calls `_attribute_carried_branch`, not `_attributed_branch`.
- "Parallels the carry-forward convention" is also unsupported. The `cmd_review_trace` docstring (review_trace.py:767-772) describes positional carry-forward, which `_attributed_branch` does not do.

Required property: delete the docstring. Nothing in it is a non-obvious decision, so no shortened or corrected version should replace it. Any real decision (why sidechain records take the main-thread timeline) is already stated in `_timeline_entry`'s docstring.

Checked against other angles: deletion creates no Comment verbosity, Multi-fact comment structure or Paragraph readability finding.

**Request changes** (R1: delete the docstring).
