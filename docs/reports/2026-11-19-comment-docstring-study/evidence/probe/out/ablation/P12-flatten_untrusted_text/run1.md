# comment-discipline-reviewer

Scope: 1 file in the diff (`claude/.claude/scripts/transcript_analysis/period_cost.py`), 1 carrying an in-scope change, the new docstring on `_flatten_untrusted_text` (lines 856-861). Nothing in the prompt was set aside. The docstring has three clauses, and each gets a finding under the rule that every docstring clause in the diff is reported as Prose restating the code.

## R1 [CONCERN] Prose restating the code

File: `claude/.claude/scripts/transcript_analysis/period_cost.py:856`

Issue: the summary line reads "Collapse every whitespace run (U+2028 and U+2029 included) to one space, then delete Cc and Cf characters." It describes `_strip_cc_cf(" ".join(text.split()))` and the function name. `str.split()` treating U+2028 and U+2029 as whitespace is standard-library behavior, so static analysis finds it.

Production failure mode: none. The comment adds reading load and can drift from the code.

Required property: delete the clause. If the ordering decision in R2 is kept, its sentence must name the collapse and strip it orders, so that sentence still names its subject.

## R2 [CONCERN] Prose restating the code

File: `claude/.claude/scripts/transcript_analysis/period_cost.py:858-859`

Issue: "The collapse runs first because \\n, \\t, and U+0085 are themselves Cc: stripping first would join the words around them." The reason rests on Unicode categories and `str.split` semantics. Both are standard-library facts, and the call order shows them.

Production failure mode: none.

Required property: delete the clause under the rule as written. This is the only clause that states a design decision with a reason, so the reviewer or author should decide whether it counts as a kept decision.

## R3 [CONCERN] Prose restating the code

File: `claude/.claude/scripts/transcript_analysis/period_cost.py:859-860`

Issue: "A deleted non-whitespace character can leave a doubled, leading, or trailing space, so the result is not idempotent." This is derivable by reading `" ".join(text.split())` followed by `_strip_cc_cf`. It is true: `"a \x01 b"` becomes `"a  b"`, and `"\x01 a"` becomes `" a"`. It is also pinned by the literal-result tests in `test_transcript_period_cost.py` (around lines 1775-1784).

Production failure mode: none.

Required property: delete the clause.
