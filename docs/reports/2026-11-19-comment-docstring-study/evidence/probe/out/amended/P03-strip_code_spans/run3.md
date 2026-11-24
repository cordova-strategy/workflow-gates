# comment-discipline-reviewer

## R1 [CONCERN] Restating the code

File: claude/.claude/scripts/check-handoff.py:95-98 (docstring of `strip_code_spans`)

Issue: The docstring opens "Remove fenced code blocks and inline code spans". The function name and its body (`_INLINE_CODE_RE.sub("", _FENCED_BLOCK_RE.sub("", text))`) already show this, and static analysis of the repo finds it. The remainder of the docstring holds the non-obvious decision: a draft quotes a cited literal in code, so stripping keeps the placeholder and anchor-shape scans from firing on it. That decision stays. The docstring also chains the restatement, the quoting rationale and the scan effect into one dash-and-comma sentence, a Multi-fact comment structure problem. Deleting the restatement removes it.

Production failure mode: None at runtime. The restating clause adds reading cost and will drift if the regexes change, for example if indented fences are added.

Required property: Delete the "Remove fenced code blocks and inline code spans" clause. Keep the decision, with the subject inside the decision sentence so the reason still names what it explains. For example: "Code spans are stripped before the placeholder and anchor-shape scans because a draft quotes a literal it is citing there, not proposing it as a next step."

Checked: the callers `check_placeholder_text` (line 165) and the §3 anchor check (line 191) confirm the two scans the docstring names. No false-claim finding.
