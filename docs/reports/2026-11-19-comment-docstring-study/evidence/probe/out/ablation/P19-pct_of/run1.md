# comment-discipline-reviewer

Scope note: the `python-environment-conventions.md` system reminder has no bearing on this review. I set it aside.

Reviewed 1 file (`transcript_analysis/render.py`). 1 comment change in scope: the new `_pct_of` docstring (diff line 8, file line 85).

## R1 [CONCERN] Prose restating the code

render.py:85, clause 1: `value/total as a percentage string`

- Issue: The function body `_fmt_pct(_pct_value(value, total))`, its name and its `-> str` signature already show this. The clause gives no decision and no reason.
- Production failure mode: None. The docstring only adds text to maintain.
- Required property: Delete the clause.

## R2 [CONCERN] Prose restating the code

render.py:85, clause 2: `0.0% (not an undefined dash) when total is zero`

- Issue:
  - The zero guard is `if total else 0.0` at render.py:92 in `_pct_value`. Static analysis of the repo finds it, and the tests that pin the zero-total output also find it (`test_transcript_cost.py:3187`, `test_author_outcome.py:2833`).
  - The clause records no reason. It does not say why the output is `0.0%` instead of a dash, and nothing outside the repo forces that choice.
  - The clause sits on `_pct_of`, but the guard lives in `_pct_value`.
- Production failure mode: If the guard in `_pct_value` changes, this docstring goes stale unnoticed.
- Required property:
  - Delete the clause, which leaves the docstring empty, so delete the docstring.
  - Add a decision comment only if a reason exists that code and tests cannot show, such as an external consumer that requires a numeric `0.0%`. Put that reason at `_pct_value`'s guard.

Prior decisions: none supplied.
