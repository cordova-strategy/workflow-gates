# comment-discipline-reviewer

Scope note: the `python-environment-conventions.md` system reminder concerns installing Python dependencies and does not bear on this review, so I set it aside. I judged the diff under the amended "Don't restate the code" bullet.

1 file reviewed, 1 carrying an in-scope comment change (`claude/.claude/scripts/post-crash-sessions.py`, new docstring on `_declared_config_dirs`, lines 1912-1918 of the post-change file).

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/post-crash-sessions.py:1912-1915`

Issue: The docstring opens with "Declared roots from ~/.claude/transcript-config-dirs (or TRANSCRIPT_CONFIG_DIRS_FILE), validated against this script's own looser sessions/-or-projects/ check". The function name, the `declared_roots_matching` call and the lambda body already show all of this. `_config_dir.py:89-95` and `:161-163` also show the file and env-var sourcing. Only the choice of the looser check over `declared_transcript_roots()` is a decision static analysis can't explain.

Production failure mode: The comment drifts from the code. For example, the file or env-var name changes, and the docstring then states a second, stale copy.

Required property: Delete the sourcing and "validated against" clauses. Keep the decision, its reason and the pointer to `main()`'s `--config-dir` validation (the check at lines 1992-1997 exists, so the pointer stays). For example: "Accepts a root that has only `sessions/`, which `declared_transcript_roots()`'s `projects/`-only check would drop: the crashed fresh-account case this tool exists for. Matches `main()`'s `--config-dir` validation, below." Each fact is its own sentence.

## R2 [CONCERN] False or unsourced claim

File: `claude/.claude/scripts/post-crash-sessions.py:1916` ("would silently drop a sessions-only root")

Issue: The claim is settleable and its subject contradicts it in part. `declared_roots_matching` prints `"{warn_prefix}: declared root {index} unreadable"` to stderr for every root that fails `is_valid` (`_config_dir.py:150-152`). A sessions-only root would therefore be dropped with a warning, not silently. The omission from the scan is real, but "silently" is not.

Production failure mode: A maintainer who reads "silently" will not look for the stderr warning when debugging a missing root.

Required property: Say "drop" with no "silently". The fix in R1 already does. If the point is that the warning is misleading for a root that exists, say that instead: "skip it with an 'unreadable' warning".

## R3 [FYI] Multi-fact comment structure

File: `claude/.claude/scripts/post-crash-sessions.py:1912-1917`

Issue: The docstring is one sentence. It chains a source, a validation choice, a parenthetical pointer, an "instead of" contrast and a dash-appended consequence. A reader has to parse the whole sentence to find where each fact ends.

Production failure mode: This is a readability cost only. Once R1 is applied, the rewritten text splits the facts into short sentences and resolves this finding too.

Required property: Use one sentence per fact, as in the R1 suggestion. Do not re-add the sourcing clause.
