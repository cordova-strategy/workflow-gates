# comment-discipline-reviewer

Reviewed 1 file (`render.py`); 1 added docstring in scope (`_pct_of`).

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/render.py:85`

Text: `"""value/total as a percentage string; 0.0% (not an undefined dash) when total is zero."""`

Issue: Every clause restates what static analysis finds.
- "value/total as a percentage string" restates the name `_pct_of` and its one-line body `_fmt_pct(_pct_value(...))`.
- "0.0% ... when total is zero" restates `100 * value / total if total else 0.0` at line 92 and `f"{pct:.1f}%"` at line 81.
- "(not an undefined dash)" names a rejected alternative but gives no reason for it.

The alternative is real: `audit_routing.py:274`, `:281`, `:550` and `commit_gate.py:171` render `"—"` for a zero denominator, and `cache_rebuild.py:626` renders `"n/a"`. Nothing in the repository states why `_pct_of` differs. The rule keeps a decision only with a reason or a pointer to one. Neither exists here, so the decision half has nothing to keep.

The claim is true, so this is not a False-claim finding. I read `render.py:80-92` and confirmed `_pct_value` returns `0.0` when `total` is falsy, which `_fmt_pct` renders as `0.0%`.

Required property: delete the docstring. If the author wants the choice kept, they must supply the reason, for example: "Zero total renders 0.0% rather than the dash `audit_routing.py` uses, because <reason>." Without a reason, delete.

Check against other angles: the deletion leaves no prose, so it creates no violation under any other angle.
