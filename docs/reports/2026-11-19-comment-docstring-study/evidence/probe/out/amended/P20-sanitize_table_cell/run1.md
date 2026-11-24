# comment-discipline-reviewer

## R1 [CONCERN] Restating the code

File: claude/.claude/scripts/transcript_analysis/render.py:130

Issue: the added docstring `"""Strip ASCII control characters from a --deny-summary table cell value."""` restates what static analysis already shows. The function name says it sanitizes a table cell, and `_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")` (line 126) plus `.sub("", value)` show it strips ASCII control characters. The docstring gives no reason the code cannot show, such as why stripping is needed or what outside the repo forces it.

The docstring is also inaccurate, so a corrected version would still restate. It scopes the helper to `--deny-summary`, but the function is called from many other surfaces:
- redaction.py:246
- review_rounds.py:1436
- subagent_mix.py:254, 266, 550, 570
- subagents.py:185, 225

Of these, only the review_trace.py calls (lines 78–134) belong to `--deny-summary`. A reader trusting the docstring would wrongly treat the helper as private to that report.

Required property: delete the docstring. Keep a comment only if the author adds a real decision, such as why control characters must not reach table output, with a reason that no file in the repo shows. A shorter or corrected restatement still restates.

## Notes

- Set aside: the `python-environment-conventions.md` rules reminder that arrived mid-session. It has no bearing on comment-discipline review.
- Files reviewed: 1; in scope: 1 (one added docstring).
