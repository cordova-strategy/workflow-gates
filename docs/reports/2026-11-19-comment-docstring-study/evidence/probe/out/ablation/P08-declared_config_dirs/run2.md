# comment-discipline-reviewer

Scope: 1 file reviewed (`claude/.claude/scripts/post-crash-sessions.py`), 1 comment change in scope (the new `_declared_config_dirs()` docstring, lines 1912-1917 of the post-image). I applied the "Don't restate the code" bullet as the dispatch's rule-under-test text replaces it. The prompt names no sites or scope that contradict the agent file, so I set no text aside. An auto-attached `python-environment-conventions.md` rule is unrelated to this diff.

Kept decision (one sentence, see R5): use the looser sessions/-or-projects/ check instead of `declared_transcript_roots()`'s projects/-only one, because a sessions-only root is the crashed-fresh-account case this tool exists for. The reason is a design rationale static analysis cannot find, so it stays. The subject clauses it names (the looser check, the projects/-only alternative) stay inside that sentence.

## R1 [CONCERN] Prose restating the code

`post-crash-sessions.py:1912-1913`, docstring clause "Declared roots from ~/.claude/transcript-config-dirs (or TRANSCRIPT_CONFIG_DIRS_FILE)".
- Issue: the clause restates what the function name and `declared_roots_matching()`'s own docstring already say (`_config_dir.py:89-91`, `:161-163`). Static analysis of the repo finds it.
- Fix: delete the clause.

## R2 [CONCERN] Prose restating the code

`post-crash-sessions.py:1913-1914`, docstring clause "validated against this script's own looser sessions/-or-projects/ check".
- Issue: the lambda at line 1920 shows exactly this predicate.
- Fix: delete the clause as a description of the code. Its subject survives inside the kept decision sentence as "accepts sessions-only roots".

## R3 [CONCERN] Prose restating the code

`post-crash-sessions.py:1914`, docstring clause "(main()'s --config-dir validation, below)".
- Issue: it points at the duplicate of the same predicate (`:1992`), not at the doc or symbol that holds the decision. The pointer exception does not apply, and a reader finds the identical check by reading the code.
- Fix: delete the clause. If you want a pointer, make the decision sentence cite the home of the reason, not the second copy of the predicate.

## R4 [CONCERN] Prose restating the code (also false in part)

`post-crash-sessions.py:1915-1916`, docstring clause "the latter would silently drop a sessions-only root".
- Issue: reading `declared_transcript_roots()` (`_config_dir.py:166-169`) and `declared_roots_matching()` shows that a projects/-less root is dropped. That is a code consequence, not a reason.
- Falsehood: the drop is not silent. `_config_dir.py:150-152` prints "`<warn_prefix>`: declared root N unreadable" to stderr for every root failing `is_valid`.
- Fix: delete the consequence clause. Keep only "accepts a sessions-only root" in the decision sentence. A corrected restatement ("drops it with a warning") still restates.

## R5 [CONCERN] Multi-fact comment structure

`post-crash-sessions.py:1912-1917`, the whole docstring.
- Issue: one sentence chains the source, the validation, a parenthetical pointer, an `instead of` contrast, a dash and a rationale. A reader must parse all of it to find the one decision.
- Fix: after R1-R4, reduce the docstring to one sentence that states the decision and its reason. Example shape: "Accepts a sessions-only root, unlike `declared_transcript_roots()`, because a crashed fresh account is the case this tool exists for." Verify that wording keeps the original reason and adds no new claim.
