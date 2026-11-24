# comment-discipline-reviewer

Set aside: the auto-loaded `python-environment-conventions.md` reminder, which names no site in this diff.

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/scope.py:86-92` (the new `_path_to_project_slug` docstring).

Issue: the docstring is mostly restatement.
- The summary line "Map an absolute path to Claude Code's project-directory slug." repeats what the function name and signature show.
- The two "Verified against real dirs" examples (`/home/<user>/repo -> -home-<user>-repo` and the `.claude/worktrees/b` one) are the output of the `re.sub(r"[/.]", "-", path)` on line 93. Reading the regex yields them, so they restate it. I checked both mappings and they are correct (the `/.` pair becomes `--`), so this is not a false-claim finding.

What stays: the sentence saying Claude Code derives its project-dir name from the session cwd by replacing `/` and `.` with `-`. The convention comes from outside this repository and is the reason the regex has this shape. Naming what it decides is not a restatement.

Failure mode: a reader maintaining the function has to read the examples and the summary line again for no new information, and the examples can drift from the regex.

Required property: delete the summary line and both examples, and keep only the Claude Code naming convention as one sentence. For example: "Claude Code derives each `projects/` dir name from the session's cwd by replacing every `/` and `.` with `-`." Dropping "Verified against real dirs" also removes an unsettleable external claim that names no source.
