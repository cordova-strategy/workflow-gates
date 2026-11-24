# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/scope.py`); 1 carried an in-scope comment change (the new `_path_to_project_slug` docstring, lines 86-92). I read the whole file and grepped the repo for the function's tests and callers.

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/scope.py:86-92`

Offending text:
> Map an absolute path to Claude Code's project-directory slug.
> Claude Code names each project dir under ~/.claude/projects/ by taking the session's cwd and replacing every '/' and '.' with '-'. Verified against real dirs: /home/<user>/repo -> -home-<user>-repo; /home/<user>/repo/.claude/worktrees/b -> -home-<user>-repo--claude-worktrees-b.

Issue: the amended "Don't restate the code" bullet keeps a clause only when it names a decision and gives a reason static analysis cannot find. Most of this docstring fails that test.
- The summary line restates the function name and signature.
- "replacing every '/' and '.' with '-'" restates `re.sub(r"[/.]", "-", path)` on line 93.
- Both example mappings restate the regex's output. The repo's own tests already pin them verbatim: `test_transcript_scope.py:393` (`test_main_repo_path`) and `:396-397` (`test_worktree_path`).
- "Verified against real dirs" cannot be checked from the repo. The examples use a `<user>` placeholder, so the claim names no dir a reader could inspect.

The one clause that survives is that this is Claude Code's own dir-naming scheme, which is outside the repo and forces the mapping.

Concrete fix: replace the whole docstring with one sentence that keeps only that decision and its reason:

```python
"""Mirror Claude Code's own naming of project dirs under ~/.claude/projects/, which this repo cannot change.

The mapping is lossy, so two distinct paths can share a slug (see `_repo_scoped_project_slugs`).
"""
```

The second sentence is optional. It keeps the existing lossiness decision, which `_repo_scoped_project_slugs` and `TestPathToProjectSlug.test_known_slug_collision_is_accepted` already state. If you drop it, a one-sentence docstring is enough. Delete the examples and "Verified against real dirs" outright; a shorter or corrected restatement would still restate.

Angles checked on the fix: it adds no PR-defined terms, no prior-version framing, and no new factual claim. It points to symbols that exist (`_repo_scoped_project_slugs` at `scope.py:96`).

## Not findings

- "Verified against real dirs" and the claim about Claude Code's naming describe an outside program, so no file in this repo can settle them. They draw no False or unsourced finding, because they are neither a number nor a cause-and-effect claim.
- The dash-and-semicolon-chained examples are not a separate Multi-fact finding: deleting them under R1 resolves it.
