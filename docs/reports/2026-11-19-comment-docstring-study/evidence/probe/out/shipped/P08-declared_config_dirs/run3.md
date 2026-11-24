# comment-discipline-reviewer

Scope: 1 file reviewed (`claude/.claude/scripts/post-crash-sessions.py`), 1 carried an in-scope comment change (the new `_declared_config_dirs()` docstring, lines 1912-1917).

## R1 [CONCERN] False or unsourced claim

`claude/.claude/scripts/post-crash-sessions.py:1915-1916`

Issue: the docstring says `declared_transcript_roots()` "would silently drop a sessions-only root". The drop is not silent. `declared_roots_matching()` prints `"{warn_prefix}: declared root {index} unreadable"` to stderr for every candidate that fails `is_valid` (`claude/.claude/scripts/_config_dir.py:150-152`). `declared_transcript_roots()` passes the `projects/`-only check at `_config_dir.py:167`, so a sessions-only root would draw that warning. The warning names the root by index only, and its wording ("unreadable") misdescribes the cause. The claim is partly right, because the root is dropped. The word "silently" is contradicted by the subject.

Production failure mode: a future maintainer who reads "silently" may rely on it as the reason `declared_transcript_roots()` is unusable here and skip checking the actual behavior. Another may conclude the warning path is untested or broken.

Required property: state only what `_config_dir.py` supports. For example, "would drop a sessions-only root (with only an index-numbered 'unreadable' warning)". Or drop the adverb: "would drop a sessions-only root".

## R2 [CONCERN] Multi-fact comment structure

`claude/.claude/scripts/post-crash-sessions.py:1912-1917`

Issue: the docstring is one sentence of about 50 words. It chains three independent facts through a parenthetical, a double-hyphen aside and a trailing dash clause. The facts are:
1. The function reads the declared-roots file.
2. It validates with a looser `sessions/`-or-`projects/` check that matches `main()`'s `--config-dir` validation.
3. `declared_transcript_roots()` requires `projects/`, so it would drop sessions-only roots, the fresh-account crash case.

A reader must parse the whole sentence to find where one fact ends. Fact 3 is a cause-and-effect pair and may share a sentence.

Required property: one sentence per fact. Fact 1 restates `declared_roots_matching()`'s own docstring (see R3) and can go. Put the instruction-like fact first: "Validates with `sessions/` or `projects/`, matching `main()`'s `--config-dir` check." Then: "Not `declared_transcript_roots()`: it requires `projects/` and would drop a sessions-only root from a freshly crashed account."

## R3 [FYI] Prose restating the code

`claude/.claude/scripts/post-crash-sessions.py:1912-1913`

Issue: "Declared roots from ~/.claude/transcript-config-dirs (or TRANSCRIPT_CONFIG_DIRS_FILE)" restates what the call to `declared_roots_matching` and its docstring (`_config_dir.py:90`) already say. The function name `_declared_config_dirs` also conveys it. The lambda on line 1920 shows the `sessions/`-or-`projects/` check. The only non-obvious content is why this function does not call `declared_transcript_roots()`.

Required property: delete the first clause and the restated check. Keep the reason (R2's second sentence). The `main()` pointer "below" is a positional reference that goes stale when the code moves. Name the check ("`main()`'s `--config-dir` validation") without "below".

## Notes

- Checked and found accurate:
  - `declared_transcript_roots()` is `projects/`-only (`_config_dir.py:167`).
  - `main()`'s `--config-dir` validation uses the `sessions/`-or-`projects/` check (`post-crash-sessions.py:1992`).
- "The crashed-fresh-account case this tool exists for" is a design rationale and unsettleable from the repository. It draws no finding.
