# comment-discipline-reviewer

Scope: 1 file in the diff (`period_cost.py`), 1 docstring added (`_flatten_untrusted_text`). Rule applied: the session's replacement "Don't restate the code" bullet.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/period_cost.py:856` (docstring first sentence)

Text: "Collapse every whitespace run (U+2028 and U+2029 included) to one space, then delete Cc and Cf characters."

Issue: the sentence re-describes the one-line body, `_strip_cc_cf(" ".join(text.split()))`. It also repeats what `TestFlattenUntrustedText` pins (`line_and_paragraph_separators_collapse`, `format_character_deleted`). The "U+2028 and U+2029 included" aside is a standard-library fact about `str.split`. It states no decision and gives no reason.

Required property: delete the sentence. Its ordering content survives in R1's replacement, which is also the fix for R2.

Suggested docstring in full, replacing all three lines of prose:

```
"""Collapse whitespace before stripping Cc and Cf: \\n, \\t, and U+0085 are themselves Cc, so stripping first would join the words around them."""
```

This keeps the one non-obvious decision (the ordering) and its reason. The sentence names what it decides, so it is not a restatement. It is a single cause-and-effect pair, so it passes Multi-fact structure. If it exceeds the line limit, wrap it across two lines.

## R2 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/period_cost.py:858-860` (docstring second sentence)

Text: "A deleted non-whitespace character can leave a doubled, leading, or trailing space, so the result is not idempotent."

Issue: this describes behavior that follows from the two-step body. Tests pin it (`deleting_a_format_character_can_leave_a_doubled_space`, `deleting_a_leading_format_character_can_leave_a_leading_space`). It records no decision, and no reason or revisit trigger is stated. Under the rule, a consequence found by reading the code and tests is deleted even when true.

I checked the claim. `"a ​ b"` flattens to `"a  b"`, and a second pass gives `"a b"`, so it is true (test lines 1780-1781). Truth does not save it.

Required property: delete the sentence. This is not a False or unsourced claim finding. If a caller really depends on the output being already normalized, that is a separate decision. State it as a decision with a reason, for example at the call site, not as a restated behavior note here.

## Checked and clean

- The "collapse first" rationale is kept in R1's replacement. It is a why-it-is-this-way reason. The test id `newline_collapses_before_the_strip` names the ordering but not its reason.
- Claims in the docstring are true: `str.split()` treats U+2028, U+2029, and U+0085 as whitespace, and U+0085, `\n`, and `\t` are Cc.
- No PR-defined terminology, no prior-version framing, no tracker IDs, and no restated canonical rule in the diff.
- The pre-existing `_strip_cc_cf` comment is not in the diff and is out of scope.
