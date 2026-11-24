# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/_config_dir.py`); 1 carried an in-scope change (a new docstring on `declared_transcript_roots`). No prompt text was set aside.

## R1 [CONCERN] Prose restating the code

`claude/.claude/scripts/_config_dir.py:162-163` (diff lines 8-9).

Issue: "Return the config dirs listed in ~/.claude/transcript-config-dirs (or TRANSCRIPT_CONFIG_DIRS_FILE) that contain a `projects/` subdirectory." The clause restates what the code already shows:
- the `lambda candidate: (candidate / "projects").is_dir()` predicate;
- the function name;
- the default path and env override, which `_config_dir.py:45-50` already defines.

It states no decision and no reason static analysis can't find. I checked it against the subject: the claim is true, so it draws no False-claim finding.

Production failure mode: none. The clause is true today but duplicates the predicate and the path logic, so it can drift if either changes.

Required property: delete the clause.

## R2 [FYI] Prose restating the code

`claude/.claude/scripts/_config_dir.py:163-164` (diff lines 9-10).

Issue: "See declared_roots_matching() for the parsing contract this builds on." This clause is a pointer to the symbol that holds the parsing contract (`_config_dir.py:89-90`). The rule under test keeps such pointers, so this finding conflicts with it. The agent's per-clause instruction says to report every docstring clause with deletion as the fix "whatever the clause says", so I report it at FYI severity.

Required property: delete the clause under the agent's per-clause rule. If the dispatcher keeps the pointer under the rule under test, the docstring then reduces to this single pointer line, and R1's deletion still stands.

Prior decisions: none supplied.
