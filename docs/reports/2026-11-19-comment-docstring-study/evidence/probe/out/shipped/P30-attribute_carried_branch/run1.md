# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/scope.py`); 1 carries an in-scope comment change (new docstring on `_attribute_carried_branch`, lines 1095-1097).

Set aside: the dispatch's `findings_path` is the only write. A system reminder on Python environment conventions has no bearing on this review and was ignored.

## R1 [CONCERN] Restating the code
scope.py:1096-1097 — "using the record's own timestamp so a record with none is never remapped."

Issue: The clause restates what the body (`_parse_ts(rec.get("timestamp"))` passed to `_attribute_pre_branch`) shows. The "None timestamp is never remapped" fact already lives in `_attribute_pre_branch`'s docstring (scope.py:1040-1041), so this is a second statement of the same fact. Repeating it also fails the single-source-of-truth rule. I verified that the claim is true: `_parse_ts` returns None for a missing timestamp (corpus.py:233-240), and `_attribute_pre_branch` returns the branch unchanged for a None `ts` (scope.py:1042). It is therefore not a false claim, only redundant.

Required property: Keep only the non-obvious fact, which is that this function skips the timeline step that `_attributed_branch` runs. For example: "Apply only the pre-branch step to a branch the caller already carried forward; there is no timeline step." Drop the timestamp clause or point to `_attribute_pre_branch`.

## R2 [FYI] Wrong altitude / undefined term
scope.py:1095 — "a positional consumer".

Issue: "Positional consumer" is defined only in the tests (`test_transcript_analysis_branch_attribution_structure.py:150`, `..._branch_attribution.py:326`, via `_POSITIONAL_CARRY_FORWARD`). scope.py itself does not define it, so a reader of this file alone cannot tell what it means. It is a codebase term rather than a PR-defined label, which is why this is only an FYI.

Required property: Name the callers instead, for example "a caller that carries the last main-thread branch forward by position (`review_rounds._session_record_branches`, `review_trace`)". Alternatively, define the term once in scope.py and use it consistently.
