# comment-discipline-reviewer

Scope: 1 file reviewed (`redaction.py`), 1 carrying an in-scope change (the new `_project_family` docstring, diff lines 8-18). No prompt text set aside.

## R1 [CONCERN] Restating the code / single-source duplicate

File: `claude/.claude/scripts/transcript_analysis/redaction.py:37-40` (docstring added to `_project_family`)

Issue: "Strips the `--claude-worktrees-<branch>` suffix that a linked worktree's project-dir slug already carries (see `_WORKTREE_SUFFIX_RE` above); `_derive_proj_label`'s output preserves that suffix unchanged…" repeats the comment directly above at `redaction.py:28-30`. That comment already says a worktree slug is the main slug plus `--claude-worktrees-<branch>` and that `_derive_proj_label` carries it through unchanged. The strip itself is visible in the one-line body (`_WORKTREE_SUFFIX_RE.sub("", …)`). The same two facts now live in two places, and the docstring itself points back at one of them with "see … above".

I confirmed the facts are true. `_derive_proj_label("-home-u-repo-a--claude-worktrees-branch-x")` yields `repo-a--claude-worktrees-branch-x`, so the suffix survives. They fail on duplication, not on accuracy.

Fix: delete the strip and "carries/preserves unchanged" sentences from the docstring. Keep the one non-obvious fact not stated elsewhere: the function accepts either a raw slug (`buckets.py:49`, `user_input.py:164`) or a `_derive_proj_label` output (`cost.py:906`). Cite the comment above for why both shapes work, e.g. "Accepts a raw project-dir slug or a `_derive_proj_label` output; both carry the worktree suffix (see `_WORKTREE_SUFFIX_RE`)."

## R2 [CONCERN] Multi-fact comment structure

File: `redaction.py:37-40`

Issue: The second sentence chains the suffix-strip fact, a parenthetical cross-reference, and a semicolon-joined second fact (`_derive_proj_label` preserves the suffix, so the same match applies to both inputs). That is more than one tightly coupled pair, so a reader has to parse the whole sentence to find where one fact ends.

Fix: One sentence per fact. If R1 is applied, this resolves with it. Otherwise split at the semicolon.

## R3 [FYI] Comment verbosity (consumer enumeration in the re-evaluate trigger)

File: `redaction.py:42-44`

Issue: "If cost --by-project, buckets' Proj count, or user-input's Scope project count ever shows an unexpected merge, re-evaluate." Each named consumer is real (`cost.py:906`, `buckets.py:49` with the `Proj` column at `buckets.py:62`, `user_input.py:164` and `:288`), so the claim is not false. The list is a call-site inventory that goes stale when a consumer is added or removed. `cost.py:771` already points readers at `_project_family` from the consumer side. The risk sentence before it is justified: `test_transcript_cost.py:1458-1468` pins that merge behavior and cites this docstring.

Fix: Replace the inventory with the trigger, e.g. "Re-evaluate if any per-project count shows an unexpected merge." Keep the collision-risk sentence.

No PR-defined terminology, "used to be" framing, or unsourced-claim findings. The "accepted risk at current scale" phrase is a design judgment, not a claim.
