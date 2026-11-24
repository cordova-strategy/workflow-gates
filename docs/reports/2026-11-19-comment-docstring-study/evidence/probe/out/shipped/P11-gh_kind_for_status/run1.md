# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/period_cost.py`); 1 in-scope comment change (the new `_gh_kind_for_status` docstring). I set aside the system-reminder text about Python environment conventions: it has no bearing on this review.

## R1 [CONCERN] Prose restating the code

period_cost.py:743-744 (the added docstring on `_gh_kind_for_status`).

Offending text: "The unavailable kind for a non-empty _gh_pr_list status. A status this table does not know is reported as an unexpected payload rather than aborting the run."

Issue: both sentences restate what the one-line body and its call site already show.
- Sentence 1 restates the function name, the `status` parameter and the `_GH_STATUS_TO_KIND` lookup. The "non-empty" precondition is visible at the only caller, `if status:` at line 754. The mapping from status to kind is visible in the table at lines 92-98.
- Sentence 2 restates `_GH_STATUS_TO_KIND.get(status, _GH_KIND_UNEXPECTED_PAYLOAD)`, a `.get` with an explicit default.

Production failure mode: none at runtime. The docstring is a duplicate that can drift from the table and the default. Reading the repo, I found both sentences accurate, so this is not a False-claim finding: `_gh_pr_list` (gh_cli.py:448-469) returns only `""`, a degraded status from `_gh_call_with_backoff`, or `_GH_PR_LIST_UNPARSEABLE`. The table at lines 92-98 maps the degraded statuses and the unparseable one, and `.get`'s default covers the rest.

Required property / fix: delete the docstring. A restatement is deleted, not shortened.

No other angles apply. There is no PR-defined label, no prior-version framing, and no unsourced number or cause-and-effect claim.
