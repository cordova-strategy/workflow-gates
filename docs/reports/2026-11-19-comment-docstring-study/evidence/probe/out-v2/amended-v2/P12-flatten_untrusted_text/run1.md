# comment-discipline-reviewer

Reviewed 1 file (`period_cost.py`); 1 carried an in-scope change (the new `_flatten_untrusted_text` docstring, diff lines 8-13). The surrounding code was read in the snapshot (`period_cost.py:848-862`).

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/period_cost.py:856` (docstring first sentence)

Text: "Collapse every whitespace run (U+2028 and U+2029 included) to one space, then delete Cc and Cf characters."

Issue: This sentence states the body `_strip_cc_cf(" ".join(text.split()))` and what `str.split()` does, including its U+2028/U+2029 handling. Static analysis of the code and the standard library finds all of it, and the rule deletes such a clause even when it is true. The name and the call chain already show the two steps.

Production failure mode: none. The cost is a docstring that duplicates the code and will drift from it.

Required property: delete the sentence. The ordering decision it introduces survives in R2's rewrite, which names what was decided.

## R2 [FYI] Restating the code

`period_cost.py:860` (docstring third sentence)

Text: "A deleted non-whitespace character can leave a doubled, leading, or trailing space, so the result is not idempotent."

Issue: This is a consequence of the chosen order, and reading the two-step body shows it. I checked that it is true, for example `"a ​ b"` gives `"a  b"`. It is not a decision, and it gives no external constraint or revisit trigger. Under the rule it is restated detail, and the test file already pins this behaviour.

Required property: delete it. Keep it only if a caller actually relies on non-idempotence, and then state that caller-facing consequence as the decision.

## R3 [FYI] Kept decision: the ordering reason

`period_cost.py:858-859` (second sentence). The ordering decision and its reason ("\n, \t, and U+0085 are themselves Cc: stripping first would join the words around them") are the one non-obvious decision in the docstring. The claim holds: `\n` and `\t` are category Cc, and U+0085 is Cc and whitespace to `str.split`. Keep it, naming the decision.

Suggested replacement for the whole docstring:

```python
"""Collapse whitespace before stripping Cc and Cf, because \\n, \\t, and U+0085 are themselves Cc and stripping first would join the words around them."""
```

(Wrap to the file's line width as needed.)

The replacement keeps the decision and its reason, adds no further angle's violation, and deletes the two restating clauses.
