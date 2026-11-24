# comment-discipline-reviewer

Set aside: the `python-environment-conventions.md` rule file that arrived mid-session. It concerns Python dependency installs, not this review, so it changes nothing here.

Scope: 1 file reviewed (`redaction.py`), 1 added docstring in scope (`_project_family`). Judged under the session's replacement "Don't restate the code" bullet.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/redaction.py:35-38` (diff lines 8-11)

Text: `Collapse a project label or a raw project-dir slug to its base-repo "family" key.` and `Strips the --claude-worktrees-<branch> suffix that a linked worktree's project-dir slug already carries (see _WORKTREE_SUFFIX_RE above);`

Issue: Both clauses say what the function does. The name, the parameter name, and the one-line body `_WORKTREE_SUFFIX_RE.sub("", raw_proj_label)` already show it. The suffix's worktree origin is stated in the comment on `_WORKTREE_SUFFIX_RE` (redaction.py:28-30), so the "see ... above" pointer leads to a restatement and not to a decision. Under the rule, a shorter or corrected restatement still restates.

Production failure mode: none. The cost is a docstring that drifts from the regex and buries the one decision in it.

Required property: delete both clauses.

## R2 [CONCERN] Restating the code / single source of truth

`redaction.py:38-40` (diff lines 11-13)

Text: `` `_derive_proj_label`'s output preserves that suffix unchanged, so the same match applies to either input shape. ``

Issue: Static analysis of `_derive_proj_label` (redaction.py:23-25) finds this. I checked it by hand: `-home-u-repo-a--claude-worktrees-branch-x` becomes `repo-a--claude-worktrees-branch-x`, so the claim is true. It repeats the comment at redaction.py:28-30 ("which _derive_proj_label carries through unchanged onto its output"), so the same fact now has two homes. Being true does not save it under the rule.

Required property: delete it. The comment above the regex stays the one home.

## R3 [FYI] Restating the code (mixed clause)

`redaction.py:41-44` (diff lines 14-17)

Text: `A project literally named with that substring would falsely merge into another family -- an accepted risk at current scale. If cost --by-project, buckets' Proj count, or user-input's Scope project count ever shows an unexpected merge, re-evaluate.`

Issue: These two sentences are the only non-obvious content in the docstring and should stay. The first is a decision (match on the literal substring, not on provenance) with a reason ("accepted at current scale"). The second is a revisit trigger. `test_non_worktree_label_colliding_with_suffix_shape_merges_into_existing_family` (test_transcript_cost.py:1458-1468) points back at this docstring, so the limitation must stay documented here. Two things to trim:
- "would falsely merge into another family" restates the behavior the test pins.
- The consumer list (cost --by-project, buckets Proj, user-input Scope) is findable by grepping `_project_family`. I confirmed it is accurate (cost.py:906, buckets.py:49 and :62, user_input.py:164 and :288). It will go stale when a caller is added.

Required property: keep the decision and the trigger, and drop the consumer enumeration. The claims are settleable and currently true, so this is not a false-claim finding.

Suggested final docstring, replacing the whole text:

```python
    """A project whose own name ends in `--claude-worktrees-<x>` merges into
    another family: accepted at current scale. If any consumer's output shows
    an unexpected family merge, re-evaluate.
    """
```

If the engineer wants the consumers named, a single clause "(cost --by-project, buckets, user-input)" is enough.

Request changes: R1 and R2 are required deletions, and R3 is optional trimming.
