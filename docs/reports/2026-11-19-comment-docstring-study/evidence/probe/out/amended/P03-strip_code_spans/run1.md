# comment-discipline-reviewer

Scope note: the system-reminder on Python environment conventions bears on no angle in this review, so I set it aside.

## R1 [CONCERN] Restating the code

File: claude/.claude/scripts/check-handoff.py:95-98 (the new `strip_code_spans` docstring).

Issue: The docstring opens with "Remove fenced code blocks and inline code spans". The function name and its body (`_INLINE_CODE_RE.sub("", _FENCED_BLOCK_RE.sub("", text))`) already show this, so under the rule under test the clause restates the code. The rest of the docstring is a real design decision that static analysis cannot find. Drafts quote literal strings they are citing, not proposing, inside code spans, and the placeholder scan (line 165) and anchor-shape scan (line 191) must not fire on them. That rationale stays.

Production failure mode: none. This is comment noise, and the restating clause pushes the one non-obvious fact into a long dash-chained sentence.

Required property: delete the restating clause. Keep the decision as a sentence that still names what it decides, so the reason has a subject. Suggested shape: "Code spans are excluded from the placeholder and anchor-shape scans because a draft quotes a literal string it is citing in them, not proposing it as a real next step." The cause-and-effect pair can share one sentence. No other angle is triggered by the compression: it has no PR-defined label, no prior-version framing, and no unsourced claim.

Other angles checked on this diff, with no finding: PR-defined terminology, "used to be X" framing, wrong altitude, canonical-rule restatement (the file is a script), and false or unsourced claims. The stated purpose matches the callers at lines 165 and 191.
