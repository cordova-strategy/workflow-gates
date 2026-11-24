# comment-discipline-reviewer

Scope note: the dispatch prompt's amended "Don't restate the code" bullet replaces the CLAUDE.md bullet of the same name for this review. I applied the amended bullet. Nothing else in the prompt was set aside.

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/_config_dir.py:45-49` (new docstring on `declared_roots_file()`)

Offending text:

> Return the path declared_roots_matching() reads: TRANSCRIPT_CONFIG_DIRS_FILE if set (a test seam mirroring cleanup-merged-branches.sh's CLEANUP_MERGED_BRANCHES_ROOTS_FILE), else ~/.claude/transcript-config-dirs. Unlike TRANSCRIPT_CONFIG_DIRS_LABEL, this DOES follow the seam.

Issue: most of the docstring restates what static analysis of the repository finds, which the amended rule says to delete even when true.
- "Return the path declared_roots_matching() reads" is a grep for the callers.
- "X if set, else ~/.claude/transcript-config-dirs" restates the `or` expression on line 50.
- "mirroring cleanup-merged-branches.sh's CLEANUP_MERGED_BRANCHES_ROOTS_FILE" is findable at `cleanup-merged-branches.sh:251-255`, whose comment already says "same pattern as".
- "this DOES follow the seam" restates line 50. The decision it contrasts with is already stated, with its reason, at `_config_dir.py:13-17`.

What is left is one decision: `TRANSCRIPT_CONFIG_DIRS_FILE` exists as a test seam, and the display label deliberately does not follow it. That decision belongs in the docstring as a pointer to the label.

Cross-check:
- The claims in the docstring are true: `declared_roots_matching()` calls `declared_roots_file()` at line 123, and the seam name matches `cleanup-merged-branches.sh:255`.
- I found no false or unsourced claim.
- The same "test seam mirroring ..." parenthetical already sits in `declared_roots_matching()`'s docstring (lines 90-92). That one predates this diff and is out of scope. The new copy still duplicates it.

Required property and fix: replace the docstring with one sentence. Suggested text:

`"""TRANSCRIPT_CONFIG_DIRS_FILE is a test seam; TRANSCRIPT_CONFIG_DIRS_LABEL deliberately ignores it."""`

Deleting the docstring entirely is also acceptable, because lines 13-17 already carry the decision.
