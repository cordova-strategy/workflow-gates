# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/_config_dir.py`); 1 docstring change in scope. The system-reminder rule file `python-environment-conventions.md` does not bear on this diff and was set aside.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/_config_dir.py:162-165` (added docstring on `declared_transcript_roots`).

Issue: the first sentence, "Return the config dirs listed in ~/.claude/transcript-config-dirs (or TRANSCRIPT_CONFIG_DIRS_FILE) that contain a `projects/` subdirectory.", restates what the code shows:
- The function name says it returns declared transcript roots.
- The lambda at line 167 shows the `projects/` check.
- `declared_roots_file()` (line 45-50) and the `declared_roots_matching` docstring (line 90) show the default path and the env override.

None of it gives a design decision or a reason static analysis cannot find. The comment never says why `projects/` is the validity test, so no kept decision is stated here.

Failure mode: the file path and the env-var name now appear in a third site (`declared_roots_file()`, the `declared_roots_matching` docstring and this one). A change to either has to be made in all three.

Required property: delete the first sentence. Keep only the pointer to the doc that holds the contract, for example `See declared_roots_matching() for the parsing contract.`, which is allowed to stay. The docstring may also be removed entirely if the pointer is judged unnecessary. Adding a reason for the `projects/` test is only worthwhile if one exists that is not derivable from the repo, and none is evident.

No other angle produced a finding. The claims in the docstring are true at the diff's state: `_config_dir.py:50` and `:167` confirm them.
