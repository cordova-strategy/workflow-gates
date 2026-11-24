# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/scope.py`); 1 carried an in-scope comment change (the new `_path_to_project_slug` docstring, diff lines 8-14).

## R1 [CONCERN] Restating the code

scope.py:86-92 (new docstring on `_path_to_project_slug`).

Issue: the docstring says "by taking the session's cwd and replacing every '/' and '.' with '-'". The one-line body `re.sub(r"[/.]", "-", path)` already shows that. The two examples (`/home/<user>/repo -> -home-<user>-repo` and the `.claude/worktrees/b` case) repeat the assertions in `test_transcript_scope.py:393-397` (`test_main_repo_path`, `test_worktree_path`). "Absolute path" and "slug" repeat the signature and name.

Production failure mode: the docstring and the regex can drift apart. Under the rule under test, a shorter or corrected restatement still restates.

Required property: delete the transform description and both examples. Keep only the decision static analysis cannot find, which is that the mapping mirrors Claude Code's own naming of project dirs under `~/.claude/projects/`. Claude Code's scheme forces this, so the function cannot be changed independently. For example: `"""Mirror Claude Code's naming of project dirs under ~/.claude/projects/; the scheme is external, so don't change it here."""` The sentence names the pointer to the external system and the reason for the mapping, and it makes no claim about how the regex works.

## R2 [FYI] False or unsourced claim

scope.py:90 ("Verified against real dirs").

Issue: this is a record of a manual check with no source, and it is not reproducible from the repository. The surrounding examples are already covered by tests. It reads as a verification claim but names no artifact.

Required property: delete it along with R1's deletion. Nothing in it is a kept decision.

No PR-defined labels, prior-version framing, or other findings.

**Request changes** (R1: delete the restating clauses and examples, keeping one sentence on the external naming constraint).
