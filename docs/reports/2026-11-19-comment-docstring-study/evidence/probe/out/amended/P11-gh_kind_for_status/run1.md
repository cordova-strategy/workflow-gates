# comment-discipline-reviewer

Reviewed 1 file (`period_cost.py`); 1 added docstring in scope. Applied the session's replacement "Don't restate the code" bullet.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/period_cost.py:743-744`, the new docstring on `_gh_kind_for_status`.

Offending text: "The unavailable kind for a non-empty _gh_pr_list status. A status this table does not know is reported as an unexpected payload rather than aborting the run."

Issue: The first sentence restates what the function name, the `-> str` signature, the `_GH_STATUS_TO_KIND.get(...)` body and its only caller show.
- The caller at line 754-755 guards `if status:` and builds `_PrListResult(unavailable_kind=...)`, which is where "non-empty" and "unavailable kind" come from.
- `_gh_pr_list` (gh_cli.py:448-469) returns the statuses.
- Static analysis finds all of this, even though it takes several files.

The second sentence is a kept decision. It says what was decided (fall back to unexpected payload) and why (not abort the run). The `.get` default alone does not give the reason. It does not need a restating lead-in.

Production failure mode: none at runtime. The cost is a docstring that restates the code and will drift from it. The "non-empty" precondition duplicates the caller's guard.

Required property: delete the first sentence and keep the decision. Name the subject inside the decision sentence, so "this table" does not dangle. For example: "A status missing from `_GH_STATUS_TO_KIND` falls back to unexpected payload rather than aborting the run."

Checked and drew no finding:
- The "rather than aborting the run" claim is a design rationale, not a settleable claim.
- The caller at line 755 has no try/except, so an unhandled lookup error would propagate. That is consistent with the rationale.
