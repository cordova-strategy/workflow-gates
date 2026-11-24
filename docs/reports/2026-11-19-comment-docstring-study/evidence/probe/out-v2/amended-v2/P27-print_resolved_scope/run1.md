# comment-discipline-reviewer

Reviewed 1 file (`scope.py`, `print_resolved_scope` docstring); 1 docstring in scope. Nothing in the dispatch prompt was set aside.

## R1 [CONCERN] Restating the code (also partly false)

`claude/.claude/scripts/transcript_analysis/scope.py:683-686`

Issue: the clause "audit-routing-samples routes it to stderr instead, since its stdout is a JSON (or curation-markdown) data stream a header line would corrupt" restates a caller's choice inside the callee. The reason already sits at the call site (`audit_routing.py:614`, "stderr, not stdout: stdout is this subcommand's JSON/markdown data stream"). Static analysis finds both the `file=sys.stderr` argument and the comment.

It also under-describes the set. Other callers pass `file=sys.stderr`: `sessions.py:42`, `turn_shape.py:288` and `:348`, `pr_cost_export.py:359`, and `analyze-context.py:229`, `:304` and `:313`. Naming one caller reads as the only exception, and the list drifts with every new caller.

Production failure mode: a reader takes `audit-routing-samples` as the sole stderr route, and the docstring goes stale when a caller is added or removed.

Required property: delete the clause. The decision (which stream a subcommand uses) belongs to each caller, and the caller's own comment already holds the reason.

## R2 [CONCERN] Restating the code

`scope.py:680-681`

Issue: "Print the one-line resolved-scope header cmd_skill_invocation already uses, so machine-wide vs. --this-repo output is never scope-ambiguous" has three problems.
- "Print the ... header" restates the function's name and body.
- Singling out `cmd_skill_invocation` is a caller list. `skill_invocation.py:164` is one of about 50 call sites. "Already uses" is also a prior-state comparison that only means something against the PR's history.
- The scope-disclosure purpose is a restatement of what `_resolved_scope_header`'s docstring (`scope.py:661-674`) already holds, since that function builds the header's text.

Required property: delete the sentence. If a pointer is wanted, keep only "see `_resolved_scope_header`".

## R3 [CONCERN] Multi-fact comment structure (on the one clause worth keeping)

`scope.py:681-684`

Issue: the call-time-default decision is the only non-obvious decision in the docstring. A reader cannot tell why the default is `None` rather than `sys.stdout`, which is the reason a design reader needs. It is buried in a sentence chaining a parenthetical, a dash, a second parenthetical clause and a semicolon with an unrelated fact (the stderr route).

Required property: state it as its own sentence, keeping the reason. Suggested replacement for the whole docstring:

```python
    """Print the resolved-scope header (see `_resolved_scope_header`).

    `file` defaults to None and falls back to `sys.stdout` at call time: a `sys.stdout`
    default would bind the stream at import, bypassing test capture and later reassignment.
    """
```

This fix checks clean against the other angles. It states one decision with its reason, holds no PR-defined label and no prior-version framing, and makes no unsourced claim.
