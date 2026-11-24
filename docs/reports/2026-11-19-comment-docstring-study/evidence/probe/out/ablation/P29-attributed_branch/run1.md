# comment-discipline-reviewer

Reviewed 1 file (`scope.py`); it carries 1 in-scope change, the new docstring on `_attributed_branch` (diff lines 8-13). Every clause of it fails Prose restating the code, so the fix is to delete the whole docstring. No clause states a decision whose reason static analysis can't find.

## R1 [CONCERN] Prose restating the code

scope.py:1085 (diff line 8)

Issue: "Resolve one record's branch for --branches filtering". The name `_attributed_branch`, its `rec`/`ctx` parameters and its `str | None` return type already say this. A `Grep` for the function's callers finds the `--branches` consumer.

Production failure mode: a clause that restates the code drifts when callers change.

Required property: delete the clause.

## R2 [CONCERN] Prose restating the code

scope.py:1085-1086 (diff lines 8-9)

Issue: "the timeline step (_timeline_entry) followed by the pre-branch step (_attribute_pre_branch)". The one-line body `_attribute_pre_branch(*_timeline_entry(rec, ctx), ctx.pre_branch_run)` shows this call order. Each callee's own docstring (lines 1065, 1038) already describes its step.

Production failure mode: a second description of the pipeline goes stale when a step is added or reordered.

Required property: delete the clause.

## R3 [CONCERN] Prose restating the code

scope.py:1087-1090 (diff lines 10-13)

Issue: "Returns None … for a main-thread record with no gitBranch, and for a sidechain record in a session with no branch-bearing main-thread record". This enumerates return paths that `_timeline_entry` (lines 1075-1078), `_branch_tag` (line 974) and `_attribute_pre_branch` (line 1042) show. I read those lines and the claim is true, so this is not a false-claim finding. It restates code that takes several functions to trace, and the rule says to delete such text even when it is true.

Production failure mode: the None conditions are owned by `_timeline_entry` and `_branch_tag`. A copy here goes stale when either changes.

Required property: delete the clause.

## R4 [CONCERN] Prose restating the code

scope.py:1087-1088 (diff lines 10-11)

Issue: 'the "?" sentinel (see cmd_review_trace's docstring for the carry-forward convention this parallels)'. This is a pointer, and a pointer to the symbol that holds a decision would stay under the rule. This one is not kept, because it points at a "?" label and a "parallels" claim that the function's own code never uses. The sentence it sits in is deleted by R3. `_session_branch_index` (lines 981-983) already carries the contrast with `cmd_review_trace`'s carry-forward, where that decision lives. I did not verify that `cmd_review_trace`'s docstring defines "?".

Production failure mode: the cross-reference ties this docstring to another function's docstring text, and that text can change independently.

Required property: delete the clause, and with it the whole docstring. If a pointer is wanted, the existing contrast in `_session_branch_index`'s docstring is its home.
