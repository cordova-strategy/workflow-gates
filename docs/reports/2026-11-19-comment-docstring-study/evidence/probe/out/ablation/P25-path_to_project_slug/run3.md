# comment-discipline-reviewer

Reviewed 1 file (`scope.py`); 1 carried an in-scope change (the new `_path_to_project_slug` docstring). The rule-under-test bullet replaces CLAUDE.md's "Don't restate the code" bullet for this session. No prompt text was set aside.

## R1 [CONCERN] Prose restating the code

scope.py:86-87 (docstring lines 1-2 of the diff), clause: "Claude Code names each project dir under ~/.claude/projects/ by taking the session's cwd and replacing every '/' and '.' with '-'."

Issue: "replacing every '/' and '.' with '-'" restates `re.sub(r"[/.]", "-", path)` on the next line. The "taking the session's cwd" part restates the `path` parameter and the callers (scope.py:203 maps worktree paths).

Required property: delete the substitution description. Keep one decision sentence that names the outside constraint and still names its subject. For example: "The slug must match Claude Code's own naming of project dirs, which this repo does not control." The outside-forced fact is that the mapping mirrors Claude Code's on-disk convention. The mechanics of that mapping are not.

## R2 [CONCERN] Prose restating the code

scope.py:88-90 (diff lines 11-13), clause: "Verified against real dirs: /home/<user>/repo -> -home-<user>-repo; /home/<user>/repo/.claude/worktrees/b -> -home-<user>-repo--claude-worktrees-b."

Issue: Both examples are what the one-line `re.sub` produces, so static analysis of the function finds them. The rule says to delete such clauses even when true. "Verified against real dirs" also names no source. It is a claim about an external, unsettleable state that no repo artifact reproduces. If that provenance matters, a test with these paths would hold it.

Required property: delete both examples and the "Verified" sentence. Pin the examples in a unit test if they are worth keeping.

## R3 [CONCERN] Prose restating the code

scope.py:85-86 (diff line 9), clause: "Map an absolute path to Claude Code's project-directory slug."

Issue: This restates the function name `_path_to_project_slug`, its `path: str` parameter and its `-> str` return type. It is a docstring clause, so the rule requires deletion.

Required property: delete the clause. R1's decision sentence becomes the whole docstring.

## R4 [FYI] False or unsourced claim

scope.py:87: "under ~/.claude/projects/"

Issue: The module resolves the projects dir as `config_dir() / "projects"` (scope.py:73). It also scans multiple declared roots (scope.py:497-500, 808). `~/.claude` is therefore only the personal account's location, and the claim holds only in part. A comment that says `~/.claude/projects/` is also wrong on the other account roots that this module scans.

Required property: R1's fix drops the path. If a location is named, name `config_dir()/projects`, not `~/.claude`.
