# comment-discipline-reviewer

Scope: 1 file reviewed (`claude/.claude/scripts/post-crash-sessions.py`), 1 comment site in scope (the new `_declared_config_dirs()` docstring, lines 1912-1917). Nothing set aside from the prompt. The substituted "Don't restate the code" bullet is in force. The input's paragraph that tells me to report every docstring clause as restating is this file's own rule, not text I set aside.

The only design decision in this docstring is: it accepts `sessions/`-only roots that `declared_transcript_roots()` would reject, because a crashed fresh account has no `projects/`. Fixes below fold that decision into one sentence. Suggested form: "Accepts a `sessions/`-only root, which `declared_transcript_roots()` would reject: a crashed fresh account may have no `projects/` yet."

## R1 [CONCERN] Prose restating the code

`post-crash-sessions.py:1912-1913`, clause "Declared roots from ~/.claude/transcript-config-dirs (or TRANSCRIPT_CONFIG_DIRS_FILE),".

- Issue: the function name `_declared_config_dirs`, its `declared_roots_matching` call, and `_config_dir.py:45-50` (`declared_roots_file()`) and `:89-91` (the `declared_roots_matching` docstring) already show which file is read and the env override.
- Required property: delete the clause. It is not a design decision.

## R2 [CONCERN] Prose restating the code

`post-crash-sessions.py:1913-1914`, clause "validated against this script's own looser sessions/-or-projects/ check".

- Issue: the lambda at line 1920 shows the check.
- Required property: delete the clause as a standalone description. Its subject, the looser check, stays only as the subject of the decision sentence above.

## R3 [CONCERN] Prose restating the code

`post-crash-sessions.py:1914`, clause "(main()'s --config-dir validation, below)".

- Issue: `main()` lines 1992-1997 show the same check, and the clause just says so.
- Required property: delete the clause per the directive. This is the one clause that could be read as a pointer to the symbol holding the decision, which the rule keeps. If the author wants it kept, the pointer must carry the decision ("same check as `main()`'s `--config-dir` validation"), not just name `main()`.

## R4 [CONCERN] Prose restating the code

`post-crash-sessions.py:1915`, clause "instead of declared_transcript_roots()'s projects/-only requirement".

- Issue: `_config_dir.py:161-169` shows the `projects/`-only requirement.
- Required property: delete the clause as a standalone contrast. It stays inside the decision sentence as the thing the decision is against.

## R5 [BLOCKER] False claim, also Prose restating the code

`post-crash-sessions.py:1916`, clause "the latter would silently drop a sessions-only root".

- Issue 1: the claim is false. `_config_dir.py:150-152` prints `{warn_prefix}: declared root {index} unreadable` to stderr for every root that fails `is_valid`. A sessions-only root passed to `declared_transcript_roots()` would be skipped with a warning, not silently.
- Issue 2: the consequence follows from `_config_dir.py:166-169` plus `_config_dir.py:147`, so it also restates the code.
- Required property: delete the clause. The decision sentence keeps the rejection as its subject and says "reject", not "silently drop".

## R6 [FYI] Prose restating the code (directive-mandated)

`post-crash-sessions.py:1916-1917`, clause "the crashed-fresh-account case this tool exists for".

- Issue: the agent's directive reports every docstring clause as restating. This clause is the reason for the decision. A fresh account that crashed has `sessions/` but no `projects/`, and that is a Claude Code runtime fact the repository's code cannot show.
- Required property: deleting it as the directive says would leave the decision with no reason, and the substituted rule keeps that reason. My recommendation is to keep the clause inside the decision sentence, as in the suggested form above. This is a conflict between the directive and the rule, for the dispatcher to settle. Unsettleable claim, no accuracy finding.

## Answers

None posed.
