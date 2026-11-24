# comment-discipline-reviewer

Set aside: the `python-environment-conventions.md` rule file that loaded mid-session. It concerns Python installs, so it plays no part in this review.

Reviewed 1 file (`redaction.py`), which carries 1 in-scope change: the new `_project_family` docstring.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/redaction.py:35-39` (docstring of `_project_family`).

Offending text:
- "Collapse a project label or a raw project-dir slug to its base-repo "family" key."
- "Strips the `--claude-worktrees-<branch>` suffix that a linked worktree's project-dir slug already carries (see `_WORKTREE_SUFFIX_RE` above); `_derive_proj_label`'s output preserves that suffix unchanged, so the same match applies to either input shape."

Issue: these clauses state no decision, only what the code and its name show.
- The summary line restates the function name and its one-line body.
- The "Strips the suffix" clause restates `_WORKTREE_SUFFIX_RE.sub("", ...)`.
- The "either input shape" clause is found by reading `_derive_proj_label` (redaction.py:25) and the callers (buckets.py:49, user_input.py:164, cost.py:906).
- That clause also duplicates the comment at redaction.py:28-30 ("which _derive_proj_label carries through unchanged onto its output"), which already holds it. This breaks single source of truth.
- Under the rule under test, a true restatement is still a restatement, so all three go.

Production failure mode: the restated detail is a second copy that drifts from the regex and its comment.

Required property: keep only the decision and its revisit trigger. Both are non-obvious and carry a reason.
- Decision: the match is on the literal substring, not on worktree provenance.
- Consequence: a project whose own name contains the substring merges into another family.
- Reason: the risk is accepted at current scale.
- Trigger: the three counters named in the docstring.
- The test `test_non_worktree_label_colliding_with_suffix_shape_merges_into_existing_family` (test_transcript_cost.py:1458-1468) cites this docstring for the limitation, so the limitation has to stay.

Concrete fix: replace the whole docstring with

```
"""Match on the literal `--claude-worktrees-` substring, not on worktree provenance.

A project whose own name contains that substring falsely merges into another family. This is an accepted risk at current scale. Re-evaluate if cost --by-project, buckets' Proj count, or user-input's Scope project count shows an unexpected merge.
"""
```

Checked against other angles: one fact per sentence, no PR-defined label, no prior-version framing.

The kept claims are sourced. The three counters exist at cost.py:906, buckets.py:49 (`Proj` column at buckets.py:62) and user_input.py:164 (`Scope: N projects` at user_input.py:288). The merge behavior is pinned by the test above.

No other findings.
