# comment-discipline-reviewer

Scope: 1 file reviewed (`claude/.claude/scripts/_config_dir.py`), 1 site in scope (new `declared_roots_file()` docstring, lines 45-49). Rule applied: the amended "Don't restate the code" bullet from the dispatch prompt.

The `python-environment-conventions.md` reminder that appeared mid-session governs Python installs, not this review. I set it aside.

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/_config_dir.py:45-47`

Offending text: "Return the path declared_roots_matching() reads: TRANSCRIPT_CONFIG_DIRS_FILE if set ..., else ~/.claude/transcript-config-dirs."

Issue: These clauses restate the function name, its return type and the one-line body at line 50 (`os.environ.get("TRANSCRIPT_CONFIG_DIRS_FILE") or ...`). The claim that `declared_roots_matching()` reads this path is true (line 123), but a grep finds it. The amended rule says to delete everything static analysis of this repository's code finds, even when true. A shorter or corrected restatement still restates.

Required property: Delete "Return the path ... reads" and the "if set ... else <default>" clause. Keep only a non-obvious decision if one is wanted; see R2.

## R2 [CONCERN] Restating the code (duplicates decisions already held elsewhere)

File: `claude/.claude/scripts/_config_dir.py:46-48`

Offending text: "(a test seam mirroring cleanup-merged-branches.sh's CLEANUP_MERGED_BRANCHES_ROOTS_FILE) ... Unlike TRANSCRIPT_CONFIG_DIRS_LABEL, this DOES follow the seam."

Issue:
- The "Unlike ... LABEL" sentence repeats the decision and its reason, which already live at lines 13-17 on `TRANSCRIPT_CONFIG_DIRS_LABEL`. That comment says the label deliberately does not follow the seam because an operator-facing message must name the real path. The new sentence carries no reason of its own, and what it does state is visible from the code. A label constant and a function that reads the env var show that contrast without a comment.
- The "test seam mirroring CLEANUP_MERGED_BRANCHES_ROOTS_FILE" clause repeats the parenthetical at lines 90-92 in `declared_roots_matching()`'s docstring, nearly word for word. The mirror claim itself is true: `cleanup-merged-branches.sh:251-255` defines that variable with the comment "same pattern as ...". It is still stated twice in one file.

Required property: Delete the "Unlike ... LABEL" sentence. For the seam, either delete the docstring entirely, or keep one pointer-style sentence naming the decision once, for example "TRANSCRIPT_CONFIG_DIRS_FILE is a test seam; see declared_roots_matching()." Drop the duplicate parenthetical from whichever of the two sites is not the home. The simplest outcome is to delete this docstring, since both decisions already have a home.

No false claims found. I checked each of the following:
- `declared_roots_matching()` calls `declared_roots_file()` at line 123.
- `cleanup-merged-branches.sh` defines `CLEANUP_MERGED_BRANCHES_ROOTS_FILE` at line 255.
- `TRANSCRIPT_CONFIG_DIRS_LABEL` does not follow the seam, per lines 13-17.
