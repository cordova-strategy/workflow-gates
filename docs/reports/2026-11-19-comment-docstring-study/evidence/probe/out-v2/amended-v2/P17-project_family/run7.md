# comment-discipline-reviewer

Scope: 1 file in the diff (`redaction.py`), 1 added docstring (`_project_family`), judged under the session's replacement "Don't restate the code" bullet. The `python-environment-conventions.md` rule file loaded mid-session does not touch this diff and is not applied.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/redaction.py:36-38` (docstring of `_project_family`)

Issue: The summary line and the "Strips the `--claude-worktrees-<branch>` suffix that a linked worktree's project-dir slug already carries (see `_WORKTREE_SUFFIX_RE` above)" clause state what the one-line body (`_WORKTREE_SUFFIX_RE.sub("", ...)`), the regex at line 31 and the comment at lines 28-30 already show. The worktree slug convention is already stated at lines 28-30 and in `iter_sessions` (`corpus.py:196-199`), so this is a second statement of it. "`above`" is also a positional reference that breaks if the constant moves.

Production failure mode: A second copy of the slug convention can drift from the regex and the original comment. It also pushes the two real decisions (accepted merge risk, revisit trigger) below restated detail.

Required property: Keep only the decision this function makes, naming what it decides, with a pointer for the suffix shape. Delete the "Strips ..." clause. Proposed opening: `"""Collapse a label or raw project-dir slug to its base-repo family key; suffix shape per the comment on `_WORKTREE_SUFFIX_RE`."""`

## R2 [CONCERN] Restating the code

`redaction.py:39-40`

Quoted: "`_derive_proj_label`'s output preserves that suffix unchanged, so the same match applies to either input shape."

Issue: The reason is findable by reading `_derive_proj_label` (line 25: `lstrip`/`replace`/`split` never touch the tail). I traced the slug `-home-u-repo-a--claude-worktrees-branch-x` through it, and the suffix survives, so the claim is true. Under the rule, a true restatement that static analysis finds is still deleted. The same fact is already stated at `redaction.py:30` ("which _derive_proj_label carries through unchanged onto its output"), which makes this a duplicate of an existing statement.

Production failure mode: Two copies of the same fact, one of which goes stale if `_derive_proj_label` changes.

Required property: Delete the clause. The "label or raw project-dir slug" wording in the summary already records the decision to accept both shapes, and the pointer to the line 28-30 comment holds the reason.

## Prior decisions and kept content

Kept, no finding:
- The accepted-risk sentence (lines 40-42) states a design decision and its reason ("at current scale"). The test at `test_transcript_cost.py:1458-1468` pins the behavior and points back to this docstring, so the sentence must stay. The test docstring says "see _project_family's docstring" and the replacement docstring still resolves it.
- The revisit trigger (lines 42-44) names real consumers: `cost --by-project` (`cost.py:906`), the buckets `Proj` column (`buckets.py:62`, `:49`) and user-input's `Scope: N projects` line (`user_input.py:164`, `:288`). All three exist at the diff's state, so I raise no false-claim finding.

Suggested final docstring:

```python
    """Collapse a label or raw project-dir slug to its base-repo family key.

    Suffix shape: see the comment on `_WORKTREE_SUFFIX_RE`. A project literally
    named with that substring would falsely merge into another family -- an
    accepted risk at current scale. If cost --by-project, buckets' Proj count,
    or user-input's Scope project count ever shows an unexpected merge,
    re-evaluate.
    """
```
