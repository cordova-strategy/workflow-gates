# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/period_cost.py`); 1 added docstring in scope. The dispatch prompt had no free-form text to set aside. The `python-environment-conventions.md` rules text that arrived mid-run is unrelated to this review and changed nothing.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/period_cost.py:743-744` (new docstring on `_gh_kind_for_status`)

Offending text: "The unavailable kind for a non-empty _gh_pr_list status. A status this table does not know is reported as an unexpected payload rather than aborting the run."

Issue: both sentences say what the one-line body already shows.
- Sentence 1 restates the function name, its `status` parameter and its `-> str` return. The "non-empty" precondition is enforced by the only caller, `_validated_pr_list` (line 754, `if status:`). Its own docstring already says "The status decides first".
- Sentence 2 restates `_GH_STATUS_TO_KIND.get(status, _GH_KIND_UNEXPECTED_PAYLOAD)`. The fallback is visible in the `.get` default. "Rather than aborting the run" describes an alternative nobody wrote (a `[status]` lookup that raises) and not a constraint on the code.
- I checked the facts. `_gh_pr_list` exists (`gh_cli.py:448`) and returns a degraded status or `_GH_PR_LIST_UNPARSEABLE`. `_GH_STATUS_TO_KIND` (lines 92-98) maps both to kinds. So the text is accurate, but it adds nothing the code does not show.

Production failure mode: none. The cost is noise, plus drift risk if the table's fallback changes.

Required property: delete the docstring. Do not shorten or correct it, because a shorter restatement still restates. If the author wants the unknown-status fallback documented as a design intent, the one place that could carry it is a comment on `_GH_STATUS_TO_KIND` (line 92). It would have to say why an unmapped status is tolerated, which the current text does not.
