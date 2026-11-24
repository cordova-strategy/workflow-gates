# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/scope.py`); 1 carried an in-scope comment change (the new docstring on `_path_to_project_slug`, lines 86-92).

## R1 [CONCERN] Restating the code

File:line: `claude/.claude/scripts/transcript_analysis/scope.py:86-92`

Issue: the new docstring is mostly restatement, with one clause that states a decision.

- "Map an absolute path to Claude Code's project-directory slug." restates the function name and signature.
- "replacing every '/' and '.' with '-'" restates the body, `re.sub(r"[/.]", "-", path)` (line 93).
- "Verified against real dirs: /home/<user>/repo -> -home-<user>-repo; /home/<user>/repo/.claude/worktrees/b -> -home-<user>-repo--claude-worktrees-b." restates what the regex produces for two inputs. The `--claude-worktrees-` infix is already named at `routing_guard.py:84` (`_WORKTREE_SLUG_INFIX`). The examples are also not a decision and give no reason.
- The one clause that survives the rule is "Claude Code names each project dir under ~/.claude/projects/ by taking the session's cwd...". That is the outside-the-repository fact forcing this function's behavior: the naming format belongs to Claude Code, not to this repo.

Production failure mode: a reader must wade through restated regex behavior to find the single fact that matters. The inline examples also create a second place to update if the format changes.

Required property: keep one sentence naming the decision and its external reason, and delete the rest. Proposed replacement:

```python
    """Reproduce Claude Code's naming of each project dir under ~/.claude/projects/.

    The format is fixed by Claude Code, not by this repository.
    """
```

If the author wants to keep "Verified against real dirs", it carries no reason and is not a decision, so the rule says to delete it.

## Claim check (no finding)

- Examples checked against the regex at line 93: both are correct. `/.claude` becomes `--claude`, which matches `_WORKTREE_SLUG_INFIX = "--claude-worktrees-"` at `routing_guard.py:84`. No False-claim finding.
- "Verified against real dirs" and the statement about Claude Code's cwd-based naming concern state outside this repository. They are unsettleable, and they are neither a number nor a cause-and-effect claim, so they draw no finding under False or unsourced claim.

No other angles apply: no PR-defined labels, no "used to be" framing, and no restated canonical rule (code file, not a record doc).
