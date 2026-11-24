# comment-discipline-reviewer

Scope: 1 file reviewed (`scope.py`), 1 docstring added in scope.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/scope.py:86-91` (docstring of `_path_to_project_slug`).

Issue: The docstring says the function replaces every `/` and `.` with `-`. The one-line body `re.sub(r"[/.]", "-", path)` already shows that. The two worked examples (`/home/<user>/repo -> -home-<user>-repo` and the `--claude-worktrees` one) only replay the regex, and the first sentence restates the function name and signature. The one non-obvious fact is that the output must equal the directory name Claude Code itself gives under `~/.claude/projects/`. The docstring buries that fact in the restatement. "Verified against real dirs" is also a past-event note with no pointer to what was checked, so it adds nothing a future reader can use.

Production failure mode: None at runtime. The cost is a docstring that duplicates the code and will mislead if the regex changes without the prose changing.

Required property: Delete the restatement, the two examples and the "Verified" sentence. Keep a single sentence stating the constraint, for example: "Must match Claude Code's own naming of project dirs under ~/.claude/projects/; callers match the result by string equality." If the examples are kept as a regression guard, move them to a test, not the docstring. Do not replace the docstring with a shorter restatement of the regex, because that still restates.

Checked, no finding: the docstring's examples agree with the regex at `scope.py:88-91`. Whether Claude Code replaces only `/` and `.` is a claim about external software the repo cannot confirm or refute, so it draws no False-or-unsourced-claim finding.
