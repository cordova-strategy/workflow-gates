# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/_config_dir.py`); 1 comment/docstring change in scope (the new `declared_roots_file()` docstring).

Set aside: the session's replacement "Don't restate the code" bullet is applied in place of CLAUDE.md's version. The `python-environment-conventions.md` rules reminder is unrelated to comment review and was not applied.

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/_config_dir.py:45-48` (added docstring on `declared_roots_file()`).

Offending text:

> Return the path declared_roots_matching() reads: TRANSCRIPT_CONFIG_DIRS_FILE if set (a test seam mirroring cleanup-merged-branches.sh's CLEANUP_MERGED_BRANCHES_ROOTS_FILE), else ~/.claude/transcript-config-dirs. Unlike TRANSCRIPT_CONFIG_DIRS_LABEL, this DOES follow the seam.

Issue: every clause is something static analysis of the repository finds, and none gives a reason it cannot find.
- "Returns the path `declared_roots_matching()` reads" is visible at `_config_dir.py:123`.
- "`TRANSCRIPT_CONFIG_DIRS_FILE` if set, else `~/.claude/transcript-config-dirs`" restates the one-line body at line 50.
- "A test seam mirroring `CLEANUP_MERGED_BRANCHES_ROOTS_FILE`" is findable from `cleanup-merged-branches.sh:251-255` and the tests. It names a precedent, not a reason.
- "Unlike `TRANSCRIPT_CONFIG_DIRS_LABEL`, this DOES follow the seam" repeats the comment at `_config_dir.py:13-17`, which already owns that contrast and its reason (an operator-facing message must name the real path). It is a second home for one fact (single source of truth).

The claims are true, checked against `_config_dir.py:14-17`, `:50` and `:123`, and `cleanup-merged-branches.sh:251-255`. Under the session rule, a true restatement is still deleted.

The docstring also chains several facts through a colon, a parenthetical and a trailing sentence. Deletion removes that problem, so no separate Multi-fact finding is raised.

Failure mode: the same facts now live in four places (this docstring, the `:13-17` comment, the `declared_roots_matching()` docstring at `:90-92`, and the code). A change to the seam name or default then has to be fixed in each.

Required property: delete the docstring. If a pointer is wanted, one sentence is enough: "The `TRANSCRIPT_CONFIG_DIRS_LABEL` comment above explains why the label does not follow the `TRANSCRIPT_CONFIG_DIRS_FILE` override." Do not restate the env var or the default path. Naming what the function resolves is not a decision needing a comment.

Related, out of scope: the pre-existing `declared_roots_matching()` docstring (`:90-92`) carries the same "test seam mirroring" clause. It is not in this diff.
