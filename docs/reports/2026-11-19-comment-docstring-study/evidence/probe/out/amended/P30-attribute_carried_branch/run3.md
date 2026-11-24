# comment-discipline-reviewer

Scope: 1 file in the diff (`scope.py`), 1 added docstring. I set aside no prompt text.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/scope.py:1095-1097`, the new docstring on `_attribute_carried_branch`:

> Apply only the pre-branch step to a branch a positional consumer carried forward from the main thread, using the record's own timestamp so a record with none is never remapped.

- **Issue.** Every clause restates what static analysis of this repository finds. No clause is a decision with a reason that static analysis cannot find.
  - "Apply only the pre-branch step": the body is one call to `_attribute_pre_branch` (scope.py:1098).
  - "using the record's own timestamp": the body passes `_parse_ts(rec.get("timestamp"))` (scope.py:1098).
  - "so a record with none is never remapped": this is `_attribute_pre_branch`'s own documented contract, `ts is None` returns `branch` unchanged (scope.py:1037-1044).
  - "a positional consumer carried forward from the main thread": the two callers show this. `review_rounds.py:259-264` and `review_trace.py:249-251,308` each carry the last main-thread branch forward and pass it in. Their own docs already explain the carry-forward and the pre-branch step (`review_rounds.py:240-247`, `review_trace.py:248-250`).
- **Why this fails.** The amended "Don't restate the code" rule says to delete every clause that static analysis of the repo finds, even when it is true and takes several files to find. A shorter or corrected restatement still restates.
- **Concrete fix.** Delete the docstring.
  - The only candidate decision is why this helper skips `_timeline_entry`, which `_attributed_branch` applies. That reason is the callers' own carry-forward, and the callers' docs already hold it.
  - Don't swap in a one-line paraphrase of that reason. It is also findable from the callers, so it restates too.
  - Add a pointer to the callers' docs only if the maintainer wants one.
