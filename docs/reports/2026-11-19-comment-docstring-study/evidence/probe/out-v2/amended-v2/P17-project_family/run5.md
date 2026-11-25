# comment-discipline-reviewer

Reviewed 1 file (`redaction.py`); 1 carried an in-scope comment change (the new `_project_family` docstring).

Ignored from the prompt: none. A system reminder carrying `python-environment-conventions.md` arrived mid-session. It concerns Python installs and has no bearing on this review, so I set it aside.

## R1 [CONCERN] Restating the code
redaction.py:35-38 (diff lines 8-11).

Text: `Collapse a project label or a raw project-dir slug to its base-repo "family" key.` and `Strips the --claude-worktrees-<branch> suffix that a linked worktree's project-dir slug already carries (see _WORKTREE_SUFFIX_RE above);`

Issue: the first sentence restates the function name `_project_family`, its parameter and its one-line body. The second restates the regex at line 31. It also repeats the worktree-naming fact that the comment at lines 28-30 already holds, and that `corpus.py:199` documents. Neither sentence states a decision with a reason that static analysis can't find. Under the session rule, a restatement is deleted even when it is true. I checked that it is true: `_WORKTREE_SUFFIX_RE` is `--claude-worktrees-.+$`.

Required property: delete both sentences. The regex comment at lines 28-30 is the home for the worktree-naming fact.

## R2 [CONCERN] Restating the code, and a second copy of a fact that already has a home
redaction.py:38-40 (diff lines 11-13).

Text: `` `_derive_proj_label`'s output preserves that suffix unchanged, so the same match applies to either input shape.``

Issue: static analysis of `_derive_proj_label` (line 25) finds this. The comment at lines 28-30 already says it ("which _derive_proj_label carries through unchanged onto its output"). That makes it a second copy of the same fact, against the single-source-of-truth rule. The sentence also depends on the "either input shape" framing from the deleted summary.

Required property: delete the sentence. Nothing in it is a decision or a trigger.

## Kept, no finding
Diff lines 13-17 state decisions with a reason and a trigger. Keep them:
- Decision: a project literally named with the suffix substring falsely merges, and that risk is accepted.
- Reason: current scale.
- Trigger: an unexpected merge in `cost --by-project` (`cost.py:720`), the buckets `Proj` column (`buckets.py:62`), or the user-input `Scope: N projects` line (`user_input.py:288`).

The named surfaces all exist, so the pointers are accurate. The "accepted risk at current scale" claim is a design judgment, not a settleable or unsourced claim.

Suggested replacement docstring after R1 and R2:

```python
    """A project literally named with `--claude-worktrees-` falsely merges into another family.

    That risk is accepted at current scale. If cost --by-project, buckets' Proj
    count, or user-input's Scope project count ever shows an unexpected merge,
    re-evaluate.
    """
```

I checked the replacement against the other angles. It is two sentences with one fact each, it states no PR-only framing, and the pointers resolve.
