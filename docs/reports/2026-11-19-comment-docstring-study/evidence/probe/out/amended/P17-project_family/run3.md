# comment-discipline-reviewer

Set aside: the `python-environment-conventions.md` system reminder (no bearing on comment review). Scope: 1 file in the diff, 1 added docstring (`_project_family`, redaction.py:35-45). Test pointer to the docstring checked at `tests/test_transcript_cost.py:1468`.

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/redaction.py:35-40`

Offending text: `"""Collapse a project label or a raw project-dir slug to its base-repo "family" key.` and `Strips the --claude-worktrees-<branch> suffix that a linked worktree's project-dir slug already carries (see _WORKTREE_SUFFIX_RE above); _derive_proj_label's output preserves that suffix unchanged, so the same match applies to either input shape.`

Issue:
- Every clause here is found by static analysis of this repository.
  - The function name and its one-line body (`_WORKTREE_SUFFIX_RE.sub("", ...)`) show the collapse and the suffix strip.
  - Following `_derive_proj_label` (redaction.py:23-25) shows that it keeps the suffix, which is why both input shapes work.
  - The worktree-naming fact is already stated at redaction.py:28-30 and in `corpus.py:196-199`. Restating it here is a second home for the same knowledge.
- The second sentence also chains three facts through a semicolon, a parenthetical and a "so" clause.
- No design decision is named in either passage.

Required property: delete both passages (the summary line and the "Strips ..." sentence). The pointer to `_WORKTREE_SUFFIX_RE` is redundant with its adjacent comment, so it goes too. The docstring then opens with the accepted-risk decision (see R2).

## R2 [CONCERN] Restating the code (consumer list and re-evaluation trigger)

File: `claude/.claude/scripts/transcript_analysis/redaction.py:40-44`

Offending text: `If cost --by-project, buckets' Proj count, or user-input's Scope project count ever shows an unexpected merge, re-evaluate.`

Issue:
- The sentence names the call sites of `_project_family`, which a grep finds: `cost.py:906`, `buckets.py:49`, `user_input.py:164`. It also tells the reader to watch for a symptom.
  - It decides nothing and gives no reason static analysis cannot find.
  - It will go stale when a caller is added or removed, such as a fourth caller of `_project_family`.
- The preceding sentence ("A project literally named with that substring would falsely merge into another family -- an accepted risk at current scale") is a real decision and stays.
  - The collision it describes is the subject of that decision, so it is not a restatement.
  - It is pinned by `tests/test_transcript_cost.py:1458-1485`, whose docstring points at this docstring (line 1468), so the pointer must keep resolving.
- Its reason, "at current scale", is vague.

Required property: delete the "If cost --by-project ... re-evaluate" sentence. Keep the accepted-risk sentence, and replace "at current scale" with the actual reason the risk is accepted. State that reason only if its source is known, for example that real project names are not expected to contain `--claude-worktrees-`. Otherwise mark it unverified. The result is one sentence: a project whose own name contains `--claude-worktrees-` merges into the family before it, and that is accepted because <reason>.
