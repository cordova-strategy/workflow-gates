# comment-discipline-reviewer

Scope: 1 file in the diff (`claude/.claude/scripts/transcript_analysis/redaction.py`), 1 carrying an in-scope change (the new `_project_family` docstring, diff lines 8-18). Under the amended "Don't restate the code" rule, only the accepted-risk sentence is a kept decision.

## R1 [CONCERN] Restating the code

redaction.py:36-38 (diff lines 8-10).

Text: `Collapse a project label or a raw project-dir slug to its base-repo "family" key.` and `Strips the --claude-worktrees-<branch> suffix that a linked worktree's project-dir slug already carries (see _WORKTREE_SUFFIX_RE above);`

Issue: Both clauses state what the one-line body (`_WORKTREE_SUFFIX_RE.sub("", raw_proj_label)`), the function name and the regex already show. Neither gives a reason static analysis cannot find. The "see `_WORKTREE_SUFFIX_RE` above" pointer only points at the very thing the sentence restates. The decision it would point to already lives in the comment at redaction.py:28-30.

Required property: delete both clauses. Nothing about what the function does should remain in the docstring.

## R2 [CONCERN] Restating the code, partly false claim

redaction.py:39-40 (diff lines 11-12).

Text: `_derive_proj_label's output preserves that suffix unchanged, so the same match applies to either input shape.`

Issue:
- It describes what `_derive_proj_label` does (redaction.py:25), which static analysis finds. The comment at redaction.py:28-30 already states it ("which _derive_proj_label carries through unchanged onto its output"), so this is a second statement of the same fact.
- It is also only partly true. `_derive_proj_label` runs `.replace("-", "/", 2)` on the lstripped slug. When fewer than three hyphen-separated segments precede the suffix, the replace consumes one hyphen of the `--`. For example, `-home-user--claude-worktrees-x` becomes `-claude-worktrees-x`, and `_WORKTREE_SUFFIX_RE` (redaction.py:31) no longer matches. "Unchanged" therefore fails for short slugs.

Required property: delete the sentence. The existing comment at redaction.py:28-30 is the single home for this fact. If the caveat matters, correct it there rather than restating it here.

## R3 [CONCERN] Restating the code, multi-fact enumeration of consumers

redaction.py:42-44 (diff lines 14-17).

Text: `If cost --by-project, buckets' Proj count, or user-input's Scope project count ever shows an unexpected merge, re-evaluate.`

Issue:
- It enumerates `_project_family`'s consumers: cost.py:906, buckets.py:49 and user_input.py:164. Grepping the callers finds them, so this is not a decision with a reason beyond the code.
- It is a hand-maintained list that goes stale when a caller is added or removed.
- It chains three differently named report surfaces into one sentence.

Required property: delete the sentence.

Kept, no finding: `A project literally named with that substring would falsely merge into another family -- an accepted risk at current scale.` This is a design decision (accepting the risk) with a rationale. `test_transcript_cost.py:1468` points back to it. After R1-R3, restate the subject inside the decision sentence. Name the literal `--claude-worktrees-` substring match as the thing whose false merge is accepted, so the sentence still says what it explains. Then the docstring holds only that one sentence.
