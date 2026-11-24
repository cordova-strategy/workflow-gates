# comment-discipline-reviewer

Scope: 1 file reviewed (`claude/.claude/scripts/_config_dir.py`), 1 carried an in-scope change (a new 4-line docstring on `declared_roots_file()`, lines 45-49 of the snapshot). The docstring has four clauses, and each gets its own finding. All four fixes delete a clause, and together they delete the whole docstring.

## R1 [CONCERN] Prose restating the code

`_config_dir.py:45`

Issue: the clause "Return the path declared_roots_matching() reads" restates what static analysis of this repository finds. A grep for the callers of `declared_roots_file()` shows it. `declared_roots_file_state()` at line 81 also reads the same path.

Production failure mode: the clause states one consumer as if it were the only one. It goes stale when a caller is added or removed.

Required property: delete the clause. It is not a design decision and gives no reason outside the repository.

## R2 [CONCERN] Prose restating the code

`_config_dir.py:45-47`

Issue: the clause "TRANSCRIPT_CONFIG_DIRS_FILE if set ..., else ~/.claude/transcript-config-dirs" repeats the function body at line 50: the `os.environ.get(...) or (Path.home() / ...)` expression.

Production failure mode: the default path now lives in three places: the body, this docstring and the `declared_roots_matching()` docstring at line 90. The copies drift when the default changes.

Required property: delete the clause. A shorter or corrected restatement still restates.

## R3 [CONCERN] Prose restating the code

`_config_dir.py:46-47`

Issue: the clause "a test seam mirroring cleanup-merged-branches.sh's CLEANUP_MERGED_BRANCHES_ROOTS_FILE" is found by grep alone. `cleanup-merged-branches.sh:251` states the same seam. The `declared_roots_matching()` docstring at lines 90-92 repeats the clause verbatim.

Production failure mode: the same fact sits in two docstrings and the shell script. Every one of them must change when the seam is renamed.

Required property: delete the clause. Under the rule under test, a true fact that static analysis finds, even across several files, is still a restatement.

## R4 [CONCERN] Prose restating the code

`_config_dir.py:48`

Issue: the clause "Unlike TRANSCRIPT_CONFIG_DIRS_LABEL, this DOES follow the seam" restates the code. The function body reads the env var directly, and the LABEL constant is a literal. The decision itself already lives at the LABEL's own comment (lines 13-17), which explains why the label ignores the seam.

Production failure mode: the same contrast is written at both ends, so the two comments can drift apart.

Required property: delete the clause. The comment at lines 13-17 keeps the decision, and the LABEL comment already points at `declared_roots_file()`, so no pointer is needed here.
