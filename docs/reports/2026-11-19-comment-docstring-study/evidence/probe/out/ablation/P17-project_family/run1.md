# comment-discipline-reviewer

Set aside: the `python-environment-conventions.md` reminder, which has nothing to do with this diff, and no prompt text widened or narrowed scope. Reviewed 1 file (`redaction.py`), and 1 carried an in-scope change: the new `_project_family` docstring (lines 35-45). The docstring has five clauses. Each is a Prose restating the code finding whose fix is deleting that clause. Every angle was checked against each fix, and deleting the whole docstring leaves nothing that trades one violation for another.

## R1 [CONCERN] Prose restating the code

`redaction.py:35` — `"""Collapse a project label or a raw project-dir slug to its base-repo "family" key.`

Issue: the clause restates what the name `_project_family`, the `_WORKTREE_SUFFIX_RE.sub("", raw_proj_label)` body and the `raw_proj_label: str` parameter already show.
Production failure mode: none. A reader gets nothing from it that the signature and body don't give.
Required property: delete the clause. No kept decision depends on it as its subject.

## R2 [CONCERN] Prose restating the code

`redaction.py:37-38` — `Strips the --claude-worktrees-<branch> suffix that a linked worktree's project-dir slug already carries (see _WORKTREE_SUFFIX_RE above);`

Issue: the regex, its body use and the comment at lines 28-30 already state this.
Static analysis of this file finds it.
Required property: delete the clause, including its "see `_WORKTREE_SUFFIX_RE` above" pointer. The pointer leads only to the same restatement. The decision it would point to sits in the comment above the regex, which stays.

## R3 [CONCERN] Prose restating the code

`redaction.py:39-40` — `_derive_proj_label's output preserves that suffix unchanged, so the same match applies to either input shape.`

Issue: this is derivable by reading `_derive_proj_label` (line 25: `lstrip`/`replace`/`split` keeps the `--claude-worktrees-…` tail). It also duplicates the pre-existing comment at lines 28-30, which already says "_derive_proj_label carries through unchanged onto its output". That duplication is a second reason it fails (single source of truth).
Required property: delete the clause. The comment above the regex remains the one home for this fact.

## R4 [CONCERN] Prose restating the code

`redaction.py:40-42` — `A project literally named with that substring would falsely merge into another family -- an accepted risk at current scale.`

Issue: the regex `--claude-worktrees-.+$` matches on the literal substring, so the merge behavior is derivable from the code. `test_transcript_cost.py:1458-1479` also pins it. The rule deletes what static analysis of the code and tests finds, even when the clause is true.
Required property: delete the clause. `test_transcript_cost.py:1468` ends with "see _project_family's docstring", which this deletion orphans. Repoint it to the test itself, or drop the pointer. That file is not in the diff. Handle it as a follow-on edit so no dangling reference is left.

## R5 [CONCERN] Prose restating the code

`redaction.py:42-44` — `If cost --by-project, buckets' Proj count, or user-input's Scope project count ever shows an unexpected merge, re-evaluate.`

Issue: the clause lists the callers of `_project_family`, which grep finds (`cost.py:906`, `buckets.py:49`, `user_input.py:164`). Its only other content is an instruction to "re-evaluate", and no reader can act on that without already knowing what to do. The caller list also goes stale as callers change.
Required property: delete the clause.

## Verdict

Request changes: delete the entire docstring (R1-R5), then repoint the orphaned `see _project_family's docstring` reference in `test_transcript_cost.py:1468`.
