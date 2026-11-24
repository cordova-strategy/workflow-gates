# comment-discipline-reviewer

Reviewed 1 file (`redaction.py`); 1 carried an in-scope change (the new `_project_family` docstring, lines 35-44 of the post-diff file).

## R1 [CONCERN] Restating the code

`redaction.py:36-40` (diff lines 9-13)

Offending text: "Strips the `--claude-worktrees-<branch>` suffix that a linked worktree's project-dir slug already carries (see `_WORKTREE_SUFFIX_RE` above); `_derive_proj_label`'s output preserves that suffix unchanged, so the same match applies to either input shape."

Issue:
- The sentence restates the one-line body, `_WORKTREE_SUFFIX_RE.sub("", raw_proj_label)`.
- The slug-naming fact is already stated in the comment above `_WORKTREE_SUFFIX_RE` (lines 28-30), which also says `_derive_proj_label` carries the suffix through.
- "`_derive_proj_label` preserves the suffix" is a fact static analysis finds by reading that function (line 25), so it is not a decision.
- The rule under test deletes everything static analysis finds, even when it is true and takes a second function to find.
- The pointer to `_WORKTREE_SUFFIX_RE` stays only as a pointer to where the decision lives. Folding it into the surviving sentence below covers that.

Required property: delete the sentence. Keep the pointer inside the retained decision sentence (see R3).

## R2 [CONCERN] Restating the code

`redaction.py:35` (diff line 8)

Offending text: "Collapse a project label or a raw project-dir slug to its base-repo "family" key."

Issue:
- The summary line restates the function name `_project_family`, its parameter `raw_proj_label` and its `.sub("", ...)` body.
- It states no decision, no external constraint and no revisit trigger.
- The rule under test says the fix for a passage with no decision is deletion.

Required property: delete the summary line. The surviving decision and trigger sentences (R3) carry the docstring.

## R3 [FYI] Kept decision and trigger: rewrite so it stands alone once R1 and R2 are applied

`redaction.py:40-44` (diff lines 13-17)

Text: "A project literally named with that substring would falsely merge into another family -- an accepted risk at current scale. If cost --by-project, buckets' Proj count, or user-input's Scope project count ever shows an unexpected merge, re-evaluate."

Issue:
- Both sentences are kept: the first is a decision with a reason, the second is a revisit trigger.
- The first sentence says "that substring", which refers to the suffix text R1 deletes, so it loses its antecedent.
- The claims check out against the code:
  - `cost.py:906` uses `_project_family` for the `--by-project` key.
  - `buckets.py:49` uses it for the project set, and `buckets.py:62` has the `Proj` column.
  - `user_input.py:164` and `:288` use it for the `Scope: N projects` line.
  - `tests/test_transcript_cost.py:1458-1484` confirms the false merge.
- The test at `test_transcript_cost.py:1468` points readers at this docstring, so the docstring must keep the limitation.

Suggested replacement for the whole docstring:

```python
    """A project literally named with `--claude-worktrees-` (see `_WORKTREE_SUFFIX_RE`)
    would falsely merge into another family -- an accepted risk at current scale.
    If cost --by-project, buckets' Proj count, or user-input's Scope project count
    ever shows an unexpected merge, re-evaluate.
    """
```

Required property: name the substring explicitly, keep the decision and the trigger, and keep the `_WORKTREE_SUFFIX_RE` pointer.

No false or unsourced claims found. "Accepted risk at current scale" is a design judgment, not a claim.
