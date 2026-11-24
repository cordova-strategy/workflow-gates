# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/post-crash-sessions.py`); 1 docstring in scope (`_declared_config_dirs`). Set-aside text: none.

## R1 [CONCERN] False or unsourced claim

`post-crash-sessions.py:1915-1918` (added docstring), subject `_config_dir.py:150-152`.

Offending text: "the latter would silently drop a sessions-only root".

Issue: `declared_roots_matching()` does not drop a root that fails `is_valid` silently. It prints `"{warn_prefix}: declared root {index} unreadable"` to stderr and then skips it (`_config_dir.py:150-152`). `declared_transcript_roots()` passes `warn_prefix="declared_transcript_roots"` and a `projects/`-only predicate (`_config_dir.py:166-169`). A sessions-only root would therefore be skipped with a misleading "unreadable" warning, not skipped silently.

Required property: the claim is the narrowest statement the subject supports. Replace "silently drop" with "skip". If the point is that the warning misdiagnoses the cause, say so as a separate sentence.

## R2 [CONCERN] Restating the code

`post-crash-sessions.py:1912-1914`.

Offending text: "Declared roots from ~/.claude/transcript-config-dirs (or TRANSCRIPT_CONFIG_DIRS_FILE), validated against this script's own looser sessions/-or-projects/ check".

Issue: The function name, the `declared_roots_matching` call, and the lambda already show the roots file and the `sessions/`-or-`projects/` predicate. `_config_dir.py:90` documents the file and the env override. Under the rule under test, only the decision survives. That decision is "use the looser predicate rather than `declared_transcript_roots()`'s", plus its reason and the pointer to `main()`'s validation.

Required property: delete the roots-file and env-var clause and the predicate spelling. Keep the decision, the reason, and the pointer to `main()`'s `--config-dir` check.

## R3 [CONCERN] Multi-fact comment structure / Paragraph readability

`post-crash-sessions.py:1912-1918`.

Issue: One sentence chains a description, a parenthetical pointer, a contrast, a dash and a reason. The decision is buried mid-sentence behind the restated detail.

Required property: with R1 and R2 applied, lead with the decision and put the reason in its own sentence. For example:

```
"""Accept a sessions-only root, unlike declared_transcript_roots(), which requires projects/.

A fresh account that crashed has no projects/ yet, the case this tool exists for.
The check matches main()'s --config-dir validation.
"""
```

This sample asserts "has no projects/ yet" and keeps the original's "crashed-fresh-account" premise. That premise is unsettleable from the repo. Keep it as the author's design rationale, or cite where it is documented.

Check of the rewrite against the other angles: it has no PR-defined labels and no "used to be" framing. The "main()'s ... below" pointer is a symbol reference that stays.

Prior decisions: none supplied.
