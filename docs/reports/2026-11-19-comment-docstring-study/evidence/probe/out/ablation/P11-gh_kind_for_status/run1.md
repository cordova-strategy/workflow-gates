# comment-discipline-reviewer

## R1 [CONCERN] Restating the code
File: claude/.claude/scripts/transcript_analysis/period_cost.py:743 (first clause of the new `_gh_kind_for_status` docstring)

Issue: "The unavailable kind for a non-empty _gh_pr_list status." This restates the function's name, its `status: str -> str` signature, and its one call site (line 755, inside `if status:`), all of which already show it.

Production failure mode: none. The clause adds reading cost and can drift from the call site.

Required property: delete this clause.

## R2 [CONCERN] Restating the code
File: claude/.claude/scripts/transcript_analysis/period_cost.py:743-744 (second clause of the new docstring)

Issue: "A status this table does not know is reported as an unexpected payload rather than aborting the run." This restates the `.get(status, _GH_KIND_UNEXPECTED_PAYLOAD)` default on line 745. `_GH_KIND_UNEXPECTED_PAYLOAD` is defined at line 88 and `_GH_STATUS_TO_KIND` at line 92. The "rather than aborting" contrast gives no reason that static analysis can't find. It names no outside constraint that forces the fallback.

Production failure mode: none. The clause duplicates the code and would go stale if the default changed.

Required property: delete this clause. Deleting both clauses leaves the function with no docstring, which is correct. If the fallback to "unexpected payload" is a real decision, a reason for it that is not visible in the code would need to be stated, but this clause supplies none.
