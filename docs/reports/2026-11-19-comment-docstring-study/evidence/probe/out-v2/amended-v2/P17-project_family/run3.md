# comment-discipline-reviewer

Reviewed 1 file in the diff (`claude/.claude/scripts/transcript_analysis/redaction.py`); it carries one in-scope change, the new `_project_family` docstring. The diff adds that docstring only.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/redaction.py:37-40` (diff lines 10-13)

Issue: the second and third sentences state what the code already shows.
- "Strips the `--claude-worktrees-<branch>` suffix that a linked worktree's project-dir slug already carries (see `_WORKTREE_SUFFIX_RE` above)" restates the one-line `_WORKTREE_SUFFIX_RE.sub("", ...)` body. It also restates the comment above the regex at lines 28-30.
- "`_derive_proj_label`'s output preserves that suffix unchanged, so the same match applies to either input shape" is found by reading `_derive_proj_label` (line 25). I traced it for `-home-u-repo-a--claude-worktrees-branch-x`: it yields `repo-a--claude-worktrees-branch-x`, so the claim is true. It still restates code, and it repeats the comment at lines 28-30 ("which _derive_proj_label carries through unchanged onto its output"), a duplicate home for one fact.

Production failure mode: when the regex or `_derive_proj_label` changes, three places (the code, the comment above the regex, the docstring) must change together, and the docstring copy is the one most likely to be left stale.

Required property: the docstring keeps only the decisions, which are the "family" definition and the accepted merge risk. Delete both sentences. The rule under test says a corrected restatement still restates, and "naming what a kept decision decides is not a restatement."

Keep the accepted-risk sentence. `test_transcript_cost.py:1468` points readers to this docstring for the documented limitation.

Proposed replacement docstring:

```
"""Collapse a project label or raw project-dir slug to its base-repo "family" key.

Accepted risk: a project whose own name contains `--claude-worktrees-` merges
into another family, tolerable at current scale. Re-evaluate if any
family-keyed project count shows an unexpected merge.
"""
```

## R2 [FYI] Restating the code (trigger half)

`claude/.claude/scripts/transcript_analysis/redaction.py:41-44` (diff lines 14-17)

Issue: "If cost --by-project, buckets' Proj count, or user-input's Scope project count ever shows an unexpected merge, re-evaluate." The revisit trigger is a kept decision. The enumerated consumers are restated detail that grep finds.
- I confirmed all three are real: `cost.py:906`, `buckets.py:49` with its `Proj` column at line 62, and `user_input.py:164` with `Scope: N projects` at line 288.
- The list goes stale when a fourth caller of `_project_family` is added. It is also a long sentence with two further facts in one run-on.

Required property: state the trigger without the caller list, as in the R1 replacement. If the author wants the observability hint kept, put it in a separate sentence.

## Prior decisions

None supplied.

No PR-defined terminology, "used to be X" framing, wrong-altitude, or false-claim findings. Every claim I could settle holds:
- the suffix-preservation claim, traced above;
- the three consumer names;
- the collision behavior, pinned by `test_transcript_cost.py:1458-1485`.
