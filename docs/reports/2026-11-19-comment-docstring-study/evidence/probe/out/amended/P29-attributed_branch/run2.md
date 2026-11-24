# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/scope.py`); 1 added docstring in scope (`_attributed_branch`). No prompt text was set aside.

## R1 [CONCERN] Restating the code
File: `claude/.claude/scripts/transcript_analysis/scope.py:1085-1090`

Issue: The docstring has two parts.
- "the timeline step (_timeline_entry) followed by the pre-branch step (_attribute_pre_branch)" restates the one-line body at line 1091, `_attribute_pre_branch(*_timeline_entry(rec, ctx), ctx.pre_branch_run)`.
- The None cases ("a main-thread record with no gitBranch, and a sidechain record in a session with no branch-bearing main-thread record") restate what `_timeline_entry` (lines 1074-1081) and `_branch_tag` (lines 970-974) show. Static analysis of this repository finds them, even though it takes three functions to do so.

Neither part records a design decision or an outside constraint. The docstring also adds a dash aside, a parenthetical and a trailing clause, so it would fail Multi-fact comment structure if any of it stayed.

Required property: Delete the docstring. No clause names a decision and a reason static analysis can't find. The pointer to `cmd_review_trace` does not qualify as a pointer to a decision (see R2).

## R2 [CONCERN] False or unsourced claim
File: `claude/.claude/scripts/transcript_analysis/scope.py:1085-1088`

Issue: Three settleable claims are contradicted or only partly supported by their subjects.
- **"None — the '?' sentinel".** The function returns None and assigns no sentinel. Callers choose what None means, and most don't pick "?":
  - `buckets.py:35` maps None to `""` and skips the record.
  - `duration.py:32`, `fail_seq.py:64`, `pr_link.py:65`, `struggle.py:59`, `subagent_mix.py:186` and `user_input.py:181` map it to `""`.
  - `period_cost.py:497` routes None to `_Destination.DEFAULT_BRANCH`.
  - Only `cost.py:827` counts it under `"?"`, and `review_trace.py:308` renders `"?"` for the carried-branch path, which doesn't use this function.
- **"for --branches filtering".** `period_cost.py:492` calls it to route spend to a destination (`_branch_target`), and `buckets.py:35` calls it to group records. Neither call is a `--branches` filter.
- **"the carry-forward convention this parallels".** `_session_branch_index`'s docstring (`scope.py:981-984`) says this machinery is "Unlike cmd_review_trace's position-based carry-forward". `_attributed_branch` carries nothing forward by position, because its sidechain branch comes from a timestamp lookup (`scope.py:1079-1081`). The pointer therefore sends the reader to a convention the function does not follow, and it contradicts the file's own contrast.

Required property: The narrowest statement these subjects support is nothing beyond what R1 already deletes. Delete the claims along with the docstring. If a future edit wants the "?" mapping documented, put it at the call sites that do the mapping (`cost.py:827`, `review_trace.py:308`).
