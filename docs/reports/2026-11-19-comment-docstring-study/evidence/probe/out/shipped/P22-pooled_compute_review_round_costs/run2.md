# comment-discipline-reviewer

Reviewed 1 file (`review_rounds.py`); 1 carried an in-scope comment change (the new docstring on `_pooled_compute_review_round_costs`, lines 1286-1290 at the diff's state).

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/review_rounds.py:1286`

Issue: the docstring's first line, "compute_review_round_costs, routed through _pooled_filtered_stderr_call.", restates the one-line body `return _pooled_filtered_stderr_call(compute_review_round_costs, ...)`.

Failure mode: the line adds nothing the body doesn't show. It also drifts if the wrapper changes.

Required property: delete the line. Keep only the non-obvious why (see R2).

## R2 [CONCERN] False or unsourced claim (misdirecting cross-reference)

`claude/.claude/scripts/transcript_analysis/review_rounds.py:1288-1289`

Text: "--pooled must never print the resolved root count (see _pooled_resolved_scope_header)."

Issue: the rule is fine, but its pointer is wrong. `_pooled_resolved_scope_header` (line 1047) only builds the stdout header line and has no connection to stderr. The wrapper this function calls exists to filter stderr. The leak it closes is the `scanning root N/M...` line, matched by `_SCANNING_ROOT_DIAGNOSTIC_RE` (line 1215) and filtered via `_POOLED_STDERR_DIAGNOSTIC_RES` (line 1246). The call site's own comment (lines 1393-1396) says this. The docstring also says nothing about the other per-account diagnostics the wrapper handles: the declared-root unreadable line, which reveals a lower bound on the root count, and withholding any unrecognized line.

Failure mode: a maintainer who follows the "see" reference lands on the header builder and learns nothing about why this wrapper exists. They may conclude the wrapper is redundant and remove it, which would leak the root count on stderr.

Required property: the docstring names the right referent. For example: "Keeps per-account scan diagnostics, including the root count, off stderr under --pooled; see _POOLED_STDERR_DIAGNOSTIC_RES." Drop the `_pooled_resolved_scope_header` reference, or keep it only as a separate mention of the stdout side.

Net: once R1 and R2 are applied, the docstring is a single sentence.
