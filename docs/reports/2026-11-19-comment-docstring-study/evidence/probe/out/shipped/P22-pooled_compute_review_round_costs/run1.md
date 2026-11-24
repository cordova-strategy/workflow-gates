# comment-discipline-reviewer

Reviewed 1 file (review_rounds.py); 1 added docstring in scope. Ignored: the system reminder on Python environment conventions, which bears on no angle in this review.

## R1 [CONCERN] Restating the code
- File:line: claude/.claude/scripts/transcript_analysis/review_rounds.py:1286 (diff lines 8-9)
- Issue: the first docstring line, "compute_review_round_costs, routed through _pooled_filtered_stderr_call.", restates the one-line body at line 1291, which calls `_pooled_filtered_stderr_call(compute_review_round_costs, ...)`. The function name and body already show it.
- Production failure mode: none at runtime. The line adds no information and would go stale if the wrapper changed.
- Required property: delete the restating line. Keep only the non-obvious fact, i.e. why this path must be filtered (see R2). If nothing non-obvious remains once R2 is applied, drop the docstring.

## R2 [CONCERN] False or unsourced claim (misdirected pointer)
- File:line: claude/.claude/scripts/transcript_analysis/review_rounds.py:1288-1289 (diff lines 10-11)
- Offending text: "--pooled must never print the resolved root count (see _pooled_resolved_scope_header)."
- Issue: the rule is fine, but the pointer is only partly supported. `_pooled_resolved_scope_header` (lines 1047-1054) explains why the stdout header is built locally instead of calling `scope.print_resolved_scope`. This wrapper filters stderr, not the header. The disclosure it guards against is the "scanning root N/M..." diagnostic, per `_SCANNING_ROOT_DIAGNOSTIC_RE` (line 1215) and the comment at lines 1393-1396. A reader who follows the pointer finds the wrong mechanism.
- Duplication: the call-site comment at lines 1393-1396 already states this reason, so the docstring restates a second home for it.
- Required property: if the docstring is kept, name the actual mechanism in one sentence. Example: "Filters stderr so scope's 'scanning root N/M...' lines don't disclose the root count under --pooled." Point at `_POOLED_STDERR_DIAGNOSTIC_RES` or `_pooled_filtered_stderr_call` rather than the header function. Otherwise delete the docstring and rely on the existing call-site comment.
