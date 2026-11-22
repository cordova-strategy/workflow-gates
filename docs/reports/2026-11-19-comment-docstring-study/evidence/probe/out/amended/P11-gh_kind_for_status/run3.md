# comment-discipline-reviewer

Scope: 1 file reviewed (`period_cost.py`), 1 added docstring in scope (`_gh_kind_for_status`, diff lines 8-9). Nothing was set aside.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/period_cost.py:743-744`

Issue: the new docstring reads "The unavailable kind for a non-empty _gh_pr_list status. A status this table does not know is reported as an unexpected payload rather than aborting the run." Both sentences restate what the code shows.

- Sentence 1 restates the function name, its `status: str` parameter and its return value. The "non-empty" condition is also visible from its only caller, `_validated_pr_list` (line 754-755), which calls it under `if status:`.
- Sentence 2 restates the `.get(status, _GH_KIND_UNEXPECTED_PAYLOAD)` default on line 745. "Rather than aborting the run" only says that `dict.get` does not raise, which the standard library already tells a reader.
- Neither sentence gives a reason static analysis cannot find, such as why an unmapped status can occur or what outside this repository forces the fallback. Rewording either sentence would still restate the code.

Production failure mode: none at runtime. The docstring repeats the code and adds nothing a reader needs, and it can drift from `_GH_STATUS_TO_KIND` (line 92).

Required property: delete the docstring. If the author wants to keep the fallback as a decision, the comment must name the decision and a reason code cannot show. One example is why a status can be missing from `_GH_STATUS_TO_KIND`, such as a status added in `gh_cli` or `pr_cost_ledger` before it is mapped. Otherwise leave the function undocumented.
