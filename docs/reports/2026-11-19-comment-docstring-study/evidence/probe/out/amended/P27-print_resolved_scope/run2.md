# comment-discipline-reviewer

Scope: 1 file reviewed (`transcript_analysis/scope.py`), 1 comment in scope (the new `print_resolved_scope` docstring, lines 680-686). No prompt text was set aside.

## R1 [CONCERN] Restating the code

scope.py:680-681 — "Print the one-line resolved-scope header cmd_skill_invocation already uses, so machine-wide vs. --this-repo output is never scope-ambiguous."

Issue: "Print the … header" restates the name and the body (`print(_resolved_scope_header(...))`). "cmd_skill_invocation already uses" is a grep-findable caller fact (skill_invocation.py:44, call at :164). It singles out one of about 50 callers, and "already" is prior-state framing. The scope-ambiguity reason is stated at the `_resolved_scope_header` docstring (scope.py:665-670), which holds the decision.

Required property: delete the sentence. If a pointer is wanted, use "Header text and rationale: `_resolved_scope_header`."

## R2 [CONCERN] Restating the code

scope.py:681-682 — "`file` defaults to stdout".

Issue: this restates `file or sys.stdout` on line 687. The clause is the subject of the kept call-time-resolution decision in the next clause, so it should survive only inside that decision sentence.

Required property: fold it into the decision sentence. For example: "`file` falls back to `sys.stdout` at call time, not import time: a `sys.stdout` default would bind the stream object present at import, bypassing test capture and later reassignment." Keep every fact in that rationale.

## R3 [CONCERN] Restating the code / Wrong altitude

scope.py:684-686 — "audit-routing-samples routes it to stderr instead, since its stdout is a JSON (or curation-markdown) data stream a header line would corrupt."

Issue: this names one caller's choice, which the call site already records (audit_routing.py:614-615, "stderr, not stdout: stdout is this subcommand's JSON/markdown data stream"). Callers are findable by grep. It is also a partial list: `sessions.py:42`, `pr_cost_export.py:359`, `turn_shape.py:288` and `:348` and `analyze-context.py:229` also pass `file=sys.stderr`. A single-caller example in the callee docstring goes stale as callers change.

Required property: delete the sentence, because the call site holds the reason. If the docstring must record why `file` exists, state it once without naming a caller: "`file` exists so subcommands whose stdout is a data stream can send the header to stderr."
