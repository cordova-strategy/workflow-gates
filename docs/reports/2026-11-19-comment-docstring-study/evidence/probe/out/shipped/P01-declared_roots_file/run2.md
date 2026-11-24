# comment-discipline-reviewer

Scope: 1 file reviewed (`claude/.claude/scripts/_config_dir.py`), 1 in-scope change (new docstring on `declared_roots_file()`, lines 45-49). One dispatch-prompt note: the `python-environment-conventions.md` rule text in context concerns installing Python dependencies, not this diff, so I set it aside.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/_config_dir.py:45-49`

Issue: the added docstring is "Return the path declared_roots_matching() reads: TRANSCRIPT_CONFIG_DIRS_FILE if set (a test seam mirroring cleanup-merged-branches.sh's CLEANUP_MERGED_BRANCHES_ROOTS_FILE), else ~/.claude/transcript-config-dirs. Unlike TRANSCRIPT_CONFIG_DIRS_LABEL, this DOES follow the seam."

- Sentence 1 restates line 50. The body shows the `TRANSCRIPT_CONFIG_DIRS_FILE`-or-default branching, and the function name and `-> Path` show that it returns the path.
- Both non-obvious facts already have a canonical home in this file:
  - The seam mirroring `CLEANUP_MERGED_BRANCHES_ROOTS_FILE` is stated in the `declared_roots_matching()` docstring (lines 90-92).
  - The contrast with `TRANSCRIPT_CONFIG_DIRS_LABEL` is stated in the comment above the label (lines 13-16).
  - The new docstring is a second copy of both. That breaks the single-source-of-truth rule.
- Sentence 1 also chains three facts in one sentence with a colon and a parenthetical: what the function reads, the env override, and the seam's lineage. That is a Multi-fact comment structure concern, but deletion resolves it.

Claim check (no False or unsourced claim finding). Every claim in the text holds against the repo:
- `declared_roots_matching()` calls `declared_roots_file()` at line 123.
- Line 50 follows `TRANSCRIPT_CONFIG_DIRS_FILE` and falls back to `~/.claude/transcript-config-dirs`.
- `TRANSCRIPT_CONFIG_DIRS_LABEL` is a constant at line 17 and does not follow the seam.
- `cleanup-merged-branches.sh:251-255` describes `CLEANUP_MERGED_BRANCHES_ROOTS_FILE` as a test seam.

Required property: the docstring is deleted, because a shorter or corrected restatement still restates. A reader who needs the seam rationale finds it at the `declared_roots_matching()` docstring and the label comment. If a pointer is wanted, give it a back-reference at the label comment (lines 13-16) rather than a second copy of the contrast.

Verdict: Approve with concerns (R1).
