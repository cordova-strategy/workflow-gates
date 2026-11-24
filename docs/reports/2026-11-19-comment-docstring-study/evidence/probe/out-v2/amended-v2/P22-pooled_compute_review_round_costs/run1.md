# comment-discipline-reviewer

Reviewed 1 file (`review_rounds.py`); 1 added docstring in scope (`_pooled_compute_review_round_costs`). Set aside: the dispatch's "Rule under test" bullet replaces CLAUDE.md's "Don't restate the code" bullet, as the prompt says. The `python-environment-conventions.md` system reminder does not touch this diff.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/review_rounds.py:1286` (added docstring, first line)

Issue: `"""compute_review_round_costs, routed through _pooled_filtered_stderr_call."""` repeats the one-line body, `return _pooled_filtered_stderr_call(compute_review_round_costs, ...)` (line 1291). It states no decision and no reason.

Required property: delete the sentence. Keep only the decision sentence from R2.

## R2 [CONCERN] False or unsourced claim (the docstring's pointer names the wrong holder of the reason)

`review_rounds.py:1288-1289`

Text: `--pooled must never print the resolved root count (see _pooled_resolved_scope_header).`

Issue: the constraint is a real decision and should stay. The pointer sends the reader to the wrong place:
- `_pooled_resolved_scope_header` (line 1047) is the stdout header. It exists because `scope.print_resolved_scope` discloses the root count (lines 1047-1053 and 1388-1389).
- This wrapper handles a different channel: stderr.
  - Evidence: `scanning root N/M...` is printed by scope's own scanning loop (comment at lines 1393-1396).
  - `_SCANNING_ROOT_DIAGNOSTIC_RE` and `_POOLED_STDERR_DIAGNOSTIC_RES` (lines 1215, 1246) are what drop it.
- A reader following the pointer finds a header builder that is never called on this path.
- The docstring also omits that the filter withholds any unrecognized stderr line (lines 1251-1257), not just the root-count line.
- The same reason already sits in the comment at the call site (lines 1393-1396). The docstring should point at the stderr filter, not repeat that comment or point at the header.

Required property: replace the whole docstring with one sentence naming the decision and the correct pointer. Suggested text:

`"""Filter stderr so --pooled never discloses the resolved root count ("scanning root N/M..."); see _POOLED_STDERR_DIAGNOSTIC_RES."""`

If you want the header cross-reference, add it as a second sentence, scoped to stdout: "The stdout header is handled by _pooled_resolved_scope_header."
