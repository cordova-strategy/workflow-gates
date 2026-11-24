# comment-discipline-reviewer

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/render.py:85` (added docstring on `_pct_of`).

Text: `"""value/total as a percentage string; 0.0% (not an undefined dash) when total is zero."""`

Issue: Every clause restates what the code shows.
- "value/total as a percentage string" restates the name, the `str` return type and the `_fmt_pct(_pct_value(value, total))` body.
- "0.0% when total is zero" restates `_pct_value`'s `if total else 0.0` (line 92) and `_fmt_pct`'s `:.1f%` format (line 81). A reader finds both by reading the two helpers in this file.
- "(not an undefined dash)" states what was decided but gives no reason static analysis cannot find, so it is not a kept decision. Nothing in the repository the comment names forces a dash, so it also rules out an alternative only a prior or imagined version raised.

Production failure mode: The docstring duplicates `_pct_value`'s zero-total behavior. If that behavior changes, this copy goes stale and misleads.

Required property: Delete the docstring.

Keep a clause only if the author can state why zero total must render as `0.0%` rather than a placeholder, for example a downstream consumer that parses the cell as a number. In that case, write that reason in one sentence.
