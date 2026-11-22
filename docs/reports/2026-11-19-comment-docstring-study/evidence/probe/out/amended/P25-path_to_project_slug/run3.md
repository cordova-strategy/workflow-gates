# comment-discipline-reviewer

Reviewed 1 file (`scope.py`); 1 docstring in scope. No prompt text was set aside.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/scope.py:86-92` (the added docstring of `_path_to_project_slug`, diff lines 8-14).

Issue: Most of the docstring restates what the code and tests already show:
- "Map an absolute path to Claude Code's project-directory slug" restates the function name and signature.
- "replacing every '/' and '.' with '-'" restates `re.sub(r"[/.]", "-", path)` on the next line.
- The two `->` examples restate the transform. `tests/test_transcript_scope.py:393-397` (`test_main_repo_path`, `test_worktree_path`) assert the same two input/output pairs.
- "Verified against real dirs" records a one-time check that nothing in the repository settles.

Required property: Keep only the decision static analysis can't find, which is that the scheme mirrors Claude Code's own directory naming and is not this repo's choice. Delete the other clauses, examples included. A corrected or shortened restatement still restates. One-line fix that keeps the decision and names its subject:

`"""Mirror Claude Code's naming of project dirs under ~/.claude/projects/, which this repo cannot change; a different transform would stop matching the real dirs."""`

The tests at `test_transcript_scope.py:399-404` already pin the known collision this scheme causes, so don't repeat it here.
