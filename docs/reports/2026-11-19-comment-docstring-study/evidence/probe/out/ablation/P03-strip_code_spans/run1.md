# comment-discipline-reviewer

## R1 [CONCERN] Prose restating the code

File: claude/.claude/scripts/check-handoff.py:95-98 (docstring of `strip_code_spans`)

Issue: The docstring has three clauses, and two of them restate the code.
- "Remove fenced code blocks and inline code spans" restates the function name and the `_FENCED_BLOCK_RE` / `_INLINE_CODE_RE` substitutions on line 99.
- "so a placeholder or anchor-shape scan does not fire on it" names the callers, `check_placeholder_text` (line 165) and the §3.5 anchor-shape check (line 191). Grep finds those callers.

The kept decision is the reason: a draft puts a literal it cites, rather than proposes as a real next step, in a code span. The code can't show that.

Production failure mode: None. The cost is a docstring that repeats the code, and a caller list that goes stale when a new caller appears.

Required property: Delete the first clause and the caller list. Keep one sentence that names the decision and its reason, with the subject inside it so the reason still names what it explains. For example: "Code spans are dropped because a draft uses them to quote literals it is citing, not proposing as real next steps." Every other part of the docstring is deleted.
