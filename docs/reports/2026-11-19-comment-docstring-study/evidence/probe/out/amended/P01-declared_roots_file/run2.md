# comment-discipline-reviewer

Scope: 1 file reviewed (`claude/.claude/scripts/_config_dir.py`); 1 carried an in-scope comment change (the new docstring on `declared_roots_file()`).

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/_config_dir.py:45-49` (new docstring on `declared_roots_file()`).

Issue: The docstring is four clauses. Each is either shown by the one-line body, or already stated elsewhere in the file.
- "Return the path declared_roots_matching() reads": the function name and the body show this, and `declared_roots_matching` calls it at line 123.
- "TRANSCRIPT_CONFIG_DIRS_FILE if set ... else ~/.claude/transcript-config-dirs": a prose copy of `os.environ.get(...) or (Path.home() / ".claude" / "transcript-config-dirs")` at line 50.
- "a test seam mirroring cleanup-merged-branches.sh's CLEANUP_MERGED_BRANCHES_ROOTS_FILE": static analysis finds this. `cleanup-merged-branches.sh:251` calls its variable a test seam, and lines 90-92 of this file's `declared_roots_matching()` docstring already state the same parenthetical. The sentence gives no reason for the mirroring, so it is not a kept decision.
- "Unlike TRANSCRIPT_CONFIG_DIRS_LABEL, this DOES follow the seam": the label's `#` comment at lines 13-17 already states this, along with the reason (an operator-facing message must name the real path). This sentence gives no reason of its own. Having the same fact at two sites also breaks single source of truth.

I checked the claims against the code. `TRANSCRIPT_CONFIG_DIRS_FILE` is read at line 50 and the label constant is a literal at line 17, so none is false. The finding is that the docstring adds nothing the code or the existing comments don't already hold.

Required property: delete the docstring. No clause is a decision with a reason static analysis cannot find. The reason the label does not follow the seam stays in the comment at lines 13-17, which is the single home for it.
