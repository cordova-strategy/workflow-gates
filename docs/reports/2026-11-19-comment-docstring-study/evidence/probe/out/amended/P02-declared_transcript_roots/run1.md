# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/_config_dir.py`); 1 carried an in-scope comment change (the new `declared_transcript_roots()` docstring). The `/home/<username>/MyCode/claude-config/.claude/rules/python-environment-conventions.md` text that arrived mid-session concerns Python installs, is not in the input contract, and was set aside.

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/_config_dir.py:162-164` (added docstring of `declared_transcript_roots`).

Offending text: "Return the config dirs listed in ~/.claude/transcript-config-dirs (or TRANSCRIPT_CONFIG_DIRS_FILE) that contain a `projects/` subdirectory."

Issue: Static analysis of this repository's code finds every clause of this sentence.
- The function name and the `list[Path]` return type give "returns the declared transcript roots".
- The lambda `(candidate / "projects").is_dir()` on line 167 gives "contain a `projects/` subdirectory".
- `declared_roots_file()` (lines 45-50) gives the roots file and its `TRANSCRIPT_CONFIG_DIRS_FILE` override. `declared_roots_matching()`'s own docstring (lines 90-91) already says the same.

The sentence names no design decision and gives no reason static analysis cannot find, such as why transcript roots require `projects/`. The amended rule says to delete such clauses even when true. Under the amended rule, "a shorter or corrected restatement still restates".

Fix: delete that sentence. Keep the pointer sentence, because a pointer to the symbol that holds a decision stays (line 164, "See declared_roots_matching() for the parsing contract this builds on."). Drop the trailing "this builds on", which the call on line 166 shows. The docstring reduces to "See declared_roots_matching() for the parsing contract." If the author knows an outside constraint that forces the `projects/` requirement (for example, Claude Code writes transcripts under `<config-dir>/projects/`), add it as one sentence naming that decision and its reason. Without such a reason, leave nothing else.

Checked for false or unsourced claims. Every statement in the docstring is supported by the code at lines 45-50, 89-158 and 166-169, so there is no finding under that angle. The sentence is deleted under the restating-the-code angle in any case.
