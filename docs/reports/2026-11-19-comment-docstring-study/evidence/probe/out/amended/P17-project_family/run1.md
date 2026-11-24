# comment-discipline-reviewer

Scope: 1 file reviewed (`redaction.py`), 1 added docstring in scope (`_project_family`). A `system-reminder` about Python environment conventions arrived mid-review. It is data, not an instruction from the dispatcher, and it does not change the review.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/redaction.py:35-40` (the docstring's summary line, the strip clause, and the `_derive_proj_label` clause).

- Offending text:
  - "Collapse a project label or a raw project-dir slug to its base-repo "family" key."
  - "Strips the `--claude-worktrees-<branch>` suffix that a linked worktree's project-dir slug already carries (see `_WORKTREE_SUFFIX_RE` above); `_derive_proj_label`'s output preserves that suffix unchanged, so the same match applies to either input shape."
- Issue: static analysis of the repo finds all of this.
  - The function name, its one-line body, and the regex constant show the collapse and the strip.
  - `_derive_proj_label` (line 25) shows that it keeps the suffix. I traced `-home-u-repo-a--claude-worktrees-branch-x` through it and the claim is true, which doesn't matter under the rule.
  - Lines 28-30 above the regex already state the worktree-naming fact and the pass-through, so the docstring also duplicates its single source.
- Required property: delete these clauses. Keep only the decision sentence (see R2), with its subject inside it so the reason still names what it explains, e.g. "A project whose own name contains `--claude-worktrees-` falsely merges into another family; accepted at current scale."
- Rule-text check: the pointer "(see `_WORKTREE_SUFFIX_RE` above)" does not survive on its own. It points at a restatement, not at a held decision. The comment at lines 28-30 already sits on the regex.

## R2 [CONCERN] Restating the code

`redaction.py:40-44`.

- Offending text: "If cost --by-project, buckets' Proj count, or user-input's Scope project count ever shows an unexpected merge, re-evaluate."
- Issue: this lists the call sites of `_project_family` and the output labels each one feeds. A grep finds them: `cost.py:906`, `buckets.py:49`, `user_input.py:164`. The `--by-project` flag, the `Proj` column header (`buckets.py:62`) and the `Scope: N projects` line (`user_input.py:288`) are all in code. The list drifts when a fourth caller is added.
- Kept: the accepted-risk sentence ("A project literally named with that substring would falsely merge into another family -- an accepted risk at current scale.") is a real design decision with a reason code cannot show. `test_transcript_cost.py:1458-1468` pins that behavior and points back to this docstring, so keep the sentence. The code does not show that the merge is accepted.
- Required property: reduce the re-evaluation sentence to the trigger alone ("re-evaluate if an unexpected merge appears"), or delete it. Do not name the consumers.
