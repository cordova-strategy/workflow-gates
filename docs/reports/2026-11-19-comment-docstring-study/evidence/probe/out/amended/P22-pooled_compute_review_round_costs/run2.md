# comment-discipline-reviewer

Reviewed 1 file (`review_rounds.py`); 1 added docstring in scope (`_pooled_compute_review_round_costs`). No prompt text was set aside.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/review_rounds.py:1286`

Issue: the docstring's first line, "compute_review_round_costs, routed through _pooled_filtered_stderr_call.", restates the one-line body at line 1291 (`return _pooled_filtered_stderr_call(compute_review_round_costs, ...)`). Static analysis of the function finds it, and it records no decision.

Production failure mode: none at runtime. The line only adds a second place to keep in sync with the body.

Required property: delete the line. The reason the wrapper exists is already kept at the call site, lines 1393-1396 ("scope's own 'scanning root N/M...' print would otherwise disclose the resolved root count on stderr"). The cleanest fix is to delete the whole docstring so that site stays the single home (§Engineering Judgment, single source of truth). If a docstring stays, it should be one pointer sentence, for example "Pooled wrapper: see _pooled_filtered_stderr_call and _POOLED_STDERR_DIAGNOSTIC_RES for why stderr is filtered." It must not repeat the body.

## R2 [CONCERN] False or unsourced claim

`claude/.claude/scripts/transcript_analysis/review_rounds.py:1288-1289`

Text: "--pooled must never print the resolved root count (see _pooled_resolved_scope_header)."

Issue: the claim and its pointer are only partly supported by the subject they name.
- `_pooled_resolved_scope_header` (lines 1047-1054) only builds the stdout header line. It replaces `scope.print_resolved_scope`, whose root-count clause the docstring at 1049-1052 says is unconditional. It has no connection to this wrapper.
- This wrapper acts only on stderr, through `_pooled_filtered_stderr_call` (lines 1260-1282). The root-count leak it closes is the "scanning root N/M..." line, matched by `_SCANNING_ROOT_DIAGNOSTIC_RE` at line 1215 and dropped via `_POOLED_STDERR_DIAGNOSTIC_RES` at lines 1246-1250.
- The filter also drops the routine non-contiguous-merge notice (line 1249), which is unrelated to root count. It also withholds every unrecognized line (lines 1278-1281).
- The "see" pointer therefore sends a reader to the header function, which does not hold the reason this wrapper exists. The home for that reason is lines 1393-1396 and the `_SCANNING_ROOT_DIAGNOSTIC_RE` comment.

Production failure mode: a maintainer reads this docstring, concludes the wrapper only guards the root count and that the header function is its counterpart, and so may drop or loosen the other filter rules or mis-edit the header.

Required property: delete the claim along with R1's line. If a pointer is kept, aim it at `_POOLED_STDERR_DIAGNOSTIC_RES` or `_pooled_filtered_stderr_call`, which hold the stderr-filter decision. It must not claim "never print the resolved root count" as this function's sole purpose.

Prior decisions: none supplied.
