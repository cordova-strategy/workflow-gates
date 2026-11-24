# comment-discipline-reviewer

Scope: 1 file reviewed (`claude/.claude/scripts/transcript_analysis/redaction.py`), 1 carrying an in-scope change (the new `_project_family` docstring). No prompt text contradicted this file's scope, so nothing was set aside. The session's replacement "Don't restate the code" bullet is applied: every docstring clause is checked, and each one other than the kept decision is deleted.

## R1 [CONCERN] Restating the code
redaction.py:36 (diff line 8)
Text: `Collapse a project label or a raw project-dir slug to its base-repo "family" key.`
Issue: The name `_project_family`, its parameter `raw_proj_label`, and the one-line body already show this. The clause states no decision and gives no reason static analysis can't find.
Required property: Delete the clause. Under the replacement rule, "family" is a self-evident name and does not earn a summary line.

## R2 [CONCERN] Restating the code
redaction.py:38-39 (diff lines 10-11)
Text: `Strips the --claude-worktrees-<branch> suffix that a linked worktree's project-dir slug already carries (see _WORKTREE_SUFFIX_RE above);`
Issue: The body `_WORKTREE_SUFFIX_RE.sub("", ...)` and the regex definition show the stripping. The worktree-naming fact is already stated at redaction.py:28-30 (and in `iter_sessions`), so this clause also duplicates a canonical home.
Required property: Delete the clause. The pointer to `_WORKTREE_SUFFIX_RE` is only worth keeping if it stays attached to a kept decision, and the remaining accepted-risk sentence needs no pointer.

## R3 [CONCERN] Restating the code
redaction.py:39-40 (diff lines 11-12)
Text: `` `_derive_proj_label`'s output preserves that suffix unchanged, so the same match applies to either input shape. ``
Issue: Reading `_derive_proj_label` at redaction.py:23-25 shows this, and redaction.py:30 already states it ("carries through unchanged onto its output"). It is a second copy of a fact that already has a home, and it describes how the code works.
Required property: Delete the clause, even though it is a short and true restatement. Note: the claim holds for realistic slugs but not universally. The `.replace("-", "/", 2)` call consumes the first `--` dash when the main dir is only two path components deep (e.g. `-home-u--claude-worktrees-b` becomes `-claude-worktrees-b`, which the regex doesn't match). Deleting the clause removes the risk of a stale overclaim.

## R4 [CONCERN] Restating the code
redaction.py:42-44 (diff lines 14-16)
Text: `If cost --by-project, buckets' Proj count, or user-input's Scope project count ever shows an unexpected merge, re-evaluate.`
Issue: The list of consumers is what a grep for `_project_family` finds (cost.py:906, buckets.py:49, user_input.py:164). It restates call sites that will drift as consumers are added, and it is not a decision with a reason.
Required property: Delete the consumer list. Keep only the "re-evaluate if an unexpected merge appears" trigger if the accepted-risk decision needs it, with no enumeration of reports.

## Kept
The sentence "A project literally named with that substring would falsely merge into another family -- an accepted risk at current scale." states a design decision (accepting the false merge) with its rationale. It stays, with its subject (a project named with `--claude-worktrees-`) inside the sentence. It is a pointed-to anchor: `test_transcript_cost.py:1468` cites "_project_family's docstring" for this limitation, so deleting it would orphan that reference. Once R1-R4 land, this is the whole docstring.
