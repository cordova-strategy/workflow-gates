# comment-discipline-reviewer

Scope: 1 file reviewed (`claude/.claude/scripts/transcript_analysis/scope.py`), 1 docstring added in scope (`_path_to_project_slug`). No prompt text was set aside.

## R1 [CONCERN] Prose restating the code

scope.py:86 (diff line 9): `"""Map an absolute path to Claude Code's project-directory slug.`

Issue: the summary line restates the function name `_path_to_project_slug` and its `path: str -> str` signature.

Production failure mode: none. The line is noise that dilutes the one non-obvious fact in the docstring.

Required property: delete this clause. The surrounding decision (R2) carries the only non-obvious content, so nothing is lost.

## R2 [CONCERN] Prose restating the code

scope.py:88-89 (diff lines 11-12): `Claude Code names each project dir under ~/.claude/projects/ by taking the session's cwd and replacing every '/' and '.' with '-'.`

Issue: the `replacing every '/' and '.' with '-'` clause restates `re.sub(r"[/.]", "-", path)` on the line below. Static analysis of the function body finds it.

Production failure mode: none today. If the regex changes, the docstring becomes a second, stale copy of the rule.

Required property: delete the replacement-rule clause and keep the decision it serves. The decision is that the function mirrors Claude Code's own directory naming, which this repo cannot change. The "session's cwd" input is also an external fact about Claude Code and stays. Keep the subject of the decision in the sentence so the reason still names what it explains, e.g. "Mirrors how Claude Code names dirs under ~/.claude/projects/ from the session's cwd; the scheme is owned by Claude Code, not this repo."

## R3 [CONCERN] Prose restating the code

scope.py:90-92 (diff lines 12-13): `Verified against real dirs: /home/<user>/repo -> -home-<user>-repo; /home/<user>/repo/.claude/worktrees/b -> -home-<user>-repo--claude-worktrees-b.`

Issue: both examples are outputs of the one-line regex, so they restate the code's behavior. Reading the function finds them. I checked them against the regex and they are correct (`/.` becomes `--`), so the problem is restatement, not falsity. "Verified against real dirs" is also a verification narrative that no later reader can re-check.

Production failure mode: none today. The examples go stale with the regex, and the `--` worktree case pushes the docstring past one distinct fact.

Required property: delete the whole sentence and both examples. The behavior is covered by tests of `_path_to_project_slug` and by its callers at scope.py:203 and routing_guard.py:950.
