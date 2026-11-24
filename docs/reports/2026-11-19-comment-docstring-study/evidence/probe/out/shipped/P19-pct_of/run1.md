# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/render.py`); 1 carried an in-scope comment change (the new `_pct_of` docstring).

No findings. Checks run on the docstring:

- **Claim accuracy:** "0.0% when total is zero" holds. `_pct_value` returns `0.0` when `total` is falsy (render.py:92), and `_fmt_pct` formats that as `0.0%` (render.py:81).
- **Restating the code:** the zero-total behaviour lives in `_pct_value`, not in `_pct_of`'s one-line body, so the docstring states something the body doesn't show.
- **"Used to be X":** the "(not an undefined dash)" aside is not prior-version framing. Sibling modules still render a `"—"` on a zero total (e.g. `audit_routing.py:274`, `commit_gate.py:171`), so the contrast is live.
- **Multi-fact structure:** the sentence is a claim plus its tightly coupled contrast, which is the exempt pairing.
