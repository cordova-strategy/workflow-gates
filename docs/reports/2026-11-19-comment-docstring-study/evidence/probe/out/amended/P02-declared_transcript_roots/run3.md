# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/_config_dir.py`); 1 carried an in-scope comment change. The system-reminder rule file on Python environments does not bear on this diff and changed nothing.

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/_config_dir.py:162-164` (new docstring on `declared_transcript_roots`).

Issue: The first sentence, "Return the config dirs listed in ~/.claude/transcript-config-dirs (or TRANSCRIPT_CONFIG_DIRS_FILE) that contain a `projects/` subdirectory", states only what static analysis finds:
- The function name and return type give "returns the declared transcript roots".
- The `lambda candidate: (candidate / "projects").is_dir()` on line 167 shows the `projects/` check.
- The default path and the `TRANSCRIPT_CONFIG_DIRS_FILE` override are in `declared_roots_matching()`'s docstring (lines 90-91) and in the path helper at lines 45-50.

It names no design decision and no reason that lies outside the code. The docstring adds nothing the code and the callee's docstring don't already show. The sentence also duplicates the file path and env-var facts from their canonical home, which breaks single source of truth.

Production failure mode: If the env-var seam or the validity predicate changes, this copy drifts from the code and from the callee's docstring.

Required property: Delete the first sentence. Keep only the pointer to the symbol that holds the parsing decisions, for example `See declared_roots_matching() for the parsing contract.` A shorter or corrected restatement of the first sentence would still be a restatement. Drop "this builds on", since it describes the call the code already shows. I checked the text against `declared_roots_matching` (lines 89-115) and found no false claim. The finding is a restatement only.
