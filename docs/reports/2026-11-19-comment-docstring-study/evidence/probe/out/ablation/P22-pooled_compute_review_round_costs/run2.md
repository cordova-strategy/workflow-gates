# comment-discipline-reviewer

Reviewed 1 file (`review_rounds.py`); it carries one in-scope change, the new docstring on `_pooled_compute_review_round_costs`. No prompt text was set aside. The rule-under-test bullet replaces CLAUDE.md's "Don't restate the code" bullet, and I applied the agent file's per-clause docstring rule on top of it.

## R1 [CONCERN] Prose restating the code

File: `claude/.claude/scripts/transcript_analysis/review_rounds.py:1286` (diff lines +8)

Issue: The docstring's first clause is "compute_review_round_costs, routed through _pooled_filtered_stderr_call." The body at line 1291 is `return _pooled_filtered_stderr_call(compute_review_round_costs, *args, **kwargs)`, so the clause only restates the call.

Production failure mode: None at runtime. The clause adds noise and will go stale if the routing changes.

Required property: Delete the clause. It is a docstring clause and states nothing static analysis cannot find. The function name `_pooled_compute_review_round_costs` and its one-line body already show it.

## R2 [CONCERN] Prose restating the code

File: `claude/.claude/scripts/transcript_analysis/review_rounds.py:1288-1289` (diff lines +10-+11)

Issue: The second clause is "--pooled must never print the resolved root count (see _pooled_resolved_scope_header)." This is the only docstring clause that carries a policy reason. The same reason is already stated, with the same pointer, at the `scope.print_resolved_scope` call site (line 1388-1389) and at the `resolve_scan_roots` site (about line 1359-1360).

Production failure mode: None at runtime. The same fact now lives in three places, which is a single-source-of-truth risk if the policy changes.

Required property: Delete the clause, per the per-docstring-clause deletion rule. Tension to note: under the rule-under-test, the clause is a decision with an outside reason, and the pointer to `_pooled_resolved_scope_header` would normally stay. If the dispatcher keeps it, the fix is to keep only that sentence, as a pointer to the doc or symbol that holds the decision, with no restatement of the wrapper's routing. Either way, R1's clause goes.

Prior-decision lines: none were supplied.
