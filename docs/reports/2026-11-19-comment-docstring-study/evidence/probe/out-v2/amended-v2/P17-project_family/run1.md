# comment-discipline-reviewer

Reviewed 1 file (`redaction.py`), 1 carrying an in-scope change: the new `_project_family` docstring (diff lines 8-18, file lines 35-45). Rule applied: the session's replacement "Don't restate the code" bullet.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/redaction.py:35-40`

Offending text: "Collapse a project label or a raw project-dir slug to its base-repo "family" key. Strips the `--claude-worktrees-<branch>` suffix that a linked worktree's project-dir slug already carries (see `_WORKTREE_SUFFIX_RE` above); `_derive_proj_label`'s output preserves that suffix unchanged, so the same match applies to either input shape."

Issue: This passage states what the code shows, and none of it is a decision with a reason.
- The one-line summary and "Strips the ... suffix" restate the function name and the one-line `_WORKTREE_SUFFIX_RE.sub("", ...)` body.
- "`_derive_proj_label`'s output preserves that suffix unchanged" is findable by static analysis (`redaction.py:25`; I traced `-home-u-repo-a--claude-worktrees-branch-x` through it and the suffix survives).
- That fact is also already stated in the comment at `redaction.py:28-30` ("which _derive_proj_label carries through unchanged onto its output"). Restating it here is a second home for the same knowledge.
- "Either input shape" is visible from the `raw_proj_label` parameter and from the callers (`buckets.py:49`, `user_input.py:164` pass a raw slug; `cost.py:906` passes a label).

Production failure mode: When the worktree naming or `_derive_proj_label` changes, two comments must change, and the stale one misleads.

Required property: Delete these two sentences. If a pointer is wanted, the existing `_WORKTREE_SUFFIX_RE` comment is the home.

Proposed replacement docstring, keeping only the decision and the revisit trigger (it also carries the R2 fix):

```
"""A project whose own name contains `--claude-worktrees-` is truncated at it
and merges with any project already named the truncated form -- an accepted
risk at current scale (pinned by
test_non_worktree_label_colliding_with_suffix_shape_merges_into_existing_family).
If cost --by-project, buckets' Proj count, or user-input's Scope project count
ever shows an unexpected merge, re-evaluate.
"""
```

## R2 [FYI] False or unsourced claim

`claude/.claude/scripts/transcript_analysis/redaction.py:40-42`

Offending text: "A project literally named with that substring would falsely merge into another family."

Issue: The code supports this only in part. `_WORKTREE_SUFFIX_RE = r"--claude-worktrees-.+$"` (`redaction.py:31`) truncates the label at the substring. A merge happens only when the truncated form equals an existing project's label. Otherwise the project is renamed into its own family. The test (`test_transcript_cost.py:1458-1466`) pins the merge case with an unrelated project that already carries the truncated name.

Required property: Use the narrower statement given in the R1 replacement text. "Truncated at it and merges with any project already named the truncated form" is what the regex and the test support.

## Kept as-is

- The "accepted risk at current scale" clause is a decision with a reason, so it stays.
- The "re-evaluate if ..." clause is a revisit trigger, so it stays. The three consumers it names exist and are family-keyed: `cost.py:771` and `cost.py:906` for `--by-project`, `buckets.py:49` and the `Proj` column at `buckets.py:62`, and `user_input.py:164` and the `Scope: N projects` line at `user_input.py:288`.
