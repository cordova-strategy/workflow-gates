# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/_config_dir.py`); 1 carried an in-scope comment change (the new `declared_transcript_roots()` docstring).

I set aside the stray `python-environment-conventions.md` reminder text. It states rules for installing Python dependencies and bears on none of this diff's comment-discipline angles.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/_config_dir.py:162-165` (added docstring on `declared_transcript_roots()`).

Offending text: "Return the config dirs listed in ~/.claude/transcript-config-dirs (or TRANSCRIPT_CONFIG_DIRS_FILE) that contain a `projects/` subdirectory. See declared_roots_matching() for the parsing contract this builds on."

Issue: Each sentence states what the body already shows.
- The function name says it returns the declared transcript roots.
- The body is a single `declared_roots_matching(...)` call, so the pointer to that function repeats what the call site shows.
- The lambda `(candidate / "projects").is_dir()` shows the `projects/` condition.
- `declared_roots_file()` (line 44-50) and `declared_roots_matching()`'s docstring (line 90) already state the file path and the `TRANSCRIPT_CONFIG_DIRS_FILE` override.

The passage is also an incomplete restatement. `declared_roots_matching()` (lines 141-157) additionally requires an absolute path and a directory, and it dedupes by resolved path. A relative line pointing at a directory that contains `projects/` is listed but excluded, so "listed ... that contain a `projects/` subdirectory" supports the behavior only in part (lines 141-144, 147, 153-157). This is a minor accuracy concern. Correcting the wording would still leave a restatement.

Required property: delete the docstring. The parsing contract stays in `declared_roots_matching()`'s docstring, its single source of truth. Add a comment only if a non-obvious fact turns up that the name, lambda, and the callee's docstring don't show.
