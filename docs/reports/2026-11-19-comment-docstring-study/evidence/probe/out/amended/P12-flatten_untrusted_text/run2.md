# comment-discipline-reviewer

Reviewed 1 file (`period_cost.py`), 1 carrying an in-scope comment change (the new `_flatten_untrusted_text` docstring, diff lines 8-13). No prompt text was set aside.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/period_cost.py:856`

Issue: the first sentence, "Collapse every whitespace run (U+2028 and U+2029 included) to one space, then delete Cc and Cf characters.", narrates `_strip_cc_cf(" ".join(text.split()))`. The "U+2028 and U+2029 included" aside restates what `str.split` does, which the standard library defines. The `_strip_cc_cf` body and its test (`test_drops_control_and_format_characters_and_keeps_everything_else`, which keeps ` `) already show the Cc/Cf deletion.

Production failure mode: none at runtime. The docstring grows a second copy of the code that can drift from it.

Required property: delete the sentence. Keep its subject (the collapse-then-strip order) inside the decision sentence, so the reason still names what it explains. For example: "Collapse whitespace before stripping Cc and Cf, because some whitespace (\\n, \\t, U+0085) is itself Cc and stripping first would join the words around it." That sentence carries the one non-obvious design decision, the ordering and its reason, so it stays.

## R2 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/period_cost.py:859-860`

Issue: "A deleted non-whitespace character can leave a doubled, leading, or trailing space, so the result is not idempotent." This is a consequence read straight off the two-step expression. Static analysis of the code and its tests finds it. I checked that it is true (`"a ​ b"` flattens to `"a  b"`), but a true restatement is still a restatement. It records no decision and no outside constraint, and a caller would find it by reading the function.

Production failure mode: none at runtime. The docstring carries a derivable behavior note that must be kept in sync with the code.

Required property: delete the sentence. If the non-idempotence matters to a caller, pin it in a test, not in prose.
