# comment-discipline-reviewer

Scope: 1 file reviewed (`claude/.claude/scripts/_config_dir.py`); 1 carried an in-scope change, the added docstring on `declared_roots_file()` (lines 45-49).

Text set aside: the rules-file reminder on Python environment conventions has no bearing on this review. It names no site, scope or exclusion.

The docstring has four clauses and no kept decision. The one decision it touches, that the display label deliberately does not follow the test seam, already lives in the pre-existing comment at `_config_dir.py:13-16`, which stays. Each clause is reported separately per the rule under test, and the fix for each is deletion. Deleting all four leaves the function with no docstring.

## R1 [CONCERN] Prose restating the code

`_config_dir.py:45`

Text: "Return the path declared_roots_matching() reads:"

Issue: Static analysis finds this. `declared_roots_matching()` calls `declared_roots_file()` at line 123. The clause also restates the function name and its `-> Path` signature. I checked the claim and it is true, so it is not a False-claim finding.

Required property: delete the clause.

## R2 [CONCERN] Prose restating the code

`_config_dir.py:45-47`

Text: "TRANSCRIPT_CONFIG_DIRS_FILE if set ... else ~/.claude/transcript-config-dirs."

Issue: This restates the body at line 50, `os.environ.get("TRANSCRIPT_CONFIG_DIRS_FILE") or (Path.home() / ".claude" / "transcript-config-dirs")`. It states no reason beyond what the branches show.

Required property: delete the clause.

## R3 [CONCERN] Prose restating the code

`_config_dir.py:45-47`

Text: "(a test seam mirroring cleanup-merged-branches.sh's CLEANUP_MERGED_BRANCHES_ROOTS_FILE)"

Issue: Static analysis finds both parts. A grep shows the env var is set only for tests, and `cleanup-merged-branches.sh:251` declares the sibling seam. Both claims are true. The parenthetical gives no reason that analysis of the repository cannot find, and the same parenthetical is already repeated in `declared_roots_matching()`'s docstring at lines 90-92.

Required property: delete the clause.

## R4 [CONCERN] Prose restating the code

`_config_dir.py:48`

Text: "Unlike TRANSCRIPT_CONFIG_DIRS_LABEL, this DOES follow the seam."

Issue: The code at line 50 shows that this function follows the seam, and the constant at line 17 is a literal. The decision itself, that the label deliberately does not follow the seam because an operator-facing message must name the real path, is already stated at lines 13-16, next to the constant it governs. This sentence repeats that decision from the other side. It is also the second site naming the contrast, so single-source-of-truth applies.

Required property: delete the clause. The existing comment on `TRANSCRIPT_CONFIG_DIRS_LABEL` stays as the single home.
