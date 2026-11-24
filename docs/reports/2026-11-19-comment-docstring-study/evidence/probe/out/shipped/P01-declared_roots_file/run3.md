# comment-discipline-reviewer

Scope note: the rules file pasted mid-conversation (python-environment-conventions.md) does not bear on this review. I set it aside and changed nothing because of it.

Reviewed 1 file (`claude/.claude/scripts/_config_dir.py`); 1 carried an in-scope change (the new `declared_roots_file()` docstring).

Checked and found true, so no False-claim finding:
- `declared_roots_matching()` reads the path through `declared_roots_file()` (`_config_dir.py:123`).
- `TRANSCRIPT_CONFIG_DIRS_FILE` is honored with a `~/.claude/transcript-config-dirs` fallback (`_config_dir.py:50`).
- `CLEANUP_MERGED_BRANCHES_ROOTS_FILE` is a test seam in `cleanup-merged-branches.sh:251-255`.
- `TRANSCRIPT_CONFIG_DIRS_LABEL` is a fixed literal that does not follow the seam (`_config_dir.py:13-17`).

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/_config_dir.py:45-49`

Issue: The docstring is `"""Return the path declared_roots_matching() reads: TRANSCRIPT_CONFIG_DIRS_FILE if set (...), else ~/.claude/transcript-config-dirs. Unlike TRANSCRIPT_CONFIG_DIRS_LABEL, this DOES follow the seam."""`. Three of its parts duplicate something else:
- "Return the path ... if set ... else ~/.claude/transcript-config-dirs" restates the one-line body (`os.environ.get(...) or Path.home()/...`) and the function name.
- "Unlike TRANSCRIPT_CONFIG_DIRS_LABEL, this DOES follow the seam" restates the comment at `_config_dir.py:13-17`, which already draws this contrast and names `declared_roots_file()`.
- "a test seam mirroring cleanup-merged-branches.sh's CLEANUP_MERGED_BRANCHES_ROOTS_FILE" repeats near-verbatim the wording in the `declared_roots_matching()` docstring (`_config_dir.py:90-92`).

Production failure mode: Three sites now state the same seam fact. When the seam is renamed or the label changes, the sites drift, which breaks single source of truth. The restated code gives the reader nothing new.

Required property: Keep only the fact the code doesn't show, the test-seam role. For example: "TRANSCRIPT_CONFIG_DIRS_FILE overrides the default path as a test seam." Delete the return and default restatement and the LABEL contrast, which is canonical at lines 13-17. Cite `cleanup-merged-branches.sh` once only. Alternatively delete the docstring, since the `declared_roots_matching()` docstring already names the seam.

## R2 [FYI] Multi-fact comment structure

File: `claude/.claude/scripts/_config_dir.py:45-47`

Issue: The first sentence chains four facts. They are the return role, the env override, a parenthetical on seam provenance and mirroring, and the default fallback. A reader must parse the parenthetical to resume the "else" clause.

Production failure mode: Readability only. R1's fix, if applied, removes this sentence structure.

Required property: If any of the facts survive R1, give each its own sentence and keep the parenthetical out of the middle of the if/else.
