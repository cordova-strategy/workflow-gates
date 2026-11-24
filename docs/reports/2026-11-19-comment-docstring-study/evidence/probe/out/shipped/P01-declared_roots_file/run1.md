# comment-discipline-reviewer

Scope note: the rule file `python-environment-conventions.md` that appeared mid-session is unrelated to this review and was set aside.

Reviewed 1 file (`claude/.claude/scripts/_config_dir.py`); 1 carried an in-scope comment change (the new `declared_roots_file()` docstring, lines 45-48).

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/_config_dir.py:45-48`

Offending text:

> Return the path declared_roots_matching() reads: TRANSCRIPT_CONFIG_DIRS_FILE if set (a test seam mirroring cleanup-merged-branches.sh's CLEANUP_MERGED_BRANCHES_ROOTS_FILE), else ~/.claude/transcript-config-dirs. Unlike TRANSCRIPT_CONFIG_DIRS_LABEL, this DOES follow the seam.

Issue:
- The first sentence paraphrases line 50, which reads the env var and falls back to `Path.home() / ".claude" / "transcript-config-dirs"`.
- The test-seam parenthetical and the `cleanup-merged-branches.sh` comparison repeat the `declared_roots_matching()` docstring (lines 90-92), so the same fact now has two homes. The contrast with `TRANSCRIPT_CONFIG_DIRS_LABEL` is already stated at the label (lines 13-16).
- I checked every factual claim and none is false:
  - `_config_dir.py:15-17` confirms that the label constant does not follow the seam.
  - `cleanup-merged-branches.sh:251-255` confirms that `CLEANUP_MERGED_BRANCHES_ROOTS_FILE` is a test seam.
  - Line 50 confirms the env var and the default path.

  The finding is redundancy, not falsehood.

Production failure mode: a later edit to the seam's name, the default path or the sibling script's variable has to be made in three docstrings, and the copies drift.

Required property:
- Delete the restating sentence and the duplicated seam and sibling-script comparison.
- Keep at most one sentence with the one fact the code doesn't show. For example: "Resolves against `Path.home()`, never `config_dir()`, so `CLAUDE_CONFIG_DIR` doesn't move it; only `TRANSCRIPT_CONFIG_DIRS_FILE` does." Line 58-60 states the `Path.home()` fact only in a different function's docstring.
- If you keep the contrast with the label, leave it at the label comment (lines 13-16) as the single home.
- If you keep any of it, give each fact its own sentence. The first sentence currently chains the default, the override, and a parenthetical aside.

Prior decisions: none supplied.

## Verdict

Approve with concerns (R1).
