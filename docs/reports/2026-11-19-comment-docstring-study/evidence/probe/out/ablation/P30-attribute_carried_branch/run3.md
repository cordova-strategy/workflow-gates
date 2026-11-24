# comment-discipline-reviewer

## R1 [CONCERN] Prose restating the code

File: `claude/.claude/scripts/transcript_analysis/scope.py:1095-1097` (the new docstring on `_attribute_carried_branch`).

Issue: the docstring is `"""Apply only the pre-branch step to a branch a positional consumer carried forward from the main thread, using the record's own timestamp so a record with none is never remapped."""`. Every clause restates something static analysis of the repository finds:

- "Apply only the pre-branch step" restates the one-line body, which calls only `_attribute_pre_branch`.
- "using the record's own timestamp" restates the `_parse_ts(rec.get("timestamp"))` argument.
- "so a record with none is never remapped" restates `_attribute_pre_branch`'s own docstring and guard (`scope.py:1040-1042`): a None timestamp returns `branch` unchanged.
- "a branch a positional consumer carried forward from the main thread" restates the `carried` parameter name and its call sites (`test_transcript_analysis_branch_attribution.py:389`).

None of the clauses gives a reason that lies outside the repository's code and tests, such as why the timeline step is skipped for carried branches.

Production failure mode: the docstring duplicates `_attribute_pre_branch`'s contract, so it can drift from it. A changed None-timestamp rule would leave this text false.

Required property: delete the docstring. Keep a comment only if you state why carried branches skip the timeline step. That reason must come from outside the code, and the comment must name the decision.
