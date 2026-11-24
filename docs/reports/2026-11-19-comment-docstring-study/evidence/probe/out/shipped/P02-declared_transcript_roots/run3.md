# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/_config_dir.py`); 1 carried an in-scope comment change. The system-reminder attaching `python-environment-conventions.md` has no bearing on this diff's scope, so I set it aside.

## R1 [CONCERN] Prose restating the code

`claude/.claude/scripts/_config_dir.py:162-165` (the new `declared_transcript_roots` docstring).

Issue: the docstring says the function returns the config dirs listed in the roots file that contain a `projects/` subdirectory. The code already shows that:
- The name is `declared_transcript_roots`.
- The body is one `declared_roots_matching(...)` call.
- The predicate is `(candidate / "projects").is_dir()`.
- `declared_roots_matching`'s docstring (lines 90-100) already names the roots file, the `TRANSCRIPT_CONFIG_DIRS_FILE` seam and the `is_valid` hook.

The sentence "See declared_roots_matching() for the parsing contract" points at the call the body already makes. The file path and env-var name are also restated from `declared_roots_file()` (lines 45-50) and `declared_roots_matching`, which makes them a second copy of knowledge that already has a home.

The restatement is accurate against the code at the diff's state (lines 50, 90, 167), so there is no false-claim finding. It still carries no fact the code doesn't show.

Production failure mode: if the default path or env-var seam changes, three docstrings need updating, and the copies drift.

Required property: delete the docstring. If one non-obvious fact is worth keeping, state only that fact and leave the path and env var to `declared_roots_file()`. One candidate fact is that the result excludes `config_dir()` and the caller adds it, but `declared_roots_matching` already says so (line 94-95), so deletion is the default.
