# comment-discipline-reviewer

Scope: 1 file in the diff (`period_cost.py`), 1 comment-discipline site (the new `_flatten_untrusted_text` docstring). No prior decisions were handed over, and no prompt text was set aside.

## R1 [CONCERN] False or unsourced claim

`claude/.claude/scripts/transcript_analysis/period_cost.py:856`

Issue: the docstring says "Collapse every whitespace run (U+2028 and U+2029 included) to one space". The subject, line 862 (`" ".join(text.split())`), does not do that for every run. `str.split()` with no argument discards leading and trailing whitespace runs entirely, so those runs become zero spaces, not one. Input `"  a  "` yields `"a"`. Only interior runs collapse to one space.

The later sentence ("can leave a doubled, leading, or trailing space") is accurate. It also shows that the author's model is that whitespace-derived edges are already gone.

Production failure mode: a reader relies on "every run → one space" and expects a leading or trailing space from whitespace-only edges. Line 1520 (`_flatten_untrusted_text(model_id) or _NO_MODEL_FIELD_LABEL`) depends on all-whitespace input becoming `""`, which the docstring wording does not support.

Required property: state the narrowest claim the code supports. Interior whitespace runs collapse to one space, and leading and trailing whitespace is dropped.

## R2 [FYI] Restating the code

`claude/.claude/scripts/transcript_analysis/period_cost.py:856`

Issue: the summary line ("Collapse … whitespace … then delete Cc and Cf characters") restates what `" ".join(text.split())` and `_strip_cc_cf(...)` show on line 862. `_strip_cc_cf`'s own comment (lines 849-851) already says what Cc and Cf are.

Required property: keep only the non-obvious facts:
- `str.split()` treats U+2028 and U+2029 as whitespace.
- Collapse-before-strip ordering matters, because \n, \t and U+0085 are Cc.
- The result is not idempotent.

The second paragraph already carries the last two. If you apply R1's fix, avoid writing a corrected restatement of the code.

Checked and fine: the Cc claim for \n, \t and U+0085, the "stripping first would join the words" claim, and the doubled, leading and trailing space and non-idempotence claim (for example, `"a ​ b"` → `"a  b"`).
