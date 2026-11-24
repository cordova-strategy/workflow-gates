# comment-discipline-reviewer

Scope: 1 file in the diff (`claude/.claude/scripts/transcript_analysis/scope.py`), 1 carrying an in-scope change (the new `print_resolved_scope` docstring). Free-form prompt text set aside: none. The `python-environment-conventions.md` rule that arrived mid-session does not bear on this review.

## R1 [CONCERN] False or unsourced claim

scope.py:680-686, `audit-routing-samples routes it to stderr instead, since its stdout is a JSON (or curation-markdown) data stream`.

- Issue: the docstring names `audit-routing-samples` as the stderr case, which suggests it is the one caller that diverts the header. Grep for `print_resolved_scope(... file=sys.stderr)` finds at least 9 other call sites:
  - analyze-context.py:229, 304, 313
  - pr_cost_export.py:359
  - sessions.py:42
  - turn_shape.py:288, 348
  - audit_routing.py:615
- The claim is true for the one caller it names (audit_routing.py:615 and the `--format json|md` flag at audit_routing.py:852 confirm the JSON/markdown stdout). The set it implies is incomplete.
- Failure mode: a future contributor takes this docstring as the full list of stderr callers.
- Required property: state the general condition ("pass `file=sys.stderr` when stdout carries machine-readable data") and drop the single-caller name, or name the caller as one example. See R3 for the altitude problem with naming it at all.

## R2 [CONCERN] "Used to be X" framing (implicit prior-version comparison)

scope.py:680, `the one-line resolved-scope header cmd_skill_invocation already uses`.

- Issue: "already uses" is extraction-history phrasing. It only makes sense to a reader who knows the header began in `cmd_skill_invocation` and was later lifted out. `cmd_skill_invocation` is now one of roughly 50 callers (skill_invocation.py:164), so naming it as the reference caller is arbitrary and will go stale.
- Required property: drop the sentence's history framing. Keep the durable fact: what the header is, and that it makes scope explicit. Per R4, the code already shows most of this.

## R3 [CONCERN] Wrong altitude / Comment verbosity

scope.py:683-686, the `audit-routing-samples ... corrupt` clause.

- Issue: caller-specific rationale sits in the shared helper's docstring. The call site already carries it at audit_routing.py:614 ("stderr, not stdout: stdout is this subcommand's JSON/markdown data stream."), so the docstring duplicates that comment. This breaks the single-source-of-truth rule.
- Fix: relocate. Leave the call-site comment as the home. In the docstring, keep at most a generic one-clause pointer such as "callers whose stdout is a data stream pass `file=sys.stderr`", then delete the named caller.

## R4 [CONCERN] Multi-fact comment structure / Paragraph readability (with restating)

scope.py:680-686.

- Issue 1, one sentence chains four facts. It carries the purpose, the `file` default, the call-time-vs-import-time rationale in a dash-and-parenthetical aside, and the stderr exception after a semicolon. A reader has to parse the whole sentence to find the instruction ("pass `file=sys.stderr` to keep stdout clean").
- Issue 2, the opening clause ("Print the one-line resolved-scope header") restates the function name and body, which Prose restating the code says to delete.
- Issue 3, the aside is imprecise. It says "resolved at call time, not import time" and then "the stream object process startup captured". A default value binds at function-definition (import) time, not at process startup.
- Fix:
  - Lead with the instruction as its own sentence: "Pass `file=sys.stderr` when stdout carries machine-readable data."
  - Give the one non-obvious fact as a second sentence: "`file` defaults to `None` and resolves to `sys.stdout` at call time, because a `sys.stdout` default would bind the import-time stream and bypass test capture and later reassignment."
  - Delete the purpose sentence and the `cmd_skill_invocation` reference (R2).
  - Keep every fact that survives R1 and R3.
