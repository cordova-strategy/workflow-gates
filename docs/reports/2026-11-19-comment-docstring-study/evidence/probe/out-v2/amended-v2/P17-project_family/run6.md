# comment-discipline-reviewer

Reviewed 1 file (`redaction.py`); 1 new docstring in scope (`_project_family`).

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/redaction.py:35-38` (diff lines 8-11).

Issue: the opening sentence ("Collapse a project label or a raw project-dir slug to its base-repo 'family' key.") and the next one ("Strips the `--claude-worktrees-<branch>` suffix that a linked worktree's project-dir slug already carries (see `_WORKTREE_SUFFIX_RE` above);") state what the function name and its one-line body (`_WORKTREE_SUFFIX_RE.sub("", ...)`) already show. The suffix's origin is already stated in the comment at lines 28-30, which sits directly above the regex.

Production failure mode: the docstring drifts from the regex, and the same fact has two homes in one file.

Required property: delete both sentences. Neither states a decision with a reason that static analysis cannot find.

## R2 [CONCERN] Restating the code

File: `redaction.py:39-40` (diff lines 11-12).

Issue: "`_derive_proj_label`'s output preserves that suffix unchanged, so the same match applies to either input shape." This states the decision to accept both input shapes, but its reason is findable. `_derive_proj_label` (lines 23-25) keeps the suffix, as the comment at lines 28-30 already says. The callers also show both shapes: `cost.py:906` passes the derived label, while `buckets.py:49` and `user_input.py:164` pass `jsonl.parent.name`. The rule says to delete what static analysis finds, even when it is true. I checked the claim against the code and it is true, so this is not a false-claim finding.

Production failure mode: it duplicates the comment at lines 28-30. If `_derive_proj_label` changes, this sentence goes stale without any signal.

Required property: delete it. The parameter name `raw_proj_label` and the comment above the regex already carry the point.

## Kept (no finding)

- "A project literally named with that substring would falsely merge into another family -- an accepted risk at current scale." This is a design decision with a stated reason. The tight cause-and-effect pairing is fine.
- "If cost --by-project, buckets' Proj count, or user-input's Scope project count ever shows an unexpected merge, re-evaluate." This is a revisit trigger.
  - Its consumer references resolve to real sites: `cost.py:906`, the `Proj` column at `buckets.py:62` and the `Scope:` line at `user_input.py:288`.
  - The merge behavior is pinned by `test_transcript_cost.py:1458-1484`, which refers back to this docstring.

## Suggested replacement docstring

```python
    """A project literally named with `--claude-worktrees-` falsely merges into another family.

    Accepted at current scale. If cost --by-project, buckets' Proj count, or
    user-input's Scope project count ever shows an unexpected merge, re-evaluate.
    """
```

The replacement leads with the decision and keeps the trigger as its own sentence. Every kept fact is preserved, and it does not trade one angle's violation for another's.
