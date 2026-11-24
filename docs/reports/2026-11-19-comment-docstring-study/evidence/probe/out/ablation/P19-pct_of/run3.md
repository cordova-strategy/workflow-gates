# comment-discipline-reviewer

Prompt text set aside: none. The prompt's replacement "Don't restate the code" bullet was applied for the Prose restating the code angle.

## R1 [CONCERN] Prose restating the code

File:line: `claude/.claude/scripts/transcript_analysis/render.py:85` (the added docstring, diff line 8).

Issue: the docstring is `"""value/total as a percentage string; 0.0% (not an undefined dash) when total is zero."""`. It has three clauses, and each is a restatement.
- "value/total as a percentage string" repeats the name `_pct_of`, the `value`/`total` signature, and the `-> str` return type. The body shows it is `_fmt_pct(_pct_value(value, total))`.
- "0.0% ... when total is zero" is found by reading `_pct_value`. It returns `100 * value / total if total else 0.0` at `render.py:92`, and `_fmt_pct` formats it as `f"{pct:.1f}%"` at `render.py:81`. The behavior sits one call away, which the replacement rule counts as findable.
- "(not an undefined dash)" names a rejected alternative but gives no reason for the choice. No outside constraint forces it, and no design decision is left once the two restated clauses are removed.

Production failure mode: the docstring doubles the description of `_pct_value`'s zero-guard. If that guard changes, for example to return a dash, this docstring goes stale without anyone noticing.

Required property: delete the whole docstring. Nothing needs to stay, because no clause gives a reason static analysis cannot find. A shorter or corrected version would still restate the code.
