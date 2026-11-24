# comment-discipline-reviewer

Scope: 1 file reviewed, 1 carrying an in-scope comment change (the new `_pct_of` docstring in `render.py`).

## R1 [CONCERN] "Used to be X" framing (implicit form)

`claude/.claude/scripts/transcript_analysis/render.py:85`

Text: `"""value/total as a percentage string; 0.0% (not an undefined dash) when total is zero."""`

Issue: the parenthetical "(not an undefined dash)" rules out an alternative rendering that nothing in the code shows. `render.py` has no dash placeholder (a grep for dash/em dash/`—` hits only this docstring). The only placeholder callers use is `"n/a"` (`cache_rebuild.py:626`, `:654`), and that sits at the call site, not in `_pct_of`. The aside therefore answers a question only a prior or alternative version raised, and a reader who has not seen that version cannot place it.

Verified true, so not a False-claim finding: `_pct_value` returns `0.0` when `total` is falsy (`render.py:92`), and `_fmt_pct` formats it as `0.0%` (`render.py:81`). The zero-total behavior lives in `_pct_value`, not in `_pct_of`'s body, so stating it is non-obvious and is not a Restating-the-code finding.

Required property: keep the zero-total fact, drop the ruled-out alternative. Compress to `value/total as a percentage string; 0.0% when total is zero.`
