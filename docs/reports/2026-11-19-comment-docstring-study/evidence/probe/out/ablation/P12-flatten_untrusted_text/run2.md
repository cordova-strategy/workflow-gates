# comment-discipline-reviewer

Reviewed 1 file (period_cost.py); 1 docstring in scope (`_flatten_untrusted_text`). No prompt text was set aside.

## R1 [CONCERN] Prose restating the code

period_cost.py:856 (diff line 8)

Issue: The summary clause "Collapse every whitespace run (U+2028 and U+2029 included) to one space, then delete Cc and Cf characters." restates the body `_strip_cc_cf(" ".join(text.split()))`. The U+2028/U+2029 parenthetical is a standard-library fact: `str.split()` with no argument splits on them.

Production failure mode: None. The clause drifts from the code if the body changes, and a reader gets it from the body.

Required property: Delete the clause as a standalone summary. Its subject (the collapse and the Cc/Cf deletion) stays only inside the kept ordering-decision sentence, so that sentence still names what it explains. Suggested whole docstring: "Whitespace collapse runs before the Cc/Cf deletion because \\n, \\t, and U+0085 are themselves Cc: stripping first would join the words around them." The sentence is the only non-obvious decision here. It names what was decided and why the order matters.

## R2 [CONCERN] Prose restating the code

period_cost.py:859-860 (diff lines 11-12)

Issue: "A deleted non-whitespace character can leave a doubled, leading, or trailing space, so the result is not idempotent." This follows from reading the body: the collapse precedes the deletion, so a deletion after it can leave adjacent or edge spaces. It is a static-analysis fact about this repository's code and the standard library. It is not a design decision and not a constraint from outside the repository.

Production failure mode: None. The statement is true today, but it states how the code behaves, not why it is built this way.

Required property: Delete the sentence. If a caller ever depends on idempotence, that belongs in the caller's own decision comment.

## Answers

No questions were posed. No other site in the diff carries a comment or doc change.
