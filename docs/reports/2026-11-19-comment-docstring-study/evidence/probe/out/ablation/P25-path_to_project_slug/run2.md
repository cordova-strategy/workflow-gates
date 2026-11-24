# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/scope.py`); 1 carried an in-scope comment change (the new `_path_to_project_slug` docstring).

Scope note: the dispatch prompt's replacement "Don't restate the code" bullet governs what counts as a restatement. I read the agent file's "report every docstring clause" sweep as an instruction to judge each clause against that bullet, not to flag a clause the bullet keeps. The bullet keeps a clause that records what outside this repository forces.

## R1 [CONCERN] Prose restating the code

`claude/.claude/scripts/transcript_analysis/scope.py:86` (docstring line 1, diff line 8)

Text: `"""Map an absolute path to Claude Code's project-directory slug.`

Issue: The function name `_path_to_project_slug`, its `path: str` parameter and its `-> str` return type already state this clause. Static analysis of the repo finds nothing in it that is a decision or an outside-forced fact.

Fix: Delete the clause. Keep the next sentence as the docstring's opening, because it names Claude Code and its project-directory naming as the subject.

## R2 [CONCERN] Prose restating the code

`claude/.claude/scripts/transcript_analysis/scope.py:90-92` (docstring lines 4-6, diff lines 11-13)

Text: `Verified against real dirs: /home/<user>/repo -> -home-<user>-repo; /home/<user>/repo/.claude/worktrees/b -> -home-<user>-repo--claude-worktrees-b.`

Issue: Both examples are the output of `re.sub(r"[/.]", "-", path)` on the given input, so static analysis of the one-line body derives them. The "Verified against real dirs" lead-in is not a decision with a reason. It also sources nothing a reader can check, because it names no directory.

Fix: Delete the sentence. The `--claude` double-dash case follows from `/` and `.` each mapping to `-`. If someone wants an on-disk example, point to a test that holds one. `test_transcript_cli_bootstrap.py:1321` already copies this mapping.

## Kept

The sentence "Claude Code names each project dir under ~/.claude/projects/ by taking the session's cwd and replacing every '/' and '.' with '-'" is kept. It records an external constraint that the slug must match Claude Code's on-disk naming. Nothing in this repository forces that, so static analysis of the repo cannot find it.

I raise no False-or-unsourced-claim finding on it. Whether Claude Code replaces only `/` and `.` is a claim about an outside system, so it is unsettleable from the repository.
