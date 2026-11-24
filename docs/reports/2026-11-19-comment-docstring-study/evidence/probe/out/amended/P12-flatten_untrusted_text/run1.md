# comment-discipline-reviewer

Scope: 1 file reviewed (`period_cost.py`), 1 carrying an in-scope change (new docstring on `_flatten_untrusted_text`). No prompt text was set aside.

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/period_cost.py:856` (diff line 8).

Issue: the first docstring sentence is "Collapse every whitespace run (U+2028 and U+2029 included) to one space, then delete Cc and Cf characters." It restates `" ".join(text.split())` and `_strip_cc_cf(...)`. The U+2028/U+2029 parenthetical is `str.split` behavior, which the standard library defines. The Cc/Cf set is already stated at `_strip_cc_cf` (lines 849-851).

Production failure mode: the sentence adds no decision or reason. It drifts silently if either step changes.

Required property: delete the sentence. Keep its subject (the collapse and the strip) inside the surviving ordering-decision sentence (see R2), so the reason still names what it explains.

## R2 [CONCERN] Restating the code

File: `period_cost.py:860-861` (diff lines 11-12).

Issue: "A deleted non-whitespace character can leave a doubled, leading, or trailing space, so the result is not idempotent." This describes what the two-step code produces. Reading the code and the Cc/Cf definition finds it. It is a consequence, not a design decision with an outside-the-repo reason. A shorter or corrected version would still restate.

Production failure mode: none beyond drift. The claim is true as written, so no False-claim finding.

Required property: delete the sentence.

## Kept

The second sentence ("The collapse runs first because \n, \t, and U+0085 are themselves Cc: stripping first would join the words around them") is a kept ordering decision with its reason. After R1 and R2 the docstring should be this sentence alone, so that it names the subject: for example, "Collapse whitespace before stripping Cc/Cf, because whitespace such as \n is itself Cc and stripping first would join the neighbouring words."

I checked that claim against the code and the standard library, and it holds. \n, \t, and U+0085 are all Cc and all split by `str.split`. U+2028 and U+2029 are split too. The diff has no PR-defined terminology, "used to be X" framing, wrong-altitude content, or unsourced claims.
