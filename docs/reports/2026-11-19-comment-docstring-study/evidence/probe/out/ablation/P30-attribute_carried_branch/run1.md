# comment-discipline-reviewer

Scope: 1 file in the diff (`scope.py`), 1 carrying an in-scope comment change (the new docstring on `_attribute_carried_branch`). No prompt text was set aside.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/scope.py:1095-1096` (docstring of `_attribute_carried_branch`).

Issue: the clause "Apply only the pre-branch step to a branch a positional consumer carried forward from the main thread" restates the code. The body is a single call to `_attribute_pre_branch` (line 1098). The parameter is named `carried`. The sibling `_attributed_branch` (lines 1084-1091) shows what the other path adds, namely `_timeline_entry`. The clause gives no reason that only the code and tests can't show.

Production failure mode: none. The cost is a comment that has to be kept in sync with the call site.

Required property: delete the clause. Deleting a sentence that merely restates the call leaves nothing for it to be shortened to.

## R2 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/scope.py:1096-1097` (docstring of `_attribute_carried_branch`).

Issue: the clause "using the record's own timestamp so a record with none is never remapped" restates the code. `_parse_ts(rec.get("timestamp"))` on line 1098 shows which timestamp is used. The "never remapped" behavior is `_attribute_pre_branch`'s `ts is None` guard (line 1042), which its docstring (lines 1038-1041) already states. The "so" reason is therefore a consequence static analysis finds in this repository, not a decision forced from outside it.

Production failure mode: none. The risk is drift, since two docstrings now state the None-timestamp behavior.

Required property: delete the clause. With R1, the whole docstring goes and the function is left with no docstring. Naming the one-line function is enough.
