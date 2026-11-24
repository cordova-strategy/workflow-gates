# comment-discipline-reviewer

Reviewed 1 file (`render.py`); 1 added comment in scope (docstring on `_pct_of`). The claim is true, so there is no False-claim finding.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/render.py:85`

Offending text: `"""value/total as a percentage string; 0.0% (not an undefined dash) when total is zero."""`

Issue:
- The first clause restates the signature and body. `_pct_of(value, total) -> str` is `_fmt_pct(_pct_value(value, total))`, and `_fmt_pct` is `f"{pct:.1f}%"` (`render.py:80-81`).
- The zero-total clause restates `_pct_value`'s `if total else 0.0` (`render.py:92`). A reader finds it by following one call.
- The parenthetical "(not an undefined dash)" names a rejected alternative but gives no reason. It also answers a question only a prior or alternative rendering would raise. Nothing in the repository searched (`render.py`) shows a dash-rendering path.
- The docstring therefore states no decision with a reason that static analysis cannot find.

Production failure mode: none at runtime. The docstring duplicates `_pct_value`'s behavior, so it will go stale if the zero-total handling changes in `_pct_value` alone.

Required property: the docstring states only a decision with a reason.
- Preferred fix: delete the docstring.
- Alternative: if the maintainer chose 0.0% over a dash for a reason (for example a downstream consumer that cannot parse a dash), keep one sentence naming that decision and its reason. Example: "Zero total renders as 0.0% because <reason>." Add a pointer to where the reason lives.
- With no reason to cite, delete.
