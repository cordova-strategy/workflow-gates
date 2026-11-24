# comment-discipline-reviewer

Scope: 1 file in the diff (`claude/.claude/scripts/transcript_analysis/redaction.py`), 1 in scope: the new `_project_family` docstring (lines 35-45 of the snapshot). Text set aside: none. The session's replacement "Don't restate the code" bullet contradicts nothing in this file, so it is applied as written.

Kept decision: the accepted-risk sentence ("A project literally named with that substring would falsely merge into another family -- an accepted risk at current scale"). It names what was decided and why. `test_transcript_cost.py:1468` points readers at this docstring for it, so the docstring must keep it. R1-R4 each delete one clause. R2 and R4 also change the kept sentence's wording.

## R1 [CONCERN] Prose restating the code

`redaction.py:35`: `Collapse a project label or a raw project-dir slug to its base-repo "family" key.`

- Issue: the function name `_project_family`, its `raw_proj_label` parameter and its one-line `re.sub` body already show this. The clause is a docstring clause that decides nothing, and static analysis finds everything it says.
- Fix: delete the clause. With R2-R4 applied, nothing of the opening line remains except the decision sentence.

## R2 [CONCERN] Prose restating the code

`redaction.py:37-38`: `Strips the --claude-worktrees-<branch> suffix that a linked worktree's project-dir slug already carries (see _WORKTREE_SUFFIX_RE above);`

- Issue: `_WORKTREE_SUFFIX_RE` and the `.sub("", ...)` call show the stripping. The comment at lines 28-30 already states the worktree naming and holds the one decision about it, which is a second copy under single-source-of-truth. The `see ... above` pointer points at a regex and comment the reader can see directly above, so it adds nothing.
- Fix: delete the clause. The kept accepted-risk sentence refers to "that substring", whose only antecedent is this clause. Make it self-contained, e.g. "A project whose own name contains `--claude-worktrees-` falsely merges into another family; accepted at current scale."

## R3 [CONCERN] Prose restating the code

`redaction.py:39-40`: `_derive_proj_label's output preserves that suffix unchanged, so the same match applies to either input shape.`

- Issue: `_derive_proj_label` (line 25) shows this (`lstrip` / `replace(..., 2)` / `split`). The comment at lines 28-30 already says `_derive_proj_label` "carries through unchanged", so it is also a duplicate statement of the same fact.
- Fix: delete the clause.

## R4 [CONCERN] Prose restating the code

`redaction.py:42-44`: `If cost --by-project, buckets' Proj count, or user-input's Scope project count ever shows an unexpected merge, re-evaluate.`

- Issue: this enumerates the consumers of `_project_family`, which grep finds: `cost.py:906`, `buckets.py:49` and `user_input.py:164`. I checked each name against its call site. The `cost --by-project` section prints at `cost.py:1087`, the buckets `Proj` column is at `buckets.py:62`, and the `Scope: N projects` line is at `user_input.py:288`. The list is accurate today but goes stale when a caller is added.
- Fix: delete the clause. If a revisit trigger is wanted, state it without naming consumers, e.g. "Revisit if any per-project count shows an unexpected merge." Even that is thin, because the decision sentence already says the risk is accepted.
