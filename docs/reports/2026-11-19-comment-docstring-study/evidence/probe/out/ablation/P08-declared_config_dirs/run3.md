# comment-discipline-reviewer

Reviewed 1 file (`post-crash-sessions.py`); 1 added docstring in scope (`_declared_config_dirs`, lines 8-14 of the diff, a single sentence that carries four clauses). No prompt text was set aside. Each clause is a separate Restating-the-code finding, per the docstring-clause rule. Cited sources were read at the snapshot's state.

## R1 [CONCERN] Prose restating the code

`post-crash-sessions.py` `_declared_config_dirs` docstring, clause "Declared roots from ~/.claude/transcript-config-dirs (or TRANSCRIPT_CONFIG_DIRS_FILE)".

- Issue: the function name and its `declared_roots_matching(...)` call show this. `_config_dir.py:45-50` and `_config_dir.py:90` already state the file path and the env override.
- Required fix: delete the clause.

## R2 [CONCERN] Prose restating the code

`post-crash-sessions.py` `_declared_config_dirs` docstring, clause "validated against this script's own looser sessions/-or-projects/ check (main()'s --config-dir validation, below)".

- Issue: the lambda on the next line (diff line 16) states the check exactly. The "main()" pointer names code that repeats the same predicate at `post-crash-sessions.py:1992`. It is not a doc or symbol that holds a decision, so the pointer rule does not keep it.
- Required fix: delete the clause. If a decision sentence survives (see R4), it may name the chosen check, "uses the sessions/-or-projects/ check", without describing the lambda.

## R3 [CONCERN] Prose restating the code

`post-crash-sessions.py` `_declared_config_dirs` docstring, clause "instead of declared_transcript_roots()'s projects/-only requirement".

- Issue: `_config_dir.py:161-163` states the `projects/`-only requirement for `declared_transcript_roots()`. A reader finds it by static analysis across two files. The clause names the alternative not taken, which is not a reason the code cannot show.
- Required fix: delete the clause. The decision subject, "not `declared_transcript_roots()`", may stay inside a kept decision sentence if one survives.

## R4 [CONCERN] Prose restating the code

`post-crash-sessions.py` `_declared_config_dirs` docstring, clause "the latter would silently drop a sessions-only root, the crashed-fresh-account case this tool exists for".

- Issue: the consequence follows from comparing the lambda with `_config_dir.py:161-163`. The "crashed-fresh-account" purpose is already stated in the repo, in the test docstring at `test_post_crash_sessions.py:3840`, so static analysis of the repo's code and tests finds it. No part of this clause is a reason outside the repository.
- Required fix: delete the clause. Once R1-R3 are applied, no decision with a reason static analysis cannot find remains, so the whole docstring is deleted. If the author judges the sessions-only purpose to be an outside constraint, keep that single sentence and cite the test at `test_post_crash_sessions.py:3840` as the pointer. That sentence should read as a short decision with its reason, such as "Accepts sessions/-only roots so a crashed fresh account is still found." It should not carry the dash or parenthetical chain.

## Notes

- The docstring is also one dash-and-parenthetical-chained sentence (Multi-fact structure). Deleting it per R1-R4 resolves that finding. A surviving sentence must be a single fact.
- Checked and found true: the "main() ... below" reference resolves (`post-crash-sessions.py:1992`), and `declared_transcript_roots()` does require `projects/` (`_config_dir.py:161-163`). No False-claim finding.

**Request changes**: delete the docstring, or reduce it to the one sentence in R4.
