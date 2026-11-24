# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/period_cost.py`); 1 comment site in scope (the new `_gh_kind_for_status` docstring).

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/period_cost.py:743-744`

Issue: the docstring reads "The unavailable kind for a non-empty _gh_pr_list status. A status this table does not know is reported as an unexpected payload rather than aborting the run."

- Sentence 1 restates the function name, signature and call site. `_validated_pr_list` (line 754-755) calls it only under `if status:`, and the return is the `_GH_STATUS_TO_KIND` lookup. It states no decision and no reason.
- The first half of sentence 2 restates the `.get(status, _GH_KIND_UNEXPECTED_PAYLOAD)` default on line 745, and the test `test_a_status_the_table_does_not_know_is_reported_as_an_unexpected_payload` already pins that behaviour.
- The only non-obvious clause is "rather than aborting the run", the reason the lookup uses a default instead of indexing. Keep that decision and its reason. Delete the rest.

Required property: the docstring states only the decision to fall back, and why, in one sentence. It names its subject so the reason still says what it explains.

Concrete fix, replacing the whole docstring:

`"""An unrecognised status falls back to the unexpected-payload kind so a new status cannot abort the run."""`

I did not rule on whether the reason is findable by static analysis. The KeyError that indexing would raise is visible in the code. If you read the amended rule strictly, so that an obvious alternative's failure counts as findable, delete the docstring entirely.

No other angle applies. There is no PR-defined terminology, no prior-version framing, and no unsourced claim.
