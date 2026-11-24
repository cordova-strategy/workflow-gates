# comment-discipline-reviewer

Scope note: the Python-environment rule file that appeared mid-session concerns installing dependencies and doesn't change this review's scope, so I set it aside. I reviewed one file with one in-scope change, a new docstring on `_gh_kind_for_status`.

## R1 [CONCERN] Prose restating the code

`claude/.claude/scripts/transcript_analysis/period_cost.py:743` (new docstring, first sentence)

Offending text: "The unavailable kind for a non-empty _gh_pr_list status."

Issue: This clause restates the function's name and signature. The "non-empty" condition is visible at the only call site, which sits behind `if status:` (line 754). The `_GH_STATUS_TO_KIND` mapping (lines 92-98) shows which kind each status gets.

Production failure mode: None at runtime. The clause adds nothing static analysis doesn't find, and it will drift if the call site changes.

Required property: Delete the clause.

## R2 [CONCERN] Prose restating the code

`claude/.claude/scripts/transcript_analysis/period_cost.py:743-744` (new docstring, second sentence)

Offending text: "A status this table does not know is reported as an unexpected payload rather than aborting the run."

Issue: This clause restates the `.get(status, _GH_KIND_UNEXPECTED_PAYLOAD)` default on line 745. A test also pins it (`test_transcript_period_cost.py:1421`). "Rather than aborting the run" names the alternative the code didn't take, but it gives no reason that lies outside this repository, so it isn't a kept design decision under the rule.

Production failure mode: None at runtime. The sentence duplicates what the code and test already show.

Required property: Delete the clause. With both clauses gone, the function has no docstring, so remove the docstring entirely.

No other angles apply: the docstring has no PR-defined labels, no prior-version framing and no unsourced numbers.

**Request changes** (R1 and R2, both resolved by deleting the docstring).
