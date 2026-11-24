# comment-discipline-reviewer

Set aside: the `python-environment-conventions.md` rule text that arrived mid-review. It is unrelated to this review and changes nothing in scope.

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/period_cost.py`). 1 carried a comment change in scope: the new docstring on `_flatten_untrusted_text`.

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/period_cost.py:856`

Offending text: `"""Collapse every whitespace run (U+2028 and U+2029 included) to one space, then delete Cc and Cf characters.`

Issue: The summary line narrates the body, `_strip_cc_cf(" ".join(text.split()))`. The call order and the helper name `_strip_cc_cf` already show "collapse whitespace, then delete Cc/Cf". CLAUDE.md §Durable text "Don't restate the code" says a shorter or corrected restatement still restates.

Verified against the code and tests:
- The remaining claims hold at the diff's state.
- `str.split()` with no argument splits on `\n`, `\t`, U+0085, U+2028 and U+2029, as `test_transcript_period_cost.py:1776-1783` pins.
- `_strip_cc_cf` (`period_cost.py:848-852`) keeps U+2028, as `test_transcript_period_cost.py:1769` shows.
- The doubled, leading and non-idempotent cases are pinned at `test_transcript_period_cost.py:1780-1781`.
- No False or unsourced claim finding applies.

Required property: Delete the summary sentence and open the docstring with the second paragraph. That paragraph carries the non-obvious facts: the collapse must run before the strip because `\n`, `\t` and U+0085 are Cc, and the result is not idempotent. If the U+2028/U+2029 point is worth keeping, it is non-obvious because those two are Zl/Zp and the strip alone would keep them. State it as its own short sentence, separate from the ordering rationale.
