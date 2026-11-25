# comment-discipline-reviewer

## R1 [CONCERN] Restating the code

- **File and line:** `claude/.claude/scripts/check-handoff.py:95-98` (docstring of `strip_code_spans`)
- **Offending text:** "Remove fenced code blocks and inline code spans -- the natural way a draft would quote a literal string it's citing rather than proposing as a real next step, so a placeholder or anchor-shape scan does not fire on it."
- **Issue:** The clause "Remove fenced code blocks and inline code spans" restates what the function name, `_FENCED_BLOCK_RE`/`_INLINE_CODE_RE` and the one-line body already show. The remainder is a real decision: code is stripped so quoted literals don't trip the placeholder and §3.5 anchor-shape scans. The callers at lines 165 and 191 confirm those two scans consume the stripped text.
- **Production failure mode:** None at runtime. The restated half adds noise and would go stale if the stripping changes.
- **Required property:** Keep the decision and its reason, and delete the restated half. Suggested replacement: `"""Strip code so a draft that quotes a literal placeholder or anchor-shape string, rather than proposing it as a next step, does not trip the placeholder and anchor-shape scans."""`. The wording keeps the reason, names the two scans it protects, and states one decision in one sentence. It trades no other angle's violation, because it adds no PR-defined label, no prior-version framing and no unsourced claim.

No other angle applies to this site. The single changed hunk is a docstring, and the diff adds no other comment or doc prose.
