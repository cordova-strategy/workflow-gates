# comment-discipline-reviewer

Scope note: 1 file reviewed (`claude/.claude/scripts/check-handoff.py`), 1 added docstring in scope. I set aside the harness-attached python-environment-conventions reminder because it has no bearing on this review.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/check-handoff.py:95-98`, the new `strip_code_spans` docstring.

Offending text: "Remove fenced code blocks and inline code spans -- the natural way a draft would quote a literal string it's citing rather than proposing as a real next step, so a placeholder or anchor-shape scan does not fire on it."

- Issue: two clauses restate what static analysis already shows.
  - "Remove fenced code blocks and inline code spans" restates the function name and its body (`_INLINE_CODE_RE.sub("", _FENCED_BLOCK_RE.sub("", text))`, regexes at lines 77-78).
  - "so a placeholder or anchor-shape scan does not fire on it" restates the callers. `check_placeholder_text` (line 165) and `check_section3_anchor_shapes` (line 191) both pass their text through this function, and finding that needs only a grep.
- Kept decision: code spans are skipped because a draft quotes a literal string there that it is citing, not proposing as a real next step. That reason is not derivable from the code, so it stays.
- The dash-and-"so" chain also packs the action, the reason, and the effect into one sentence. The fix below leaves one fact.
- Production failure mode: a future reader sees the docstring echo the body and the callers, and the echo drifts when a caller is added or the regexes change.
- Required property: the docstring carries only the decision and its reason, as one sentence naming what is decided (code spans are excluded from scans) and why. For example: "Code spans are excluded from the placeholder and anchor-shape scans because a draft uses them to quote a literal string it is citing, not proposing as a real next step." If that wording still reads as naming the scans, shorten it to "Code spans are skipped because a draft uses them to quote literals it is citing, not proposing as a real next step." That keeps the decision's subject (code spans) inside the decision sentence.

No other angle applies. There is no PR-defined terminology, no prior-version framing, and no false claim: the docstring's "inline code spans" matches `_INLINE_CODE_RE` and "anchor-shape scan" matches `check_section3_anchor_shapes`.
