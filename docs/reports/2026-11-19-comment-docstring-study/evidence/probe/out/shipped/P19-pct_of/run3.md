# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/render.py`); 1 carried an in-scope comment change (the new `_pct_of` docstring).

## R1 [CONCERN] "Used to be X" framing

File: `claude/.claude/scripts/transcript_analysis/render.py:85`

Issue: the added docstring reads `value/total as a percentage string; 0.0% (not an undefined dash) when total is zero.` The parenthetical "(not an undefined dash)" rules out an alternative that no code in the file implements. `Grep` for a `"-"` placeholder in `render.py` found none, and the `—` hits are all unrelated prose. It answers a question only a prior version, or a rejected design, would raise. A future reader who never saw that alternative has to guess what an "undefined dash" is.

Required property: state only the behavior that exists, with no disclaimer ruling out an absent mechanism. Suggested text: `"""value/total as a percentage string; 0.0% when total is zero."""`. The first clause restates the function's name and body, so the zero-total fact is the part worth keeping. It sits in `_pct_value` (line 92), which `_pct_of` delegates to, so a reader of `_pct_of` can't see it from this body alone.

Claim check (no finding): "0.0% when total is zero" is true. `_pct_value` returns `0.0` when `total` is falsy (`render.py:92`), and `_fmt_pct` formats it as `0.0%` (`render.py:81`).
