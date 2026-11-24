# comment-discipline-reviewer

Scope: 1 file reviewed (`claude/.claude/scripts/transcript_analysis/scope.py`), 1 added docstring in scope (`print_resolved_scope`). The `python-environment-conventions.md` system-reminder that arrived mid-review has no bearing on this diff and was set aside.

## R1 [CONCERN] Multi-fact comment structure

scope.py:681-686 (the sentence beginning "`file` defaults to stdout").

Issue: one sentence chains four independent facts through a parenthetical, a dash, a semicolon, and a "since" clause:
- `file` defaults to stdout.
- The default is resolved at call time rather than import time.
- Why: a `sys.stdout` default would bind the original stream and bypass test capture and later reassignment.
- audit-routing-samples passes stderr because its stdout is a data stream.

The reader must parse the whole run to find where one fact ends. The parenthetical also says "process startup captured" while the same sentence says "import time". A default binds when `def` executes, which is at import of scope.py, so the two terms name the same moment inconsistently.

Required property: one sentence per fact, with one term for the moment of binding. For example: "`file=None` resolves to `sys.stdout` at call time. A `sys.stdout` default would bind the stream object present at import time, bypassing test capture and later reassignment." Delete the audit-routing-samples fact (R2) and the "defaults to stdout" restatement (R2).

## R2 [CONCERN] Restating the code / single source of truth

scope.py:683-686, "`file` defaults to stdout ... audit-routing-samples routes it to stderr instead, since its stdout is a JSON (or curation-markdown) data stream a header line would corrupt."

Issue, in two parts:
- "`file` defaults to stdout" restates the signature and `file or sys.stdout` on line 687.
- The audit-routing-samples sentence documents one caller's choice inside the callee. That rationale already lives at the call site, audit_routing.py:614: "stderr, not stdout: stdout is this subcommand's JSON/markdown data stream." The claim is accurate, since `--format` is json or md at audit_routing.py:852 and the output paths are at 776 and 783. But the docstring names one of many stderr callers, and a second copy of the rationale will drift. Other callers that pass `file=sys.stderr`: sessions.py:42, turn_shape.py:288 and 348, pr_cost_export.py:359, and analyze-context.py:229, 304 and 313.

Required property: delete the audit-routing-samples sentence and the "defaults to stdout" clause. If a caller-facing hint is wanted, state it generically (for example, "pass `file=sys.stderr` when stdout carries data"), with no per-caller naming. The call-time-resolution rationale from R1 is the only non-obvious fact here worth keeping.

## R3 [CONCERN] "Used to be X" framing / PR-relative reference

scope.py:680, "the one-line resolved-scope header cmd_skill_invocation already uses".

Issue: "already uses" is relative to the moment this function was introduced. It describes the history of the helper's extraction, not how it behaves. It will not parse for a later reader. It also points at one caller out of roughly 45. skill_invocation.py:164 is only one of many `scope.print_resolved_scope` call sites, so the reference is a misleading anchor. This is not strictly false.

Required property: drop the cmd_skill_invocation reference. For example: "Print the one-line resolved-scope header so machine-wide and `--this-repo` output are never scope-ambiguous." The `--this-repo` flag is real (audit_routing.py:85).
