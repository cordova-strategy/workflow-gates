# comment-discipline-reviewer

Scope: 1 file in the diff (`review_rounds.py`), 1 added docstring in scope (`_pooled_compute_review_round_costs`). Read the surrounding region (lines 1047-1054, 1215-1291) at the diff's state.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/review_rounds.py:1286`

Offending text: `"""compute_review_round_costs, routed through _pooled_filtered_stderr_call.`

Issue: the one-line body at 1291 (`return _pooled_filtered_stderr_call(compute_review_round_costs, ...)`) and the function name already show this. Under the replacement "Don't restate the code" rule, a clause that static analysis of the repository finds is deleted, even if true.

Required property: delete this clause. It is not the subject of a kept decision. The decision sentence below it never refers to it, so nothing needs to keep it.

## R2 [CONCERN] Restating the code / misdirected pointer (one decision sentence, wrong home)

`claude/.claude/scripts/transcript_analysis/review_rounds.py:1288-1289`

Offending text: `--pooled must never print the resolved root count (see _pooled_resolved_scope_header).`

Issue:
- The sentence states a real decision, with a reason from outside the code. The root count is a per-account dimension that `--pooled` must not disclose. That part may stay.
- The pointer sends the reader to the wrong mechanism. `_pooled_resolved_scope_header` (1047-1054) covers the stdout header only. It never touches stderr.
- What this wrapper does is the stderr filter. `_SCANNING_ROOT_DIAGNOSTIC_RE` (1215) matches `scanning root N/M...` lines, which carry the root count. `_DECLARED_ROOT_DIAGNOSTIC_RE` (1221) matches lines whose index reveals the count's lower bound.
- A reader following the pointer finds the header builder, not the reason this call is wrapped.
- The root-count rationale already lives in `_pooled_resolved_scope_header`'s docstring. The stderr-side rationale lives at 1216-1220, in `_POOLED_STDERR_DIAGNOSTIC_RES` (1241-1250) and in `_pooled_filtered_stderr_call`.

Required property: keep one sentence, with the decision first and the pointer aimed at the stderr filter. For example: "Wrapped so --pooled never discloses the resolved root count through stderr diagnostics (see _POOLED_STDERR_DIAGNOSTIC_RES)."

Alternative: if one sentence cannot add anything beyond the existing homes, drop the docstring entirely. The function is a thin wrapper, and the decision is already documented at `_pooled_filtered_stderr_call` and `_POOLED_STDERR_DIAGNOSTIC_RES`.

Other angles for the proposed fix:
- It names what was decided and why, so it is not a restatement.
- It carries no PR-defined label.
- It makes no unsourced claim.
- It is one sentence.
