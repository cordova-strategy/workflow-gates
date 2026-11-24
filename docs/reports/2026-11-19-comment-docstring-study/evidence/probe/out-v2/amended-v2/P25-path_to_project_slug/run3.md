# comment-discipline-reviewer

Set aside: the `python-environment-conventions.md` rule file that arrived mid-session. It is not a field this agent's contract defines and bears on no site in this diff.

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/scope.py:88-91` (added docstring body of `_path_to_project_slug`)

Issue: "…by taking the session's cwd and replacing every '/' and '.' with '-'. Verified against real dirs: /home/<user>/repo -> -home-<user>-repo; /home/<user>/repo/.claude/worktrees/b -> -home-<user>-repo--claude-worktrees-b." The replacement rule and both worked examples restate `re.sub(r"[/.]", "-", path)` at line 93. A reader derives both example outputs from the regex alone, including the double dash in `--claude`. The rule says a shorter or corrected restatement still restates, so these clauses are deleted, not trimmed.

Production failure mode: when Claude Code changes its slug scheme, the regex and this prose drift apart, and the prose then asserts a false mapping next to the code that implements another.

Required property: keep only the decision, which is that this function must track a naming scheme owned outside the repo. Delete the rule and the examples. "Verified against real dirs" is unsettleable from the repo and draws no finding of its own, but it goes with the examples.

Proposed replacement for lines 86-92 (one sentence, with R2's fix applied):

```python
"""Must match how Claude Code derives a project dir's name from the session's cwd; that scheme is owned by Claude Code, so revisit if it changes."""
```

## R2 [FYI] Restating the code

File: `scope.py:86`

Issue: "Map an absolute path to Claude Code's project-directory slug." restates the name `_path_to_project_slug` and the `path: str` -> `str` signature. The only non-obvious part is that the mapping is Claude Code's, not this repo's, and R1's replacement carries that.

Required property: delete the sentence as a standalone summary. R1's replacement subsumes it, so no extra sentence is needed.
