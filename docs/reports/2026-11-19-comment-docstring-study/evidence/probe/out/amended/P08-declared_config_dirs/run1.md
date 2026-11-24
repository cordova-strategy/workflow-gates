# comment-discipline-reviewer

Scope note: the diff adds one docstring (`_declared_config_dirs`, post-crash-sessions.py:1912-1917). The dispatch carried no scope text that conflicts with the agent file. The `python-environment-conventions.md` system-reminder has no bearing on this review, so I set it aside. The "Don't restate the code" bullet from the prompt applies in place of the CLAUDE.md version.

## R1 [CONCERN] Restating the code

File: claude/.claude/scripts/post-crash-sessions.py:1912-1915

Issue: The docstring opens with "Declared roots from ~/.claude/transcript-config-dirs (or TRANSCRIPT_CONFIG_DIRS_FILE), validated against this script's own looser sessions/-or-projects/ check (main()'s --config-dir validation, below)". The function name, its `declared_roots_matching` call and the lambda body show all of this. `declared_roots_matching`'s own docstring (_config_dir.py:90) holds the file-path and env-var facts. Static analysis finds every clause, so none of it is a kept decision.

Required property: Delete the "Declared roots from ... (or TRANSCRIPT_CONFIG_DIRS_FILE)" clause and the restated lambda condition. Keep one sentence carrying the decision and its reason. For example: "Accepts a root that has only sessions/, unlike declared_transcript_roots(), because a freshly crashed account may have no projects/ yet; main()'s --config-dir validation applies the same rule." The sentence names what was decided and the reason, and keeps the pointer to main(). It avoids the dash/parenthetical chain, which was multi-fact as written.

## R2 [CONCERN] False or unsourced claim

File: claude/.claude/scripts/post-crash-sessions.py:1915-1917

Issue: The docstring says `declared_transcript_roots()` "would silently drop a sessions-only root". The drop is not silent. `declared_transcript_roots()` calls `declared_roots_matching`, which prints `"{warn_prefix}: declared root {index} unreadable"` to stderr for every root that fails `is_valid` (_config_dir.py:150-152, the `print` at line 151). The root is dropped, but with a warning.

Required property: Remove "silently". The narrowest statement the code supports is "would drop a sessions-only root". If R1's rewrite is applied, keep the word out of it. Do not replace it with "with a warning". That detail restates the code.
