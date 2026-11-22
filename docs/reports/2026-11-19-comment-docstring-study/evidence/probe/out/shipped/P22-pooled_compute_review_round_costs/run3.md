# comment-discipline-reviewer

Scope: 1 file in the diff (`review_rounds.py`), 1 added docstring on `_pooled_compute_review_round_costs`. No prompt text was set aside.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/review_rounds.py:1286` (the added docstring's first line).

Issue: "compute_review_round_costs, routed through _pooled_filtered_stderr_call." only paraphrases the one-line body, `return _pooled_filtered_stderr_call(compute_review_round_costs, ...)`. The body, the function name and its signature already show this.

Production failure mode: none at runtime. The cost is a docstring that duplicates the code, which §Durable text's "Don't restate the code" bullet says to delete outright.

Required property: delete that first line. Do not shorten or correct it.

## R2 [CONCERN] False or unsourced claim (misdirected cross-reference), with a duplication element

`review_rounds.py:1288-1289`: "--pooled must never print the resolved root count (see _pooled_resolved_scope_header)."

Issue:
- The rule is fine, but the pointer sends the reader to the wrong source.
  - `_pooled_resolved_scope_header` (`review_rounds.py:1047-1054`) concerns the stdout header and replacing `scope.print_resolved_scope`.
  - This wrapper protects the stderr stream. It filters `scope`'s "scanning root N/M..." line and the declared-root warning (`review_rounds.py:1215-1221`, `1246-1250`).
  - A reader following "see" learns nothing about why this wrapper exists.
- The stderr rationale already sits at the call site, `review_rounds.py:1393-1396`, and above `_DECLARED_ROOT_DIAGNOSTIC_RE` (`review_rounds.py:1216-1220`). The docstring restates it with the wrong referent, which breaks single-source-of-truth.

Required property: if the docstring stays, state the non-obvious fact as its own sentence and point at the stderr mechanism.
- Example: "Under --pooled, scope's stderr diagnostics (e.g. "scanning root N/M...") would disclose the resolved root count; see _POOLED_STDERR_DIAGNOSTIC_RES."
- Drop the `_pooled_resolved_scope_header` reference.
- Otherwise delete the whole docstring and rely on the call-site comment at 1393-1396.

Together with R1, the narrowest result is a one-sentence docstring (the R2 example) with no restatement line.
