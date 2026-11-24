# comment-discipline-reviewer

Scope: 1 file in the diff (`claude/.claude/scripts/post-crash-sessions.py`), 1 added docstring (`_declared_config_dirs`, lines 1912-1917 in the snapshot). The only prompt text set aside: none. The injected python-environment-conventions reminder is unrelated to comment discipline and was ignored.

## R1 [CONCERN] False or unsourced claim

File: `claude/.claude/scripts/post-crash-sessions.py:1915-1916` (docstring of `_declared_config_dirs`).

Issue: the docstring says `declared_transcript_roots()`'s projects/-only requirement "would silently drop a sessions-only root". `declared_roots_matching()` does not drop a failing root silently. It prints `"<warn_prefix>: declared root <index> unreadable"` to stderr at `claude/.claude/scripts/_config_dir.py:150-152`, and `declared_transcript_roots()` passes `is_valid` as `(candidate / "projects").is_dir()` at `_config_dir.py:166-169`. Only the "drops a sessions-only root" half holds. "Silently" is contradicted, and the warning it emits ("unreadable") is itself misleading for a root that is readable but has no `projects/`.

Production failure mode: a maintainer who reads "silently" will conclude no diagnostic exists and may skip checking stderr when debugging a missing declared root.

Required property: state only what the subject supports. Drop "silently", or say the root is dropped with a misleading "unreadable" warning.

## R2 [CONCERN] Restating the code

File: `claude/.claude/scripts/post-crash-sessions.py:1912-1915`.

Issue: three clauses restate what static analysis of this repository finds, and the rule under test says to delete these even when true.
- "Declared roots from ~/.claude/transcript-config-dirs (or TRANSCRIPT_CONFIG_DIRS_FILE)" restates the `declared_roots_matching` call. `_config_dir.py:44-50` and `:90` hold the path and env-var seam.
- "validated against this script's own looser sessions/-or-projects/ check" restates the lambda on line 1920.
- "instead of declared_transcript_roots()'s projects/-only requirement" restates what `_config_dir.py:166-169` shows.

What stays is the decision (use the sessions-or-projects check, not `declared_transcript_roots()`), its reason (a sessions-only root of a crashed fresh account would be dropped), and the pointer to `main()`'s `--config-dir` validation. The reason names an outside-the-code purpose, so static analysis cannot supply it.

Required property: one sentence per decision, with the restated halves deleted.

## R3 [FYI] Multi-fact comment structure

File: `claude/.claude/scripts/post-crash-sessions.py:1912-1917`.

Issue: the docstring is one sentence chaining the source, the validation choice, a parenthetical pointer, a dash-introduced reason and an appositive ("the crashed-fresh-account case…"). A reader has to parse the whole run-on to find where each fact ends.

Concrete fix, which also resolves R1 and R2 and adds no new restatement:

```python
"""Accept a declared root that has only sessions/ or only projects/, matching main()'s --config-dir check.

declared_transcript_roots() requires projects/, so it would drop a sessions-only root:
the crashed fresh account this tool exists to recover.
"""
```

(Wrap to the repo's line length.)

## Answers

No questions were posed in the dispatch prompt.
