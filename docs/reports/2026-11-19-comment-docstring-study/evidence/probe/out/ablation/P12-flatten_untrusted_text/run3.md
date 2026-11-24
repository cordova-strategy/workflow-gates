# comment-discipline-reviewer

Text set aside: none. The session's replacement "Don't restate the code" bullet was applied as the Restating-the-code rule.

Scope: 1 file in the diff (`period_cost.py`), 1 added docstring on `_flatten_untrusted_text` (3 clauses) in scope.

## R1 [CONCERN] Prose restating the code

`claude/.claude/scripts/transcript_analysis/period_cost.py:856` (docstring first sentence)

Issue: "Collapse every whitespace run (U+2028 and U+2029 included) to one space, then delete Cc and Cf characters." This states what the one-line body shows: `" ".join(text.split())`, then `_strip_cc_cf`. The U+2028/U+2029 parenthetical is a stdlib fact about `str.split()`.

Production failure mode: the docstring has to be kept in sync with the body, and it adds no decision.

Required property: delete this clause.

## R2 [CONCERN] Prose restating the code

`claude/.claude/scripts/transcript_analysis/period_cost.py:858-859` (second docstring sentence)

Issue: "The collapse runs first because \\n, \\t, and U+0085 are themselves Cc: stripping first would join the words around them." The ordering is a real decision, but its reason is findable without leaving the repository and the standard library:
- `unicodedata.category` gives Cc for `\n`, `\t`, and U+0085.
- `str.split()` splits on all three.
- `_strip_cc_cf` at line 848-852 deletes Cc.

Under the session rule a reason that static analysis finds, even across several files, is deleted. The claim is true, so this is not a false-claim finding.

Production failure mode: the clause only restates what the code's order of operations already shows.

Required property: delete this clause.

## R3 [CONCERN] Prose restating the code

`claude/.claude/scripts/transcript_analysis/period_cost.py:859-860` (third docstring sentence)

Issue: "A deleted non-whitespace character can leave a doubled, leading, or trailing space, so the result is not idempotent." This is a consequence derived from the body, not a decision. For example, `"a ​ b"` flattens to `"a  b"`, and `"​ a"` flattens to `" a"`. Reading `split`/`join` followed by a delete shows both. The claim is true. A shorter or corrected restatement still restates, so tightening it would not fix it.

Production failure mode: none beyond drift. If a caller needs idempotence, a test is the durable place for it, and `TestFlattenUntrusted` already pins literal results.

Required property: delete this clause. With R1 and R2 gone, delete the whole docstring, leaving the one-line body.
