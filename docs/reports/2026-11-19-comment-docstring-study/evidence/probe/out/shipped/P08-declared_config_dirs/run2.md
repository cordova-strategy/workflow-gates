# comment-discipline-reviewer

Scope: 1 file reviewed (`claude/.claude/scripts/post-crash-sessions.py`), 1 with an in-scope comment change (the new `_declared_config_dirs()` docstring, lines 1912-1917). No text was set aside from the dispatch.

## R1 [CONCERN] False or unsourced claim

`post-crash-sessions.py:1915-1917`

Issue: the docstring says `declared_transcript_roots()`'s projects/-only requirement "would silently drop a sessions-only root". The claim is false as written. A root that fails the `is_valid` check is skipped with a stderr warning. `_config_dir.py:150-152` shows `if not valid: print(f"{warn_prefix}: declared root {index} unreadable", file=sys.stderr); continue`. For `declared_transcript_roots()` the warning is prefixed `declared_transcript_roots` (`_config_dir.py:168`). The `declared_roots_matching` docstring (`_config_dir.py:116-118`) also says a skipped root is "skipped with a warning naming it by index only". The root is dropped, but not silently.

Production failure mode: a future contributor reads "silently" and, when debugging a missing sessions-only root, looks for the absence of any signal. They overlook the "declared root N unreadable" warning, which is the actual diagnostic.

Required property: state the narrowest claim the code supports. Either "would drop a sessions-only root (warning only that it is 'unreadable')" or just "would skip a sessions-only root". The "silently" claim can't stay.

The rationale that this is "the crashed-fresh-account case this tool exists for" is a design judgment. It draws no finding.

## R2 [CONCERN] Multi-fact comment structure

`post-crash-sessions.py:1912-1917`

Issue: one run-on sentence chains four independent facts through a parenthetical, an "instead of" clause and a dash aside:
- where the roots come from;
- that validation uses the looser sessions/-or-projects/ check;
- that this mirrors `main()`'s `--config-dir` validation;
- why the projects/-only check is unsuitable.

A reader has to parse the whole sentence to find where one fact ends. The first clause ("Declared roots from ~/.claude/transcript-config-dirs (or TRANSCRIPT_CONFIG_DIRS_FILE)") also repeats what `declared_roots_matching`'s docstring (`_config_dir.py:90`) already documents and what the call shows.

Required property: drop the source clause, or reduce it to a pointer to `declared_roots_matching()`. Then give each remaining fact its own sentence, with the constraint first, for example:
- "Validates with the same `sessions/`-or-`projects/` check as `main()`'s `--config-dir` handling."
- "`declared_transcript_roots()` requires `projects/`, so it would drop a sessions-only root, which is the crashed fresh-account case this tool targets."

The second sentence must also carry the R1 correction.
