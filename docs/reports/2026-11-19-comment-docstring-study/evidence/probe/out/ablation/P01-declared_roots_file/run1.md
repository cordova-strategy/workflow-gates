# comment-discipline-reviewer

Scope: 1 file reviewed (`claude/.claude/scripts/_config_dir.py`), 1 with an in-scope comment change: the new docstring on `declared_roots_file()`, lines 45-49. Text set aside: none. The diff has one docstring and four clauses. Each draws a Prose restating the code finding under the session's replacement "Don't restate the code" bullet. Deleting all four removes the docstring.

## R1 [CONCERN] Prose restating the code

File: `claude/.claude/scripts/_config_dir.py:45`

Issue: Clause "Return the path declared_roots_matching() reads". The function name and the `-> Path` signature already say this. Searching the file for `declared_roots_file()` finds the reader, `declared_roots_matching()`. Static analysis of this repo's code finds the fact, so it is a restatement.

Required property: delete the clause.

## R2 [CONCERN] Prose restating the code

File: `claude/.claude/scripts/_config_dir.py:45-47`

Issue: Clause "TRANSCRIPT_CONFIG_DIRS_FILE if set ..., else ~/.claude/transcript-config-dirs". The body at line 50 is `os.environ.get("TRANSCRIPT_CONFIG_DIRS_FILE") or (Path.home() / ".claude" / "transcript-config-dirs")`. The clause retells the `or` fallback branch by branch.

Required property: delete the clause. A shorter or corrected paraphrase still restates.

## R3 [CONCERN] Prose restating the code

File: `claude/.claude/scripts/_config_dir.py:46-47`

Issue: Clause "a test seam mirroring cleanup-merged-branches.sh's CLEANUP_MERGED_BRANCHES_ROOTS_FILE". Two reasons it is not a kept decision:
- A grep finds the mirrored pattern. `cleanup-merged-branches.sh:251` already says "same pattern as".
- The test-seam rationale already lives at two other sites:
  - The comment at lines 13-17 (`TRANSCRIPT_CONFIG_DIRS_LABEL`).
  - The `declared_roots_matching()` docstring at lines 90-92, which repeats the same parenthetical.

  This clause is a third copy of one decision.

Required property: delete the clause. Keep the decision at its existing home, the comment at lines 13-17. If a pointer is wanted, it can name that symbol, but nothing here needs one.

## R4 [CONCERN] Prose restating the code

File: `claude/.claude/scripts/_config_dir.py:48`

Issue: Clause "Unlike TRANSCRIPT_CONFIG_DIRS_LABEL, this DOES follow the seam". The body reads the env var, so the clause is visible from the code. It also mirrors the decision recorded at lines 13-17 from the opposite side. That is a restatement and a duplicate home for one decision.

Required property: delete the clause. The LABEL comment is the single home for the contrast. Delete the whole docstring once R1-R4 land.
