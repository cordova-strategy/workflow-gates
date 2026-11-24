# comment-discipline-reviewer

## R1 [CONCERN] Restating the code

File: claude/.claude/scripts/transcript_analysis/period_cost.py:743-744 (docstring of `_gh_kind_for_status`, added in this diff)

Issue: The docstring is `"The unavailable kind for a non-empty _gh_pr_list status. A status this table does not know is reported as an unexpected payload rather than aborting the run."` Its first sentence restates what the name, the signature and the single caller already show. The `_GH_STATUS_TO_KIND` lookup and the `if status:` guard at line 754 show that the function returns the kind for a non-empty status. The "non-empty" qualifier is only the caller's `if status:` at line 754. The first half of the second sentence restates `.get(status, _GH_KIND_UNEXPECTED_PAYLOAD)` at line 745, which is the lookup fallback. Only the clause "rather than aborting the run" carries a decision and its reason, namely why the fallback is a default rather than a `KeyError`. Static analysis cannot recover that.

Required property: Delete the first sentence. Reduce the second sentence to the decision and its reason, keeping the subject so the reason still names what it explains. For example: `"An unknown status falls back to the unexpected-payload kind so a new status cannot abort the run."` Check this wording against `_GH_STATUS_TO_KIND` before keeping it: it is stated as a design judgment and draws no false-claim finding.

Checks run on the other angles:
- No PR-defined terminology.
- No "used to be" framing.
- No false claim: the fallback behavior matches period_cost.py:745, and the test at test_transcript_period_cost.py:1420-1421 confirms it.
