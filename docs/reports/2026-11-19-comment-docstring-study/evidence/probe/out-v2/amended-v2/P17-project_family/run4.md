# comment-discipline-reviewer

Scope: 1 file in the diff (`claude/.claude/scripts/transcript_analysis/redaction.py`), 1 added docstring (`_project_family`). I set aside the rules-file system-reminder (`python-environment-conventions.md`): it is not a diff or input field and has no bearing on this scope.

## R1 [CONCERN] Restating the code

`redaction.py:35-40` (the docstring's first three sentences).

Offending text:
- "Collapse a project label or a raw project-dir slug to its base-repo "family" key."
- "Strips the `--claude-worktrees-<branch>` suffix that a linked worktree's project-dir slug already carries (see `_WORKTREE_SUFFIX_RE` above);"
- "`_derive_proj_label`'s output preserves that suffix unchanged, so the same match applies to either input shape."

Issue: these clauses state what the one-line body (`_WORKTREE_SUFFIX_RE.sub("", raw_proj_label)`), the function name, and the callers already show. The two input shapes are visible at `buckets.py:49` (raw slug) and `cost.py:906` (label). The worktree-slug naming and the suffix pass-through are already documented at `redaction.py:28-30` (the comment above the regex) and `corpus.py:199` (`iter_sessions`). The regression tests at `test_transcript_buckets.py:119` and `test_transcript_user_input.py:392` also pin the pass-through. The rule under test says to delete anything static analysis of the repo's code and tests finds, even when it takes several files. It also says a shorter or corrected restatement still restates. None of the three clauses states a decision with a reason, so the "keep the decision half" provision does not apply.

Production failure mode: the same fact now lives in three places (regex comment, docstring, `iter_sessions`). A rename of the suffix convention then has to be updated in all three.

Required property: delete all three clauses. The pointer to `_WORKTREE_SUFFIX_RE` goes with them, since it points at no decision. Keep only the decision and its trigger (see R2 for the replacement text).

## R2 [FYI] Vague reason on the kept decision

`redaction.py:40-44` ("A project literally named with that substring would falsely merge into another family -- an accepted risk at current scale. If cost --by-project, buckets' Proj count, or user-input's Scope project count ever shows an unexpected merge, re-evaluate.").

This is the part to keep: it names an accepted risk and gives a revisit trigger. I checked the three named surfaces and all exist: `cost --by-project` (`cost.py:906`, `:1087`), buckets' `Proj` column (`buckets.py:49`, `:62`) and user-input's `Scope: N projects` line (`user_input.py:164`, `:288`). No false-claim finding.

Weakness: "at current scale" gives no checkable reason, and a reader cannot tell what scale would break it. The collision behavior is pinned by `test_transcript_cost.py:1458-1468`, which cites this docstring by name as the limitation's record. That test is the pointer to keep, and the docstring must keep a statement of the decision so the cross-reference still resolves.

Proposed replacement for the whole docstring:

```python
"""A project literally named with `--claude-worktrees-` falsely merges into another family.

Accepted risk (pinned by test_non_worktree_label_colliding_with_suffix_shape_merges_into_existing_family).
If cost --by-project, buckets' Proj count, or user-input's Scope project count shows an
unexpected merge, re-evaluate.
"""
```

This keeps every decision and trigger. It also gives "current scale" a checkable stand-in: the pinning test. If the author has a concrete reason the risk is acceptable (for example, the corpus never contains such names), state it there instead of "at current scale".
