# comment-discipline-reviewer

Scope: 1 file reviewed, 1 added docstring in scope (`_declared_config_dirs`, post-crash-sessions.py:1912-1918). I set no prompt text aside.

## R1 [CONCERN] False or unsourced claim

post-crash-sessions.py:1915-1917 (diff lines 8-14).

Text: "the latter would silently drop a sessions-only root".

Issue: the claim is settleable and the subject contradicts it. `declared_transcript_roots()` calls `declared_roots_matching()` with a `projects/`-only validator (`_config_dir.py:166-169`). That function prints `"{warn_prefix}: declared root {index} unreadable"` to stderr for every root `is_valid` rejects (`_config_dir.py:150-152`). A sessions-only root would be dropped with a warning, not silently. The projects/-only requirement itself is correct (`_config_dir.py:167`).

Failure mode: a maintainer reading "silently" would expect no diagnostic, and would misdiagnose the stderr warning "declared root N unreadable" as a different bug.

Required property: state only what the subject supports, e.g. "would drop a sessions-only root (with an 'unreadable' warning)", or drop "silently".

## R2 [CONCERN] Restating the code

post-crash-sessions.py:1912-1915 (diff lines 8-11).

Text: "Declared roots from ~/.claude/transcript-config-dirs (or TRANSCRIPT_CONFIG_DIRS_FILE), validated against this script's own looser sessions/-or-projects/ check ... instead of declared_transcript_roots()'s projects/-only requirement".

Issue: the lambda on the next lines shows the sessions/-or-projects/ check. `declared_roots_matching()`'s docstring and `declared_transcript_roots()`'s docstring (`_config_dir.py:90`, `:162-163`) hold the file name, the env override, and the projects/-only rule. Those clauses are findable by static analysis, so they restate the code.

Required property: delete the "Declared roots from ... (or ...)" lead and the description of what the validator checks. Keep the one decision and its reason: this wrapper accepts sessions/-only roots, and the reason is the fresh-account case the tool exists for. Keep the pointer to main()'s `--config-dir` validation (`:1992`) if the author wants the link, since it names where the matching check lives. Keep `declared_transcript_roots()` named in the decision sentence so the reason still names what it contrasts with.

## R3 [FYI] Multi-fact comment structure

post-crash-sessions.py:1912-1917 (diff lines 8-13).

Text: the whole docstring is one sentence chained with a parenthetical, a "(main()'s ... below)" aside, and a dash.

Issue: it carries four independent facts in one sentence: where the roots come from, which validator is used, where that validator is mirrored, and why. A reader must parse it all to find the decision.

Required property: after R2's deletions, two sentences at most, decision first and reason second. For example: "Accepts sessions/-only roots, unlike declared_transcript_roots()'s projects/-only check, mirroring main()'s --config-dir validation. A freshly crashed account may have no projects/ yet, and this tool exists for that case."
