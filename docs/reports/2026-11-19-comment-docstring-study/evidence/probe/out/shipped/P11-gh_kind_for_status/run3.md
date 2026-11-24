# comment-discipline-reviewer

Set aside: the `python-environment-conventions.md` rule text that arrived mid-session. It is about Python installs and does not change this review's scope.

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/period_cost.py`); 1 comment site in scope (the new docstring on `_gh_kind_for_status`, lines 743-744).

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/period_cost.py:743-744`

Issue: The docstring reads "The unavailable kind for a non-empty _gh_pr_list status. A status this table does not know is reported as an unexpected payload rather than aborting the run."

- Sentence 2 restates the one-line body. `_GH_STATUS_TO_KIND.get(status, _GH_KIND_UNEXPECTED_PAYLOAD)` already shows that an unknown status falls back to the unexpected-payload kind. It also shows that nothing raises. `test_transcript_period_cost.py:1421` pins the same fallback.
- Sentence 1 restates the function name, its `status: str -> str` signature and the table lookup. Its "non-empty" precondition is true. `_validated_pr_list` guards on `if status:` at line 754 before the only call at line 755. The call site shows the guard, so a docstring is not needed to carry it.
- The claims checked out against the code, so this is not a false-claim finding. `_gh_pr_list` returns a degraded status string or `_GH_PR_LIST_UNPARSEABLE` (`gh_cli.py:451-469`). `_GH_STATUS_TO_KIND` (`period_cost.py:92-98`) maps exactly those five statuses.

Why it fails: §Durable text "Don't restate the code". A shorter or corrected restatement still restates.

Required property: delete the docstring. If the author wants to keep the one fact the code doesn't state, keep a single sentence such as "Callers pass only a non-empty status; an empty one would map to unexpected payload." Drop the rest.
