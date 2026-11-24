# comment-discipline-reviewer

## R1 [CONCERN] Prose restating the code

File: claude/.claude/scripts/transcript_analysis/period_cost.py:743 (docstring of `_gh_kind_for_status`, first sentence)

Text: "The unavailable kind for a non-empty _gh_pr_list status."

Issue: The function name, the `status: str` signature, the `-> str` return and the `_GH_STATUS_TO_KIND.get(...)` body already show that it maps a status to an unavailable kind. The "non-empty" precondition is visible at the sole caller (`_validated_pr_list`, line 754, `if status:`). Static analysis of the repository finds every part of the clause.

Required property: Delete the clause. It records no design decision with a reason that lies outside the repository.

## R2 [CONCERN] Prose restating the code

File: claude/.claude/scripts/transcript_analysis/period_cost.py:743-744 (docstring, second sentence)

Text: "A status this table does not know is reported as an unexpected payload rather than aborting the run."

Issue: `.get(status, _GH_KIND_UNEXPECTED_PAYLOAD)` shows the fallback, and `test_a_status_the_table_does_not_know_is_reported_as_an_unexpected_payload` (tests line 1420) covers it. "Rather than aborting" is the only reason the clause adds, and it is the ordinary behavior of `dict.get`. Neither the fallback nor the reason depends on anything outside this repository.

Required property: Delete the clause. With both sentences deleted, the docstring is empty, so remove it entirely.
