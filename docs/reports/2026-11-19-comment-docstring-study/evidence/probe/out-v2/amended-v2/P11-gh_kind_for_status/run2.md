# comment-discipline-reviewer

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/period_cost.py:743-744` (new docstring on `_gh_kind_for_status`).

Issue: the docstring reads "The unavailable kind for a non-empty _gh_pr_list status. A status this table does not know is reported as an unexpected payload rather than aborting the run."
- Sentence 1 restates the function name, its `status` parameter and the caller's `if status:` guard at line 754. The table lookup is visible in line 745.
- The first half of sentence 2 restates the `.get(status, _GH_KIND_UNEXPECTED_PAYLOAD)` default. The test at `test_transcript_period_cost.py:1421` already pins it.
- Only "rather than aborting the run" is a decision with a reason: the lookup falls back instead of raising. That is a design choice static analysis cannot find. The surrounding gh-failure paths do abort (e.g. `gh_cli.py:489-490`).

Production failure mode: none at runtime. The docstring repeats the code, so it can drift from it, and it buries the one decision worth keeping.

Required property: delete sentence 1. Reduce sentence 2 to the decision, naming its subject. Suggested replacement:

`"""An unmapped status falls back to "unexpected payload" instead of raising, so a status added to _gh_pr_list without a table entry does not abort the run."""`

This is one sentence and one decision. Verbosity, multi-fact and readability checks pass. No terminology, "used to be" or false-claim concern: the replacement makes no unsettleable number or cause claim. The "abort the run" cause is a design rationale.

Nothing else in the diff is in scope: it is a single docstring addition in one file.
