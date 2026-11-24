# comment-discipline-reviewer

Scope note: 1 file reviewed (`claude/.claude/scripts/transcript_analysis/scope.py`), 1 added docstring in scope (`print_resolved_scope`, lines 680-686). I read the diff as handed. A harness-attached rules file (`python-environment-conventions.md`) arrived mid-session. It concerns Python installs, not this review, so I set it aside.

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/scope.py:680-681` and `:682`

Offending text: "Print the one-line resolved-scope header cmd_skill_invocation already uses, so machine-wide vs. --this-repo output is never scope-ambiguous. `file` defaults to stdout (resolved at call time, …)"

Issue: Four clauses state what the code, its name or its call sites already show.
- "Print the one-line resolved-scope header" restates the function name and its one-line body.
- "cmd_skill_invocation already uses" is a call-site fact. Grep finds it (`skill_invocation.py:164`), and it is one of about 50 callers, so singling it out says nothing about a decision.
- "so machine-wide vs. --this-repo output is never scope-ambiguous" is the header's purpose. It is the subject's name, and `_resolved_scope_header`'s docstring (scope.py:660-675) already holds the rationale (the corpus-undercount it prevents). Per single source of truth, point there and do not restate it.
- "`file` defaults to stdout" restates `file or sys.stdout`.

Failure mode: the docstring spends its opening on text a reader can derive in one grep, and the one real decision sits buried in a parenthetical.

Required property: keep only the decision half of the mixed clause (why `file` is `None`-defaulted) and the stderr-routing decision (R3). Delete the rest. Suggested replacement for the whole docstring:

```
"""`file` is None-defaulted, not `sys.stdout`-defaulted, because a `sys.stdout` default would bind the stream at import time, bypassing test capture and later reassignment of `sys.stdout`.

Pass `file=sys.stderr` from a subcommand whose stdout is a data stream (JSON, curation markdown) that a header line would corrupt."""
```

## R2 [CONCERN] Multi-fact comment structure

File: `scope.py:681-686`

Offending text: the second sentence, which chains the default-resolution rule, an em-dash parenthetical about import-time binding, a semicolon, the audit-routing-samples special case, and a "since" clause about its stdout format. The sentence runs about 70 words.

Issue: three independent facts share one sentence with a nested parenthetical and a semicolon, so a reader must parse the whole thing to find where one ends. The facts are the None-default reason, the stderr routing, and the reason stdout would be corrupted. The stderr routing and its reason are tightly coupled, so they may share a sentence. The None-default reason is separate.

Failure mode: the instruction a caller needs (pass `file=sys.stderr` when stdout is data) comes last, after the rationale for an unrelated default.

Required property: one sentence per fact, with the caller-facing instruction first. The replacement in R1 does this.

## R3 [CONCERN] Restating the code (names one call site, not the rule)

File: `scope.py:684-686`

Offending text: "audit-routing-samples routes it to stderr instead, since its stdout is a JSON (or curation-markdown) data stream a header line would corrupt."

Issue: the stderr routing is visible at the call site (`audit_routing.py:615`). The reason (stdout is a data stream) is the decision worth keeping. Naming one subcommand is also an incomplete enumeration. `file=sys.stderr` is also passed by `sessions.py:42`, `turn_shape.py:288` and `:348`, `pr_cost_export.py:359` and `analyze-context.py:229`, `:304`, `:313`. The comment reads as if audit-routing-samples is the only case, and it goes stale as callers change. The audit-routing-samples facts themselves check out (`audit_routing.py:783` prints JSON, `:853` offers an md format).

Failure mode: a reader concludes only one caller needs stderr, or the comment is silently wrong once a caller is added or removed.

Required property: state the rule (a subcommand whose stdout carries data passes `file=sys.stderr`), name no caller. See the R1 replacement.

## R4 [FYI] False or unsourced claim

File: `scope.py:682-684`

Offending text: "a `sys.stdout` default value would bind the stream object process startup captured"

Issue: the sentence contradicts its own earlier phrase, "resolved at call time, not import time". A default argument binds when the `def` runs, which is module import, not process startup. Pytest capture and later reassignment replace `sys.stdout` after that point. The mechanism is Python language semantics, so this draws no repo-based finding. It is still inexact wording.

Failure mode: a reader infers the binding happens before any import, which is wrong.

Required property: say "at import time", as in the R1 replacement.

Prior decisions: none supplied.
