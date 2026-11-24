# comment-discipline-reviewer

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/render.py:85` (the added docstring on `_pct_of`).

Offending text: `"""value/total as a percentage string; 0.0% (not an undefined dash) when total is zero."""`

Issue: every clause is something static analysis of this repository finds.
- "value/total as a percentage string" restates the name, the signature (`-> str`) and the body (`_fmt_pct(_pct_value(value, total))`).
- "0.0% ... when total is zero" is stated by `_pct_value` at line 92 (`... if total else 0.0`) and by `_fmt_pct` at line 81 (`f"{pct:.1f}%"`).
- "(not an undefined dash)" names the alternative that was not chosen. It gives no reason static analysis cannot find, and no reason that something outside the repository forces it.

The claim is true: line 92 returns `0.0` for a zero total. Under the rule under test, a true restatement is still a restatement, and no decision is kept here because no reason accompanies it.

Required property: delete the docstring. Add a decision sentence only if there is a reason for 0.0% over a dash that the code cannot show, such as a downstream consumer or an external format requiring a number. That sentence would name the decision and give the reason. Do not shorten or correct the existing text, since a shorter restatement still restates.
