# comment-discipline-reviewer

Set aside: none. The rule-under-test bullet replaces CLAUDE.md's "Don't restate the code" bullet, and I applied it.

## R1 [CONCERN] Prose restating the code

render.py:85 (`_pct_of` docstring), clause "value/total as a percentage string".

Issue: The function name `_pct_of`, its `(value, total)` signature, its `-> str` return type and its body `_fmt_pct(_pct_value(value, total))` already show this. The clause names no decision and gives no reason.

Production failure mode: none. The cost is a comment that has to be kept in sync with the code.

Required property: delete the clause.

## R2 [CONCERN] Prose restating the code

render.py:85 (`_pct_of` docstring), clause "0.0% (not an undefined dash) when total is zero".

Issue: Static analysis of this repository finds this in one hop. `_pct_value` at render.py:92 returns `0.0` when `total` is falsy, and `_fmt_pct` at render.py:81 formats that as `0.0%`. The claim is true (render.py:81, 92), but the rule deletes a clause even when it is true and takes several files to find. The "(not an undefined dash)" aside rules out an alternative and gives no reason an outside constraint forces. No kept decision sentence remains for it to sit inside.

Production failure mode: none. The zero-total behavior is already visible in `_pct_value`.

Required property: delete the clause. The docstring is then empty, so remove it entirely. If the zero-total fallback has a non-obvious reason, such as an outside consumer that requires `0.0%`, state that reason. The reason must be one static analysis cannot find. It belongs on `_pct_value`, where the branch lives.
