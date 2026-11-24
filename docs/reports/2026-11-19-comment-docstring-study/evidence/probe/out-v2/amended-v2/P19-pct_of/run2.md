# comment-discipline-reviewer

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/render.py:85` (the only added line; 1 file reviewed, 1 carries an in-scope comment change).

Offending text: `"""value/total as a percentage string; 0.0% (not an undefined dash) when total is zero."""`

Issue: every clause restates what static analysis of this repository finds.
- "value/total as a percentage string" restates the name `_pct_of`, its signature and its return type `str`.
- "0.0% ... when total is zero" restates `_pct_value` at line 92 (`100 * value / total if total else 0.0`), which `_pct_of` calls, and `_fmt_pct` at line 81 (`f"{pct:.1f}%"`). It takes two functions to find, but the rule deletes it even when it is true and spans several files.
- "(not an undefined dash)" names a rejected alternative but states no reason for the choice, and the diff offers no pointer to where a reason lives.

I read the repository and found the claim true, so this is not a False or unsourced claim finding. The docstring does not survive the "Don't restate the code" rule, and a shorter or corrected version would still restate.

Production failure mode: the docstring duplicates the zero-total behavior in `_pct_value`. If that fallback changes, this text silently goes stale.

Required property: delete the docstring. Keep a sentence only if the author can state why a zero total renders `0.0%` instead of a dash. In that case the sentence names the decision and gives the reason, for example "Zero total renders 0.0% because <reason>."
