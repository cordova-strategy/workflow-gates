# comment-discipline-reviewer

Reviewed 1 file (`period_cost.py`); 1 carried an in-scope comment change (the new `_flatten_untrusted_text` docstring, lines 856-861). Rule under test: the session's replacement "Don't restate the code" bullet.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/period_cost.py:856`

Issue: the opening sentence "Collapse every whitespace run (U+2028 and U+2029 included) to one space, then delete Cc and Cf characters." restates the body `_strip_cc_cf(" ".join(text.split()))`. The "U+2028 and U+2029 included" parenthetical is a stdlib fact about `str.split`, and the Cc/Cf set is already explained at `_strip_cc_cf` (lines 849-851). It states no decision and gives no reason.

Why it fails: the rule deletes anything that static analysis of this repo or the standard library finds, even if true.

Required property: delete the sentence. Keep only the ordering decision in the next sentence (see the fix under R2).

## R2 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/period_cost.py:859-860`

Issue: "A deleted non-whitespace character can leave a doubled, leading, or trailing space, so the result is not idempotent." This is a consequence of the call order. A reader finds it by tracing `split`/`join` and then `_strip_cc_cf`, and `TestFlattenUntrustedText` pins the literal results. It is true: `"a ​ b"` gives `"a  b"`. It states no decision and no reason, and it names no caller trigger.

Why it fails: it is derivable detail, not a design decision. The rule says to keep a decision with a reason and delete the rest.

Required property: delete the sentence. The docstring then keeps only the ordering decision (lines 858-859), which is true and not derivable. `\n`, `\t`, and U+0085 are Cc, and `str.split` splits on them. Replacement text, naming what is decided:

```python
"""Collapse whitespace before deleting Cc and Cf characters, because \\n, \\t, and U+0085 are themselves Cc and deleting first would join the words around them."""
```

(Keep it to the one sentence. If it wraps, a wrapped single-sentence docstring is fine under the line cap.)

Prior decisions: none supplied.
