# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/scope.py`); 1 carried an in-scope change: the new docstring on `_attributed_branch` (diff lines 8-13). No prompt text contradicted this file's scope, so none was set aside.

The function is a one-line delegation: `_attribute_pre_branch(*_timeline_entry(rec, ctx), ctx.pre_branch_run)`. The docstring carries no design decision (what was decided plus a reason static analysis can't find). The rule under test says to delete every other clause, so each clause below is its own finding. Deleting all six removes the docstring entirely.

## R1 [CONCERN] Prose restating the code
File: scope.py:1085, `_attributed_branch` docstring, first clause.
Issue: "Resolve one record's branch for --branches filtering" restates what the name `_attributed_branch` and the `rec` parameter already show. The `--branches` link is found by grepping the callers.
Production failure mode: the clause drifts if the caller set changes, and it adds nothing a reader can't get from the name and call sites.
Required property: delete this clause.

## R2 [CONCERN] Prose restating the code
File: scope.py:1085-1086, second clause.
Issue: "the timeline step (_timeline_entry) followed by the pre-branch step (_attribute_pre_branch)" narrates the one-line body, which already shows both calls and their order.
Production failure mode: the clause goes stale if the body gains or reorders a step.
Required property: delete this clause.

## R3 [CONCERN] Prose restating the code
File: scope.py:1086, third clause.
Issue: "Returns None" restates the `-> str | None` return annotation.
Production failure mode: none beyond noise, because the annotation is the source of truth.
Required property: delete this clause.

## R4 [CONCERN] Prose restating the code
File: scope.py:1086-1087, fourth clause.
Issue: "the '?' sentinel (see cmd_review_trace's docstring for the carry-forward convention this parallels)" says what `None` maps to and how it relates to another function. Both are findable by static analysis of the repo, including the `cmd_review_trace` docstring. The instruction for docstring clauses is to report this one for deletion, whatever it says, even though it is a pointer.
Production failure mode: the cross-reference rots if `cmd_review_trace` is renamed or its docstring changes.
Required property: delete this clause. The sentinel and carry-forward convention stay documented in `cmd_review_trace`.

## R5 [CONCERN] Prose restating the code
File: scope.py:1087-1088, fifth clause.
Issue: "for a main-thread record with no gitBranch" describes a branch of `_timeline_entry` / `_attribute_pre_branch` that the callee code and its tests show.
Production failure mode: it duplicates callee behavior, so it silently goes false when that logic changes. The wrapper's own body doesn't show the case.
Required property: delete this clause.

## R6 [CONCERN] Prose restating the code
File: scope.py:1088-1089, sixth clause.
Issue: "for a sidechain record in a session with no branch-bearing main-thread record" restates callee behavior the same way as R5.
Production failure mode: same drift as R5.
Required property: delete this clause. With R1-R6 applied, the function has no docstring.
