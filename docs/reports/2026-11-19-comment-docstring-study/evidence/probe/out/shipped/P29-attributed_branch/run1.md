# comment-discipline-reviewer

Reviewed 1 diff (1 file, `scope.py`); the docstring added to `_attributed_branch` is the only site in scope.

## R1 [CONCERN] False or unsourced claim
scope.py:1087-1088 (docstring of `_attributed_branch`).
Issue: "Returns None — the "?" sentinel (see cmd_review_trace's docstring for the carry-forward convention this parallels)" is contradicted by the code in two ways:
- The function returns plain `None`. It never produces "?". Callers choose the rendering: `review_trace.py:308` and `cost.py:827` use `or "?"`, while `buckets.py:35`, `duration.py:32`, `fail_seq.py:64`, `pr_link.py:65`, `subagents.py:135` and others use `or ""`. So "None is the '?' sentinel" holds for only some callers.
- `_attributed_branch` does no carry-forward. A main-thread record with no tag returns None (`scope.py:1076`, `_timeline_entry`), not the previous record's branch. `cmd_review_trace`'s carry-forward (`review_trace.py:767-773`) is the positional last-non-empty-value mechanism that `_attributed_branch` does not use. `scope.py:981-984` already contrasts the timeline with that carry-forward. "Parallels" therefore describes the opposite of what `scope.py:982` says. `_attributed_branch` shares only the "?" rendering with `cmd_review_trace` (`review_trace.py:774`), via the caller.

The opening "for --branches filtering" also narrows a function that every cost, bucket, duration, subagent and similar consumer calls (grep of `_attributed_branch`), not only the filter.
Required property: state only what the function returns. Drop the "?" sentinel and the "parallels" cross-reference. If the "?" rendering is worth keeping, say in a separate sentence that callers decide how None displays. Name the two None cases precisely (a main-thread record with an absent, empty or non-string `gitBranch`; a sidechain record in a session whose main thread has no tagged record). `test_transcript_cost.py:2043` and `test_transcript_pr_cost.py:147` already cite this "None-return docstring", so the None contract is the part to keep.

## R2 [CONCERN] Prose restating the code
scope.py:1085-1086: "Resolve one record's branch for --branches filtering: the timeline step (_timeline_entry) followed by the pre-branch step (_attribute_pre_branch)."
Issue: the body is a single call, `_attribute_pre_branch(*_timeline_entry(rec, ctx), ctx.pre_branch_run)`, and the sentence restates it in prose. The callee names already carry the "what".
Required property: delete this sentence. The helpers' own docstrings (`scope.py:1065-1073`, `1038-1041`) hold the detail. The one non-obvious fact left, when None is returned, is covered in R1.

## R3 [FYI] Multi-fact comment structure
scope.py:1087-1090: one sentence chains the return value, a dash-delimited sentinel aside, a parenthetical cross-reference, and two None conditions joined by "and for".
Issue: several independent facts share one sentence, and the reader must parse the whole sentence to find where one ends.
Required property: give each None condition its own sentence, or a two-item list, and keep the cross-reference out of the middle. If R1 and R2 are applied, only the two-case None statement remains and this is resolved.
