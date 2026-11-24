# comment-discipline-reviewer

Reviewed 1 file; 1 carried an in-scope comment change.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/render.py:85`

Issue: the added docstring `"""value/total as a percentage string; 0.0% (not an undefined dash) when total is zero."""` restates the code. "value/total as a percentage string" is what the name `_pct_of`, its signature and its `_fmt_pct(_pct_value(...))` body show. "0.0% ... when total is zero" is what `_pct_value` shows at line 92 (`return 100 * value / total if total else 0.0`) and `_fmt_pct` at line 81 (`f"{pct:.1f}%"`); it takes two functions to find but static analysis of this repository finds it. The one candidate decision, "not an undefined dash", names a rejected alternative but gives no reason static analysis cannot find, and no site in `render.py` renders a dash (grep for `"—"`, `"-"`, `n/a` returned no hits). It is true, and the rule still says delete: a true restatement is still a restatement.

Production failure mode: the comment duplicates `_pct_value`'s zero-total behavior, so the two drift apart if that behavior changes. The "dash" aside also refers to an alternative a reader of the current code never meets.

Required property: delete the docstring. If the zero-total policy is a deliberate decision, state it once, with its reason, on `_pct_value` (line 89), which owns the behavior. Keep the reason only if something outside the repository forces it or it is non-obvious. A pointer on `_pct_of` to `_pct_value` is the only acceptable addition here.
