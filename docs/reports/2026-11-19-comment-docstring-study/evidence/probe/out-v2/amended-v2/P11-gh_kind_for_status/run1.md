# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/period_cost.py`); it carries one in-scope change, the new docstring on `_gh_kind_for_status` (lines 743-744).

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/period_cost.py:743-744`

Issue: the docstring is `"""The unavailable kind for a non-empty _gh_pr_list status. A status this table does not know is reported as an unexpected payload rather than aborting the run."""`. It has two parts, and only the second is a design decision.
- The first sentence, "The unavailable kind for a non-empty _gh_pr_list status", restates the function's name, signature and sole caller.
  - The name `_gh_kind_for_status` and the `str -> str` signature already say it maps a status to a kind.
  - "Non-empty" restates the `if status:` guard at line 754 in `_validated_pr_list`, the only call site (line 755).
  - It states no decision and no reason, so the rule deletes it.
- The second sentence says what the `.get(status, _GH_KIND_UNEXPECTED_PAYLOAD)` default does, and "rather than aborting the run" is the reason, so the sentence is kept.
  - The "this table" in it only resolves because the first sentence sat beside it, so it needs a name once that sentence is gone.
  - I checked that the table is currently exhaustive, so the fallback is a defensive decision with no live trigger. Every status `_gh_pr_list` and `_gh_call_with_backoff` can return is a key in `_GH_STATUS_TO_KIND` (`period_cost.py:92-98`, `gh_cli.py:23-27`, `gh_cli.py:321-338`, `pr_cost_ledger.py:114-115`). That makes the reason ("a new status must not abort the run") one that static analysis of the call graph cannot supply, so it belongs in the comment.

Production failure mode: none. The cost is a docstring that mostly restates the code, which the rule treats as noise to delete.

Required property: the docstring states only the fallback decision and its reason, and names its subject.

Concrete fix: replace the docstring with one sentence:
`"""A status missing from _GH_STATUS_TO_KIND is reported as an unexpected payload rather than aborting the run."""`
This is not a trade of one angle's violation for another's. The replacement is a single fact in one sentence, so it needs no list or reordering. It names `_GH_STATUS_TO_KIND` instead of "this table". It carries no PR-only terminology and no prior-version framing.

No findings on claim accuracy. The statement that an unknown status is reported as an unexpected payload is confirmed by `period_cost.py:745`.
