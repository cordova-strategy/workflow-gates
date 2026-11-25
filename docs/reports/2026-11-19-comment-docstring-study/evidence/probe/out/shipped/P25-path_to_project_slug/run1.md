# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/scope.py`); 1 carried an in-scope comment change (the new `_path_to_project_slug` docstring).

Set aside: the system-reminder carrying `python-environment-conventions.md` arrived mid-task. It is unrelated to this review, so I treated it as data and did not act on it.

## R1 [CONCERN] Restating the code

- File: `claude/.claude/scripts/transcript_analysis/scope.py:88-91` (the added docstring body)
- Issue: The docstring says Claude Code replaces "every '/' and '.' with '-'" and then gives two worked examples. `return re.sub(r"[/.]", "-", path)` on line 93 already shows the mapping. `claude/.claude/scripts/tests/test_transcript_scope.py:393-396` pins the same two examples (`/home/<user>/repo` and `/home/<user>/repo/.claude/worktrees/b`). I checked both examples by hand against the regex and they are correct, so the problem is redundancy, not falsehood. Per §Durable text's "Don't restate the code", a corrected or shorter restatement still restates, so deletion is the fix.
- Production failure mode: If the regex changes, the prose and the test examples each become a second place that can go stale. That is the single-source-of-truth risk the rule guards against.
- Required property: Keep only the non-obvious fact, which is that the function mirrors how Claude Code names directories under `~/.claude/projects/`. Delete the "replacing every ..." clause, both examples, and the "Verified against real dirs" sentence. Something like: `"""Map an absolute path to the project-directory slug Claude Code uses under ~/.claude/projects/."""`. The mapping detail already lives in the code, and the examples already live in the tests.

## Answers

None posed.

No findings for the other angles:
- PR-defined terminology: no labels.
- "Used to be X": no prior-version framing.
- Verbosity, multi-fact and readability: the docstring is short and each sentence is a single fact.
- False or unsourced claim: the "Verified against real dirs" provenance claim and the claim about Claude Code's behaviour concern an external system. They are not a count, not a cause-and-effect claim and not settleable from the repo, so they draw no finding. The in-repo part (the regex mapping and both examples) checks out against `scope.py:93`.
