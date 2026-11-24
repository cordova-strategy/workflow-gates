# comment-discipline-reviewer

Scope: 1 file reviewed (`claude/.claude/scripts/_config_dir.py`), 1 with an in-scope docstring change (`declared_transcript_roots`). The system-reminder with the Python environment rules file has no bearing on this review, so I set it aside.

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/_config_dir.py:162-163`

Issue: the new docstring's first clause is "Return the config dirs listed in ~/.claude/transcript-config-dirs (or TRANSCRIPT_CONFIG_DIRS_FILE) that contain a `projects/` subdirectory."

- The `projects/` condition is the lambda `(candidate / "projects").is_dir()` at line 167.
- The file location and the env override come from `declared_roots_file()` (lines 45-50) and the `declared_roots_matching` docstring (line 90).
- Static analysis of this repository finds every part of the clause. It records no decision that reads "why it is this way" or "what outside this repository forces it".

Production failure mode: the clause duplicates the lambda and the `declared_roots_file()` logic. It goes stale silently if either changes, for example if the predicate loosens to a `sessions/`-or-`projects/` check.

Required property: delete the first clause, including its parenthetical about `TRANSCRIPT_CONFIG_DIRS_FILE`. A shorter or corrected version of the clause still restates the code.

The second sentence, "See declared_roots_matching() for the parsing contract this builds on.", stays. It points at the symbol that holds the parsing decisions, and `declared_roots_matching`'s docstring does hold them (lines 90-121). After the deletion the docstring is that pointer alone.
