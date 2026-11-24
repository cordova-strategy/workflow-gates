# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/_config_dir.py`); 1 added docstring in scope. I set aside the python-environment-conventions rule text that arrived mid-session. It is unrelated to comment discipline and changes no scope.

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/_config_dir.py:45-48` (new docstring on `declared_roots_file()`).

Offending text:

> Return the path declared_roots_matching() reads: TRANSCRIPT_CONFIG_DIRS_FILE if set (a test seam mirroring cleanup-merged-branches.sh's CLEANUP_MERGED_BRANCHES_ROOTS_FILE), else ~/.claude/transcript-config-dirs. Unlike TRANSCRIPT_CONFIG_DIRS_LABEL, this DOES follow the seam.

Issue: under the amended "Don't restate the code" rule, most of the docstring says what static analysis finds. I checked each clause against the repo.
- "Return the path ... if set ... else ~/.claude/transcript-config-dirs" restates the one-line body (line 50). The caller relationship ("reads") is found by grep (`declared_roots_file_state` at line 81, `declared_roots_matching` at line 89 onward).
- "mirroring cleanup-merged-branches.sh's CLEANUP_MERGED_BRANCHES_ROOTS_FILE" is true (`cleanup-merged-branches.sh:255`), but it is a cross-file fact grep finds. It also restates the identical parenthetical already at `_config_dir.py:90-92`, so the same fact now has two homes.
- "Unlike TRANSCRIPT_CONFIG_DIRS_LABEL, this DOES follow the seam" is true (line 50 against the line 13-17 comment). It restates the contrast the `TRANSCRIPT_CONFIG_DIRS_LABEL` comment already holds at lines 14-16, so the constant's own comment is the home.

Production failure mode: none at runtime. The cost is a second and third copy of the seam description that drift from the first when the env var or the label changes.

Required property: the docstring keeps only the decision it names, which is that `TRANSCRIPT_CONFIG_DIRS_FILE` is a test seam. It points at the symbol that holds the label-versus-path contrast, and drops the rest.

Concrete fix, replacing the docstring:

```python
"""TRANSCRIPT_CONFIG_DIRS_FILE overrides the default path as a test seam.

Operator-facing messages use TRANSCRIPT_CONFIG_DIRS_LABEL instead, which deliberately ignores the seam.
"""
```

Alternatively, keep only the first sentence and drop the pointer, since the `TRANSCRIPT_CONFIG_DIRS_LABEL` comment already points back at `declared_roots_file()`.

Other angles checked: no PR-defined terminology, no "used to be" framing, and no false claims. The only claims are about named symbols, and both hold at the diff state (`cleanup-merged-branches.sh:255`, `_config_dir.py:50`).
