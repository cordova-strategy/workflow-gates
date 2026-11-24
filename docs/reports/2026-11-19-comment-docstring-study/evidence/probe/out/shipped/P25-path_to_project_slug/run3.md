# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/scope.py`); 1 carried an in-scope change (new docstring on `_path_to_project_slug`, lines 86-92 of the snapshot).

The rules file auto-attached mid-session (`python-environment-conventions.md`) does not bear on this diff and was set aside.

## R1 [CONCERN] Restating the code

scope.py:86-92, `_path_to_project_slug` docstring.

Issue: the second sentence ("taking the session's cwd and replacing every '/' and '.' with '-'") restates the one-line body `re.sub(r"[/.]", "-", path)`. The first line ("Map an absolute path to ... slug") restates the function name and signature. The two worked examples restate the same transform and are already pinned as assertions in `claude/.claude/scripts/tests/test_transcript_scope.py:393-397`. I checked both examples against the regex and they are correct, so this is not a false-claim finding.

Failure mode: the transform is rewritten by a reader, then the docstring and the code can drift. The tests already catch any drift in the examples.

Required property: delete the restatement, the examples and the name-echo. Keep only the one non-obvious fact, that the mapping must match how Claude Code names dirs under `~/.claude/projects/`. For example: "Must mirror Claude Code's on-disk project-dir naming; lossy by design (see `test_known_slug_collision_is_accepted`)."

## R2 [CONCERN] Comment verbosity

scope.py:90, "Verified against real dirs:".

Issue: this narrates how the author checked the behavior, which is PR-description material. A future reader cannot repeat the check, and the docstring names no source for it. The two examples after it also chain with `->` and a `;` into one run.

Required property: drop the "Verified against real dirs" narration. If the examples stay, give each its own sentence or list item. The better fix is the R1 deletion, since the tests already carry the examples.

## Answers

No questions posed.
