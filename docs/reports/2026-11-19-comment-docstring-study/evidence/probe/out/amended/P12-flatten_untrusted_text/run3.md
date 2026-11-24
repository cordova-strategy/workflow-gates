# comment-discipline-reviewer

Reviewed 1 diff file (`period_cost.py`); 1 docstring added, `_flatten_untrusted_text`. No text from the prompt was set aside.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/period_cost.py:856`

Issue: the first sentence, "Collapse every whitespace run (U+2028 and U+2029 included) to one space, then delete Cc and Cf characters.", describes `" ".join(text.split())` followed by `_strip_cc_cf(...)`. Reading the one-line body shows this. The U+2028/U+2029 inclusion is `str.split()`'s standard-library behavior, and `TestFlattenUntrustedText` pins it (`test_transcript_period_cost.py:1777`). The Cc/Cf set is already stated on `_strip_cc_cf` (`period_cost.py:849`).

Production failure mode: none. The sentence will drift from the body if the body changes, and it holds no decision.

Required property: delete the sentence. The ordering sentence (second) is the kept decision. Keep its subject inside it, e.g. "Whitespace collapses before the Cc/Cf deletion because \\n, \\t, and U+0085 are themselves Cc: stripping first would join the words around them." That way the reason still names what it explains.

## R2 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/period_cost.py:859-860`

Issue: "A deleted non-whitespace character can leave a doubled, leading, or trailing space, so the result is not idempotent." This follows from the code's order of operations: deletion runs after the collapse, so it can reopen spaces. The tests already pin each case (`deleting_a_format_character_can_leave_a_doubled_space`, `..._leading_space`, `test_transcript_period_cost.py:1780-1781`). It is a consequence of the code, not a decision with a reason static analysis can't find. The rule says to delete anything that analysis of this repository's code and tests finds, even when true.

Production failure mode: none. The sentence also adds a third fact and a trailing clause to the docstring.

Required property: delete the sentence. Any caller that needs idempotence can see that from the body and the tests.
