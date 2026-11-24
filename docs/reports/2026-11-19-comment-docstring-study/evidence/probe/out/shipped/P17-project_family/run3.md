# comment-discipline-reviewer

Scope: 1 file reviewed (`claude/.claude/scripts/transcript_analysis/redaction.py`), 1 docstring added (`_project_family`). Setting aside: the later system-reminder on Python environment conventions has no bearing on this review, so I did not apply it.

## R1 [CONCERN] Restating the code
redaction.py:36-40 (docstring sentence 1: "Strips the `--claude-worktrees-<branch>` suffix that a linked worktree's project-dir slug already carries (see `_WORKTREE_SUFFIX_RE` above); `_derive_proj_label`'s output preserves that suffix unchanged, so the same match applies to either input shape.")
- Issue: Most of the sentence restates what the one-line body (`_WORKTREE_SUFFIX_RE.sub("", ...)`) and the regex name show. The rest restates the comment at redaction.py:28-30, which already says `_derive_proj_label` carries the suffix through unchanged. That duplicates a fact with a canonical home one screen above it.
- I checked the claim itself: `_derive_proj_label` (line 23-25) does preserve the suffix, so it is true. The finding is duplication, not falsehood.
- Required property: delete the "Strips ... suffix" restatement and the repeated `_derive_proj_label` explanation. Keep the one non-obvious fact, that the function accepts both a label and a raw slug, as a single short clause that points at the comment above. For example: "Accepts either a derived label or a raw slug; see the `_WORKTREE_SUFFIX_RE` comment for why."

## R2 [CONCERN] Multi-fact comment structure
redaction.py:36-40, same sentence as R1.
- Issue: One sentence chains three facts through a parenthetical, a semicolon and a "so". The facts are what gets stripped, what the other function does, and the consequence for input shapes. A reader must parse the whole thing to separate them.
- Required property: if R1's fix is not taken in full, split into one sentence per fact. Otherwise this is resolved by R1.

## R3 [FYI] Paragraph readability / coupling to other modules' output text
redaction.py:41-44 ("If cost --by-project, buckets' Proj count, or user-input's Scope project count ever shows an unexpected merge, re-evaluate.")
- Issue: The sentence puts the instruction ("re-evaluate") after a long condition that lists three consumers by their rendered output strings. I verified each name against the code: `Proj` is at buckets.py:62, `Scope: N projects` at user_input.py:288, and `_project_family` is called in cost.py:906. All three are accurate today. But the strings live in other modules and will drift silently if those headings are renamed. The sentence also puts the risk, its acceptance and the re-evaluation trigger in one run.
- Required property: lead with the trigger, then name the callers by function or module. For example: "Accepted risk at current scale: a project literally named with this substring merges into another family. Re-evaluate if a caller's project count (cost `--by-project`, buckets, user-input) shows an unexpected merge." This drops the display-string coupling and keeps every fact.

## Checked, no finding
- "A project literally named with that substring would falsely merge" is supported by the pinned test at tests/test_transcript_cost.py:1458-1484. The regex needs at least one character after the substring, which the docstring does not state. That is too minor to raise.
- "Accepted risk at current scale" is a design judgment, not a claim, so it draws no False or unsourced finding.
- No PR-defined labels, "used to be X" framing, or auto-memory citations were found in the added text.
