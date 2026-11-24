# comment-discipline-reviewer

Scope note: reviewed 1 file (`review_rounds.py`), 1 added docstring in scope. No prompt text was set aside.

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/review_rounds.py`, added docstring at diff lines 8-12 (file lines 1286-1290).

Issue: The first line, `compute_review_round_costs, routed through _pooled_filtered_stderr_call.`, restates the one-line body at line 1291. The function name and the `return _pooled_filtered_stderr_call(compute_review_round_costs, ...)` already show it. Under the session's "Don't restate the code" rule, a clause that static analysis of the repository finds gets deleted. The second sentence is the only decision here: `--pooled` must never print the resolved root count.

The second sentence names the wrong pointer. `_pooled_resolved_scope_header` is the sibling mechanism, which builds the header locally (lines 1047-1053). The reason this wrapper exists is that scope's `scanning root N/M...` stderr print discloses the root count. That reason lives in the call-site comment at lines 1393-1396, and the test docstring at test_transcript_review_rounds.py:6213-6218 also explains it. A reader following the pointer lands on a different leak, not this wrapper's reason.

Required property: The docstring states only the decision and points to where its reason lives.

Concrete fix: Delete the first line and keep one sentence that names its subject:

```python
"""Wrapper that keeps --pooled from disclosing the resolved root count on stderr.

See the --pooled branch in cmd_review_round_cost for why.
"""
```

If you prefer to keep the existing pointer, change only the first line, deleting the restatement:

```python
"""--pooled must never print the resolved root count (see _pooled_resolved_scope_header)."""
```

The first option is better because it points at the reason for this wrapper. Both options satisfy the other angles. Each is a single fact, so there is no verbosity or multi-fact problem, and no PR-defined label or "used to be" framing is introduced.

No other angle applies. The claim "must never print the root count" is a rule, not a settleable claim.
