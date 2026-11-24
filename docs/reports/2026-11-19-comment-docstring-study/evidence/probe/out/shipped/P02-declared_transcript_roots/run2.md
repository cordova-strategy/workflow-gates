# comment-discipline-reviewer

Scope note: the diff adds one docstring (`declared_transcript_roots()`). I judged it against every angle. The loaded `python-environment-conventions.md` reminder has no bearing on this review and I set it aside.

## R1 [FYI] Prose restating the code

- File: `claude/.claude/scripts/_config_dir.py:162-164`
- Offending text: "Return the config dirs listed in ~/.claude/transcript-config-dirs (or TRANSCRIPT_CONFIG_DIRS_FILE) that contain a `projects/` subdirectory."
- Issue:
  - The `projects/` clause restates the lambda `(candidate / "projects").is_dir()` on line 167, and the function name already says it returns declared transcript roots.
  - The file-path and env-override clause repeats the `declared_roots_matching()` docstring (lines 90-91) and the `declared_roots_file()` docstring (lines 45-47). That is a third copy of the same fact, which the single-source-of-truth rule discourages.
  - Both clauses are accurate. I checked each against lines 44-50, 89-158 and 166-169, so this is not a false-claim finding.
- Required property: the only non-obvious content is the pointer to where the parsing and skip rules live. Delete the restating sentence and keep one line, for example "Parsing, skip and warning rules: see declared_roots_matching()."

Prior decisions: none supplied.

Not flagged:
- Verbosity, multi-fact structure, paragraph readability, terminology, "used to be" framing and durable-doc self-test: the docstring is two sentences, each with one fact, in reading order, with no PR-only labels.
- Restated canonical rule: it does not apply, because the file is code.
