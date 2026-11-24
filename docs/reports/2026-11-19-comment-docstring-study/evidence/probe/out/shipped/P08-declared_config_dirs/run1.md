# comment-discipline-reviewer

Reviewed 1 file (post-crash-sessions.py); 1 docstring in scope (`_declared_config_dirs`, lines 1912-1918 post-diff).

Set aside: nothing. The `python-environment-conventions.md` rule text that arrived mid-session has no bearing on this diff's scope.

## R1 [CONCERN] Multi-fact comment structure

claude/.claude/scripts/post-crash-sessions.py:1912-1918

Issue: One sentence chains four facts: what the function reads, which check validates it, what it is chosen over, and what the other check would lose. It uses a parenthetical, an `instead of`, and a dash aside. The reader has to parse the whole sentence to find where the one non-obvious fact starts.

Offending text: "Declared roots from ~/.claude/transcript-config-dirs (or TRANSCRIPT_CONFIG_DIRS_FILE), validated against this script's own looser sessions/-or-projects/ check (main()'s --config-dir validation, below) instead of declared_transcript_roots()'s projects/-only requirement -- the latter would silently drop a sessions-only root, the crashed-fresh-account case this tool exists for."

Required property: one sentence per fact. A compression that keeps every fact:

> Accepts a root with `sessions/` or `projects/`, not `declared_transcript_roots()`'s `projects/`-only check, which would silently drop a sessions-only root (the crashed-fresh-account case this tool exists for). Mirrors the `--config-dir` validation in `main()`.

## R2 [FYI] Restating the code

claude/.claude/scripts/post-crash-sessions.py:1912-1913

Issue: The lead clause "Declared roots from ~/.claude/transcript-config-dirs (or TRANSCRIPT_CONFIG_DIRS_FILE)" restates the function name, its `declared_roots_matching` call, and that function's own docstring (`_config_dir.py:90`). The inline lambda also shows the `sessions/`-or-`projects/` condition.

Required property: delete the lead clause and keep only the non-obvious part, which is why the check differs from `declared_transcript_roots()`. The R1 compression already does this.

## R3 [FYI] Fragile positional reference

claude/.claude/scripts/post-crash-sessions.py:1914

Issue: "main()'s --config-dir validation, below" points by position and not by name. The reference breaks if `main()` moves. I confirmed that the target exists, at lines 1992-1994.

Required property: drop "below". The R1 fix names `main()` and `--config-dir`, which is enough.

## Verified claims, no finding

- `declared_transcript_roots()` requires only `projects/`: `_config_dir.py:166-169`.
- `main()` accepts `sessions/` or `projects/`: `post-crash-sessions.py:1992`, matching the lambda at line 1920.
- Together these confirm that a sessions-only root would be dropped by `declared_transcript_roots()`.
- "The crashed-fresh-account case this tool exists for" is a design rationale and draws no finding.
