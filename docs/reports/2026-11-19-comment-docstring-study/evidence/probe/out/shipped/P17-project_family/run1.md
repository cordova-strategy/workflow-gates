# comment-discipline-reviewer

Scope: 1 file reviewed (`redaction.py`), 1 carried an in-scope change (the new `_project_family` docstring). Checked every factual claim in it against the repo and found none false: `_derive_proj_label` does preserve the suffix, and the three named consumers exist at `cost.py:906`, `buckets.py:49` and `user_input.py:164`/`:288`. The collision limitation matches the pinned test at `test_transcript_cost.py:1458`.

## R1 [CONCERN] Restating the code
File: `claude/.claude/scripts/transcript_analysis/redaction.py:37-40` (docstring paragraph 1).
Issue: "Strips the `--claude-worktrees-<branch>` suffix that a linked worktree's project-dir slug already carries (see `_WORKTREE_SUFFIX_RE` above); `_derive_proj_label`'s output preserves that suffix unchanged". The regex on line 31 and the one-line body show the stripping. The comment directly above the regex (lines 28-30) already states both facts: the slug is the main slug plus `--claude-worktrees-<branch>`, and `_derive_proj_label` carries it through unchanged. The docstring therefore duplicates a neighbouring comment, which breaks single-source-of-truth.
Production failure mode: two copies of the naming convention drift apart when the worktree naming changes.
Required property: delete the restated naming and carry-through sentences. Keep only what is not stated elsewhere: the input may be either a raw slug or a derived label (a short sentence, since the `_derive_proj_label` carry-through is documented on the regex comment), plus the collision risk and re-evaluation trigger.

## R2 [CONCERN] Multi-fact comment structure
File: `redaction.py:37-40`.
Issue: the first docstring sentence chains three facts through a parenthetical `(see ...)` and a semicolon: what is stripped, where the definition lives, and that the label input preserves the suffix. The tightly-coupled-pair exemption covers two facts and not a third aside.
Production failure mode: a reader has to parse the whole sentence to find that "either input shape" is the point.
Required property: if R1's trimming is not applied, give each fact its own sentence. After R1, the remaining content should be: one sentence saying the function accepts a raw slug or a derived label, then the risk, then the re-evaluation trigger.

## R3 [FYI] Prose at the wrong altitude / goes stale
File: `redaction.py:42-44`.
Issue: "If cost --by-project, buckets' Proj count, or user-input's Scope project count ever shows an unexpected merge, re-evaluate." This lists consumers by name inside the callee's docstring. The list is accurate now, but a new `_project_family` caller would not be added to it.
Required property: either keep it, accepting that it can go stale, or say "if any caller's project counts show an unexpected merge". The test docstring at `test_transcript_cost.py:1461-1468` already points back to this docstring as the home of the limitation, so the list is better kept short.
