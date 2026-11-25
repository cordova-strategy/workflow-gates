# comment-discipline-reviewer

Scope: 1 file reviewed (`claude/.claude/scripts/check-handoff.py`), 1 docstring added. No prompt text was set aside.

## R1 [CONCERN] Prose restating the code

claude/.claude/scripts/check-handoff.py:95

Issue: The clause "Remove fenced code blocks and inline code spans" restates the function name `strip_code_spans` and its body (`_INLINE_CODE_RE.sub("", _FENCED_BLOCK_RE.sub("", text))`, regexes at lines 77-78). Static analysis of this file finds it.

Production failure mode: The clause adds nothing the code does not show, and it drifts if the regexes change.

Required property: Delete the clause. Keep the decision it introduces: the reason for stripping, which comes from how drafts are written and which the code cannot show. Keep the subject inside that sentence so the reason still names what it explains, for example: "Code spans are skipped because a draft quotes a literal string it is citing there, not proposing it as a real next step."

## R2 [CONCERN] Prose restating the code

claude/.claude/scripts/check-handoff.py:97-98

Issue: The tail "so a placeholder or anchor-shape scan does not fire on it" lists the callers, `check_placeholder_text` (line 165) and the §3.5 anchor-shape check (line 191). A `Grep` for `strip_code_spans` finds both. It also restates the effect of the stripping.

Production failure mode: The caller list goes stale when a third caller is added or one is removed.

Required property: Delete the clause. The reason in R1's rewrite ("quotes a literal string it is citing, not proposing") is the only non-obvious design decision the docstring needs.
